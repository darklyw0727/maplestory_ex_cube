import itertools
import logging
import time
from dataclasses import dataclass

from . import ocr, regions
from .config import Config
from .window import GameWindow

log = logging.getLogger("auto_shine_cube")


@dataclass
class OptionRow:
    index: int
    name: str  # 潛能名稱，例如「魔法攻擊力」
    value: object  # 數值字串，例如"12%"(百分比)或"300"(固定數值)，讀不到時為 None
    click_point_abs: tuple  # client 座標 (x, y)，目前流程用不到點擊，保留供除錯/未來使用

    @property
    def display(self) -> str:
        return f"{self.name} +{self.value}" if self.value is not None else self.name


class AbortError(RuntimeError):
    pass


class Controller:
    def __init__(self, config: Config, window: GameWindow, stop_event=None):
        self.cfg = config
        self.win = window
        self.used_cubes = 0
        self.stop_event = stop_event  # threading.Event，供GUI等外部要求提早停止(可為None)

    # ---------- 基礎工具 ----------

    def _wait(self, sec=None):
        time.sleep(sec if sec is not None else self.cfg.click_delay_sec)

    def _click(self, point_frac):
        w, h = self.win.client_size()
        x, y = regions.scale_point(point_frac, w, h)
        log.debug("click at client(%d, %d)", x, y)
        if not self.cfg.dry_run:
            self.win.click(x, y)
        self._wait()

    def _crop(self, img, box_frac):
        w, h = img.size
        x0, y0, x1, y1 = regions.scale_box(box_frac, w, h)
        return img.crop((x0, y0, x1, y1))

    # ---------- 畫面讀取 ----------

    def _read_currency_label(self) -> str:
        img = self.win.screenshot()
        crop = self._crop(img, self.cfg.regions.currency_label_box)
        raw = ocr.read_row_text(crop)
        return ocr.extract_name(raw)

    def _read_option_rows(self, y_bounds_ref, box_frac, text_x_offset_frac) -> list:
        img = self.win.screenshot()
        w, h = img.size
        x0, y0, x1, y1 = regions.scale_box(box_frac, w, h)
        text_x0 = x0 + regions.scale_x(text_x_offset_frac, w)

        rows = []
        for i in range(len(y_bounds_ref) - 1):
            ry0 = regions.scale_y(y_bounds_ref[i], h)
            ry1 = regions.scale_y(y_bounds_ref[i + 1], h)
            text_row = img.crop((text_x0, ry0, x1, ry1))
            name, value = ocr.split_name_value(ocr.read_row_text(text_row))
            logging.debug(f"OCR輸出潛能結果: {name} {value}")
            cy = (ry0 + ry1) // 2
            cx = x0 + (x1 - x0) // 2
            rows.append(OptionRow(index=i, name=name, value=value, click_point_abs=(cx, cy)))
        return rows

    # ---------- 判斷流程種類 ----------

    def detect_flow(self) -> str:
        """讀取「使用貨幣」欄位，判斷這次要走哪種流程。

        回傳 "simple"(珍貴附加方塊/絕對附加方塊/萌獸方塊) 或 "restore"(恢復附加方塊)。
        完全辨識不到文字(代表面板可能根本沒開/擷取錯位置)才視為致命錯誤，
        辨識到但相似度偏低則只警告、不中止流程，留給使用者自行判斷。
        """
        label = self._read_currency_label()
        candidates = [("simple", t) for t in self.cfg.regions.currency_expected_texts]
        candidates += [("restore", t) for t in self.cfg.regions.restore_currency_expected_texts]
        flow, best_text, best_score = max(
            ((flow, t, ocr.match_score(label, t)) for flow, t in candidates),
            key=lambda triple: triple[2],
        )
        if best_score < 0.15:
            raise AbortError(
                f"讀不到使用貨幣欄位內容(讀到「{label}」)，"
                f"請確認已開啟潛在能力面板並選擇「珍貴附加方塊」「絕對附加方塊」「萌獸方塊」或「恢復附加方塊」。"
            )
        if best_score < 0.4:
            log.warning(
                "使用貨幣欄位讀到「%s」，與「%s」相似度僅%.2f，"
                "若目前面板選的方塊不對請自行中止程式(Ctrl+C)",
                label, best_text, best_score,
            )
        else:
            log.info("已確認目前使用貨幣為「%s」 (相似度%.2f)", best_text, best_score)
        return flow

    def is_goal_met(self, rows) -> bool:
        """rows 只要滿足 target_potentials 任一組合，就算達成目標。

        組合內的項目彼此沒有順序之分，只要能把組合中每個非空字串各自對應到
        一個不重複的 row 即可(空字串不需要對應任何 row)。若用「依序找第一個
        符合的 row 就佔用」的貪婪作法，會在某個 row 同時模糊符合多個目標時，
        因為組合內項目的書寫順序不同而誤判(佔錯 row 導致後面的目標找不到對象)，
        所以改成窮舉所有可能的 row 指派方式，只要存在任一種指派讓每個目標都
        對應到不同的 row，就算符合。
        """
        threshold = self.cfg.ocr_match_threshold
        for combo in self.cfg.target_potentials:
            targets = [t for t in combo if t]
            if len(targets) > len(rows):
                continue
            if any(
                all(ocr.potential_matches(row.name, row.value, target, threshold)
                    for row, target in zip(assignment, targets))
                for assignment in itertools.permutations(rows, len(targets))
            ):
                return True
        return False

    # ---------- 流程1: 珍貴附加方塊 / 絕對附加方塊 / 萌獸方塊 ----------

    def click_reset(self):
        log.debug("點擊「重新設定」")
        self._click(self.cfg.regions.reset_button)
        self._wait(self.cfg.post_action_wait_sec)
        log.debug("點擊重新設定確認彈窗「確認」")
        self._click(self.cfg.regions.reset_confirm_button)
        self._wait(self.cfg.post_action_wait_sec)

    def read_potentials(self):
        """重新設定會立即套用結果，直接顯示3個潛能(無需另外選取/鎖定)。"""
        return self._read_option_rows(
            self.cfg.regions.result_row_y_bounds,
            self.cfg.regions.result_list_box,
            self.cfg.regions.result_text_x_offset,
        )

    def _run_simple_flow(self):
        while True:
            if self.stop_event is not None and self.stop_event.is_set():
                log.info("收到停止要求，結束")
                return "stopped"

            if self.cfg.max_cubes and self.used_cubes >= self.cfg.max_cubes:
                log.info("已達方塊使用上限(%d)，結束", self.cfg.max_cubes)
                return "limit_reached"

            self.click_reset()
            self.used_cubes += 1

            rows = self.read_potentials()
            log.info("第%d次重設後的潛能: %s", self.used_cubes, [r.display for r in rows])

            for r in rows:
                if r.display == "":
                    return "empty"

            if self.is_goal_met(rows):
                log.info("已達成目標潛能，共使用 %d 個方塊，結束程式", self.used_cubes)
                return "success"

    # ---------- 流程2: 恢復附加方塊 ----------

    def read_restore_after_potentials(self):
        """BEFORE/AFTER比較畫面中，讀取右邊AFTER潛能組的3個潛能。"""
        return self._read_option_rows(
            self.cfg.regions.restore_result_row_y_bounds,
            self.cfg.regions.restore_result_list_box,
            self.cfg.regions.restore_result_text_x_offset,
        )

    def click_restore_reroll(self):
        log.debug("點擊「重新設定1次」")
        self._click(self.cfg.regions.restore_reroll_button)
        self._wait(self.cfg.post_action_wait_sec)
        log.debug("點擊「重新設定1次」確認彈窗「確認」(第1個)")
        self._click(self.cfg.regions.restore_reroll_confirm_button)
        self._wait(self.cfg.post_action_wait_sec)
        log.debug("點擊「重新設定1次」確認彈窗「確認」(第2個)")
        self._click(self.cfg.regions.restore_reroll_confirm_button_2)
        self._wait(self.cfg.post_action_wait_sec)

    def click_select_after(self):
        log.debug("點選右邊AFTER潛能組")
        self._click(self.cfg.regions.restore_select_after_point)

    def _run_restore_flow(self):
        # 第一次「重新設定」用來進入 BEFORE/AFTER 比較畫面
        self.click_reset()
        self.used_cubes += 1

        while True:
            if self.stop_event is not None and self.stop_event.is_set():
                log.info("收到停止要求，結束(維持BEFORE，不套用AFTER)")
                return "stopped"

            rows = self.read_restore_after_potentials()
            log.info("第%d次重設後AFTER的潛能: %s", self.used_cubes, [r.display for r in rows])

            if self.is_goal_met(rows):
                log.info("已達成目標潛能，點選AFTER套用，共使用 %d 個方塊，結束程式", self.used_cubes)
                self.click_select_after()
                return "success"

            if self.cfg.max_cubes and self.used_cubes >= self.cfg.max_cubes:
                log.info("已達方塊使用上限(%d)，結束(維持BEFORE，不套用AFTER)", self.cfg.max_cubes)
                return "limit_reached"

            self.click_restore_reroll()
            self.used_cubes += 1

    # ---------- 主流程 ----------

    def run(self):
        self.win.find()
        self.win.ensure_foreground()

        flow = self.detect_flow()
        if flow == "restore":
            log.info("偵測到「恢復附加方塊」，走恢復流程(BEFORE/AFTER比較)")
            return self._run_restore_flow()

        log.info("偵測到「珍貴附加方塊」「絕對附加方塊」或「萌獸方塊」，走一般流程")
        return self._run_simple_flow()

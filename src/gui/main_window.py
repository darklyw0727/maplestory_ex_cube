import json
import logging
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTextEdit, QComboBox, QLabel, QMessageBox,
)

from src import calibration, ocr
from src import hotkey as hotkey_mod
from .calibration_dialog import CalibrationDialog
from .combo_editor import TargetPotentialsEditor
from .worker import AutomationWorker

log = logging.getLogger("auto_shine_cube")

CONFIG_PATH = "config.json"


class _OcrInitWorker(QThread):
    ready = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, ocr_lang: str, parent=None):
        super().__init__(parent)
        self.ocr_lang = ocr_lang

    def run(self):
        try:
            ocr.configure(self.ocr_lang)
            self.ready.emit()
        except Exception as e:  # noqa: BLE001
            # 有些例外(例如 paddlex 的 DependencyError)是被包成通用訊息再用
            # `raise ... from e` 往外丟，真正原因在 __cause__ 裡，一併帶出來
            # 才看得出實際少了什麼。
            detail = str(e)
            cause = e.__cause__
            while cause is not None:
                detail += f"\n  原因: {cause!r}"
                cause = cause.__cause__
            self.failed.emit(detail)


class _HotkeyBridge(QObject):
    """全域熱鍵的callback是在keyboard套件自己的背景執行緒上執行的，不能直接操作
    Qt元件；透過signal轉回GUI主執行緒(跨執行緒emit會自動排入主執行緒的事件佇列)。"""

    triggered = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自動洗珍貴/絕對/萌獸/恢復附加方塊")
        self.resize(760, 680)

        self.config_path = Path(CONFIG_PATH)
        self.config_data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.config_data.pop("// 使用說明", None)
        self.regions_dict = calibration.merge_regions(self.config_data)

        self.automation_worker: AutomationWorker | None = None
        self._run_hotkey_bridge = _HotkeyBridge()
        self._run_hotkey_bridge.triggered.connect(self._on_run_hotkey)
        self._start_hotkey_handle = None
        self._stop_hotkey_handle = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # ---------- 目標潛能組設定區 ----------
        combo_box = QGroupBox("目標潛能組設定")
        combo_layout = QVBoxLayout(combo_box)
        self.combo_editor = TargetPotentialsEditor()
        self.combo_editor.load(self.config_data.get("target_potentials") or [["", "", ""]])
        combo_layout.addWidget(self.combo_editor)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_combo_btn = QPushButton("儲存目標潛能設定")
        self.save_combo_btn.clicked.connect(self._save_target_potentials)
        save_row.addWidget(self.save_combo_btn)
        combo_layout.addLayout(save_row)
        root.addWidget(combo_box, stretch=2)

        # ---------- 開始/停止 ----------
        run_box = QGroupBox("執行")
        run_layout = QHBoxLayout(run_box)
        self.start_btn = QPushButton("開始")
        self.start_btn.setMinimumHeight(36)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        run_layout.addWidget(self.start_btn)
        run_layout.addWidget(self.stop_btn)
        root.addWidget(run_box)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        root.addWidget(self.log_view, stretch=3)

        # ---------- 座標校正功能 ----------
        calib_box = QGroupBox("座標校正")
        calib_layout = QVBoxLayout(calib_box)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("校正流程："))
        self.mode_combo = QComboBox()
        for mode, label in calibration.MODE_LABELS.items():
            self.mode_combo.addItem(label, userData=mode)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, stretch=1)
        calib_layout.addLayout(mode_row)

        full_row = QHBoxLayout()
        self.calibrate_all_btn = QPushButton("全部校正")
        self.calibrate_all_btn.clicked.connect(self._on_calibrate_all)
        full_row.addWidget(self.calibrate_all_btn)
        full_row.addStretch(1)
        calib_layout.addLayout(full_row)

        single_row = QHBoxLayout()
        single_row.addWidget(QLabel("單一按鈕校正："))
        self.step_combo = QComboBox()
        single_row.addWidget(self.step_combo, stretch=1)
        self.calibrate_one_btn = QPushButton("校正選定項目")
        self.calibrate_one_btn.clicked.connect(self._on_calibrate_one)
        single_row.addWidget(self.calibrate_one_btn)
        calib_layout.addLayout(single_row)
        self._reload_step_combo()

        root.addWidget(calib_box)

        self.status_label = QLabel("正在初始化 OCR 引擎，請稍候…")
        root.addWidget(self.status_label)

        self._set_busy(True)
        self._ocr_worker = _OcrInitWorker(self.config_data.get("ocr_lang", "chinese_cht"))
        self._ocr_worker.ready.connect(self._on_ocr_ready)
        self._ocr_worker.failed.connect(self._on_ocr_failed)
        self._ocr_worker.start()

    # ---------- 初始化 ----------

    def _set_busy(self, busy: bool):
        self.start_btn.setEnabled(not busy)
        self.calibrate_all_btn.setEnabled(not busy)
        self.calibrate_one_btn.setEnabled(not busy)

    def _on_ocr_ready(self):
        self.status_label.setText("就緒")
        self._set_busy(False)
        self._register_run_hotkeys()

    def _on_ocr_failed(self, message: str):
        self.status_label.setText("OCR 引擎初始化失敗")
        QMessageBox.critical(self, "初始化失敗", f"PaddleOCR 初始化失敗：\n{message}")

    # ---------- config 存檔 ----------

    def _write_config(self):
        self.config_path.write_text(
            json.dumps(self.config_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _save_target_potentials(self):
        combos = self.combo_editor.to_list()
        if not combos:
            QMessageBox.warning(self, "設定錯誤", "至少需要一組目標潛能(可以三個槽位都留空)。")
            return
        self.config_data["target_potentials"] = combos
        self._write_config()
        self.status_label.setText("已儲存目標潛能設定")

    def _on_region_step_saved(self, key: str):
        self._write_config()
        self._append_log(f"已寫入 config.json -> {key} = {self.regions_dict[key]}")

    # ---------- 座標校正 ----------

    def _current_mode(self) -> str:
        return self.mode_combo.currentData()

    def _reload_step_combo(self):
        self.step_combo.clear()
        for key, kind, label, param in calibration.STEPS_BY_MODE[self._current_mode()]:
            self.step_combo.addItem(f"{key} — {label}", userData=key)

    def _on_mode_changed(self):
        self._reload_step_combo()

    def _prepare_calibration(self):
        """尋找遊戲視窗、檢查參考解析度是否吻合，回傳 hwnd 或 None(使用者取消/視窗不存在)。"""
        window_title = self.config_data.get("window_title", "貓貓TMS")
        hwnd = calibration.find_window(window_title)
        if not hwnd:
            QMessageBox.warning(self, "找不到視窗", f"找不到遊戲視窗「{window_title}」，請先開啟遊戲。")
            return None

        left, top, right, bottom = calibration.client_rect_on_screen(hwnd)
        actual_w, actual_h = right - left, bottom - top
        ref_w, ref_h = self.regions_dict["ref_width"], self.regions_dict["ref_height"]
        if (actual_w, actual_h) != (ref_w, ref_h):
            resp = QMessageBox.question(
                self,
                "解析度不一致",
                f"視窗目前實際大小為 {actual_w}x{actual_h}，但 config.json 的 "
                f"ref_width/ref_height 是 {ref_w}x{ref_h}。\n"
                f"建議先把這兩個值改成 {actual_w}/{actual_h} 再校正，這樣座標最準確。\n\n"
                f"仍要用目前的參考解析度繼續校正嗎？",
            )
            if resp != QMessageBox.StandardButton.Yes:
                return None
        return hwnd

    def _on_calibrate_all(self):
        hwnd = self._prepare_calibration()
        if hwnd is None:
            return
        ref_w, ref_h = self.regions_dict["ref_width"], self.regions_dict["ref_height"]
        steps = calibration.STEPS_BY_MODE[self._current_mode()]
        dialog = CalibrationDialog(
            hwnd, ref_w, ref_h, self.regions_dict, steps, self._on_region_step_saved,
            hotkeys=self._calibration_hotkeys(), parent=self,
        )
        dialog.exec()

    def _on_calibrate_one(self):
        hwnd = self._prepare_calibration()
        if hwnd is None:
            return
        key = self.step_combo.currentData()
        step = calibration.STEP_BY_KEY_BY_MODE[self._current_mode()][key]
        ref_w, ref_h = self.regions_dict["ref_width"], self.regions_dict["ref_height"]
        dialog = CalibrationDialog(
            hwnd, ref_w, ref_h, self.regions_dict, [step], self._on_region_step_saved,
            hotkeys=self._calibration_hotkeys(), parent=self,
        )
        dialog.exec()

    def _calibration_hotkeys(self) -> dict:
        return {
            "confirm": self.config_data.get("calibrate_confirm_hotkey", "ctrl+f3"),
            "skip": self.config_data.get("calibrate_skip_hotkey", "ctrl+f4"),
            "finish": self.config_data.get("calibrate_finish_hotkey", "ctrl+f5"),
        }

    # ---------- 開始/停止熱鍵(全程有效，不受目前是否執行中影響) ----------

    def _register_run_hotkeys(self):
        start_hotkey = self.config_data.get("start_hotkey", "ctrl+f1")
        stop_hotkey = self.config_data.get("stop_hotkey", "ctrl+f2")
        self._start_hotkey_handle = hotkey_mod.register(
            start_hotkey, lambda: self._run_hotkey_bridge.triggered.emit("start")
        )
        self._stop_hotkey_handle = hotkey_mod.register(
            stop_hotkey, lambda: self._run_hotkey_bridge.triggered.emit("stop")
        )
        hints = []
        if self._start_hotkey_handle is not None:
            hints.append(f"開始={start_hotkey}")
        if self._stop_hotkey_handle is not None:
            hints.append(f"停止={stop_hotkey}")
        if hints:
            self._append_log(f"(全域熱鍵已啟用: {', '.join(hints)}，不用切換視窗)")

    def _on_run_hotkey(self, action: str):
        if action == "start" and self.start_btn.isEnabled():
            self._on_start()
        elif action == "stop" and self.stop_btn.isEnabled():
            self._on_stop()

    # ---------- 開始/停止 ----------

    def _append_log(self, text: str):
        self.log_view.append(text)

    def _on_start(self):
        combos = self.combo_editor.to_list()
        if not combos:
            QMessageBox.warning(self, "設定錯誤", "至少需要一組目標潛能(可以三個槽位都留空)。")
            return
        self.config_data["target_potentials"] = combos
        self._write_config()

        stop_hotkey = self.config_data.get("stop_hotkey", "ctrl+f2")
        hotkey_hint = f"或按下熱鍵 {stop_hotkey}(不用切換視窗)，" if stop_hotkey else ""
        resp = QMessageBox.question(
            self,
            "確認開始",
            "即將開始自動操作滑鼠使用方塊。\n"
            "請確認遊戲已開啟、已進入潛在能力面板並選擇了「珍貴附加方塊」「絕對附加方塊」\n"
            "「萌獸方塊」或「恢復附加方塊」其中一種，程式會自動判斷走哪個流程。\n"
            f"執行期間若要緊急停止，可把滑鼠移到螢幕任一角落、點擊「停止」按鈕，{hotkey_hint}"
            "都會在這一輪結束後停止。\n\n"
            "是否開始？",
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.log_view.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.calibrate_all_btn.setEnabled(False)
        self.calibrate_one_btn.setEnabled(False)
        self.status_label.setText("執行中…")

        self.automation_worker = AutomationWorker(str(self.config_path))
        self.automation_worker.log_line.connect(self._append_log)
        self.automation_worker.finished_run.connect(self._on_run_finished)
        self.automation_worker.failed.connect(self._on_run_failed)
        self.automation_worker.start()

    def _on_stop(self):
        if self.automation_worker is not None:
            self.automation_worker.request_stop()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("已送出停止要求，將於這一輪結束後停止…")

    def _reset_run_buttons(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.calibrate_all_btn.setEnabled(True)
        self.calibrate_one_btn.setEnabled(True)

    def _on_run_finished(self, result: str):
        messages = {
            "success": "已達成目標潛能，流程結束。",
            "limit_reached": "已達方塊使用上限，流程結束。",
            "empty": "讀取到空白潛能內容(可能是座標或OCR辨識有問題)，流程已中止。",
            "stopped": "已依要求停止，流程結束。",
            "failsafe": "偵測到 fail-safe(滑鼠移到螢幕角落)，已中止。",
        }
        self._append_log(messages.get(result, f"流程結束：{result}"))
        self.status_label.setText("就緒")
        self._reset_run_buttons()

    def _on_run_failed(self, message: str):
        self._append_log(f"錯誤：{message}")
        QMessageBox.critical(self, "執行失敗", message)
        self.status_label.setText("就緒")
        self._reset_run_buttons()

    def closeEvent(self, event):
        hotkey_mod.unregister(self._start_hotkey_handle)
        hotkey_mod.unregister(self._stop_hotkey_handle)
        super().closeEvent(event)

"""
互動式座標校正工具：依序引導你在遊戲畫面上對應位置移動滑鼠、按 Enter 記錄，
不需要自己輸入名稱，每記錄一項就立刻寫回 config.json 的 regions 區塊。

用法:
    python tools/locate.py [--config config.json]

操作方式:
    程式會照 currency_label_box -> reset_button -> reset_confirm_button ->
    result_list_box -> result_row_y_bounds -> result_text_x_offset 的順序，
    逐項提示你「遊戲畫面該停在哪一步」、「滑鼠要移到哪裡」。
    - 移到定點後直接按 Enter：記錄並寫入 config.json，自動進入下一項。
    - 輸入 s 再 Enter：跳過這一項，保留 config.json 原本的值。
    - 輸入 q 再 Enter：結束校正(已記錄的項目不會遺失)。
"""
import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyautogui
import win32gui

import src.window  # noqa: F401  (import 時會順便設定本程式為 DPI-aware)
from src.regions import DEFAULT_REGIONS


class Quit(Exception):
    pass


def find_window(title):
    return win32gui.FindWindow(None, title) or None


def client_rect_on_screen(hwnd):
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    left, top = win32gui.ClientToScreen(hwnd, (left, top))
    right, bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
    return left, top, right, bottom


def current_ref_point(hwnd, ref_w, ref_h):
    """回傳 (提示文字, (rx, ry) 參考解析度座標 or None)。"""
    sx, sy = pyautogui.position()
    left, top, right, bottom = client_rect_on_screen(hwnd)
    cw, ch = right - left, bottom - top
    cx, cy = sx - left, sy - top
    if cw <= 0 or ch <= 0 or not (0 <= cx <= cw and 0 <= cy <= ch):
        return f"螢幕座標=({sx},{sy})  (滑鼠不在遊戲視窗範圍內)", None
    rx, ry = round(cx / cw * ref_w), round(cy / ch * ref_h)
    return f"視窗內座標=({cx:4d},{cy:4d})  參考解析度座標=({rx:4d},{ry:4d})", (rx, ry)


def live_loop(hwnd, ref_w, ref_h, stop_event, pause_event):
    while not stop_event.is_set():
        if not pause_event.is_set():
            text, _ = current_ref_point(hwnd, ref_w, ref_h)
            print("\r" + text + " " * 10, end="", flush=True)
        time.sleep(0.05)


class Prompter:
    def __init__(self, hwnd, ref_w, ref_h, pause_event):
        self.hwnd = hwnd
        self.ref_w = ref_w
        self.ref_h = ref_h
        self.pause_event = pause_event

    def capture_point(self, instruction):
        """提示使用者移到定點按 Enter，回傳 (rx, ry)；輸入 s 回傳 None(跳過)。"""
        while True:
            self.pause_event.set()
            print()
            print(instruction)
            try:
                cmd = input("  移到定點後按 Enter 記錄 (s=跳過本項 / q=結束校正): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                self.pause_event.clear()
                raise Quit()
            text, point = current_ref_point(self.hwnd, self.ref_w, self.ref_h)
            self.pause_event.clear()
            if cmd == "q":
                raise Quit()
            if cmd == "s":
                return None
            if point is None:
                print(f"  -> 抓不到座標({text})，請確認滑鼠在遊戲視窗內，再試一次")
                continue
            print(f"  -> 記錄到 {text}")
            return point

    def capture_box(self, label):
        tl = self.capture_point(f"【{label}】請將滑鼠移到區域的『左上角』")
        if tl is None:
            return None
        while True:
            br = self.capture_point(f"【{label}】請將滑鼠移到區域的『右下角』")
            if br is None:
                return None
            if br[0] > tl[0] and br[1] > tl[1]:
                return [tl[0], tl[1], br[0], br[1]]
            print("  -> 右下角的x、y都必須比左上角大(框要有實際寬高)，請重新移到右下角")

    def capture_line_bounds(self, label, count):
        """依序記錄 count 個分隔線的 y 座標(嚴格遞增)，回傳 y 值陣列；跳過則回傳 None。"""
        ys = []
        i = 0
        while i < count:
            pt = self.capture_point(f"【{label}】第 {i + 1}/{count} 條分隔線")
            if pt is None:
                return None
            y = pt[1]
            if ys and y <= ys[-1]:
                print(f"  -> 這個位置(y={y})沒有比上一條(y={ys[-1]})更低，請由上往下依序移動，重新記錄這一條")
                continue
            ys.append(y)
            i += 1
        return ys


def save(config_path, data):
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="互動式座標校正工具")
    parser.add_argument("--config", default="config.json", help="設定檔路徑")
    args = parser.parse_args()
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"找不到設定檔 {config_path}，請先確認 config.json 存在。")
        return
    data = json.loads(config_path.read_text(encoding="utf-8"))
    data.setdefault("regions", {})
    regions = {**DEFAULT_REGIONS, **data["regions"]}
    data["regions"] = regions
    window_title = data.get("window_title", "貓貓TMS")
    ref_w, ref_h = regions["ref_width"], regions["ref_height"]

    hwnd = find_window(window_title)
    if not hwnd:
        print(f"找不到遊戲視窗「{window_title}」，請開啟遊戲後重新執行。")
        return

    left, top, right, bottom = client_rect_on_screen(hwnd)
    actual_w, actual_h = right - left, bottom - top
    print(f"已找到遊戲視窗「{window_title}」")
    print(f"視窗目前實際 client area 大小: {actual_w} x {actual_h}")
    if (actual_w, actual_h) != (ref_w, ref_h):
        print(
            f"目前 ref_width/ref_height 是 {ref_w}x{ref_h}，與實際視窗大小不同，"
            f"建議先手動把 config.json 的 ref_width 改成 {actual_w}、ref_height 改成 {actual_h}，"
            f"存檔後重新執行本工具，這樣記錄的座標會跟畫面像素 1:1 對應。"
        )
        try:
            input("仍要用目前的 ref_width/ref_height 繼續嗎？按 Enter 繼續，或 Ctrl+C 取消: ")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return

    print(__doc__)

    stop_event = threading.Event()
    pause_event = threading.Event()
    t = threading.Thread(target=live_loop, args=(hwnd, ref_w, ref_h, stop_event, pause_event), daemon=True)
    t.start()

    prompter = Prompter(hwnd, ref_w, ref_h, pause_event)

    def commit(key, value):
        if value is None:
            print(f"  (保留 {key} 原值: {regions[key]})")
            return
        regions[key] = value
        save(config_path, data)
        print(f"  已寫入 config.json -> {key} = {value}")

    try:
        commit("currency_label_box", prompter.capture_box(
            "step1: 潛在能力面板「方塊」分頁，『使用貨幣』文字欄位"
            "(顯示珍貴附加方塊/絕對附加方塊那格)"))

        commit("reset_button", prompter.capture_point(
            "step2: 同一畫面，『重新設定』按鈕"))

        commit("reset_confirm_button", prompter.capture_point(
            "step3: 按下重新設定後彈出的提示框，『確認』按鈕"))

        commit("result_list_box", prompter.capture_box(
            "step4: 重新設定後立即顯示的3個潛能清單，整塊區域"))

        commit("result_row_y_bounds", prompter.capture_line_bounds(
            "step4: 3個潛能清單，逐條分隔線(由上到下，共4條: 3列的上緣+最後一列下緣)", 4))

        pt = prompter.capture_point(
            "step4: 任一列『文字』開頭處(跳過左邊等級圖示，移到潛能名稱第一個字的左緣)")
        if pt is not None:
            offset = pt[0] - regions["result_list_box"][0]
            commit("result_text_x_offset", offset)
        else:
            print(f"  (保留 result_text_x_offset 原值: {regions['result_text_x_offset']})")

        print("\n全部項目校正完畢！")
    except Quit:
        print("\n已手動結束校正，目前為止記錄的項目已經寫入 config.json。")
    finally:
        stop_event.set()
        t.join(timeout=0.5)

    print("=" * 70)
    print(f"結果已即時寫入 {config_path}，可以直接執行程式或用 dry_run 測試。")
    print("=" * 70)


if __name__ == "__main__":
    main()

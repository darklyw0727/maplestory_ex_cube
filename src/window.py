import ctypes
import time

import mss
import numpy as np
import pyautogui
import win32con
import win32gui
from PIL import Image

pyautogui.FAILSAFE = True  # 游標移到螢幕四個角落任一個即觸發 FailSafeException
pyautogui.PAUSE = 0  # 節奏由 controller 的 click_delay_sec/post_action_wait_sec 自行控制


def ensure_dpi_aware():
    """宣告本程式為 DPI-aware。

    若螢幕顯示縮放不是100%(常見於筆電/高解析度螢幕，例如125%/150%)，未宣告
    DPI-aware 的程式從 win32gui 讀到的視窗座標會是「縮放後」的邏輯座標，但
    pyautogui 移動游標用的是「實際物理像素」座標，兩者對不齊會導致算出來
    的點擊座標整個偏掉(輕則點不準，重則游標跑到画面外、看起來完全沒反應)。

    只有 CLI 進入點(run.py / tools/locate.py)需要呼叫這個函式。PyQt6 GUI
    (gui.py)不要呼叫——Qt6 在 Windows 上預設就會自己設定 per-monitor-v2
    DPI-aware，若這裡搶先設定過，Qt 內部再次嘗試設定時會失敗，印出
    「SetProcessDpiAwarenessContext() failed: 存取被拒」的警告(雖然無害，
    但沒必要，交給 Qt 自己處理最單純)。
    """
    user32 = ctypes.windll.user32
    try:
        # Windows 10 1703+：per-monitor v2，多螢幕/不同縮放時最準確
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except (AttributeError, OSError):
        pass
    try:
        user32.SetProcessDPIAware()
    except OSError:
        pass


class FailSafeAbort(RuntimeError):
    pass


class GameWindow:
    def __init__(self, title: str):
        self.title = title
        self.hwnd = None

    def find(self):
        hwnd = win32gui.FindWindow(None, self.title)
        if not hwnd:
            raise RuntimeError(f"找不到視窗: {self.title}，請確認遊戲已開啟且視窗標題正確")
        self.hwnd = hwnd
        return hwnd

    def ensure_foreground(self):
        if win32gui.IsIconic(self.hwnd):
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
        try:
            win32gui.SetForegroundWindow(self.hwnd)
        except win32gui.error:
            pass
        time.sleep(0.15)

    def client_rect_on_screen(self):
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        left, top = win32gui.ClientToScreen(self.hwnd, (left, top))
        right, bottom = win32gui.ClientToScreen(self.hwnd, (right, bottom))
        return left, top, right, bottom

    def client_size(self):
        left, top, right, bottom = self.client_rect_on_screen()
        return right - left, bottom - top

    def screenshot(self) -> Image.Image:
        left, top, right, bottom = self.client_rect_on_screen()
        with mss.mss() as sct:
            raw = sct.grab({"left": left, "top": top, "width": right - left, "height": bottom - top})
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return img

    def screenshot_np(self) -> np.ndarray:
        return np.array(self.screenshot())

    def client_to_screen(self, x, y):
        left, top, _, _ = self.client_rect_on_screen()
        return left + x, top + y

    def click(self, x, y):
        sx, sy = self.client_to_screen(x, y)
        try:
            pyautogui.click(sx, sy)
        except pyautogui.FailSafeException as e:
            raise FailSafeAbort(str(e)) from e

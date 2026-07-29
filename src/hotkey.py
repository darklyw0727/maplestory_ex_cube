"""全域熱鍵共用小工具：包一層 keyboard 套件，統一錯誤處理，讓 CLI 跟 GUI 都能用
同一組函式註冊/取消「停止」等熱鍵，不管遊戲視窗有沒有 focus 都能觸發。"""
import logging

log = logging.getLogger("auto_shine_cube")


def register(hotkey: str, callback):
    """註冊全域熱鍵，回傳 handle(給 unregister 用)；hotkey 為空或註冊失敗時
    回傳 None(並記錄警告)，不會讓呼叫端出錯。"""
    if not hotkey:
        return None
    try:
        import keyboard
        return keyboard.add_hotkey(hotkey, callback)
    except Exception as e:  # noqa: BLE001 - 熱鍵註冊失敗不該讓整個流程掛掉
        log.warning(
            "註冊熱鍵「%s」失敗(%s)，仍可用滑鼠移到螢幕角落，或程式內的按鈕",
            hotkey, e,
        )
        return None


def unregister(handle):
    if handle is None:
        return
    try:
        import keyboard
        keyboard.remove_hotkey(handle)
    except Exception:  # noqa: BLE001 - 取消註冊失敗只是留下無用的hook，不影響正確性
        pass

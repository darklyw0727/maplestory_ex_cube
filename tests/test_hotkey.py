"""
測試 src/hotkey.py 的 register/unregister 錯誤處理邏輯。用 monkeypatch 換掉
`keyboard` 模組，不需要真的註冊全域熱鍵、不需要開遊戲。
"""
import sys

from src import hotkey


class _FakeKeyboardOK:
    def __init__(self):
        self.added = []
        self.removed = []

    def add_hotkey(self, hk, callback):
        handle = f"handle:{hk}"
        self.added.append((hk, callback))
        return handle

    def remove_hotkey(self, handle):
        self.removed.append(handle)


class _FakeKeyboardBroken:
    def add_hotkey(self, hk, callback):
        raise RuntimeError("模擬註冊失敗(例如熱鍵語法錯誤或系統不支援)")

    def remove_hotkey(self, handle):
        raise RuntimeError("模擬取消註冊失敗")


def _install_fake_keyboard(monkeypatch, fake_module):
    monkeypatch.setitem(sys.modules, "keyboard", fake_module)


def test_register_empty_hotkey_returns_none(monkeypatch):
    _install_fake_keyboard(monkeypatch, _FakeKeyboardOK())

    assert hotkey.register("", lambda: None) is None
    assert hotkey.register(None, lambda: None) is None


def test_register_success_returns_handle_and_calls_add_hotkey(monkeypatch):
    fake = _FakeKeyboardOK()
    _install_fake_keyboard(monkeypatch, fake)

    cb = lambda: None
    handle = hotkey.register("ctrl+f2", cb)

    assert handle == "handle:ctrl+f2"
    assert fake.added == [("ctrl+f2", cb)]


def test_register_failure_returns_none_and_does_not_raise(monkeypatch):
    _install_fake_keyboard(monkeypatch, _FakeKeyboardBroken())

    handle = hotkey.register("bogus++key", lambda: None)

    assert handle is None


def test_unregister_none_handle_is_noop(monkeypatch):
    fake = _FakeKeyboardOK()
    _install_fake_keyboard(monkeypatch, fake)

    hotkey.unregister(None)  # 不應該呼叫 keyboard.remove_hotkey 或丟例外
    assert fake.removed == []


def test_unregister_success_calls_remove_hotkey(monkeypatch):
    fake = _FakeKeyboardOK()
    _install_fake_keyboard(monkeypatch, fake)

    hotkey.unregister("some-handle")
    assert fake.removed == ["some-handle"]


def test_unregister_failure_is_swallowed(monkeypatch):
    _install_fake_keyboard(monkeypatch, _FakeKeyboardBroken())

    hotkey.unregister("some-handle")  # 不應該丟例外

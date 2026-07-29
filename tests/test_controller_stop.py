"""
測試 Controller 的 stop_event 支援(GUI「停止」按鈕用)：兩種流程在收到停止要求
時都應該乾淨地回傳 "stopped"，不需要開啟遊戲、不需要 OCR。用 monkeypatch 取代
實際的滑鼠點擊/畫面讀取。
"""
import threading

import pytest

from src.config import Config
from src.controller import Controller
from src.regions import Regions


def _make_controller(stop_event=None):
    cfg = Config(
        target_potentials=[["", "", ""]],
        log_lv="info",
        max_cubes=0,
        window_title="x",
        ocr_lang="chinese_cht",
        ocr_match_threshold=0.55,
        click_delay_sec=0,
        post_action_wait_sec=0,
        dry_run=True,
        stop_hotkey="",
        regions=Regions({}),
    )
    ctrl = Controller.__new__(Controller)
    ctrl.cfg = cfg
    ctrl.win = None
    ctrl.used_cubes = 0
    ctrl.stop_event = stop_event
    return ctrl


def test_stop_event_none_does_not_break_simple_flow(monkeypatch):
    """stop_event=None(CLI用法)不應該被誤判成「已要求停止」。"""
    ctrl = _make_controller(stop_event=None)
    calls = {"n": 0}

    def fake_click_reset():
        calls["n"] += 1

    monkeypatch.setattr(ctrl, "click_reset", fake_click_reset)
    monkeypatch.setattr(ctrl, "read_potentials", lambda: [])
    monkeypatch.setattr(ctrl, "is_goal_met", lambda rows: calls["n"] >= 2)

    result = ctrl._run_simple_flow()
    assert result == "success"
    assert calls["n"] == 2


def test_simple_flow_stops_immediately_when_stop_event_already_set():
    stop_event = threading.Event()
    stop_event.set()
    ctrl = _make_controller(stop_event=stop_event)

    result = ctrl._run_simple_flow()
    assert result == "stopped"
    assert ctrl.used_cubes == 0  # 完全沒開始跑，不應該用掉方塊


def test_simple_flow_stops_after_stop_event_set_mid_loop(monkeypatch):
    stop_event = threading.Event()
    ctrl = _make_controller(stop_event=stop_event)
    calls = {"n": 0}

    def fake_click_reset():
        calls["n"] += 1
        if calls["n"] >= 2:
            stop_event.set()  # 模拟 GUI 使用者在第2輪跑完後按下「停止」

    monkeypatch.setattr(ctrl, "click_reset", fake_click_reset)
    monkeypatch.setattr(ctrl, "read_potentials", lambda: [])
    monkeypatch.setattr(ctrl, "is_goal_met", lambda rows: False)

    result = ctrl._run_simple_flow()
    assert result == "stopped"
    assert calls["n"] == 2  # 跑完第2輪後，第3輪開始前偵測到停止要求就結束


def test_restore_flow_stops_before_second_reroll(monkeypatch):
    stop_event = threading.Event()
    ctrl = _make_controller(stop_event=stop_event)
    calls = {"reset": 0, "reroll": 0, "select": 0}

    monkeypatch.setattr(ctrl, "click_reset", lambda: calls.__setitem__("reset", calls["reset"] + 1))
    monkeypatch.setattr(ctrl, "read_restore_after_potentials", lambda: [])
    monkeypatch.setattr(ctrl, "is_goal_met", lambda rows: False)

    def fake_reroll():
        calls["reroll"] += 1
        stop_event.set()

    monkeypatch.setattr(ctrl, "click_restore_reroll", fake_reroll)
    monkeypatch.setattr(ctrl, "click_select_after", lambda: calls.__setitem__("select", 1))

    result = ctrl._run_restore_flow()
    assert result == "stopped"
    assert calls["reset"] == 1  # 進入 BEFORE/AFTER 畫面的第一次重設仍會執行
    assert calls["reroll"] == 1  # 跑了一次reroll後停止
    assert calls["select"] == 0  # 不會套用AFTER


def test_restore_flow_does_not_apply_after_when_stopped_before_any_read(monkeypatch):
    # 進入 BEFORE/AFTER 畫面的第一次「重新設定」是無條件執行的(不受 stop_event
    # 影響)，之後才會檢查是否該停止；這裡驗證即使一開始就已經要求停止，也不會
    # 誤點選套用AFTER或去讀取潛能。
    stop_event = threading.Event()
    stop_event.set()
    ctrl = _make_controller(stop_event=stop_event)
    calls = {"reset": 0, "read": 0, "select": 0}

    monkeypatch.setattr(ctrl, "click_reset", lambda: calls.__setitem__("reset", calls["reset"] + 1))
    monkeypatch.setattr(ctrl, "read_restore_after_potentials",
                         lambda: pytest.fail("不應該讀取AFTER潛能") or calls.__setitem__("read", 1))
    monkeypatch.setattr(ctrl, "click_select_after", lambda: calls.__setitem__("select", 1))

    result = ctrl._run_restore_flow()
    assert result == "stopped"
    assert calls == {"reset": 1, "read": 0, "select": 0}

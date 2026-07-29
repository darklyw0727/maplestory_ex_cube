"""
測試 src/calibration.py 的 WizardState 邏輯(point/box/lines/text_offset 四種
校正種類)，以及 STEPS_DEFAULT/STEPS_RESTORE 步驟清單本身的一致性。不需要開啟
遊戲即可執行(用假的 current_position 序列取代真正的 win32gui 讀取)，也不需要
Qt/顯示環境。
"""
from src import calibration
from src.regions import DEFAULT_REGIONS


def _make_state(steps, points, regions=None):
    """建立一個 WizardState，並把 current_position 換成依序回傳 points 的假函式。

    注意：regions 若是空dict(falsy)，不能用 `regions or {}` 這種寫法——那樣在
    傳入空dict時會生出一個「新的」空dict，跟呼叫端保留的參照就不是同一個物件，
    之後對 state.regions 的修改就不會反映到呼叫端手上那個 regions 變數。
    """
    if regions is None:
        regions = {}
    state = calibration.WizardState(hwnd=1, ref_w=1360, ref_h=793, regions=regions, steps=steps)
    it = iter(points)
    state.current_position = lambda: next(it)
    return state


def test_point_step_records_and_advances():
    steps = [("reset_button", "point", "重新設定按鈕", None)]
    regions = {}
    state = _make_state(steps, [(100, 200)], regions)

    ok, err = state.capture()
    assert ok is True
    assert err is None
    assert regions["reset_button"] == [100, 200]
    assert state.finished is True


def test_box_step_requires_two_points_in_order():
    steps = [("currency_label_box", "box", "使用貨幣欄位", None)]
    regions = {}
    state = _make_state(steps, [(10, 20), (110, 60)], regions)

    ok, err = state.capture()  # top-left
    assert ok is False and err is None
    assert not state.finished

    ok, err = state.capture()  # bottom-right
    assert ok is True and err is None
    assert regions["currency_label_box"] == [10, 20, 110, 60]
    assert state.finished


def test_box_step_rejects_invalid_bottom_right():
    steps = [("currency_label_box", "box", "使用貨幣欄位", None)]
    regions = {}
    # 右下角的 x,y 都必須比左上角大；這裡故意給一個不合法的點
    state = _make_state(steps, [(10, 20), (5, 5)], regions)

    state.capture()  # top-left, ok
    ok, err = state.capture()  # invalid bottom-right
    assert ok is False
    assert err is not None
    assert "currency_label_box" not in regions


def test_lines_step_requires_strictly_increasing_y():
    steps = [("result_row_y_bounds", "lines", "分隔線", 3)]
    regions = {}
    state = _make_state(steps, [(0, 10), (0, 5), (0, 30), (0, 50)], regions)

    ok, err = state.capture()  # line1 y=10, ok
    assert ok is False and err is None

    ok, err = state.capture()  # line2 y=5 <= 10, 應該被拒絕
    assert ok is False and err is not None

    ok, err = state.capture()  # line2 y=30, ok
    assert ok is False and err is None

    ok, err = state.capture()  # line3 y=50, 湊滿3條，完成
    assert ok is True and err is None
    assert regions["result_row_y_bounds"] == [10, 30, 50]
    assert state.finished


def test_text_offset_step_relative_to_referenced_box():
    steps = [("result_text_x_offset", "text_offset", "文字偏移", "result_list_box")]
    regions = {"result_list_box": [578, 345, 780, 422]}
    state = _make_state(steps, [(595, 350)], regions)

    ok, err = state.capture()
    assert ok is True and err is None
    assert regions["result_text_x_offset"] == 595 - 578


def test_skip_advances_without_recording():
    steps = [
        ("reset_button", "point", "重新設定按鈕", None),
        ("reset_confirm_button", "point", "確認按鈕", None),
    ]
    regions = {"reset_button": [1, 1], "reset_confirm_button": [2, 2]}
    state = _make_state(steps, [(999, 999)], regions)

    state.skip()
    assert state.step_idx == 1
    assert regions["reset_button"] == [1, 1]  # 未被覆寫

    ok, err = state.capture()
    assert ok is True
    assert regions["reset_confirm_button"] == [999, 999]
    assert state.finished


def test_multi_step_sequence_mixes_kinds():
    steps = [
        ("reset_button", "point", "重新設定按鈕", None),
        ("currency_label_box", "box", "使用貨幣欄位", None),
        ("result_row_y_bounds", "lines", "分隔線", 2),
    ]
    regions = {}
    points = [
        (100, 200),          # point
        (10, 20), (110, 60),  # box tl, br
        (0, 5), (0, 15),      # 2 lines
    ]
    state = _make_state(steps, points, regions)

    while not state.finished:
        state.capture()

    assert regions["reset_button"] == [100, 200]
    assert regions["currency_label_box"] == [10, 20, 110, 60]
    assert regions["result_row_y_bounds"] == [5, 15]


def test_current_position_none_returns_error_without_advancing():
    steps = [("reset_button", "point", "重新設定按鈕", None)]
    regions = {}
    state = _make_state(steps, [None], regions)

    ok, err = state.capture()
    assert ok is False
    assert err is not None
    assert state.step_idx == 0


def test_steps_by_mode_keys_exist_in_default_regions():
    for mode, steps in calibration.STEPS_BY_MODE.items():
        for key, kind, label, param in steps:
            assert key in DEFAULT_REGIONS, f"{mode}模式的欄位「{key}」沒有對應的 DEFAULT_REGIONS 預設值"
            if kind == "text_offset":
                assert param in DEFAULT_REGIONS, f"text_offset欄位「{key}」參照的box「{param}」不存在"


def test_step_by_key_by_mode_matches_steps_by_mode():
    for mode, steps in calibration.STEPS_BY_MODE.items():
        by_key = calibration.STEP_BY_KEY_BY_MODE[mode]
        assert set(by_key.keys()) == {s[0] for s in steps}
        for step in steps:
            assert by_key[step[0]] == step


def test_mode_labels_cover_all_modes():
    assert set(calibration.MODE_LABELS.keys()) == set(calibration.STEPS_BY_MODE.keys())

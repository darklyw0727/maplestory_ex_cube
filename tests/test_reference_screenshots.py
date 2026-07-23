"""
用從 plan.md 附帶的 step4.png 裁出的 tests/fixtures/reset_result_three.png
(重新設定後直接顯示的3個潛能清單，即 plan.md 圖中的紅框範圍)，驗證OCR辨識、
潛能比對(is_goal_met)邏輯是否正確。不需要開啟遊戲即可執行:

    python -m pytest tests/ -v

註：plan.md 附的 step*.png 是完整桌面截圖(用來標示操作步驟給人看)，並非遊戲
client area 的原始像素，所以不能直接套用 config.json 的 regions 比例換算；
這裡改用單獨裁切好、以圖片自身尺寸為準的小型 fixture 座標。
"""
from pathlib import Path

import pytest
from PIL import Image

from src import ocr
from src.config import Config
from src.controller import Controller, OptionRow
from src.regions import Regions

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "reset_result_three.png"

try:
    ocr.configure("chinese_cht")
except Exception as e:  # pragma: no cover - 環境沒裝好時直接略過整份測試
    pytest.skip(f"PaddleOCR 初始化失敗，略過OCR相關測試: {e}", allow_module_level=True)

# fixture 圖片本身就是「3個潛能清單」的區域(222x77)，region座標以圖片自身尺寸
# 為參考解析度，list_box涵蓋整張圖，row bounds切成3等份，text offset跳過左側
# tier圖示(圖示寬約18px)。
FIXTURE_REGIONS = Regions({
    "ref_width": 222,
    "ref_height": 77,
    "result_list_box": [0, 0, 222, 77],
    "result_row_y_bounds": [0, 25, 51, 77],
    "result_text_x_offset": 18,
})

EXPECTED = [
    ("MaxMP", 11),
    ("HP恢復道具及恢復技能效率", 30),
    ("MaxMP", 300),
]


def _make_controller(target_potentials):
    """target_potentials: 多組允許組合的list，每組3個字串，例如
    [["無視怪物防禦率", "", ""]]；為了方便測試呼叫，傳入單一組合(flat list)
    時會自動包成只有一組的巢狀list。"""
    if target_potentials and isinstance(target_potentials[0], str):
        target_potentials = [target_potentials]
    cfg = Config(
        target_potentials=target_potentials,
        log_lv="info",
        max_cubes=0,
        window_title="x",
        ocr_lang="chinese_cht",
        ocr_match_threshold=0.55,
        click_delay_sec=0,
        post_action_wait_sec=0,
        dry_run=True,
        regions=FIXTURE_REGIONS,
    )
    ctrl = Controller.__new__(Controller)
    ctrl.cfg = cfg
    return ctrl


@pytest.fixture(scope="module")
def result_rows():
    ctrl = _make_controller(["", "", ""])

    class FakeWindow:
        def screenshot(self_inner):
            return Image.open(FIXTURE)

    ctrl.win = FakeWindow()
    return ctrl.read_potentials()


def test_reads_three_potentials(result_rows):
    for row, (name, value) in zip(result_rows, EXPECTED):
        score = ocr.match_score(row.name, name)
        assert score >= 0.55, f"row{row.index} name={row.name!r} expected~={name!r} score={score:.2f}"
        assert row.value == value, f"row{row.index} value={row.value!r} expected={value}"


def test_goal_met_when_all_targets_present_name_only(result_rows):
    ctrl = _make_controller(["MaxMP", "", ""])
    assert ctrl.is_goal_met(result_rows) is True


def test_goal_met_requires_exact_value_when_specified(result_rows):
    # MaxMP 在畫面中出現兩次(+11% 和 +300%)，指定其中一個明確數值時應各自符合。
    ctrl_11 = _make_controller(["MaxMP +11%", "", ""])
    assert ctrl_11.is_goal_met(result_rows) is True

    ctrl_300 = _make_controller(["MaxMP +300%", "", ""])
    assert ctrl_300.is_goal_met(result_rows) is True

    # 指定一個畫面上不存在的數值則不算達成
    ctrl_fail = _make_controller(["MaxMP +50%", "", ""])
    assert ctrl_fail.is_goal_met(result_rows) is False


def test_goal_not_met_when_target_absent(result_rows):
    ctrl = _make_controller(["物理攻擊力", "", ""])
    assert ctrl.is_goal_met(result_rows) is False


def test_goal_met_if_any_combo_matches(result_rows):
    # 最終3個潛能是 MaxMP+11% / HP恢復道具及恢復技能效率+30% / MaxMP+300。
    # 設定多組允許組合，只要其中一組被滿足就算達成，即使其他組合完全對不上。
    ctrl = _make_controller([
        ["物理攻擊力", "", ""],  # 這組對不上
        ["HP恢復道具及恢復技能效率", "", ""],  # 這組對得上
    ])
    assert ctrl.is_goal_met(result_rows) is True


def test_goal_not_met_when_no_combo_matches(result_rows):
    ctrl = _make_controller([
        ["物理攻擊力", "", ""],
        ["STR", "LUK", ""],
    ])
    assert ctrl.is_goal_met(result_rows) is False


def test_goal_met_independent_of_target_order_within_combo():
    # 「魔法攻擊力」同時模糊符合"攻擊力"(無指定數值)與"魔法攻擊力 +12%"(指定數值)
    # 兩個目標。若用貪婪演算法依序把每個目標配對到第一個符合的row，"攻擊力"
    # 排在前面時會先佔走「魔法攻擊力」那個row，導致後面的"魔法攻擊力 +12%"找
    # 不到row可配對而誤判失敗——即使實際上讓「物理攻擊力」配"攻擊力"、
    # 「魔法攻擊力」配"魔法攻擊力 +12%"就能兩個都符合。這裡驗證同一組目標
    # 不論寫的順序為何，結果都應該一致(True)。
    rows = [
        OptionRow(0, "魔法攻擊力", 12, (0, 0)),
        OptionRow(1, "物理攻擊力", 9, (0, 0)),
        OptionRow(2, "STR", 9, (0, 0)),
    ]
    order_a = _make_controller(["攻擊力", "魔法攻擊力 +12%", ""])
    order_b = _make_controller(["魔法攻擊力 +12%", "攻擊力", ""])
    assert order_a.is_goal_met(rows) is True
    assert order_b.is_goal_met(rows) is True

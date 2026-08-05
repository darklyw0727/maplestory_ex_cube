import json
from dataclasses import dataclass, field
from pathlib import Path

from .regions import Regions


@dataclass
class Config:
    target_potentials: list
    log_lv: str
    max_cubes: int
    window_title: str
    ocr_lang: str
    ocr_match_threshold: float
    click_delay_sec: float
    post_action_wait_sec: float
    dry_run: bool
    stop_hotkey: str
    delay_currency_expected_delay_time: float
    regions: Regions

    def __post_init__(self):
        # target_potentials 是多組「允許的目標組合」，每組固定3個槽位(可含空字串)，
        # 只要最終3個潛能滿足其中任一組合，就算達成目標。
        if not self.target_potentials:
            raise ValueError("target_potentials 至少需要一組(可以是三個空字串)")
        for combo in self.target_potentials:
            if len(combo) > 3:
                raise ValueError(f"target_potentials 每組最多只能設定3個字串，收到: {combo}")
            while len(combo) < 3:
                combo.append("")


def load_config(path: str = "config.json") -> Config:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.pop("// 使用說明", None)
    return Config(
        target_potentials=[list(combo) for combo in data["target_potentials"]],
        log_lv=str(data["log_lv"]),
        max_cubes=int(data.get("max_cubes", 0)),
        window_title=data.get("window_title", "貓貓TMS"),
        delay_currency_expected_delay_time=float(data.get("delay_currency_expected_delay_time", 2)),
        ocr_lang=data.get("ocr_lang", "chinese_cht"),
        ocr_match_threshold=float(data.get("ocr_match_threshold", 0.55)),
        click_delay_sec=float(data.get("click_delay_sec", 0.35)),
        post_action_wait_sec=float(data.get("post_action_wait_sec", 0.6)),
        dry_run=bool(data.get("dry_run", False)),
        stop_hotkey=data.get("stop_hotkey", "ctrl+f2"),
        regions=Regions(data.get("regions", {})),
    )

import difflib
import re

import numpy as np
from paddleocr import PaddleOCR
from PIL import Image
import logging

_TRAILING_NUMBER_RE = re.compile(r"([+＋\-－]?\s*\d+)\s*(%)?\s*\.?\s*$")

_engine: PaddleOCR = None


def configure(lang: str = "chinese_cht"):
    global _engine
    # enable_mkldnn=False: 部分 paddlepaddle 版本用 mkldnn(oneDNN) CPU加速跑這裡用到
    # 的偵測模型會直接丟出 NotImplementedError(PIR執行器不支援)，關掉才能穩定執行。
    # 其餘幾個 use_xxx=False 的前處理階段(文件方向/去扭曲/文字列方向)是給掃描文件
    # 用的，我們裁切的都是端正的遊戲UI小圖，關掉可以省下對應模型的下載與推論時間。
    _engine = PaddleOCR(
        lang=lang,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
    )


def read_row_text(img: Image.Image) -> str:
    """辨識單一列裁切區域內的文字。

    潛能名稱與數值有時會被偵測成分開的兩段(例如「魔法攻擊力」與「+12%」)，
    依偵測框由左到右排序後拼接，確保順序正確。
    """
    arr = np.array(img.convert("RGB"))
    result = _engine.predict(arr)
    if not result:
        return ""
    r = result[0]
    texts = list(r.get("rec_texts") or [])
    boxes = r.get("rec_boxes")
    if boxes is not None and len(boxes) == len(texts):
        order = sorted(range(len(texts)), key=lambda i: boxes[i][0])
        texts = [texts[i] for i in order]
    ret = " ".join(t.strip() for t in texts if t.strip())
    logging.debug(f"read_row_text: {ret}")
    return ret


def clean_text(raw_text: str) -> str:
    return raw_text.strip()


def extract_name(raw_text: str) -> str:
    """去除數值(+9%等)，只留下潛能名稱部分(不含數值)。"""
    name, _ = split_name_value(raw_text)
    return name


def split_name_value(raw_text: str):
    """將文字拆成 (名稱, 數值or None)。

    數值保留原本是否帶"%"的資訊(回傳字串如"13%"或"300")，因為同一個數字
    有無百分比代表不同的潛能(例如"MaxMP +300"是固定數值、"無視怪物防禦率
    +30%"是百分比)，兩者不能視為相同數值。
    """
    text = raw_text.strip()
    m = _TRAILING_NUMBER_RE.search(text)
    if not m:
        return text, None
    name = text[: m.start()].strip()
    digits = re.sub(r"\D", "", m.group(1))
    if not digits:
        return name, None
    value = digits + "%" if m.group(2) else digits
    return name, value


def match_score(candidate: str, target: str) -> float:
    if not target:
        return 0.0
    candidate = candidate.replace(" ", "")
    target = target.replace(" ", "")
    if not candidate:
        return 0.0
    if target in candidate or candidate in target:
        shorter = min(len(target), len(candidate))
        longer = max(len(target), len(candidate))
        return shorter / longer
    return difflib.SequenceMatcher(None, candidate, target).ratio()


def potential_matches(candidate_name: str, candidate_value, target_text: str, threshold: float) -> bool:
    """比對「潛能選項(名稱+數值)」與 config 設定的「目標潛能文字」。

    若目標文字有指定數值(例如"魔法攻擊力 +12%")，數值(含是否帶"%")必須完全
    相同才算符合，名稱部分則用模糊比對容忍OCR誤差；若目標文字沒有指定數值
    (只寫"魔法攻擊力")，則只比對名稱、忽略數值，維持彈性。
    """
    t_name, t_value = split_name_value(target_text)
    if match_score(candidate_name, t_name) < threshold:
        return False
    if t_value is None:
        return True
    return candidate_value is not None and candidate_value == t_value

"""
所有座標皆以「參考解析度」(ref_width x ref_height，對應 plan.md 附圖 step1~step4
的視窗 client area 尺寸) 為基準，記錄在 config.json 的 "regions" 區塊(單位是該
參考解析度下的像素，不是比例)。執行時依實際擷取到的視窗 client area 尺寸等比例
換算，藉此對視窗大小的些微差異有一定容錯度。

流程只有4個畫面(見 plan.md)：
step1 使用貨幣欄位(currency_label_box) -> step2「重新設定」按鈕(reset_button)
-> step3 確認彈窗按鈕(reset_confirm_button) -> step4 重設後直接出現的3個潛能
(result_list_box/result_row_y_bounds/result_text_x_offset)，沒有「6選3」的
中間步驟，也不需要另外點擊「使用」或「離開」。

若遊戲改版、UI位置跑掉，或想在不同解析度下重新校正，可直接修改 config.json 的
regions 區塊，不需要改程式碼，或執行 tools/locate.py 互動校正。
"""

DEFAULT_REGIONS = {
    "ref_width": 1360,
    "ref_height": 793,
    # step1: "使用貨幣" 欄位中間灰色藥丸按鈕文字區域，用來確認目前選擇的是
    # 「珍貴附加方塊」或「絕對附加方塊」其中之一
    "currency_label_box": [865, 540, 1128, 564],
    "currency_expected_texts": ["珍貴附加方塊", "絕對附加方塊"],
    # step2: 「重新設定」按鈕
    "reset_button": [997, 762],
    # step3: 重新設定確認彈窗的「確認」按鈕(按下後立即套用新的潛在能力)
    "reset_confirm_button": [632, 487],
    # step4: 重新設定後直接顯示的3個潛能清單方塊，含每一列的上下邊界
    # (共4條分隔線，切出3列)，用來讀取結果比對目標潛能
    "result_list_box": [578, 345, 780, 422],
    "result_row_y_bounds": [347, 372, 397, 420],
    # 潛能文字起始位置，相對於整列左緣的 x 偏移 (跳過 tier 圖示)
    "result_text_x_offset": 17,
}


class Regions:
    """把 config.json 的 regions 區塊(參考解析度像素)轉成執行時要用的比例(0~1)。"""

    def __init__(self, data: dict):
        merged = {**DEFAULT_REGIONS, **data}
        ref_w = merged["ref_width"]
        ref_h = merged["ref_height"]

        def box(key):
            x0, y0, x1, y1 = merged[key]
            if x1 <= x0 or y1 <= y0:
                raise ValueError(
                    f"regions.{key} 的座標無效: {merged[key]}。"
                    f"必須是 [x0, y0, x1, y1] 且 x1>x0、y1>y0(框需要有實際寬高)，"
                    f"請用 tools/locate.py 重新分別記錄左上角與右下角兩個不同的點。"
                )
            return (x0 / ref_w, y0 / ref_h, x1 / ref_w, y1 / ref_h)

        def point(key):
            x, y = merged[key]
            return (x / ref_w, y / ref_h)

        def y_bounds(key):
            values = merged[key]
            if any(b <= a for a, b in zip(values, values[1:])):
                raise ValueError(
                    f"regions.{key} 的分隔線座標無效: {values}。"
                    f"必須由小到大嚴格遞增(每一列都要有實際高度)，請用 tools/locate.py 重新校正。"
                )
            return [y / ref_h for y in values]

        self.currency_label_box = box("currency_label_box")
        self.currency_expected_texts = list(merged["currency_expected_texts"])
        self.reset_button = point("reset_button")
        self.reset_confirm_button = point("reset_confirm_button")
        self.result_list_box = box("result_list_box")
        self.result_row_y_bounds = y_bounds("result_row_y_bounds")
        self.result_text_x_offset = merged["result_text_x_offset"] / ref_w


def scale_point(point_frac, client_w, client_h):
    fx, fy = point_frac
    return int(round(fx * client_w)), int(round(fy * client_h))


def scale_box(box_frac, client_w, client_h):
    x0, y0, x1, y1 = box_frac
    return (
        int(round(x0 * client_w)),
        int(round(y0 * client_h)),
        int(round(x1 * client_w)),
        int(round(y1 * client_h)),
    )


def scale_x(x_frac, client_w):
    return int(round(x_frac * client_w))


def scale_y(y_frac, client_h):
    return int(round(y_frac * client_h))

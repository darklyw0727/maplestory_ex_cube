# 自動洗珍貴/絕對/恢復附加方塊

依 [plan.md](plan.md) 實作，讀取遊戲畫面(視窗標題預設「貓貓TMS」)並自動操作滑鼠，
重複使用方塊直到附加潛在能力符合設定的目標，或用完設定的方塊上限為止。

程式會依畫面上「使用貨幣」目前選擇的方塊名稱，自動判斷要走哪一種流程，不需要
額外設定：

- **珍貴附加方塊 / 絕對附加方塊**：每次「重新設定」立即套用新的3條潛能，直接
  判斷是否達成目標。
- **恢復附加方塊**：每次「重新設定」會顯示 BEFORE(重設前) / AFTER(重設後) 兩組
  潛能讓你選擇套用哪一組，程式只看右邊AFTER，符合目標就點選套用，不符合就點
  「重新設定1次」再骰一輪。

## 安裝

滑鼠控制用 [pyautogui](https://pyautogui.readthedocs.io/)，畫面文字辨識用
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)。PaddleOCR 底層的
`paddlepaddle` 目前還沒有 Python 3.14 的預編譯版本，**必須用 Python 3.13 (或更早)**：

安裝方式可選用python虛擬環境或python系統環境，不希望此程式所使用到的library影響到日常開發環境時請使用python虛擬環境，一般使用者則可以將library直接安裝在系統環境中

### Python系統環境安裝
```
pip install -r requirements.txt
```

### Python虛擬環境安裝
```
py -3.13 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

第一次執行時 PaddleOCR 會自動下載偵測/辨識模型(存到 `~/.paddlex/official_models/`)，
需要網路連線，之後就會用本機快取，不用再下載。

## 設定 (config.json)

```json
{
  "target_potentials": [
    ["魔法攻擊力", "", ""],
    ["物理攻擊力", "", ""]
  ],
  "log_lv": "info",
  "max_cubes": 0,
  "window_title": "貓貓TMS",
  "ocr_lang": "chinese_cht",
  "ocr_match_threshold": 0.55,
  "click_delay_sec": 0.35,
  "post_action_wait_sec": 0.6,
  "dry_run": false,
  "regions": { "...": "所有按鈕/讀取區域座標，見下方「座標校正」" }
}
```

珍貴/絕對附加方塊流程很單純：每按一次「重新設定」就會消耗1個方塊、立即套用新
的3條附加潛在能力，沒有「6選3」之類的中間選擇步驟，也不需要另外按「使用」或
「離開」——判斷達成目標後程式直接結束即可(此時畫面上已經是套用好的結果)。

恢復附加方塊流程則是：第一次「重新設定」進入 BEFORE/AFTER 比較畫面後，之後每
判斷一次AFTER都算用掉1個方塊；若AFTER符合目標，程式會點選AFTER套用並結束；若
用完 `max_cubes` 仍未達成目標，程式會直接結束、不會點選套用(維持BEFORE，也就
是沒有套用任何重新設定的結果)。

- `target_potentials`：**多組允許的目標組合**組成的list，每組固定3個字串槽位
  (空字串代表「除了其他目標潛能外的任意潛能」)，**list中排越前面的組合優先權
  越高**。每次按下「重新設定」後畫面上的3個潛能，只要滿足**其中任一組合**就算
  達成目標、程式自動結束；不滿足則繼續下一次重新設定，直到達成目標或用完
  `max_cubes`。上面範例代表優先追求「魔法攻擊力」，只要這3個潛能裡沒有魔法攻擊力
  才會去比對「物理攻擊力」那組。
  - 每個字串可只寫名稱，例如 `"魔法攻擊力"`：只比對名稱，不限數值。
  - 也可以連數值一起寫，例如 `"魔法攻擊力 +12%"`：數值必須完全相同才算符合(包含
    有無`%`，例如`+300`和`+300%`視為不同數值)，用來區分同名但不同數值的重複
    選項(例如"無視怪物防禦率"同時出現 +30% 和 +40% 兩種)，或名稱相同但一個是
    百分比、一個是固定數值的潛能(例如"MaxMP"同時出現 +11% 和 +300 兩種)。
- `log_lv`：`"debug"` 會印出每次點擊的詳細座標，其餘(含預設)只印重點流程訊息。
- `max_cubes`：最多使用幾個方塊，`0` 代表不限制。
- `dry_run`：`true` 時只讀取畫面、印出判斷結果，不會真的點擊滑鼠(用來乾跑測試座標/OCR)。

## 座標校正 (regions)

所有滑鼠點擊/畫面讀取用的座標都放在 `config.json` 的 `regions` 區塊，不用改程式碼。
座標是以 `ref_width` x `ref_height`(預設 1360x793，對應 plan.md 附圖的視窗大小)這個
「參考解析度」下的像素記錄，執行時會依實際視窗大小等比例換算，因此視窗大小只要沒
差異太大都還算容錯。各欄位意義：

| 欄位 | 說明 |
| --- | --- |
| `currency_label_box` | 讀取「使用貨幣」欄位文字的區域，**兩種流程共用**同一個畫面位置 |
| `currency_expected_texts` / `restore_currency_expected_texts` | 可接受的方塊名稱：前者是珍貴附加方塊/絕對附加方塊(走一般流程)，後者是恢復附加方塊(走恢復流程)；程式讀取使用貨幣文字後兩邊比對，自動決定走哪個流程 |
| `reset_button` / `reset_confirm_button` | 「重新設定」按鈕與其確認彈窗的「確認」按鈕，**兩種流程共用**(按下後立即套用新的潛在能力，或進入恢復流程的BEFORE/AFTER比較畫面) |
| `result_list_box` / `result_row_y_bounds` / `result_text_x_offset` | (一般流程)重新設定後直接顯示的3個潛能清單方框、其中4條分隔線(切出3列)、每列文字起始位置相對整列左緣的x偏移(跳過tier圖示) |
| `restore_result_list_box` / `restore_result_row_y_bounds` / `restore_result_text_x_offset` | (恢復流程)BEFORE/AFTER比較畫面中，右邊AFTER潛能組的清單方框/分隔線/文字x偏移，意義同上 |
| `restore_select_after_point` | (恢復流程)AFTER符合目標時，點選套用AFTER潛能組的位置 |
| `restore_reroll_button` / `restore_reroll_confirm_button` / `restore_reroll_confirm_button_2` | (恢復流程)AFTER不符合目標時要點的「重新設定1次」按鈕，與其後依序跳出的**兩個**確認彈窗各自的「確認」按鈕 |

若遊戲改版、UI位置跟預設值對不上、或想確認目前設定是否準確，可執行座標校正工具：

```
.venv\Scripts\python tools/locate.py
```

預設(`--mode default`)校正一般流程(珍貴/絕對附加方塊)用的欄位，依
`currency_label_box` → `reset_button` → `reset_confirm_button` →
`result_list_box` → `result_row_y_bounds` → `result_text_x_offset` 的順序。

若要校正恢復附加方塊流程，加上 `--mode restore`：

```
.venv\Scripts\python tools/locate.py --mode restore
```

依 `currency_label_box` → `reset_button` → `reset_confirm_button` →
`restore_result_list_box` → `restore_result_row_y_bounds` →
`restore_result_text_x_offset` → `restore_select_after_point` →
`restore_reroll_button` → `restore_reroll_confirm_button` →
`restore_reroll_confirm_button_2` 的順序；前3項與
一般流程共用同一個畫面位置，若已經校正過且畫面沒變，可以輸入 `s` 跳過。

逐項提示你「遊戲畫面該停在哪一步、滑鼠要移到哪裡」；移到定點後直接按 Enter
就會記錄並立刻寫回 `config.json`，自動進入下一項，不用自己輸入名稱。也支援
輸入 `s` 跳過該項(保留原值)、`q` 結束校正(已記錄的項目不會遺失)。

## 執行

1. 先手動在遊戲中開啟潛在能力面板、切到「方塊」分頁並選擇「珍貴附加方塊」
   「絕對附加方塊」或「恢復附加方塊」其中一種(對應 plan.md 步驟1)，程式會自動
   判斷走哪個流程。
2. 執行：

```
.venv\Scripts\python run.py
```

3. 依提示輸入 `y` 開始，程式會倒數3秒後開始自動操作。
4. **緊急停止**：執行期間把滑鼠移到螢幕**任一角落**即會觸發 pyautogui 的 fail-safe
   中止(`pyautogui.FAILSAFE`)；也可以直接 Ctrl+C。
5. 點擊完不會把滑鼠移回原位，游標會停在最後一次點擊的位置。

執行紀錄會寫在 `logs/run_*.log`。

## 測試（不需要開遊戲）

`tests/test_reference_screenshots.py` 用從 plan.md 附的截圖裁出的
`tests/fixtures/*.png`(重新設定後3個潛能清單、AFTER潛能清單、兩種流程的使用
貨幣文字等紅框範圍)驗證 OCR 辨識、流程判斷(`detect_flow`)、目標比對邏輯是否
正確：

```
.venv\Scripts\python -m pytest tests/ -v
```

## 已知限制

- 所有座標是用參考截圖(約 1360x793 視窗大小)校準、以比例換算，若遊戲視窗大小差異
  太大可能會點不準，建議維持接近該大小的視窗，或用 `tools/locate.py` 重新校正。
- PaddleOCR 對繁體字偶爾會辨識成筆劃相近的簡體/日文變體字(例如「擊」讀成「撃」、
  「視」讀成「视」)，但比對邏輯本來就用模糊比對容忍1~2個字差異，不影響判斷。
- 已在真實遊戲視窗上實際測試調整過座標與流程；若換了新的視窗大小/位置或遊戲改版
  導致點不準，先用 `tools/locate.py` 重新校正，仍有問題建議先開 `dry_run: true`
  觀察 log 判斷是哪個步驟不對。

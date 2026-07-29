# 自動洗珍貴/絕對/萌獸/恢復附加方塊

依 [plan.md](plan.md) 實作，讀取遊戲畫面(視窗標題預設「貓貓TMS」)並自動操作滑鼠，
重複使用方塊直到附加潛在能力符合設定的目標，或用完設定的方塊上限為止。

程式會依畫面上「使用貨幣」目前選擇的方塊名稱，自動判斷要走哪一種流程，不需要
額外設定：

- **珍貴附加方塊 / 絕對附加方塊 / 萌獸方塊**：三者操作流程完全一致，每次「重新
  設定」立即套用新的3條潛能，直接判斷是否達成目標。
- **恢復附加方塊**：每次「重新設定」會顯示 BEFORE(重設前) / AFTER(重設後) 兩組
  潛能讓你選擇套用哪一組，程式只看右邊AFTER，符合目標就點選套用，不符合就點
  「重新設定1次」再骰一輪。

使用上分成三個步驟，以下依序說明：**1. 架設 Python 環境 → 2. 設定 config.json
→ 3. 啟動程式(先用 `tools/locate.py` 校正座標，再執行 `run.py`)**。

也可以改用整合了目標潛能設定、座標校正、執行於一體的 PyQt6 圖形介面，見下方
「圖形介面 (GUI)」，環境還是要先照第1步架好，之後就不需要再手動編輯
`config.json` 或跑 `tools/locate.py` 這兩支指令了。

## 1. 架設 Python 環境

滑鼠控制用 [pyautogui](https://pyautogui.readthedocs.io/)，畫面文字辨識用
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)。PaddleOCR 底層的
`paddlepaddle` 目前還沒有 Python 3.14 的預編譯版本，**必須用 Python 3.13 (或更早)**。

安裝方式可選用 Python 虛擬環境或 Python 系統環境：不希望此程式用到的 library
影響到日常開發環境時，請使用虛擬環境；一般使用者則可以將 library 直接安裝在
系統環境中。

### 方式A：安裝在 Python 系統環境

```
pip install -r requirements.txt
```

### 方式B：安裝在 Python 虛擬環境(建議)

```
py -3.13 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

之後執行本專案所有指令(`tools/locate.py`、`run.py`、`pytest`)都要改用
`.venv\Scripts\python` 而不是系統的 `python`，範例都以虛擬環境路徑表示。

第一次執行時 PaddleOCR 會自動下載偵測/辨識模型(存到 `~/.paddlex/official_models/`)，
需要網路連線，之後就會用本機快取，不用再下載。

## 2. 設定 config.json

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
  "start_hotkey": "ctrl+f1",
  "stop_hotkey": "ctrl+f2",
  "calibrate_confirm_hotkey": "ctrl+f3",
  "calibrate_skip_hotkey": "ctrl+f4",
  "calibrate_finish_hotkey": "ctrl+f5",
  "regions": { "...": "所有按鈕/讀取區域座標，見下方「座標校正」，設定時不用管這塊" }
}
```

珍貴/絕對附加方塊/萌獸方塊流程很單純：每按一次「重新設定」就會消耗1個方塊、
立即套用新的3條附加潛在能力，沒有「6選3」之類的中間選擇步驟，也不需要另外按
「使用」或「離開」——判斷達成目標後程式直接結束即可(此時畫面上已經是套用好
的結果)。

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
- `window_title`：遊戲視窗標題，預設「貓貓TMS」，若你的視窗標題不同請修改這裡。
- `dry_run`：`true` 時只讀取畫面、印出判斷結果，不會真的點擊滑鼠(用來乾跑測試座標/OCR)。
- `start_hotkey` / `stop_hotkey`：全域開始/停止熱鍵(語法例如 `"f8"`、`"ctrl+alt+q"`)，
  不管遊戲視窗有沒有 focus 都能觸發；`start_hotkey` 只在 GUI 有作用(等同點擊
  「開始」)，CLI 沒有「啟動中」以外的待機狀態，不需要開始熱鍵。停止會在目前這一輪
  跑完後收尾(一般流程：這次重新設定判斷完就停；恢復流程：這次AFTER判斷完就停、
  不會套用)，不是立即中斷。設成空字串 `""` 則不註冊該熱鍵，停止仍可改用滑鼠移到
  螢幕角落、Ctrl+C(CLI)或視窗裡的按鈕(GUI)。
- `calibrate_confirm_hotkey` / `calibrate_skip_hotkey` / `calibrate_finish_hotkey`：
  只有 GUI 的座標校正對話框會用到，分別對應「記錄」「跳過本項」「結束」。校正時
  滑鼠要停在遊戲畫面上的定點，**務必用這三個熱鍵觸發，不要點對話框裡的按鈕**——
  點按鈕會讓滑鼠先移到按鈕上，記錄到的會是按鈕座標而不是遊戲畫面上的定點。
- `regions`：所有滑鼠點擊/畫面讀取用的座標，設定 config 時通常不用手動編輯這塊，
  下一節會說明如何用 `tools/locate.py` 自動校正並寫入。

## 3. 啟動程式

啟動分兩步：**先用 `tools/locate.py` 校正座標，再執行 `run.py`**。座標沒校正過
(或跟預設值差異太大)，滑鼠會點不準，所以第一次使用務必先做校正。

### 3.1 校正座標 (`tools/locate.py`)

所有滑鼠點擊/畫面讀取用的座標都放在 `config.json` 的 `regions` 區塊，不用改
程式碼。座標是以 `ref_width` x `ref_height`(預設 1360x793，對應 plan.md 附圖
的視窗大小)這個「參考解析度」下的像素記錄，執行時會依實際視窗大小等比例換算，
因此視窗大小只要沒差異太大都還算容錯。各欄位意義：

| 欄位 | 說明 |
| --- | --- |
| `currency_label_box` | 讀取「使用貨幣」欄位文字的區域，**兩種流程共用**同一個畫面位置 |
| `currency_expected_texts` / `restore_currency_expected_texts` | 可接受的方塊名稱：前者是珍貴附加方塊/絕對附加方塊/萌獸方塊(走一般流程)，後者是恢復附加方塊(走恢復流程)；程式讀取使用貨幣文字後兩邊比對，自動決定走哪個流程 |
| `reset_button` / `reset_confirm_button` | 「重新設定」按鈕與其確認彈窗的「確認」按鈕，**兩種流程共用**(按下後立即套用新的潛在能力，或進入恢復流程的BEFORE/AFTER比較畫面) |
| `result_list_box` / `result_row_y_bounds` / `result_text_x_offset` | (一般流程)重新設定後直接顯示的3個潛能清單方框、其中4條分隔線(切出3列)、每列文字起始位置相對整列左緣的x偏移(跳過tier圖示) |
| `restore_result_list_box` / `restore_result_row_y_bounds` / `restore_result_text_x_offset` | (恢復流程)BEFORE/AFTER比較畫面中，右邊AFTER潛能組的清單方框/分隔線/文字x偏移，意義同上 |
| `restore_select_after_point` | (恢復流程)AFTER符合目標時，點選套用AFTER潛能組的位置 |
| `restore_reroll_button` / `restore_reroll_confirm_button` / `restore_reroll_confirm_button_2` | (恢復流程)AFTER不符合目標時要點的「重新設定1次」按鈕，與其後依序跳出的**兩個**確認彈窗各自的「確認」按鈕 |

先手動開啟遊戲，進入潛在能力面板、切到「方塊」分頁，並選擇你要使用的方塊種類
(「珍貴附加方塊」「絕對附加方塊」「萌獸方塊」或「恢復附加方塊」其中一種)，
接著執行校正工具：

```
.venv\Scripts\python tools/locate.py
```

預設(`--mode default`)校正一般流程(珍貴/絕對附加方塊/萌獸方塊)用的欄位，依
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

若遊戲改版、UI位置跟預設值對不上、或換了新視窗大小/位置，重新執行這個工具
再校正一次即可，不需要改程式碼。

### 3.2 執行 (`run.py`)

1. 先手動在遊戲中開啟潛在能力面板、切到「方塊」分頁並選擇「珍貴附加方塊」
   「絕對附加方塊」「萌獸方塊」或「恢復附加方塊」其中一種(對應 plan.md 步驟1)，
   程式會自動判斷走哪個流程。
2. 執行：

```
.venv\Scripts\python run.py
```

3. 依提示輸入 `y` 開始，程式會倒數3秒後開始自動操作。
4. **緊急停止**：執行期間把滑鼠移到螢幕**任一角落**即會觸發 pyautogui 的 fail-safe
   中止(`pyautogui.FAILSAFE`)；也可以直接 Ctrl+C；或按下 `stop_hotkey` 設定的
   全域熱鍵(預設 `ctrl+f2`)，**不用切換視窗**、遊戲畫面保持在前景也能觸發，會在
   這一輪結束後停止(不是立即中斷)。
5. 點擊完不會把滑鼠移回原位，游標會停在最後一次點擊的位置。

執行紀錄會寫在 `logs/run_*.log`。

## 圖形介面 (GUI)

除了 CLI(`tools/locate.py` + `run.py`)之外，也提供一個 PyQt6 圖形介面，把目標潛能
設定、座標校正、執行整合在同一個視窗：

```
.venv\Scripts\python gui.py
```

- **目標潛能組設定區**：視覺化編輯 `target_potentials`——每組3個輸入框，可以「+ 新增
  目標組合」新增一組、用每組右邊的 ↑/↓ 調整優先權順序(由上到下優先權由高到低)、
  「刪除」移除整組(至少保留一組)；「儲存目標潛能設定」會把目前畫面上的內容寫回
  `config.json`。
- **開始/停止按鈕**：「開始」會先自動儲存目前的目標潛能設定，跳出確認提示後才開始
  自動化，執行中的 log 會即時顯示在下方文字區；「停止」會在目前這一輪跑完後收尾
  (一般流程：這次重新設定判斷完就停；恢復流程：這次AFTER判斷完就停、不會套用)，
  不是立即中斷，跟 CLI 版本一樣可以隨時把滑鼠移到螢幕角落觸發 fail-safe 立即中止。
  這兩個動作**全程**都可以用全域熱鍵觸發，不用點擊視窗——`start_hotkey`(預設
  `ctrl+f1`)、`stop_hotkey`(預設 `ctrl+f2`)，遊戲畫面保持在前景也能按。
- **座標校正**：
  - 「校正流程」下拉選單：切換要校正「一般流程(珍貴/絕對附加方塊/萌獸方塊)」還是
    「恢復流程(恢復附加方塊)」，對應 CLI 的 `tools/locate.py --mode default` /
    `--mode restore`；下方「單一按鈕校正」的下拉選單內容會跟著切換。
  - 「全部校正」：依序引導校正目前選定流程的全部欄位，跟 `tools/locate.py` 是同一套
    邏輯(共用 `src/calibration.py`)、同一份步驟清單，行為完全一致。
  - 「單一按鈕校正」：從下拉選單挑選某一個欄位，只重新校正那一項，不用整套重跑；
    兩種流程共用的欄位(使用貨幣欄位、重新設定按鈕、確認按鈕)只要校正過其中一種
    流程，通常另一種就不用重做。
  校正時會有一個小視窗即時顯示滑鼠所在的參考解析度座標。**記錄／跳過／結束建議用
  熱鍵觸發**——`calibrate_confirm_hotkey`(預設 `ctrl+f3`)、`calibrate_skip_hotkey`
  (預設 `ctrl+f4`)、`calibrate_finish_hotkey`(預設 `ctrl+f5`)。這三個動作也有
  對應按鈕，但**點按鈕會讓滑鼠先移過去**，記錄到的會是按鈕座標而不是遊戲畫面上
  的定點，所以校正時請用熱鍵、不要點按鈕。

首次開啟視窗會先在背景初始化 PaddleOCR 引擎(需要一點時間，尤其是第一次要下載模型)，
初始化完成前「開始」與「座標校正」按鈕會維持停用狀態。

## 測試（不需要開遊戲）

```
.venv\Scripts\python -m pytest tests/ -v
```

- `tests/test_reference_screenshots.py`：用從 plan.md 附的截圖裁出的
  `tests/fixtures/*.png`(重新設定後3個潛能清單、AFTER潛能清單、兩種流程的使用
  貨幣文字等紅框範圍)驗證 OCR 辨識、流程判斷(`detect_flow`)、目標比對邏輯是否
  正確。
- `tests/test_calibration.py`：驗證 `src/calibration.py` 的校正精靈邏輯(point/
  box/lines/text_offset 四種校正種類、跳過、STEPS_DEFAULT/STEPS_RESTORE 步驟
  清單本身的一致性)，CLI 與 GUI 的校正共用這份邏輯。
- `tests/test_controller_stop.py`：驗證 `Controller` 的 `stop_event`(GUI「停止」
  按鈕用)在兩種流程下都能乾淨地中止，不會誤點選套用/誤用掉方塊。
- `tests/test_hotkey.py`：驗證 `src/hotkey.py` 的錯誤處理(熱鍵為空、註冊/取消
  註冊失敗都不應該讓程式掛掉)，用假的 `keyboard` 模組取代，不會真的註冊全域熱鍵。

## 已知限制

- 所有座標是用參考截圖(約 1360x793 視窗大小)校準、以比例換算，若遊戲視窗大小差異
  太大可能會點不準，建議維持接近該大小的視窗，或用 `tools/locate.py` 重新校正。
- PaddleOCR 對繁體字偶爾會辨識成筆劃相近的簡體/日文變體字(例如「擊」讀成「撃」、
  「視」讀成「视」)，但比對邏輯本來就用模糊比對容忍1~2個字差異，不影響判斷。
- 已在真實遊戲視窗上實際測試調整過座標與流程；若換了新的視窗大小/位置或遊戲改版
  導致點不準，先用 `tools/locate.py` 重新校正，仍有問題建議先開 `dry_run: true`
  觀察 log 判斷是哪個步驟不對。
- `gui.py` 圖形介面目前只驗證過視窗能正常建立、目標潛能組編輯/存檔、校正流程
  下拉選單切換、找到真實遊戲視窗且不誤觸任何按鈕，**尚未在真實視窗環境實際點過
  「開始」跑完整流程或跑完一次「全部校正」**，建議第一次使用先搭配
  `dry_run: true` 觀察 log，或先用 CLI(`tools/locate.py` + `run.py`)驗證整體
  流程沒問題後再改用 GUI。

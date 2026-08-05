# 自動洗珍貴/絕對/萌獸/恢復附加方塊

依 [plan.md](plan.md) 實作，讀取遊戲畫面(視窗標題預設「貓貓TMS」)並自動操作滑鼠，
重複使用方塊直到附加潛在能力符合設定的目標，或用完設定的方塊上限為止。程式會依
畫面上「使用貨幣」目前選擇的方塊名稱自動判斷流程，不需要額外設定：

- **珍貴附加方塊 / 絕對附加方塊 / 萌獸方塊**：三者操作流程完全一致，每次「重新
  設定」立即套用新的3條潛能，直接判斷是否達成目標。
- **恢復附加方塊**：每次「重新設定」會顯示 BEFORE(重設前) / AFTER(重設後) 兩組
  潛能讓你選擇套用哪一組，程式只看右邊AFTER，符合目標就點選套用，不符合就點
  「重新設定1次」再骰一輪。

提供兩種使用方式：**圖形介面(GUI)** 或 **程式碼(CLI)**，擇一即可，功能完全對等。
不熟悉命令列的話建議用 GUI。

## 安裝

滑鼠控制用 [pyautogui](https://pyautogui.readthedocs.io/)，畫面文字辨識用
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)。PaddleOCR 底層的
`paddlepaddle` 目前還沒有 Python 3.14 的預編譯版本，**必須用 Python 3.13 (或更早)**：

```
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

第一次執行時 PaddleOCR 會自動下載偵測/辨識模型(存到 `~/.paddlex/official_models/`)，
需要網路連線，之後就會用本機快取，不用再下載。(如果是用打包好的 exe，模型檔已經
內建，不受此限制，見下方「打包成 exe」。)

安裝完成後，繼續看下方「使用教學」開始設定並執行。

## 使用教學

### 方式一：圖形介面 (GUI)

```
.venv\Scripts\python gui.py
```

#### 1. 等待初始化完成

視窗開啟後會先在背景初始化 PaddleOCR 引擎(第一次執行需要下載模型，需要一點時間)。
**初始化完成前，「開始」跟「座標校正」的按鈕都會維持反灰、不能按**，狀態列會顯示
「正在初始化 OCR 引擎，請稍候…」；等狀態列變成「就緒」，按鈕才會恢復可以點擊。
如果初始化失敗，會跳出錯誤訊息視窗說明原因。

#### 2. 設定遊戲解析度

視窗上方「遊戲解析度設定」區塊：對應 `config.json` 的 `regions.ref_width` /
`ref_height`，所有按鈕座標都是以這個解析度為基準記錄的。

- 「偵測目前遊戲視窗大小」：自動抓取目前遊戲視窗的實際大小，填入寬度/高度欄位
  (不會馬上存檔，填入後可以自己再檢查一次)。
- 「儲存解析度設定」：把目前欄位裡的數值寫回 `config.json`。

**第一次使用、或遊戲視窗大小變動過，建議先點「偵測目前遊戲視窗大小」再「儲存
解析度設定」，存檔後接著做下一步的「全部校正」**——只改解析度不重新校正，既有
的按鈕座標會套用新的縮放比例，但不會自動變準確；唯一準確的方式還是解析度存好後
重新走一次「全部校正」。

#### 3. 校正座標(第一次使用、或遊戲視窗變動過，必須先做這一步)

視窗下方「座標校正」區塊：

- **「校正流程」下拉選單**：先選要校正哪一種流程——「一般流程(珍貴/絕對附加方塊/
  萌獸方塊)」或「恢復流程(恢復附加方塊)」，兩者座標欄位不同，下方「單一按鈕校正」
  的清單會跟著切換。兩種流程開頭3項(使用貨幣欄位、重新設定按鈕、確認按鈕)座標
  共用，只要校正過其中一種，另一種通常不用重做。
- **「全部校正」**：依序引導校正目前選定流程的全部欄位，跟 CLI 的 `tools/locate.py`
  是同一套邏輯(共用 `src/calibration.py`)、行為完全一致。
- **「單一按鈕校正」**：從下拉選單挑選某一個欄位，只重新校正那一項，不用整套重跑。

點下去後會開一個小視窗，即時顯示滑鼠所在的參考解析度座標，操作方式：

1. 依畫面提示，先手動把遊戲切到對應的畫面/步驟。
2. 把滑鼠移到遊戲畫面上要記錄的定點。
3. 觸發「記錄」——**強烈建議用熱鍵 `ctrl+f3` 觸發，不要用滑鼠點對話框裡的按鈕**。
   點按鈕會讓滑鼠先移到按鈕上，記錄到的會是按鈕座標，不是遊戲畫面上的定點，
   整組校正就會是錯的。
4. 想跳過這一項(保留原本的值)按 `ctrl+f4`；全部做完或想中途結束按 `ctrl+f5`。

校正結果會即時寫回 `config.json`，不用手動存檔。

#### 4. 設定目標潛能組

視窗上方「目標潛能組設定」區塊：每一組是3個輸入框(對應3個潛能槽位，留空代表
「任意潛能」)，可以：

- 「+ 新增目標組合」：新增一組。
- 每組右邊的 `↑`/`↓`：調整優先權順序，**由上到下優先權由高到低**。
- 「刪除」：移除整組(至少保留一組)。
- 「儲存目標潛能設定」：把目前畫面上的內容寫回 `config.json`。

詳細比對規則(數值要不要完全相符、多組之間怎麼決定優先權)見下方「Config 設定教學」
的 `target_potentials` 說明。

#### 5. 開始執行

1. 先手動在遊戲中開啟潛在能力面板、切到「方塊」分頁，並選擇「珍貴附加方塊」
   「絕對附加方塊」「萌獸方塊」或「恢復附加方塊」其中一種——程式會自動判斷走
   哪個流程。
2. 點「開始」——會先自動儲存目前的目標潛能設定，跳出確認提示後才真正開始自動化。
3. 執行中的 log 會即時顯示在視窗下方文字區。

#### 6. 停止

- 點視窗裡的「停止」按鈕。
- 或按熱鍵 `ctrl+f2`(`stop_hotkey`)——不用切換視窗，遊戲畫面保持在前景也能按。
- 或把滑鼠移到螢幕**任一角落**，觸發 pyautogui 的 fail-safe 中止。

「停止」不是立即中斷，會等**目前這一輪跑完**才收尾(一般流程：這次重新設定判斷完
就停；恢復流程：這次AFTER判斷完就停、不會套用，維持BEFORE)。「開始」也有對應
熱鍵 `ctrl+f1`(`start_hotkey`)，等同點擊「開始」按鈕。

以上5個熱鍵(`start_hotkey`/`stop_hotkey`/`calibrate_confirm_hotkey`/
`calibrate_skip_hotkey`/`calibrate_finish_hotkey`)都可以在 `config.json` 改成別的
按鍵組合。

### 方式二：程式碼 (CLI)

#### 1. 校正座標(第一次使用、或遊戲視窗變動過，必須先做這一步)

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
`restore_reroll_confirm_button_2` 的順序；前3項與一般流程共用同一個畫面位置，
若已經校正過且畫面沒變，可以輸入 `s` 跳過。

程式會逐項提示你「遊戲畫面該停在哪一步、滑鼠要移到哪裡」；移到定點後直接按 Enter
就會記錄並立刻寫回 `config.json`，自動進入下一項，不用自己輸入名稱。也支援輸入
`s` 跳過該項(保留原值)、`q` 結束校正(已記錄的項目不會遺失)。

#### 2. 設定 `config.json`

至少確認 `window_title`(遊戲視窗標題)跟 `target_potentials`(目標潛能)符合你的
需求，詳見下方「Config 設定教學」。

#### 3. 執行

1. 先手動在遊戲中開啟潛在能力面板、切到「方塊」分頁，並選擇「珍貴附加方塊」
   「絕對附加方塊」「萌獸方塊」或「恢復附加方塊」其中一種——程式會自動判斷走
   哪個流程。
2. 執行：
   ```
   .venv\Scripts\python run.py
   ```
3. 依提示輸入 `y` 開始，程式會倒數3秒後開始自動操作。

#### 4. 停止

- 把滑鼠移到螢幕**任一角落**，觸發 pyautogui 的 fail-safe 中止。
- 直接按 Ctrl+C。
- 按熱鍵 `ctrl+f2`(`stop_hotkey`)——不用切換視窗，會在目前這一輪跑完後收尾。
  (CLI 沒有「待機中」狀態可以用熱鍵啟動，所以 `start_hotkey` 只有 GUI 有作用。)

執行紀錄會寫在 `logs/run_*.log`。點擊完不會把滑鼠移回原位，游標會停在最後一次
點擊的位置。

## Config 設定教學

所有設定都在專案根目錄的 `config.json`，用文字編輯器打開即可修改，不用重開程式、
存檔後下次執行就會套用(GUI 的目標潛能組設定與座標校正另外有介面可以直接改，
改完會自動存檔)。

### 完整範例

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
  "regions": { "...": "所有按鈕/讀取區域座標，見下方「regions：座標設定」" }
}
```

### 目標潛能設定

- `target_potentials`：**多組允許的目標組合**組成的list，每組固定3個字串槽位
  (空字串代表「除了其他目標潛能外的任意潛能」)，**list中排越前面的組合優先權
  越高**。每次按下「重新設定」後畫面上的3個潛能(恢復流程則是AFTER的3個潛能)，
  只要滿足**其中任一組合**就算達成目標、程式自動結束；不滿足則繼續下一次重新
  設定，直到達成目標或用完 `max_cubes`。上面範例代表優先追求「魔法攻擊力」，
  只要這3個潛能裡沒有魔法攻擊力，才會去比對「物理攻擊力」那組。
  - 每個字串可只寫名稱，例如 `"魔法攻擊力"`：只比對名稱，不限數值。
  - 也可以連數值一起寫，例如 `"魔法攻擊力 +12%"`：數值必須完全相同才算符合(包含
    有無`%`，例如`+300`和`+300%`視為不同數值)，用來區分同名但不同數值的重複
    選項(例如"無視怪物防禦率"同時出現 +30% 和 +40% 兩種)，或名稱相同但一個是
    百分比、一個是固定數值的潛能(例如"MaxMP"同時出現 +11% 和 +300 兩種)。
  - **組內3個槽位彼此沒有順序之分**：比對時會窮舉所有可能的配對方式，只要畫面
    上3個潛能存在某種排列方式能讓組合裡每個非空目標都對應到不同的一個，就算
    符合，不用刻意把目標依畫面顯示順序填入對應槽位。
  - GUI 使用者可直接用「目標潛能組設定」區塊編輯，不用手動改 JSON。

### 熱鍵設定

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

### 其他基本設定

- `window_title`：遊戲視窗標題，預設 `"貓貓TMS"`，需要跟實際視窗標題完全一致
  才找得到視窗。
- `ocr_lang`：PaddleOCR 的語言模型，預設 `"chinese_cht"`(繁體中文)。
- `ocr_match_threshold`：潛能文字模糊比對的相似度門檻(0~1)，預設 `0.55`，數值
  越高比對越嚴格，OCR 稍有誤差就可能判定不符合。一般不需要調整。
- `max_cubes`：最多使用幾個方塊，`0` 代表不限制。
- `click_delay_sec` / `post_action_wait_sec`：每次點擊之間、以及每個動作(如按下
  重新設定)之後的等待秒數，數值太小可能因為遊戲畫面還沒反應過來、截圖讀到舊畫面
  而誤判，一般不需要調整。
- `dry_run`：`true` 時只讀取畫面、印出判斷結果，不會真的點擊滑鼠(用來乾跑測試
  座標/OCR 設定是否正確，建議調整完設定後先開著這個測一輪再正式執行)。
- `log_lv`：`"debug"` 會印出每次點擊的詳細座標，其餘(含預設 `"info"`)只印重點
  流程訊息。

### regions：座標設定

所有滑鼠點擊/畫面讀取用的座標都放在 `regions` 區塊，**不用改程式碼**，用座標校正
工具(GUI 的「座標校正」或 CLI 的 `tools/locate.py`，見上方「使用教學」)就能重新
產生，一般不需要手動編輯這個區塊。

座標是以 `ref_width` x `ref_height`(預設 1360x793，對應 plan.md 附圖的視窗大小)這個
「參考解析度」下的像素記錄，執行時會依實際視窗大小等比例換算，因此視窗大小只要沒
差異太大都還算容錯；但若遊戲視窗大小差異太大，仍建議重新校正一次，會更準確。
GUI 使用者可以直接用「遊戲解析度設定」區塊的「偵測目前遊戲視窗大小」按鈕填入這兩個
值，不用手動量測。

各欄位意義：

| 欄位 | 說明 |
| --- | --- |
| `currency_label_box` | 讀取「使用貨幣」欄位文字的區域，**兩種流程共用**同一個畫面位置 |
| `currency_expected_texts` / `delay_currency_expected_texts` / `restore_currency_expected_texts` | 可接受的方塊名稱：前者是珍貴附加方塊/絕對附加方塊(走一般流程)，中間是萌獸方塊(一般流程，但有結束延遲)，後者是恢復附加方塊(走恢復流程)；程式讀取使用貨幣文字後兩邊比對，自動決定走哪個流程 |
| `delay_currency_expected_delay_time` | 使用萌獸方塊重設潛能後讀取潛能的延遲時間 |
| `reset_button` / `reset_confirm_button` | 「重新設定」按鈕與其確認彈窗的「確認」按鈕，**兩種流程共用**(按下後立即套用新的潛在能力，或進入恢復流程的BEFORE/AFTER比較畫面) |
| `result_list_box` / `result_row_y_bounds` / `result_text_x_offset` | (一般流程)重新設定後直接顯示的3個潛能清單方框、其中4條分隔線(切出3列)、每列文字起始位置相對整列左緣的x偏移(跳過tier圖示) |
| `restore_result_list_box` / `restore_result_row_y_bounds` / `restore_result_text_x_offset` | (恢復流程)BEFORE/AFTER比較畫面中，右邊AFTER潛能組的清單方框/分隔線/文字x偏移，意義同上 |
| `restore_select_after_point` | (恢復流程)AFTER符合目標時，點選套用AFTER潛能組的位置 |
| `restore_reroll_button` / `restore_reroll_confirm_button` / `restore_reroll_confirm_button_2` | (恢復流程)AFTER不符合目標時要點的「重新設定1次」按鈕，與其後依序跳出的**兩個**確認彈窗各自的「確認」按鈕 |

什麼時候需要重新校正：第一次使用、遊戲改版導致 UI 位置跑掉、換了不同大小/位置的
遊戲視窗，或懷疑目前設定不準確時。

---

## 打包成 exe

用 [PyInstaller](https://pyinstaller.org/) 把 GUI(`gui.py`)打包成不需要安裝 Python
就能執行的程式：

```
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\python -m PyInstaller AutoExCube.spec
```

打包結果在 `dist/AutoExCube/`，裡面的 `AutoExCube.exe` 加上整個 `_internal/`
資料夾都要一起帶走(不能只複製 exe 單獨那個檔案)，`config.json` 要放在跟 exe 同一層
目錄。整包大約 850MB+(主要是 `paddlepaddle` 本身很大，OCR 模型檔約再多133MB)。
打包好的 exe 使用方式跟上方「使用教學 → 方式一：圖形介面 (GUI)」完全一樣。

`AutoExCube.spec` 已經包含打包 `paddleocr`/`paddlex`/`paddle`/`keyboard` 這幾個
套件需要的 `--collect-all` 設定，改完程式碼後重新打包只要重跑上面第二行指令即可，
不需要重新產生 `.spec`。

**OCR 模型檔已直接打包進 exe，執行時不需要網路**：`.spec` 會把 `paddlex_models/`
資料夾(PaddleOCR 官方模型檔)一起收進 `_internal/`，`gui.py` 在打包後的 frozen
模式下會把 `PADDLE_PDX_CACHE_HOME` 指到這裡，完全不會嘗試連線下載。這個資料夾
預設不在版控裡(`.gitignore` 已排除，因為133MB對版控來說太大)，第一次要打包前
需要自己準備：

1. 用 `python gui.py`(一般開發環境、非打包模式)正常執行一次，讓程式走完整個
   OCR 初始化流程。PaddleOCR 偵測到本機沒有對應語言的模型，會自動連線官方模型
   來源(HuggingFace/AIStudio/ModelScope/BOS 其中之一)下載，存到
   `~/.paddlex/official_models/`(Windows 上是
   `C:\Users\<你的帳號>\.paddlex\official_models\`)。這一步需要網路連線。
2. 把下載好的模型資料夾複製到專案裡，讓 `.spec` 打包時抓得到：
   ```
   mkdir paddlex_models\official_models
   xcopy /E /I "%USERPROFILE%\.paddlex\official_models\PP-OCRv6_medium_det" paddlex_models\official_models\PP-OCRv6_medium_det
   xcopy /E /I "%USERPROFILE%\.paddlex\official_models\PP-OCRv6_medium_rec" paddlex_models\official_models\PP-OCRv6_medium_rec
   ```
   (實際的模型資料夾名稱依 `config.json` 的 `ocr_lang` 而定；`chinese_cht` 對應的
   就是上面這兩個。換了 `ocr_lang` 導致用到別的模型時，同樣先跑一次
   `python gui.py` 讓它下載好，再照上面方式複製過來、重新打包一次。)

之後只要 `paddlex_models/` 資料夾內容沒變，重新打包(`python -m PyInstaller
AutoExCube.spec`)就會沿用同一份模型檔，不需要每次都重新下載複製。

**已知問題**：打包後第一次執行若跳出「PaddleOCR 初始化失敗：A dependency error
occurred during pipeline creation」，是因為 `paddlex` 會用 `importlib.metadata`
讀取自己跟一串依賴套件(`imagesize`/`opencv-contrib-python`/`pyclipper`/
`pypdfium2`/`python-bidi`/`shapely`)的 dist-info 來判斷 OCR 功能是否可用，但
PyInstaller 預設不會打包這些 metadata，導致誤判成依賴缺失。`.spec` 裡已經用
`copy_metadata()` 補上這幾個套件的 metadata 解決這個問題；如果升級
`paddlepaddle`/`paddleocr`/`paddlex` 版本後又跳出同樣錯誤，多半是新版本用到了
別的 extra 套件組合，可以參考 `.spec` 裡的註解，用同樣方式把新缺的套件名稱
加進 `copy_metadata` 清單。GUI 的錯誤訊息視窗也會一併顯示例外的 `__cause__`
鏈，通常能直接看出實際少了哪個套件。

若防毒軟體對這個 exe 跳出誤判警告，這是 PyInstaller 打包的未簽章大型執行檔常見的
現象(尤其是包含大量原生 DLL 的 ML 相關套件)，可以自行評估是否加入例外。

CLI(`run.py`/`tools/locate.py`)目前沒有另外打包，仍需要用 Python 執行；如果需要
CLI 版本的 exe，可以比照 `.spec` 的做法各自打包一份。

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
  按鈕/`stop_hotkey`用)在兩種流程下都能乾淨地中止，不會誤點選套用/誤用掉方塊。
- `tests/test_hotkey.py`：驗證 `src/hotkey.py` 的錯誤處理(熱鍵為空、註冊/取消
  註冊失敗都不應該讓程式掛掉)，用假的 `keyboard` 模組取代，不會真的註冊全域熱鍵。

## 已知限制

- 所有座標是用參考截圖(約 1360x793 視窗大小)校準、以比例換算，若遊戲視窗大小差異
  太大可能會點不準，建議維持接近該大小的視窗，或重新校正。
- PaddleOCR 對繁體字偶爾會辨識成筆劃相近的簡體/日文變體字(例如「擊」讀成「撃」、
  「視」讀成「视」)，但比對邏輯本來就用模糊比對容忍1~2個字差異，不影響判斷。
- 已在真實遊戲視窗上實際測試調整過座標與流程；若換了新的視窗大小/位置或遊戲改版
  導致點不準，先重新校正，仍有問題建議先開 `dry_run: true` 觀察 log 判斷是哪個
  步驟不對。
- `gui.py` 圖形介面目前只驗證過視窗能正常建立、目標潛能組編輯/存檔、校正流程
  下拉選單切換、找到真實遊戲視窗且不誤觸任何按鈕，**尚未在真實視窗環境實際點過
  「開始」跑完整流程或跑完一次「全部校正」**，建議第一次使用先搭配
  `dry_run: true` 觀察 log，或先用 CLI(`tools/locate.py` + `run.py`)驗證整體
  流程沒問題後再改用 GUI。

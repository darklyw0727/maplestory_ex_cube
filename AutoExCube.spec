# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, copy_metadata


def _collect_dir_datas(src_root, dest_root):
    """把 src_root 底下所有檔案(遞迴)加進 datas，保留原本的目錄結構。"""
    entries = []
    for dirpath, _, filenames in os.walk(src_root):
        rel = os.path.relpath(dirpath, src_root)
        dest_dir = dest_root if rel == '.' else os.path.join(dest_root, rel)
        for fn in filenames:
            entries.append((os.path.join(dirpath, fn), dest_dir))
    return entries

datas = []
binaries = []
hiddenimports = ['win32timezone']
tmp_ret = collect_all('paddleocr')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('paddlex')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('paddle')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('keyboard')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# paddlex 在 import 階段就會用 importlib.metadata 讀取自己(以及一長串依賴)的
# dist-info 來判斷哪些「extra」功能可用；PyInstaller 預設不會打包 dist-info，
# 沒有這些 metadata 會被誤判成依賴缺失，導致 GUI 顯示「PaddleOCR 初始化失敗：
# A dependency error occurred during pipeline creation」。
# recursive=True 只會複製 paddlex「必要」依賴的 metadata，不會複製用
# extra(例如 ocr / ocr-core)條件標記的依賴，所以下面另外針對 OCR pipeline
# 實際會檢查、且這個環境真的有裝的套件(paddlex.utils.deps.EXTRAS["ocr-core"])
# 手動加上 copy_metadata，缺一個都會被誤判成「OCR」這個extra不可用。
datas += copy_metadata('paddlex', recursive=True)
datas += copy_metadata('paddleocr')
datas += copy_metadata('paddlepaddle')
for _pkg in ('imagesize', 'opencv-contrib-python', 'pyclipper', 'pypdfium2', 'python-bidi', 'shapely'):
    datas += copy_metadata(_pkg)

# 把已經下載好的 OCR 模型檔一起打包進 exe，這樣在完全沒有網路、或連不到
# huggingface/modelscope/aistudio/bos 任何一個模型來源的乾淨電腦上，也不會
# 卡在「初始化 OCR」等連線逾時甚至直接卡死——gui.py 在 frozen 模式下會把
# PADDLE_PDX_CACHE_HOME 指到這裡，paddlex 會直接用本地檔案，完全不碰網路。
# 如果之後改了 config.json 的 ocr_lang 導致需要別的模型，記得重新用
# python gui.py 跑一次(讓 paddlex 下載新模型到 ~/.paddlex/official_models/)，
# 再把新的模型資料夾複製一份到 paddlex_models/official_models/ 底下。
datas += _collect_dir_datas('paddlex_models/official_models', os.path.join('paddlex_models', 'official_models'))

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoExCube',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoExCube',
)

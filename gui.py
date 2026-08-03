"""PyQt6 圖形介面入口。用法: python gui.py"""
import logging
import os
import sys
import time
from pathlib import Path

# 這幾個環境變數要在 import 任何 paddleocr/paddlex 相關模組「之前」設定，因為
# paddlex 在 import 階段就會讀取這些變數決定模型快取路徑，晚了就沒用。
#
# 打包成 exe(PyInstaller frozen)時，模型檔已經跟著執行檔一起打包在
# paddlex_models/official_models/ 底下(見 AutoExCube.spec)，把
# PADDLE_PDX_CACHE_HOME 指過去就完全不需要網路下載——這是為了解決在完全沒有
# 快取、且網路連不到 huggingface/modelscope/aistudio/bos 任何一個模型來源
# (例如離線、防火牆擋住)的乾淨電腦上，OCR 初始化會卡住等連線逾時甚至直接
# 掛住的問題。DISABLE_MODEL_SOURCE_CHECK 則是防呆：萬一之後改了語言設定、需要
# 用到沒有一起打包的模型，直接跳過「連線檢查模型來源」那一步、快速失敗，
# 不要卡在等連線逾時。
if getattr(sys, "frozen", False):
    _bundled_cache = os.path.join(sys._MEIPASS, "paddlex_models")
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", _bundled_cache)
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow

# 注意：這裡刻意不呼叫 src.window.ensure_dpi_aware()。Qt6 在 Windows 上會自己
# 設定 per-monitor-v2 DPI-aware，搶先手動設定反而會讓 Qt 內部再次嘗試設定時失敗，
# 印出「SetProcessDpiAwarenessContext() failed: 存取被拒」的警告。


def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / time.strftime("gui_%Y%m%d_%H%M%S.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
    )
    return log_path


def main():
    setup_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

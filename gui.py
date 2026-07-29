"""PyQt6 圖形介面入口。用法: python gui.py"""
import logging
import sys
import time
from pathlib import Path

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

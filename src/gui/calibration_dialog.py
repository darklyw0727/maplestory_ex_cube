"""座標校正精靈對話框：全部校正/單一按鈕校正共用同一個對話框，差別只在傳入的
steps 是完整清單還是篩選後的單一項目。"""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from src import calibration


class CalibrationDialog(QDialog):
    def __init__(self, hwnd, ref_w, ref_h, regions: dict, steps, on_step_saved, parent=None):
        super().__init__(parent)
        self.setWindowTitle("座標校正")
        self.setMinimumWidth(480)

        self.state = calibration.WizardState(hwnd, ref_w, ref_h, regions, steps)
        self.on_step_saved = on_step_saved

        layout = QVBoxLayout(self)

        self.prompt_label = QLabel()
        self.prompt_label.setWordWrap(True)
        layout.addWidget(self.prompt_label)

        self.pos_label = QLabel()
        layout.addWidget(self.pos_label)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #cc3333;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        self.capture_btn = QPushButton("記錄（滑鼠移到定點後點擊）")
        self.skip_btn = QPushButton("跳過本項")
        self.close_btn = QPushButton("結束")
        btn_row.addWidget(self.capture_btn)
        btn_row.addWidget(self.skip_btn)
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        self.capture_btn.clicked.connect(self._on_capture)
        self.skip_btn.clicked.connect(self._on_skip)
        self.close_btn.clicked.connect(self.accept)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_position)
        self.timer.start(80)

        self._refresh_prompt()

    def _refresh_prompt(self):
        if self.state.finished:
            self.prompt_label.setText("全部項目校正完畢！可以關閉這個視窗了。")
            self.capture_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
            return
        self.prompt_label.setText(f"【{self.state.prompt()}】")

    def _update_position(self):
        if self.state.finished:
            return
        pt = self.state.current_position()
        if pt is None:
            self.pos_label.setText("(滑鼠不在遊戲視窗範圍內)")
        else:
            self.pos_label.setText(f"參考解析度座標 = ({pt[0]}, {pt[1]})")

    def _on_capture(self):
        key = self.state.current_step[0]
        ok, err = self.state.capture()
        if err:
            self.error_label.setText(err)
            return
        self.error_label.setText("")
        if ok and self.on_step_saved:
            self.on_step_saved(key)
        self._refresh_prompt()

    def _on_skip(self):
        key = self.state.current_step[0]
        self.state.skip()
        self.error_label.setText(f"已跳過「{key}」，保留原值")
        self._refresh_prompt()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

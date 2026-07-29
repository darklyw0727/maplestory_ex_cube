"""座標校正精靈對話框：全部校正/單一按鈕校正共用同一個對話框，差別只在傳入的
steps 是完整清單還是篩選後的單一項目。

支援全域熱鍵操作(記錄/跳過/結束)：校正時滑鼠要停在遊戲畫面上的定點，若改用
滑鼠點擊對話框裡的按鈕，游標會先移到按鈕上，抓到的就會是按鈕的座標而不是遊戲
畫面上的定點；改用鍵盤熱鍵觸發就不會移動滑鼠，才能正確記錄到滑鼠原本所在的
座標。
"""
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from src import calibration
from src import hotkey as hotkey_mod


class _CalibHotkeyBridge(QObject):
    """熱鍵callback在keyboard套件的背景執行緒上執行，用signal轉回GUI主執行緒。"""

    triggered = pyqtSignal(str)


class CalibrationDialog(QDialog):
    def __init__(self, hwnd, ref_w, ref_h, regions: dict, steps, on_step_saved, hotkeys: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("座標校正")
        self.setMinimumWidth(520)

        self.state = calibration.WizardState(hwnd, ref_w, ref_h, regions, steps)
        self.on_step_saved = on_step_saved
        self.hotkeys = hotkeys or {}

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

        confirm_hk = self.hotkeys.get("confirm")
        skip_hk = self.hotkeys.get("skip")
        finish_hk = self.hotkeys.get("finish")

        btn_row = QHBoxLayout()
        self.capture_btn = QPushButton(self._btn_text("記錄（滑鼠移到定點後觸發）", confirm_hk))
        self.skip_btn = QPushButton(self._btn_text("跳過本項", skip_hk))
        self.close_btn = QPushButton(self._btn_text("結束", finish_hk))
        btn_row.addWidget(self.capture_btn)
        btn_row.addWidget(self.skip_btn)
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        if any([confirm_hk, skip_hk, finish_hk]):
            hint = QLabel(
                "提示：滑鼠停在遊戲畫面定點後，建議用熱鍵觸發「記錄」而不是點滑鼠——"
                "點按鈕會讓游標先移到按鈕上，記錄到的會是按鈕的座標。"
            )
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #666666;")
            layout.addWidget(hint)

        self.capture_btn.clicked.connect(self._on_capture)
        self.skip_btn.clicked.connect(self._on_skip)
        self.close_btn.clicked.connect(self.accept)

        self._hotkey_bridge = _CalibHotkeyBridge()
        self._hotkey_bridge.triggered.connect(self._on_hotkey)
        self._hotkey_handles = [
            hotkey_mod.register(confirm_hk, lambda: self._hotkey_bridge.triggered.emit("confirm")),
            hotkey_mod.register(skip_hk, lambda: self._hotkey_bridge.triggered.emit("skip")),
            hotkey_mod.register(finish_hk, lambda: self._hotkey_bridge.triggered.emit("finish")),
        ]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_position)
        self.timer.start(80)

        self._refresh_prompt()

    @staticmethod
    def _btn_text(label: str, hk) -> str:
        return f"{label} [{hk}]" if hk else label

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

    def _on_hotkey(self, action: str):
        if action == "confirm" and self.capture_btn.isEnabled():
            self._on_capture()
        elif action == "skip" and self.skip_btn.isEnabled():
            self._on_skip()
        elif action == "finish":
            self.accept()

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
        for h in self._hotkey_handles:
            hotkey_mod.unregister(h)
        super().closeEvent(event)

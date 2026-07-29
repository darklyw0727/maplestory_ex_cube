"""目標潛能組設定區：編輯 config.json 的 target_potentials(多組允許組合，
排越前面優先權越高)。"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QScrollArea, QFrame, QSizePolicy,
)


class ComboRow(QFrame):
    """單一組目標潛能(固定3個字串槽位)，附上移/下移/刪除按鈕。"""

    move_up = pyqtSignal(object)
    move_down = pyqtSignal(object)
    remove = pyqtSignal(object)

    def __init__(self, combo=None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        self.priority_label = QLabel()
        self.priority_label.setFixedWidth(28)
        layout.addWidget(self.priority_label)

        self.slot_edits = []
        for i in range(3):
            edit = QLineEdit()
            edit.setPlaceholderText(f"槽位{i + 1}：留空=任意潛能")
            layout.addWidget(edit, stretch=1)
            self.slot_edits.append(edit)

        self.up_btn = QPushButton("↑")
        self.down_btn = QPushButton("↓")
        self.remove_btn = QPushButton("刪除")
        for btn in (self.up_btn, self.down_btn, self.remove_btn):
            btn.setFixedWidth(44)
        layout.addWidget(self.up_btn)
        layout.addWidget(self.down_btn)
        layout.addWidget(self.remove_btn)

        self.up_btn.clicked.connect(lambda: self.move_up.emit(self))
        self.down_btn.clicked.connect(lambda: self.move_down.emit(self))
        self.remove_btn.clicked.connect(lambda: self.remove.emit(self))

        if combo:
            self.set_combo(combo)

    def set_priority_label(self, rank: int):
        self.priority_label.setText(f"#{rank}")

    def get_combo(self) -> list:
        return [edit.text().strip() for edit in self.slot_edits]

    def set_combo(self, combo: list):
        for edit, value in zip(self.slot_edits, list(combo) + ["", "", ""]):
            edit.setText(value)


class TargetPotentialsEditor(QWidget):
    """target_potentials 編輯區：多組 ComboRow，由上到下代表優先權由高到低。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[ComboRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        header = QLabel(
            "目標潛能組設定（每組3個槽位，留空代表任意潛能；由上到下優先權由高到低，"
            "每次重新設定後畫面上的3個潛能只要滿足其中一組即達成目標。組內項目順序"
            "不影響比對結果，不用刻意對齊順序）"
        )
        header.setWordWrap(True)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.addStretch(1)
        scroll.setWidget(self._rows_container)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer.addWidget(scroll, stretch=1)

        add_btn = QPushButton("+ 新增目標組合")
        add_btn.clicked.connect(lambda: self.add_row())
        outer.addWidget(add_btn)

    def add_row(self, combo=None):
        row = ComboRow(combo)
        row.move_up.connect(self._on_move_up)
        row.move_down.connect(self._on_move_down)
        row.remove.connect(self._on_remove)
        self.rows.append(row)
        self._rebuild()
        return row

    def _on_move_up(self, row):
        i = self.rows.index(row)
        if i > 0:
            self.rows[i - 1], self.rows[i] = self.rows[i], self.rows[i - 1]
            self._rebuild()

    def _on_move_down(self, row):
        i = self.rows.index(row)
        if i < len(self.rows) - 1:
            self.rows[i + 1], self.rows[i] = self.rows[i], self.rows[i + 1]
            self._rebuild()

    def _on_remove(self, row):
        if len(self.rows) <= 1:
            return  # 至少保留一組
        self.rows.remove(row)
        self._rebuild()

    def _rebuild(self):
        while self._rows_layout.count() > 1:  # 保留最後的 stretch
            item = self._rows_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for rank, row in enumerate(self.rows, start=1):
            row.set_priority_label(rank)
            self._rows_layout.insertWidget(rank - 1, row)

    def load(self, target_potentials: list):
        self.rows = []
        for combo in target_potentials or [["", "", ""]]:
            row = ComboRow(combo)
            row.move_up.connect(self._on_move_up)
            row.move_down.connect(self._on_move_down)
            row.remove.connect(self._on_remove)
            self.rows.append(row)
        self._rebuild()

    def to_list(self) -> list:
        return [row.get_combo() for row in self.rows]

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QWidget


class CardGrid(QWidget):
    def __init__(self, min_card_width: int = 340, gap: int = 16, parent=None) -> None:
        super().__init__(parent)
        self.min_card_width = min_card_width
        self.gap = gap
        self._cards: list[QWidget] = []
        self._columns = 0
        self.available_width = 0
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(gap)
        self._layout.setVerticalSpacing(gap)
        self._layout.setAlignment(_top_left())

    def set_cards(self, cards: list[QWidget]) -> None:
        self._cards = list(cards)
        for card in self._cards:
            if card.parentWidget() is not self:
                card.setParent(self)
        self._relayout(force=True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        columns = max(1, (self._available_width() + self.gap) // (self.min_card_width + self.gap))
        if columns != self._columns:
            self._relayout(force=True)

    def _relayout(self, force: bool = False) -> None:
        columns = max(1, (self._available_width() + self.gap) // (self.min_card_width + self.gap))
        if not force and columns == self._columns and self._layout.count() == len(self._cards):
            return
        while self._layout.count():
            self._layout.takeAt(0)
        self._columns = columns
        for index, card in enumerate(self._cards):
            self._layout.addWidget(card, index // columns, index % columns)
        for column in range(max(columns, 4)):
            self._layout.setColumnStretch(column, 1 if column < columns else 0)

    def _available_width(self) -> int:
        if self.available_width > 0:
            return self.available_width
        parent = self.parentWidget()
        if parent and self.width() > parent.width():
            return parent.width()
        return self.width()

    def set_available_width(self, width: int) -> None:
        width = max(0, int(width))
        if width == self.available_width:
            return
        self.available_width = width
        self._relayout(force=True)

    def sizeHint(self):
        hint = super().sizeHint()
        if self._cards:
            columns = max(1, self._columns)
            rows = (len(self._cards) + columns - 1) // columns
            height = sum(max(card.sizeHint().height() for card in self._cards[row * columns:(row + 1) * columns]) for row in range(rows))
            height += max(0, rows - 1) * self.gap
            hint.setHeight(max(hint.height(), height))
        return hint


def _top_left():
    from PySide6.QtCore import Qt

    return Qt.AlignTop | Qt.AlignLeft

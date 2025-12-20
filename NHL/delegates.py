from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QColor, QPainter, QPen


class HighlightDelegate(QStyledItemDelegate):
    def __init__(self, highlight_rows, parent=None):
        super().__init__(parent)
        self.highlight_rows = highlight_rows
        self.parent_table = parent

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.row() in self.highlight_rows:
            painter.save()
            pen = QPen(QColor("white"), 2)
            painter.setPen(pen)
            rect = option.rect
            painter.drawRect(rect)
            painter.restore()


class FavoriteDelegate(QStyledItemDelegate):
    def __init__(self, favorite_rows, parent=None):
        super().__init__(parent)
        self.favorite_rows = favorite_rows

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.row() in self.favorite_rows:
            painter.save()
            pen = QPen(QColor("white"), 2)
            painter.setPen(pen)
            rect = option.rect
            painter.drawRect(rect)
            painter.restore()


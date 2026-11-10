"""Continuous glyph runs with in-place target-box handles; no outline mutations."""

from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui

from .model import decompose, drag_box, layout_run, visible_run, hit_role
from .metrics import metric_rows

COLORS = ('#177962', '#b94e72', '#3679ac')


def value(item):
    return item() if callable(item) else item


class GlyphCanvas(QtGui.QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.items = []
        self.characters = []
        self.cell = 108
        self.widths = {}
        self.drag = None
        self.pan = None
        self.space_down = False
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMinimumWidth(250)
        self.setMinimumHeight(340)
        self.setMouseTracking(True)

    def reflow(self):
        mode = value(self.owner.breaks.currentIndex)
        self.widths = {c: max(1., self.owner.adapter.advance(c) * self.scale()) for c in self.characters}
        self.items, total_height = layout_run(self.characters, self.cell, mode, self.widths, self.metrics_height())
        height = value(self.height)
        self.owner.scrollbar.setPageStep(height)
        self.owner.scrollbar.setRange(0, max(0, total_height - height))
        total_width = max((x + self.widths[c] + 16 for c, x, _ in self.items), default=0)
        self.owner.hscrollbar.setPageStep(value(self.width))
        self.owner.hscrollbar.setRange(0, max(0, int(total_width - value(self.width))))
        self.update()

    def resizeEvent(self, event):
        self.reflow()

    def screen_box(self, box, x, y):
        scale = self.scale()
        baseline = y + self.cell
        return QtCore.QRectF(x + box['x'] * scale, baseline - (box['y'] + box['h']) * scale,
                             box['w'] * scale, box['h'] * scale)

    def scale(self):
        return self.cell / self.owner.adapter.upm

    def metrics_height(self):
        return 100 if value(self.owner.metrics_mode.currentIndex) < 3 else 0

    def handles(self, rect):
        return {'nw': (rect.left(), rect.top()), 'ne': (rect.right(), rect.top()),
                'sw': (rect.left(), rect.bottom()), 'se': (rect.right(), rect.bottom())}

    def visible_items(self):
        offset = value(self.owner.scrollbar.value)
        height = value(self.height)
        return visible_run(self.items, offset, height, self.cell,
                           value(self.owner.hscrollbar.value), value(self.width), self.widths, self.metrics_height())

    def wheelEvent(self, event):
        delta = event.pixelDelta()
        if delta.isNull():
            delta = event.angleDelta()
        if event.modifiers() & QtCore.Qt.ShiftModifier:
            bar = self.owner.hscrollbar
            bar.setValue(value(bar.value) - (delta.x() or delta.y()))
        else:
            for bar, distance in ((self.owner.scrollbar, delta.y()),
                                  (self.owner.hscrollbar, delta.x())):
                bar.setValue(value(bar.value) - distance)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.space_down = True
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
            event.accept()

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space and not event.isAutoRepeat():
            self.space_down = False
            if self.pan is None:
                self.unsetCursor()
            event.accept()

    def focusOutEvent(self, event):
        self.space_down = False
        self.pan = None
        self.drag = None
        self.unsetCursor()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            self.paint_contents(painter, event)
        finally:
            painter.end()

    def paint_contents(self, painter, event):
        painter.fillRect(event.rect(), QtGui.QColor('#ffffff'))
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        scale = self.scale()
        for char, x, y in self.visible_items():
            if y + self.cell * 1.4 + self.metrics_height() < event.rect().top() or y > event.rect().bottom():
                continue
            active = char == self.owner.selected
            width = self.widths[char]
            highlight = value(self.owner.highlight.currentIndex)
            if highlight and char in self.owner.repertoires[highlight-1]:
                painter.fillRect(QtCore.QRectF(x, y - 8, width, self.cell * 1.4), QtGui.QColor('#fff3d6'))
            if active:
                painter.fillRect(QtCore.QRectF(x, y - 8, width, self.cell * 1.4), QtGui.QColor('#d8eee5'))
            if char in self.owner.edit_selection:
                painter.setBrush(QtGui.QBrush())
                painter.setPen(QtGui.QPen(QtGui.QColor('#177962'), 2))
                painter.drawRect(QtCore.QRectF(x + 1, y - 7, width - 2, self.cell * 1.4 - 2))
            painter.setPen(QtGui.QPen(QtGui.QColor('#e4e8e6'), 1))
            painter.drawLine(QtCore.QPointF(x, y + self.cell), QtCore.QPointF(x + width, y + self.cell))
            path, measured = self.owner.outline_for_display(char)
            if path is not None:
                painter.save()
                painter.translate(x, y + self.cell)
                painter.scale(scale, -scale)
                no_pen = QtGui.QPen()
                no_pen.setStyle(QtCore.Qt.NoPen)
                painter.setPen(no_pen)
                painter.setBrush(QtGui.QBrush(QtGui.QColor('#424947' if measured else '#858d89')))
                painter.drawPath(path)
                painter.restore()
            else:
                font = QtGui.QFont()
                font.setPixelSize(int(self.cell * .70))
                painter.setFont(font)
                painter.setPen(QtGui.QPen(QtGui.QColor('#d8dddb')))
                painter.drawText(QtCore.QRectF(x, y, width, self.cell), QtCore.Qt.AlignCenter, char)
            for role in range(3):
                svc_path = self.owner.svc_paths.get((char, role))
                if svc_path is not None:
                    painter.save()
                    painter.translate(x, y + self.cell)
                    painter.scale(scale, -scale)
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(COLORS[role])))
                    painter.drawPath(svc_path)
                    painter.restore()
                    if value(self.owner.show_boxes.checked) or (char in self.owner.edit_selection and role == self.owner.role):
                        r = svc_path.boundingRect()
                        actual = dict(x=r.x(), y=r.y(), w=r.width(), h=r.height())
                        painter.setBrush(QtGui.QBrush())
                        painter.setPen(QtGui.QPen(QtGui.QColor(COLORS[role]), 1))
                        painter.drawRect(self.screen_box(actual, x, y))
                box = self.owner.display_box(char, role)
                if box is None:
                    continue
                chosen = char in self.owner.edit_selection and role == self.owner.role
                if not value(self.owner.show_boxes.checked) and not chosen:
                    continue
                rect = self.screen_box(box, x, y)
                painter.setBrush(QtGui.QBrush())
                pen = QtGui.QPen(QtGui.QColor(COLORS[role]), 2 if chosen else 1)
                if svc_path is not None:
                    pen.setStyle(QtCore.Qt.DashLine)
                painter.setPen(pen)
                painter.drawRect(rect)
                if chosen and not self.owner.preview and len(self.owner.edit_selection) <= 1:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
                    for hx, hy in self.handles(rect).values():
                        painter.drawRect(QtCore.QRectF(hx - 3, hy - 3, 6, 6))
            font = QtGui.QFont()
            font.setPixelSize(11)
            painter.setFont(font)
            painter.setPen(QtGui.QPen(QtGui.QColor('#717a76')))
            suffix = '' if char in self.owner.session.observations else ' · ' + self.owner.session.state(char)
            if self.owner.session.predictions.get(char, {}).get('mode') == 'reference' and char not in self.owner.session.observations:
                suffix = ' · 전이'
            if decompose(char)[2] and char not in self.owner.session.observations:
                suffix = ' · ㅁ 기준' if self.owner.display_box(char, self.owner.role) is not None else ' · 근거 부족'
            if char in self.owner.session.observations:
                suffix = ' · 표본'
            painter.drawText(QtCore.QRectF(x, y + self.cell * 1.14, width, 20),
                             QtCore.Qt.AlignCenter, char + suffix)
            if self.metrics_height():
                painter.save()
                top = y + self.cell * 1.4
                painter.setClipRect(QtCore.QRectF(x, top, width, self.metrics_height()))
                font.setPixelSize(10)
                painter.setFont(font)
                evaluated = self.owner.svc_paths.get((char, self.owner.role))
                rect = evaluated.boundingRect() if evaluated is not None else None
                actual = dict(x=rect.x(), y=rect.y(), w=rect.width(), h=rect.height()) if rect is not None else None
                rows = metric_rows(self.owner.session, char, self.owner.role,
                                   value(self.owner.metrics_mode.currentIndex),
                                   self.owner.display_box(char, self.owner.role), actual, strict_closed=True)
                for i, (label, text) in enumerate(rows):
                    rect = QtCore.QRectF(x, top + i*18, width, 18)
                    painter.fillRect(rect, QtGui.QColor('#e8f3ed' if char in self.owner.edit_selection else '#f3f5f4'))
                    painter.setPen(QtGui.QPen(QtGui.QColor('#424947')))
                    short = QtGui.QFontMetricsF(font).elidedText(label+' '+text, QtCore.Qt.ElideRight, max(1., width-4))
                    painter.drawText(rect, QtCore.Qt.AlignCenter, short)
                painter.restore()

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == QtCore.Qt.MiddleButton or (self.space_down and event.button() == QtCore.Qt.LeftButton):
            self.drag = None
            self.pan = (event.pos().x(), event.pos().y(), value(self.owner.hscrollbar.value),
                        value(self.owner.scrollbar.value))
            self.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        point = event.pos()
        modifiers = event.modifiers()
        extend = bool(modifiers & QtCore.Qt.ShiftModifier)
        toggle = bool(modifiers & (QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier))
        # Test selected handles first, including handles beyond the em boundary.
        for char, x, y in self.visible_items():
            if char != self.owner.selected:
                continue
            box = self.owner.display_box(char, self.owner.role)
            if box is not None and not self.owner.preview and not (extend or toggle) and len(self.owner.edit_selection) <= 1:
                for name, (hx, hy) in self.handles(self.screen_box(box, x, y)).items():
                    if abs(point.x() - hx) <= 7 and abs(point.y() - hy) <= 7:
                        self.drag = (point.x(), point.y(), box, name)
                        return
        for char, x, y in self.visible_items():
            if not QtCore.QRectF(x, y - 8, self.widths[char], self.cell * 1.4 + self.metrics_height()).contains(point.x(), point.y()):
                continue
            scale = self.scale()
            role = hit_role([self.owner.display_box(char, r) for r in range(3)],
                            (point.x() - x) / scale, (y + self.cell - point.y()) / scale,
                            self.owner.role)
            hit = role is not None
            if point.y() >= y + self.cell * 1.4:
                hit = False
            if not hit:
                role = self.owner.role
            was_multiple = len(self.owner.edit_selection) > 1
            self.owner.select_cell(char, role, extend, toggle)
            if hit and not self.owner.preview and not (extend or toggle or was_multiple):
                self.drag = (point.x(), point.y(), self.owner.display_box(char, role), 'move')
            return

    def mouseMoveEvent(self, event):
        if self.pan is not None:
            x, y, horizontal, vertical = self.pan
            self.owner.hscrollbar.setValue(horizontal + x - event.pos().x())
            self.owner.scrollbar.setValue(vertical + y - event.pos().y())
            return
        if not self.drag:
            return
        x, y, box, handle = self.drag
        scale = self.scale()
        updated = drag_box(box, handle, (event.pos().x() - x) / scale,
                           (y - event.pos().y()) / scale)
        stored = self.owner.session.box(self.owner.selected, self.owner.role)
        shown = self.owner.display_box(self.owner.selected, self.owner.role)
        if stored is None or shown is None:
            return
        self.owner.session.set_box(self.owner.selected, self.owner.role,
                                   {k: stored[k] + updated[k] - shown[k] for k in updated})
        self.owner.svc_paths = {}
        self.owner.schedule_save()
        self.owner.sync_panel()
        self.update()

    def mouseReleaseEvent(self, event):
        edited = self.drag is not None
        self.drag = None
        self.owner.schedule_save()
        if edited:
            self.owner.schedule_preview()
        self.pan = None
        if self.space_down:
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
        else:
            self.unsetCursor()

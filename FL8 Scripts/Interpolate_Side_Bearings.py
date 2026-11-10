#FLM: MW: Interpolate Side Bearings

import re

import fontlab as fl6
from PythonQt import QtGui
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui.widgets import getProcessGlyphs


qapp = QtGui.QApplication.instance()
app_version = '1.3.0'
app_name = 'Minwoo | Interpolate Side Bearings'

NUMBER_EXPRESSION = re.compile(r'=?\s*[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)')
SELECTED_ONLY = False

def plan_interpolation(glyph, layers, axis_index, start, end):
    groups = {}
    for name, position in layers:
        coordinate = position[axis_index]
        if start <= coordinate <= end:
            fixed_coordinates = position[:axis_index] + position[axis_index + 1:]
            groups.setdefault(fixed_coordinates, []).append((coordinate, name))

    updates = {}
    for group in groups.values():
        if len(group) < 3:
            continue
        group.sort()
        if len({coordinate for coordinate, _ in group}) != len(group):
            print(f"SKIP {glyph.name}: multiple masters at the same position")
            continue
        first_position, first_name = group[0]
        last_position, last_name = group[-1]
        first_equations = glyph.getSBeq(first_name)
        last_equations = glyph.getSBeq(last_name)

        for side, getter in enumerate((glyph.getLSB, glyph.getRSB)):
            first = (first_equations[side] or '').strip()
            last = (last_equations[side] or '').strip()
            if first and first == last:
                for _, name in group[1:-1]:
                    updates.setdefault(name, {})[side] = first
                continue

            first_literal = NUMBER_EXPRESSION.fullmatch(first)
            last_literal = NUMBER_EXPRESSION.fullmatch(last)
            if first and last and not first_literal and not last_literal:
                side_name = ('LSB', 'RSB')[side]
                print(f"SKIP {glyph.name} / {side_name} / {first_name} → {last_name}: {first} ≠ {last}")
                continue

            first_value = float(first.lstrip('=')) if first_literal else getter(first_name)
            last_value = float(last.lstrip('=')) if last_literal else getter(last_name)
            for coordinate, name in group[1:-1]:
                ratio = (coordinate - first_position) / (last_position - first_position)
                value = first_value + (last_value - first_value) * ratio
                updates.setdefault(name, {})[side] = f'={value:.12f}'.rstrip('0').rstrip('.') if first or last else value

    return updates


def apply_interpolation(glyph, updates):
    for name, sides in updates.items():
        equations = glyph.getSBeq(name)
        preserve_right = 0 in sides and not isinstance(sides[0], str) and 1 not in sides and not equations[1]
        if preserve_right:
            original_right = glyph.getRSB(name)
        for side, setter, equation_setter, side_name in (
            (0, glyph.setLSB, glyph.setLSBeq, 'LSB'),
            (1, glyph.setRSB, glyph.setRSBeq, 'RSB'),
        ):
            if side not in sides:
                continue
            value = sides[side]
            if isinstance(value, str):
                equation_setter(value, name)
            else:
                if equations[side]:
                    equation_setter('', name)
                setter(value, name)
            print(f"{glyph.name} / {name} / {side_name}: {value}")
        if preserve_right and glyph.getRSB(name) != original_right:
            glyph.setRSB(original_right, name)


def master_layers(glyph, axis_names, master_order):
    layers = []
    for layer in glyph.layers():
        if not layer.isMasterLayer or layer.isMaskLayer or layer.isImgLayer:
            continue
        if axis_names:
            location = layer.getMasterPosition()
            try:
                position = tuple(float(location[axis]) for axis in axis_names)
            except (KeyError, TypeError, ValueError):
                print(f"SKIP {glyph.name} / {layer.name}: missing master position")
                continue
        else:
            position = (master_order[layer.name],)
        layers.append((layer.name, position))
    return layers


class InterpolateDialog(QtGui.QDialog):
    def __init__(self, axis_names, glyph_layers, coordinates, labels, master_order):
        super(InterpolateDialog, self).__init__()
        self.axis_names = axis_names
        self.glyph_layers = glyph_layers
        self.coordinates = coordinates
        self.labels = labels
        self.master_order = master_order
        self.setWindowTitle(f"{app_name} {app_version}")
        dlg_width = 350
        dlg_height = 160
        desktop_geo = qapp.desktop().geometry

        center_x = desktop_geo.x() + int(desktop_geo.width() / 2) - int(dlg_width / 2)
        center_y = desktop_geo.y() + int(desktop_geo.height() / 2) - int(dlg_height)
        self.setGeometry(center_x, center_y, dlg_width, dlg_height)

        self.setModal(True)

        layout = QtGui.QFormLayout(self)
        self.axis_picker = QtGui.QComboBox()
        for axis in axis_names or ['레이어 이름 순']:
            self.axis_picker.addItem(axis)
        layout.addRow('보간 축', self.axis_picker)

        self.start_picker = QtGui.QComboBox()
        self.end_picker = QtGui.QComboBox()
        layout.addRow('시작 좌표', self.start_picker)
        layout.addRow('끝 좌표', self.end_picker)
        
        self.selected_only = QtGui.QCheckBox("선택된 글리프만 타겟으로")
        self.selected_only.setChecked(SELECTED_ONLY)
        layout.addRow(self.selected_only)
        
        self.apply_button = QtGui.QPushButton('사이드 베어링 보간하기')
        self.apply_button.clicked.connect(self.apply)
        layout.addRow(self.apply_button)

        self.axis_picker.currentIndexChanged.connect(self.update_range)
        self.start_picker.currentIndexChanged.connect(self.update_apply_button)
        self.end_picker.currentIndexChanged.connect(self.update_apply_button)
        self.update_range()

    def update_range(self):
        axis_index = self.axis_picker.currentIndex
        for picker in (self.start_picker, self.end_picker):
            picker.clear()
            for coordinate in self.coordinates[axis_index]:
                picker.addItem(self.labels.get(coordinate, f'{coordinate:g}'), coordinate)
        self.end_picker.setCurrentIndex(self.end_picker.count - 1)
        self.update_apply_button()

    def update_apply_button(self):
        self.apply_button.setEnabled(0 <= self.start_picker.currentIndex < self.end_picker.currentIndex)

    def apply(self):
        axis_index = self.axis_picker.currentIndex
        start = self.start_picker.currentData
        end = self.end_picker.currentData
        glyph_layers = self.glyph_layers
        if self.selected_only.isChecked():
            if not fl6.CurrentGlyph():
                QtGui.QMessageBox.information(self, '사이드베어링 보간', '현재 글리프를 활성화해 주세요.')
                return
            glyph_layers = [(glyph, master_layers(glyph, self.axis_names, self.master_order))
                            for glyph in getProcessGlyphs(0)]
        plans = [(glyph, plan_interpolation(glyph, layers, axis_index, start, end))
                 for glyph, layers in glyph_layers]
        if not any(updates for _, updates in plans):
            QtGui.QMessageBox.information(self, '사이드베어링 보간', '선택한 범위에 보간할 메트릭이 없습니다.')
            return
        for glyph, updates in plans:
            apply_interpolation(glyph, updates)
        self.accept()


def main():
    if not fl6.CurrentFont():
        print('열린 폰트가 없습니다.')
        return
    workspace = fl6.flWorkspace.instance()
    pMode = 1 if workspace.getActiveCanvas() is not None else 2
    # if mode == 0: [selected glyph]
    # if mode == 1: [glyphs in edit window]
    # if mode == 2: [selected glyphs in font window]
    # if mode == 3: [all glyphs in font]
    font = pFont()
    axis_names = [axis.shortName for axis in font.pDesignSpace.axes_list]
    master_names = sorted(font.masters())
    master_order = {name: index for index, name in enumerate(master_names)}
    coordinates = [set() for _ in axis_names or ['레이어 이름 순']]
    glyph_layers = [(glyph, master_layers(glyph, axis_names, master_order))
                    for glyph in getProcessGlyphs(pMode)]
    for _, layers in glyph_layers:
        for _, position in layers:
            for values, coordinate in zip(coordinates, position):
                values.add(coordinate)
    if not any(coordinates) and fl6.CurrentGlyph():
        for glyph in getProcessGlyphs(0):
            for _, position in master_layers(glyph, axis_names, master_order):
                for values, coordinate in zip(coordinates, position):
                    values.add(coordinate)

    if not any(coordinates):
        print('보간할 마스터가 없습니다.')
        return
    labels = {} if axis_names else dict(enumerate(master_names))
    dialog = InterpolateDialog(axis_names, glyph_layers,
                               [sorted(values) for values in coordinates], labels, master_order)
    dialog.exec_()


main()

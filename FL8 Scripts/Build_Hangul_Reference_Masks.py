#FLM: MW: Build Hangul Reference Masks

import fontlab as fl6
from PythonQt import QtCore, QtGui
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.objects.glyph import pGlyph

qapp = QtGui.QApplication.instance()
app_version = '1.1.0'
app_name = 'Minwoo | Build Hangul Reference Masks'


# -------- Settings --------
LAYER_NAME = None            # None: current foreground master; or e.g. "Regular"
MASK_MODE = "append"  # "skip": 기존 내용 있으면 건너뛰기
                      # "replace": 기존 도형 지우고 복사
                      # "append": 기존 도형에 추가
SELECTED_ONLY = False       # True: selected glyphs only

INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
BASE, END, BLOCK = 0xAC00, 0xD7A3, 21 * 28

def valid(obj):
    if obj is None:
        return False
    value = obj.isValid
    return bool(value() if callable(value) else value)
    
def hangul_codes(glyph):
    return [int(u) for u in glyph.unicodes
            if BASE <= int(u) <= END]

def build_masks(source_initial, target_initials, layer_name, mask_mode, selected_only):
    if not fl6.CurrentFont():
        raise RuntimeError("열린 폰트가 없습니다.")
    source_index = INITIALS.index(source_initial)
    target_initials = set(target_initials) - {source_initial}
    font = pFont()
    if layer_name is None:
        active = pGlyph().layer()
        if not valid(active) or active.isMaskLayer or not active.isMasterLayer:
            raise RuntimeError("마스크가 아닌 마스터 레이어를 활성화해 주세요.")
        layer_name = active.name
    elif layer_name not in font.masters():
        raise RuntimeError("현재 폰트에 '{}' 마스터가 없습니다.".format(layer_name))

    # Unicode lookup: no dependency on uniXXXX/CID glyph names.
    by_unicode = {}
    raw_glyphs = list(font.glyphs())
    for raw in raw_glyphs:
        for u in raw.unicodes:
            u = int(u)
            if BASE <= u <= END:
                if u in by_unicode and by_unicode[u] != raw.name:
                    raise RuntimeError("Duplicate Unicode: U+{:04X}".format(u))
                by_unicode[u] = raw.name

    targets = (font.selectedGlyphs() if selected_only
               else [font.glyph(raw.name) for raw in raw_glyphs])
    copied, skipped = 0, 0

    for target in targets:
        codes = hangul_codes(target)
        matches = []
        for u in codes:
            initial = INITIALS[(u - BASE) // BLOCK]
            if initial in target_initials:
                matches.append(u)
        if not matches:
            continue
        source_codes = {BASE + source_index * BLOCK + (u - BASE) % BLOCK
                        for u in matches}
        if len(source_codes) != 1:
            print("SKIP {}: ambiguous Unicode mapping".format(target.name))
            skipped += 1
            continue

        target_u = matches[0]
        source_u = next(iter(source_codes))
        label = "{} <- {} ({})".format(chr(target_u), chr(source_u), layer_name)
        source_name = by_unicode.get(source_u)
        if source_name is None:
            print("SKIP {}: source glyph missing".format(label))
            skipped += 1
            continue
        source = font.glyph(source_name)

        # findLayer does not create a missing layer.
        src_layer = source.fl.findLayer(layer_name)
        dst_layer = target.fl.findLayer(layer_name)
        if not valid(src_layer) or not valid(dst_layer):
            print("SKIP {}: matching layer missing".format(label))
            skipped += 1
            continue
        shapes = list(source.shapes(layer_name))
        if not shapes:
            print("SKIP {}: source layer empty".format(label))
            skipped += 1
            continue
        existing_mask = dst_layer.getMaskLayer(False)
        if valid(existing_mask) and existing_mask.shapes and mask_mode == "skip":
            print("SKIP {}: mask already contains shapes".format(label))
            skipped += 1
            continue
        # Clone before touching the destination; preserve original coordinates.
        copies = [shape.clone() for shape in shapes]
        for shape in copies:
            shape.independedAll()
        mask = dst_layer.getMaskLayer(True)
        if not valid(mask):
            raise RuntimeError("Cannot create mask: {}".format(label))
        if mask_mode == "replace":
            mask.removeAllShapes()
        for shape in copies:
            mask.addShape(shape)
        target.updateObject(target.fl, "Hangul reference mask: " + label,
                            verbose=False)
        copied += 1
        print("OK {}".format(label))

    print("Layer: {} | copied: {} | skipped: {}".format(layer_name, copied, skipped))

class HangulMaskDialog(QtGui.QDialog):
    def __init__(self):
        super(HangulMaskDialog, self).__init__()
        self.setWindowTitle('%s %s' %(app_name, app_version))
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        width = 380
        height = 450
        desktop_geo = qapp.desktop().geometry
        center_x = desktop_geo.x() + int(desktop_geo.width() / 2) - int(width / 2)
        center_y = desktop_geo.y() + int(desktop_geo.height() / 2) - int(height / 2)
        self.setGeometry(center_x, center_y, width, height)
        self.setStyleSheet("""
            QPushButton { min-height: 25px; }
            QGroupBox QPushButton { font-size: 17px; }
            QPushButton:checked {
                background-color: #3585fd;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:pressed { background-color: #2d77e2; }
        """)

        layout = QtGui.QVBoxLayout(self)
        source_box, self.source_buttons = self.initial_picker("소스 초성", "ㅁ", True)
        target_box, self.target_buttons = self.initial_picker("타겟 초성", "ㅇ", False)
        layout.addWidget(source_box)
        layout.addWidget(target_box)

        settings = QtGui.QFormLayout()
        settings.setVerticalSpacing(10)
        self.layer_picker = QtGui.QComboBox()
        self.layer_picker.addItem("현재 마스터")
        if fl6.CurrentFont():
            for name in pFont().masters():
                self.layer_picker.addItem(name, name)
        if LAYER_NAME is not None:
            index = self.layer_picker.findData(LAYER_NAME)
            if index >= 0:
                self.layer_picker.setCurrentIndex(index)
        settings.addRow("마스터", self.layer_picker)

        self.mask_mode_picker = QtGui.QComboBox()
        self.mask_mode_picker.addItem("기존 마스크에 추가", "append")
        self.mask_mode_picker.addItem("기존 마스크가 있으면 건너뛰기", "skip")
        self.mask_mode_picker.addItem("기존 마스크 도형 교체", "replace")
        self.mask_mode_picker.setCurrentIndex(self.mask_mode_picker.findData(MASK_MODE))
        settings.addRow("마스크 처리", self.mask_mode_picker)

        self.selected_only = QtGui.QCheckBox("선택된 글리프만 타겟으로")
        self.selected_only.setChecked(SELECTED_ONLY)
        settings.addRow(self.selected_only)
        layout.addLayout(settings)

        self.apply_button = QtGui.QPushButton("마스크 넣기")
        self.apply_button.clicked.connect(self.apply_masks)
        layout.addWidget(self.apply_button)

        self.source_buttons.buttonToggled.connect(self.update_targets)
        self.target_buttons.buttonToggled.connect(self.update_targets)
        self.update_targets()
        self.source_buttons.checkedButton().setFocus()

    def initial_picker(self, title, default, exclusive):
        box = QtGui.QGroupBox(title)
        grid = QtGui.QGridLayout(box)
        grid.setSpacing(1)
        group = QtGui.QButtonGroup(box)
        group.setExclusive(exclusive)
        for index, initial in enumerate(INITIALS):
            button = QtGui.QPushButton(initial)
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setFixedSize(45, 33)
            group.addButton(button, index)
            grid.addWidget(button, index // 7, index % 7)
            button.setChecked(initial == default)
        return box, group

    def update_targets(self):
        source_id = self.source_buttons.checkedId()
        for index in range(len(INITIALS)):
            button = self.target_buttons.button(index)
            if index == source_id and button.isChecked():
                button.setChecked(False)
            button.setEnabled(index != source_id)
        self.apply_button.setEnabled(any(button.isChecked() for button in self.target_buttons.buttons()))

    def apply_masks(self):
        source_initial = INITIALS[self.source_buttons.checkedId()]
        target_initials = [INITIALS[index] for index in range(len(INITIALS))
                           if self.target_buttons.button(index).isChecked()]
        try:
            build_masks(source_initial, target_initials,
                        self.layer_picker.currentData, self.mask_mode_picker.currentData,
                        self.selected_only.isChecked())
        except RuntimeError as error:
            QtGui.QMessageBox.warning(self, "마스크 넣기", str(error))


dialog = HangulMaskDialog()
dialog.show()

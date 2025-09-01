#FLM: MW: Jitter Glyphs
import math, random, warnings

import fontlab as fl6
import fontgate as fgt

from typerig.proxy.fl.objects.font import eFont
from typerig.proxy.fl.objects.glyph import pGlyph
from typerig.proxy.fl.objects.node import eNode
from typerig.proxy.fl.application.app import *
from typerig.proxy.fl.application.app import pWorkspace

from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui
from typerig.proxy.fl.gui.widgets import getProcessGlyphs

flP = fl6.flPackage(fl6.CurrentFont())
qapp = QtGui.QApplication.instance()
ws = fl6.flWorkspace.instance()
font = eFont()
fontMetrics = font.fontMetricsInfo(0)
upm = fontMetrics.upm
nT = fgt.fgNametable()
yTop, yBottom = fontMetrics.ascender, fontMetrics.descender
fontHeight = yTop - yBottom
initialValues = {
                'min_len': 10, 
                'max_len': 80, 
                'min_move_x': -20, 
                'max_move_x': 20, 
                'min_move_y': -20, 
                'max_move_y': 20, 
                'focus': 0,
                'simplify': False,
                'collapse': False,
                'edge_effect_strength': 0 # New parameter
            }


global pMode
pMode = 0
    # if mode == 0: [selected glyph]
    # if mode == 1: [glyphs in edit window]
    # if mode == 2: [selected glyphs in font window]
    # if mode == 3: [all glyphs in font]

table_draw_size = 130
canvas_draw_size = 450

color_white = QtGui.QColor('white')
color_gray = QtGui.QColor('lightgray')
color_black = QtGui.QColor('black')
color_gold = QtGui.QColor('gold')
color_coral = QtGui.QColor('coral')


# init ====
app_name, app_version = 'Minwoo | Jitter Glyphs', '1.0'


# Style Sheet ===
style = """
QWidget {
    background-color: #202020;
    color: #dddddd;
    margin: 0;
    padding: 0;
    font-family: SF Pro, Noto Sans Cjk KR, Arial, Helvetica, sans-serif;
    font-size: 13px;
}
QHeaderView::section {
    background-color: #262626;
    border-bottom: 1px solid #2B2B2B;
    height: 25px;
}
QHeaderView::down-arrow {
    border-top: 3px solid #ffffff; 
    border-left: 4px solid none; 
    border-right: 4px solid none; 
    width: 0; 
    height: 0;
}
QHeaderView::up-arrow {
    border-bottom: 3px solid #cccccc; 
    border-left: 4px solid none; 
    border-right: 4px solid none; 
    width: 0; 
    height: 0;
}
QTreeView {
    alternate-background-color: #444444;
    border: 2px solid #3d3e3e;
    background: #313233;
    margin: 20px 0 0 0;
    text-align: center;
}
QTreeView::item{
    height:25px;
    font-size: 12px;
}
QGroupBox{
    border: 2px solid #3d3e3e;
    background: #313233;
    padding: 5px 0;
    margin: 18px 0 0 0;
}
QGroupBox:title {
    subcontrol-origin: margin;
}
QHeaderView, QPushButton, QLabel {
    font-weight: 400;
}
QLabel{
    background: transparent;
    font-size: 15px;
}

QPushButton{
    background-color: #202020;
    border-radius: 5px;
    height: 35px;
    border: 1px solid #5E5E5E;
    font-size: 15px;
}
QPushButton:hover{
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 5px;
    height: 30px;
    border: 1px solid #6C6C6C;
}
QPushButton:checked{
    background-color: rgba(255, 255, 255, 0.35);
    border-radius: 5px;
    height: 35px;
    border: 1px solid #7E7E7E;
}
QPushButton:checked:hover{
    background-color: rgba(255, 255, 255, 0.5);
    border-radius: 5px;
    height: 30px;
    border: 1px solid #8C8C8C;
}
QPushButton:disabled {
    background-color: #333333;
    color: #5E5E5E
}
QCheckBox {
    font-size: 15px;
}
QComboBox {
    padding-left: 6px;
    height: 25px;
    background-color: #1A1B1C;
    width: 80px;
    border:none;
    selection-background-color: rgba(255, 255, 255, 0.2);
}

QComboBox::drop-down{
    background: #4A4A4A;
}
QComboBox::down-arrow {
    margin: 0 4px;
    border-top: 3px solid #cccccc; 
    border-left: 4px solid #4A4A4A; 
    border-right: 4px solid #4A4A4A; 
    width: 0; 
    height: 0;
}
QComboBox:hover {
    background-color: rgba(255, 255, 255, 0.2);
}
QComboBox::drop-down:hover{
    background: #666666;
}
QComboBox::down-arrow:hover {
    margin: 0 4px;
    border-top: 3px solid #cccccc; 
    border-left: 4px solid #666666; 
    border-right: 4px solid #666666; 
    width: 0; 
    height: 0;
}
QComboBox:on {
    background-color: rgba(255, 255, 255, 0.2);
    color: #dddddd;
    border: none;
}
QComboBox::drop-down:on{
    background: #666666;
}
QComboBox::down-arrow:on {
    margin: 0 7px;
    margin-bottom: 2px;
    margin-top: 0;
    border-top: none;
    border-bottom: 3px solid #cccccc; 
    border-left: 4px solid #666666; 
    border-right: 4px solid #666666; 
    width: 0; 
    height: 0;
}
QComboBox QAbstractItemView {
    selection-background-color: rgba(255, 255, 255, 0.2);
}

QSpinBox { 
    padding-left: 20px;
    height: 25px;
    background-color: #1A1B1C;
    width: 100px;
    selection-background-color: rgba(255, 255, 255, 0.2);

}

QSpinBox::up-button { 
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px; 
    background: #4A4A4A;
}
QSpinBox::up-button:hover { 
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px; 
    background-color: #666666;
}
QSpinBox::down-button { 
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px; 
    background: #4A4A4A;
}
QSpinBox::down-button:hover { 
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px; 
    background-color: #666666;
}

QSpinBox::up-arrow { 
    margin-top: 0;
    background: transparent;
    border-bottom: 3px solid #cccccc; 
    border-left: 4px solid #4A4A4A; 
    border-right: 4px solid #4A4A4A; 
    width: 0; 
    height: 0;
}
QSpinBox::up-arrow:hover {     
    margin-top: 0;
    background: transparent;
    border-bottom: 3px solid #ffffff; 
    border-left: 4px solid #666666; 
    border-right: 4px solid #666666; 
    width: 0; 
    height: 0;
}
QSpinBox::down-arrow { 
    margin-bottom: 0;
    background: transparent;
    border-top: 3px solid #cccccc; 
    border-left: 4px solid #4A4A4A; 
    border-right: 4px solid #4A4A4A; 
    width: 0; 
    height: 0;
}
QSpinBox::down-arrow:hover { 
    margin-bottom: 0;
    background: transparent;
    border-top: 3px solid #ffffff; 
    border-left: 4px solid #666666; 
    border-right: 4px solid #666666; 
    width: 0; 
    height: 0;
}

"""

def concatStr(*args):
    new_str = []
    for i in args:
        new_str.append(i)
    new_str = ''.join(new_str)
    return new_str

def signInt(x):
    return (x > 0) - (x < 0)

class TableWidgetItem(QtGui.QTableWidgetItem):
    def __init__(self, index, contours, aux):
        super(TableWidgetItem, self).__init__()
        self.index = index
        self.contours = contours
        self.aux = aux
        self.pixmap = self.aux.drawIcon(self.contours).scaled(table_draw_size, table_draw_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.new_icon = QtGui.QIcon(self.pixmap)
        self.setSizeHint(QtCore.QSize(table_draw_size, table_draw_size))
        self.setIcon(self.new_icon)



class TableWidget(QtGui.QTableWidget):
    def __init__(self, aux):
        super(TableWidget, self).__init__()

        self.aux = aux
        self.set_table()	
        self.setIconSize(QtCore.QSize(table_draw_size, table_draw_size))
        self.setShowGrid(False)
        # self.setFocusPolicy(QtCore.Qt.TabFocus)

        # self.setStyleSheet('border: 1px solid red')

    def set_table(self, clear=True):
        # - Fix sorting
        if clear: self.clear()
        self.blockSignals(True)
        # self.setDragDropMode(self.InternalMove)
        # self.setDragEnabled(True)
        # self.setDropIndicatorShown(True)
        # self.model().sort(-1)
        self.setSelectionMode(1)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setDefaultSectionSize(table_draw_size)
        self.verticalHeader().setDefaultSectionSize(table_draw_size)
        self.verticalHeader().setFixedWidth(20)
        self.setIconSize(QtCore.QSize(table_draw_size, table_draw_size))
        # - Init
        # column_names = []
        self.setRowCount(0)
        self.setColumnCount(1)
        # self.resizeRowsToContents()
        # self.resizeColumnsToContents()

        self.blockSignals(False)

    def keyPressEvent(self, e):
        if e.key() != QtCore.Qt.Key_Down and e.key() != QtCore.Qt.Key_Up :
            e.ignore()
            return
        QtGui.QTableWidget.keyPressEvent(self, e)

    
class CustomBtn(QtGui.QPushButton):
    def __init__(self, button_text, checkable=False, checked=False, enabled=True, tooltip=None, obj_name=None):
        super(CustomBtn, self).__init__(button_text)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
    
class CustomSpinBox(QtGui.QSpinBox):
    def __init__(self, *args):
        super(CustomSpinBox, self).__init__(*args)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def keyPressEvent(self, e):
        key = e.key()
        # print(e, key)
        if key == QtCore.Qt.Key_Escape:
            self.clearFocus()
        if key in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down] and (e.modifiers() & QtCore.Qt.ShiftModifier):
            self.setSingleStep(10)
        else:
            self.setSingleStep(1)
        QtGui.QSpinBox.keyPressEvent(self, e)


    #         return e
    #     else:
    #         self.clearFocus()
    #         print(2)


class PreviewCanvas(QtGui.QLabel):
    def __init__(self, aux, isOriginal=True):
        super(PreviewCanvas, self).__init__()    

        self.aux = aux
        
        self.glyph = aux.glyph
        self.isOriginal = isOriginal
        self.glyhp_pixmaps = self.pixmaps_refresh()
        self.setFocusPolicy(QtCore.Qt.NoFocus)


    def setData(self):
        if self.isOriginal == True:
            self.data = self.aux.originalContours
        else:
            self.data = self.aux.selectedContours


    def pixmaps_refresh(self):
        self.setData()
        return_pixmap = self.aux.drawCanvas(self.data).scaled(canvas_draw_size, canvas_draw_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(return_pixmap)

        return return_pixmap
    



class MainWindow(QtGui.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.workspace = pWorkspace()
        self.activeCanvas = self.workspace.getCanvas()
        self.tempValues = False
        self.readPreference()
        self.showNode = False
        self.simplify = self.inputValues.get('simplify', False)
        self.collapse = self.inputValues.get('collapse', False)
        self.setData()


        # spacer
        self.hSpacer300 = QtGui.QSpacerItem(300, 1)
        self.hSpacer400 = QtGui.QSpacerItem(400, 1)
        self.hSpacer500 = QtGui.QSpacerItem(500, 1)

        self.lbl_header = QtGui.QLabel(f'Selected Glyph : {self.glyph.name} ( {self.chr} )')
        self.btn_prevGlyph = CustomBtn('Previous Glyph')
        self.btn_nextGlyph = CustomBtn('Next Glyph')

        self.header_Widget = QtGui.QWidget()
        self.header_GridLayout = QtGui.QGridLayout()
        self.header_GridLayout.addWidget(self.lbl_header,       0, 0, 1, 1)
        self.header_GridLayout.addItem(self.hSpacer400,         0, 1, 1, 4)
        self.header_GridLayout.addWidget(self.btn_prevGlyph,    0, 5, 1, 1, QtCore.Qt.AlignBottom)
        self.header_GridLayout.addWidget(self.btn_nextGlyph,    0, 6, 1, 1, QtCore.Qt.AlignBottom)
        self.header_GridLayout.setContentsMargins(0, 25, 0, 0)
        self.header_Widget.setLayout(self.header_GridLayout)


        self.original_GroupBox = QtGui.QGroupBox('Original')
        self.original_HBoxLayout = QtGui.QHBoxLayout()

        self.original_canvas = PreviewCanvas(self)
        self.original_HBoxLayout.addWidget(self.original_canvas)
        self.original_GroupBox.setLayout(self.original_HBoxLayout)

        self.preview_GroupBox = QtGui.QGroupBox('Preview')
        self.preview_HBoxLayout = QtGui.QHBoxLayout()
        self.preview_canvas = PreviewCanvas(self, False)
        self.preview_Table = TableWidget(self)
        
        self.preview_HBoxLayout.addWidget(self.preview_Table)
        self.preview_HBoxLayout.addWidget(self.preview_canvas)
        self.preview_GroupBox.setLayout(self.preview_HBoxLayout)

        # -- Jitter Controls --
        # Min/Max Length
        self.edt_min_len = CustomSpinBox()
        self.edt_min_len.setRange(1, 500)
        self.edt_min_len.setValue(self.inputValues['min_len'])
        self.edt_min_len.setAlignment(0x0002)
        self.edt_min_len.setMaximumWidth(60)
        self.edt_min_len.setSuffix('u')

        self.edt_max_len = CustomSpinBox()
        self.edt_max_len.setRange(1, 500)
        self.edt_max_len.setValue(self.inputValues['max_len'])
        self.edt_max_len.setAlignment(0x0002)
        self.edt_max_len.setMaximumWidth(60)
        self.edt_max_len.setSuffix('u')

        # Min/Max Move X
        self.edt_min_move_x = CustomSpinBox()
        self.edt_min_move_x.setRange(-500, 500)
        self.edt_min_move_x.setValue(self.inputValues['min_move_x'])
        self.edt_min_move_x.setAlignment(0x0002)
        self.edt_min_move_x.setMaximumWidth(60)

        self.edt_max_move_x = CustomSpinBox()
        self.edt_max_move_x.setRange(-500, 500)
        self.edt_max_move_x.setValue(self.inputValues['max_move_x'])
        self.edt_max_move_x.setAlignment(0x0002)
        self.edt_max_move_x.setMaximumWidth(60)

        # Min/Max Move Y
        self.edt_min_move_y = CustomSpinBox()
        self.edt_min_move_y.setRange(-500, 500)
        self.edt_min_move_y.setValue(self.inputValues['min_move_y'])
        self.edt_min_move_y.setAlignment(0x0002)
        self.edt_min_move_y.setMaximumWidth(60)

        self.edt_max_move_y = CustomSpinBox()
        self.edt_max_move_y.setRange(-500, 500)
        self.edt_max_move_y.setValue(self.inputValues['max_move_y'])
        self.edt_max_move_y.setAlignment(0x0002)
        self.edt_max_move_y.setMaximumWidth(60)

        # Focus
        self.edt_focus = CustomSpinBox()
        self.edt_focus.setRange(-300, 300)
        self.edt_focus.setValue(self.inputValues['focus'])
        self.edt_focus.setAlignment(0x0002)
        self.edt_focus.setMaximumWidth(150)
        self.edt_focus.setSuffix('%')

        self.btn_reset = CustomBtn('↺')
        self.btn_transform = CustomBtn('Transform')

        # Labels
        self.lbl_segment_len = QtGui.QLabel('Segment Length')
        self.lbl_move_x = QtGui.QLabel('Move X')
        self.lbl_move_y = QtGui.QLabel('Move Y')
        self.lbl_focus = QtGui.QLabel('Focus')

        self.input_GroupBox = QtGui.QGroupBox()
        self.input_GridLayout = QtGui.QGridLayout()
        self.input_GroupBox.setStyleSheet('margin: 0; padding:0 0 0 3px; border:1px solid transparent;')
        self.btn_reset.setStyleSheet('border: 1px solid #5E5E5E;')
        self.btn_transform.setStyleSheet('border: 1px solid #5E5E5E;')

        # Layout
        self.input_GridLayout.addWidget(self.lbl_segment_len, 0, 0, 1, 2)
        self.input_GridLayout.addWidget(self.edt_min_len, 0, 2, 1, 1)
        self.input_GridLayout.addWidget(self.edt_max_len, 0, 3, 1, 1)

        self.input_GridLayout.addWidget(self.lbl_move_x, 1, 0, 1, 2)
        self.input_GridLayout.addWidget(self.edt_min_move_x, 1, 2, 1, 1)
        self.input_GridLayout.addWidget(self.edt_max_move_x, 1, 3, 1, 1)

        self.input_GridLayout.addWidget(self.lbl_move_y, 2, 0, 1, 2)
        self.input_GridLayout.addWidget(self.edt_min_move_y, 2, 2, 1, 1)
        self.input_GridLayout.addWidget(self.edt_max_move_y, 2, 3, 1, 1)
        
        self.input_GridLayout.addWidget(self.lbl_focus, 3, 0, 1, 2)
        self.input_GridLayout.addWidget(self.edt_focus, 3, 2, 1, 2)

        self.lbl_edge_effect = QtGui.QLabel('Edge Effect')
        self.edt_edge_effect = CustomSpinBox()
        self.edt_edge_effect.setRange(0, 100)
        self.edt_edge_effect.setValue(self.inputValues.get('edge_effect_strength', 0))
        self.edt_edge_effect.setAlignment(0x0002)
        self.edt_edge_effect.setMaximumWidth(60)
        self.edt_edge_effect.setSuffix('%')

        self.input_GridLayout.addWidget(self.lbl_edge_effect, 4, 0, 1, 2)
        self.input_GridLayout.addWidget(self.edt_edge_effect, 4, 2, 1, 1)

        # Add spacer to push controls to the top
        self.input_GridLayout.addItem(QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding), 5, 0)


        self.input_GridLayout.addWidget(self.btn_transform, 11, 0, 1, 3)
        self.input_GridLayout.addWidget(self.btn_reset, 11, 3, 1, 1)

        self.input_GroupBox.setLayout(self.input_GridLayout)
        self.original_HBoxLayout.addWidget(self.input_GroupBox)

        # footer
        self.chk_showNode = QtGui.QCheckBox('Show Nodes')
        self.chk_showNode.setChecked(self.showNode)
        self.chk_showNode.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_collapse = CustomBtn('Collapse')
        self.btn_collapse.setCheckable(True)
        self.btn_collapse.setChecked(self.collapse)
        self.btn_simplify = CustomBtn('Simplify')
        self.btn_simplify.setCheckable(True)
        self.btn_simplify.setChecked(self.simplify)
        self.btn_apply = CustomBtn('Apply')
        self.btn_close = CustomBtn('Close')

        self.footer_Widget = QtGui.QWidget()
        self.footer_GridLayout = QtGui.QGridLayout()
        self.footer_GridLayout.addWidget(self.chk_showNode, 0, 0, 1, 1, QtCore.Qt.AlignTop)
        self.footer_GridLayout.addItem(self.hSpacer300,     0, 1, 1, 2)
        self.footer_GridLayout.addWidget(self.btn_collapse, 0, 3, 1, 1)
        self.footer_GridLayout.addWidget(self.btn_simplify, 0, 4, 1, 1)
        self.footer_GridLayout.addWidget(self.btn_apply,    0, 5, 1, 1)
        self.footer_GridLayout.addWidget(self.btn_close,    0, 6, 1, 1)
        self.footer_GridLayout.setContentsMargins(0, 0, 0, 0)
        self.footer_Widget.setLayout(self.footer_GridLayout)

        self.gridLayout = QtGui.QGridLayout()
#       QGridLayout.addWidget(widget, fromRow, fromCol, rowSpan, colSpan)
        self.gridLayout.addWidget(self.header_Widget,       0,  0,  1, 10)
        self.gridLayout.addWidget(self.original_GroupBox,   1,  0,  5,  5)
        self.gridLayout.addWidget(self.preview_GroupBox,    1,  5,  5,  5)
        self.gridLayout.addWidget(self.footer_Widget,       6,  0,  1, 10)

        self.setLayout(self.gridLayout)

        # slots
        self.btn_prevGlyph.clicked.connect(self.prevClicked)
        self.btn_nextGlyph.clicked.connect(self.nextClicked)
        
        self.edt_min_len.editingFinished.connect(lambda: self.spinboxChanged(self.edt_min_len, 'min_len'))
        self.edt_max_len.editingFinished.connect(lambda: self.spinboxChanged(self.edt_max_len, 'max_len'))
        self.edt_min_move_x.editingFinished.connect(lambda: self.spinboxChanged(self.edt_min_move_x, 'min_move_x'))
        self.edt_max_move_x.editingFinished.connect(lambda: self.spinboxChanged(self.edt_max_move_x, 'max_move_x'))
        self.edt_min_move_y.editingFinished.connect(lambda: self.spinboxChanged(self.edt_min_move_y, 'min_move_y'))
        self.edt_max_move_y.editingFinished.connect(lambda: self.spinboxChanged(self.edt_max_move_y, 'max_move_y'))
        self.edt_focus.editingFinished.connect(lambda: self.spinboxChanged(self.edt_focus, 'focus'))
        self.edt_edge_effect.editingFinished.connect(lambda: self.spinboxChanged(self.edt_edge_effect, 'edge_effect_strength'))

        self.btn_reset.clicked.connect(self.resetValue)
        self.btn_transform.clicked.connect(self.add_tableItem)
        self.chk_showNode.clicked.connect(self.toggle_nodeVisibility)
        self.btn_collapse.toggled.connect(self.toggle_collapse)
        self.btn_simplify.toggled.connect(self.toggle_simplify)
        self.btn_apply.clicked.connect(self.apply_transform)
        self.btn_close.clicked.connect(self.closeWidget)
        self.preview_Table.currentCellChanged.connect(self.paintPreviewCanvas)
        self.preview_Table.cellClicked.connect(self.paintPreviewCanvas)

        self.setStyleSheet(style)
        self.header_Widget.setStyleSheet(style)
        self.footer_Widget.setStyleSheet(style)
        self.setWindowTitle(f'{app_name} {app_version}')
        self.setGeometry(300, 100, 1450, 630)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocus()

        # self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) # Always on top!!
        
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        qapp.applicationStateChanged.connect(self.setFlag)
        self.show()
        self.toggle_collapse()
        self.toggle_simplify()


    def prevClicked(self): 
        prevGlyph = font.glyph(self.glyph.index-1)

        self.preview_Table.clear()
        self.preview_Table.setRowCount(0)
        self.setData(prevGlyph)
        self.original_canvas.pixmaps_refresh()
        self.preview_canvas.pixmaps_refresh()
        self.lbl_header.setText(f'Selected Glyph : {self.glyph.name} ( {self.chr} )')


    def nextClicked(self): 
        nextGlyph = font.glyph(self.glyph.index+1)

        self.preview_Table.clear()
        self.preview_Table.setRowCount(0)
        self.setData(nextGlyph)
        self.original_canvas.pixmaps_refresh()
        self.preview_canvas.pixmaps_refresh()
        self.lbl_header.setText(f'Selected Glyph : {self.glyph.name} ( {self.chr} )')

    def toggle_nodeVisibility(self):
        self.showNode = self.chk_showNode.isChecked()
        self.original_canvas.pixmaps_refresh()
        self.preview_canvas.pixmaps_refresh()

    def toggle_collapse(self):
        self.collapse = self.btn_collapse.isChecked()
        onoff = "On" if self.collapse else "Off"
        self.btn_collapse.setText(f'Collapse {onoff}')
        self.inputValues['collapse'] = self.collapse # Save state

    def toggle_simplify(self):
        self.simplify = self.btn_simplify.isChecked()
        onoff = "On" if self.simplify else "Off"
        self.btn_simplify.setText(f'Simplify {onoff}')
        self.inputValues['simplify'] = self.simplify # Save state to inputValues


    def spinboxChanged(self, sender, value): 
        self.inputValues[value] = sender.value

    def paintPreviewCanvas(self):
        try:
            self.selectedContours = self.preview_Table.selectedItems()[0].contours
        except:
            self.selectedContours = []
        self.preview_canvas.pixmaps_refresh()

    def resetValue(self):
        if self.tempValues :
            self.inputValues = self.tempValues
            self.tempValues = False
        else :
            self.tempValues = {**self.inputValues}
            self.inputValues = initialValues
        
        self.edt_min_len.setValue(self.inputValues['min_len'])
        self.edt_max_len.setValue(self.inputValues['max_len'])
        self.edt_min_move_x.setValue(self.inputValues['min_move_x'])
        self.edt_max_move_x.setValue(self.inputValues['max_move_x'])
        self.edt_min_move_y.setValue(self.inputValues['min_move_y'])
        self.edt_max_move_y.setValue(self.inputValues['max_move_y'])
        self.edt_focus.setValue(self.inputValues['focus'])


    def add_tableItem(self):
        processed_contours = self.getProcessedContours()

        # self.original_canvas.pixmaps_refresh()
        # self.preview_canvas.pixmaps_refresh()

        i = self.preview_Table.rowCount #0
        j = self.preview_Table.columnCount -1 #1
        newItem = TableWidgetItem(i, processed_contours, self)
        self.preview_Table.setRowCount(i+1)
        self.preview_Table.setItem(i, j, newItem)
        self.preview_Table.setCurrentCell(i, j)


    #edit another glyph
    def setData(self, pG=None):
        if pG == None:
            self.glyph = pGlyph()
        else: 
            self.glyph = pG

        self.adv = self.glyph.getAdvance()
        self.xmin = self.glyph.getLSB()
        self.xmax = self.xmin+self.adv
        self.slicedName = list(self.glyph.name.partition('.')) # ex) ['uniAC00','alt'] from 'uniAC00.alt' 
        self.chr = concatStr(chr(nT.unc(self.slicedName[0])), ''.join(self.slicedName[1:]))
        self.originalContours = []
        self.selectedContours = []

        for shape in self.glyph.shapes():
            cloned_shape = shape.clone()
            cloned_shape.applyTransform()
            self.originalContours.extend(cloned_shape.contours)

        self.refresh()

    #refresh data / pixmap
    def refresh(self):
        self.glyph.update()
        try:
            pWorkspace().getCanvas(True).refreshAll()
        except AttributeError:
            print('Open Glyph Editing Window')

    def keyPressEvent(self, e):
        key = e.key()
        if key == QtCore.Qt.Key_Space:
            if self.showNode == False:
                self.showNode = True
                self.chk_showNode.setChecked(self.showNode)
                self.toggle_nodeVisibility()

    def keyReleaseEvent(self, e):
        key = e.key()

        if key == QtCore.Qt.Key_Space:
            if self.showNode == True:
                self.showNode = False
                self.chk_showNode.setChecked(self.showNode)
                self.toggle_nodeVisibility()

    def closeWidget(self):
        self.writePreference()
        self.close()

    def setFlag(self):
        if (qapp.applicationState() == QtCore.Qt.ApplicationActive):
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        self.show()
    
    def closeEvent(self, event):
        qapp.applicationStateChanged.disconnect(self.setFlag)
        event.accept()

    def apply_transform(self):
        self.layer_duplicate_mask()
        
        for shape in self.glyph.shapes():
            self.glyph.removeShape(shape)

        src_contours = [contour.clone() for contour in self.selectedContours]
        new_shape = fl6.flShape()

        for cid in range(len(src_contours)):
            new_shape.addContour(src_contours[cid], True) 

        self.glyph.layer().addShape(new_shape)
        self.glyph.updateObject(self.glyph.fl, 'Shape Modified')

        self.refresh()


    def subdivide_contour(self, contour):
        min_len = self.inputValues['min_len']
        max_len = self.inputValues['max_len']

        if max_len <= min_len:
            max_len = min_len + 1
        if min_len <= 0:
            min_len = 1

        # Per user instruction, this line is omitted.

        iterations = 0
        max_iterations = 5000 

        while iterations < max_iterations:
            was_split = False
            for i in range(len(contour.segments())):
                segment = contour.segments()[i]
                
                # Use fastLength as requested by user
                if segment.fastLength() > max_len:
                    # Segment is too long. Split it at a random point.
                    # Use a Gaussian distribution to make splits closer to the midpoint more likely.
                    # mu=0.5 (midpoint), sigma=0.1 makes it favor the center but allows some variation.
                    split_point = random.gauss(0.5, 0.1)
                    # Clamp to avoid splitting too close to the ends of the segment
                    split_point = max(0.1, min(0.9, split_point))

                    contour.insertNodeTo(i + split_point)
                    
                    was_split = True
                    # Break from the for loop and restart the while loop
                    # to get a fresh list of segments.
                    break
            
            if not was_split:
                # If we went through the whole contour and didn't split anything, we're done.
                break
            
            iterations += 1

        if iterations >= max_iterations:
            warnings.warn("Jitter: Max iterations reached in subdivide_contour. Contour may not be fully subdivided.")

    def jitter_nodes(self, contours):
        min_x = self.inputValues['min_move_x']
        max_x = self.inputValues['max_move_x']
        min_y = self.inputValues['min_move_y']
        max_y = self.inputValues['max_move_y']
        focus = self.inputValues['focus']

        mu_x = (min_x + max_x) / 2
        mu_y = (min_y + max_y) / 2

        # Calculate sigma based on absolute focus value
        abs_focus = abs(focus)
        focus_divisor = 6 * (abs_focus / 100.0)
        if focus_divisor == 0:
            focus_divisor = 0.01 # Prevent division by zero

        sigma_x = (max_x - min_x) / focus_divisor if max_x > min_x else 0
        sigma_y = (max_y - min_y) / focus_divisor if max_y > min_y else 0

        for contour in contours:
            for node in contour.nodes():
                if focus >= 0: # Normal bell curve distribution
                    dx = random.gauss(mu_x, sigma_x) if sigma_x > 0 else mu_x
                    dy = random.gauss(mu_y, sigma_y) if sigma_y > 0 else mu_y
                else: # Inverted bell curve (U-shaped) distribution
                    # Generate two uniform random numbers and pick the one further from the mean
                    # This creates a U-shaped distribution
                    r1_x = random.uniform(min_x, max_x)
                    r2_x = random.uniform(min_x, max_x)
                    dx = r1_x if abs(r1_x - mu_x) > abs(r2_x - mu_x) else r2_x

                    r1_y = random.uniform(min_y, max_y)
                    r2_y = random.uniform(min_y, max_y)
                    dy = r1_y if abs(r1_y - mu_y) > abs(r2_y - mu_y) else r2_y

                # Clamp the values to the min/max range to avoid extreme outliers
                dx = max(min_x, min(max_x, dx))
                dy = max(min_y, min(max_y, dy))

                # Apply edge effect
                multiplier = 1.0
                edge_effect_strength = self.inputValues.get('edge_effect_strength', 0)
                if edge_effect_strength > 0:
                    center_x = (self.xmin + self.xmax) / 2
                    center_y = (yTop + yBottom) / 2
                    width = self.xmax - self.xmin
                    height = yTop - yBottom

                    # Avoid division by zero if glyph has zero width/height
                    if width == 0: width = 1
                    if height == 0: height = 1

                    norm_x = abs(node.x - center_x) / (width / 2)
                    norm_y = abs(node.y - center_y) / (height / 2)
                    
                    radial_norm_dist = math.sqrt(norm_x**2 + norm_y**2)
                    radial_norm_dist = min(radial_norm_dist, 1.0) # Clamp to 1.0

                    multiplier = 1.0 + (radial_norm_dist * (edge_effect_strength / 100.0))

                node.x += dx * multiplier
                node.y += dy * multiplier
            
            if self.simplify:
                contour.simplify(1, True, True)
        
        return contours

    def getProcessedContours(self):
        cloned_contours = [c.clone() for c in self.originalContours]
        
        for contour in cloned_contours:
            self.subdivide_contour(contour)
            if self.collapse:
                for node in contour.nodes():
                    node.collapseHandles()

        return_contours = self.jitter_nodes(cloned_contours)
        return return_contours
    
    def drawCanvas(self, contours):     

        cloned_contours = [contour.clone() for contour in contours]
        main_shape = fl6.flShape()

        for cid in range(len(cloned_contours)):
            main_shape.addContour(cloned_contours[cid], True)

        # for cid in range(len(cloned_contours)):
        #     contour_shape = fl6.flShape()
        #     contour_shape.addContour()
        
        shape_bbox = main_shape.boundingBox
        draw_padding = 50
        draw_dimension = max(shape_bbox.width(), shape_bbox.height(), self.glyph.getAdvance(), fontHeight) + 2 * draw_padding
        cont_painter = QtGui.QPainter()
        cont_pixmap = QtGui.QPixmap(draw_dimension, draw_dimension)

        #background    
        cont_painter.begin(cont_pixmap)
        cont_painter.setBrush(QtGui.QBrush(color_white))
        cont_painter.drawRect(QtCore.QRectF(0, 0, draw_dimension, draw_dimension))

        #contour
        if self.showNode:
            cont_painter.setBrush(QtGui.QBrush(color_gray))
        else:
            cont_painter.setBrush(QtGui.QBrush(color_black))
        cont_painter.setPen(QtGui.QPen(color_black, 2, QtCore.Qt.SolidLine))
        new_transform = main_shape.transform.translate(-shape_bbox.x() + max((draw_dimension - shape_bbox.width())/2, draw_padding), -shape_bbox.y() + max((draw_dimension - shape_bbox.height())/2, draw_padding))
        main_shape.applyTransform(new_transform)
        main_shape.ensurePaths()
        draw_path = main_shape.closedPath
        cont_painter.drawPath(draw_path)
        
        # #nodes
        if self.showNode:
            for i in range(draw_path.elementCount()):
                draw_radius = 8
                cont_painter.setBrush(QtGui.QBrush(color_coral))
                cont_painter.setPen(QtGui.QPen(color_black, 1, QtCore.Qt.SolidLine))

                node_info = main_shape.getNodeAt(i, 7)

                if node_info is None:
                    continue

                if not node_info.isOn():
                    cont_painter.setBrush(QtGui.QBrush(color_gold))
                    cont_painter.setPen(QtGui.QPen(color_black, 1, QtCore.Qt.SolidLine))
                    onNode = node_info.getOn()
                    cont_painter.drawLine(node_info.x, node_info.y, onNode.x, onNode.y)

                    draw_radius = 5
                # if node_info is not None:# and node_info.isOn():
                cont_painter.drawEllipse(node_info.x - draw_radius, node_info.y - draw_radius, draw_radius*2, draw_radius*2)

        cont_painter.end()

        pixmap_transform = QtGui.QTransform().scale(1, -1)
        pixmap_flipped = cont_pixmap.transformed(pixmap_transform)


        return pixmap_flipped

    def drawIcon(self, contours):     

        cloned_contours = [contour.clone() for contour in contours]
        main_shape = fl6.flShape()

        for cid in range(len(cloned_contours)):
            main_shape.addContour(cloned_contours[cid], True)

        # for cid in range(len(cloned_contours)):
        #     contour_shape = fl6.flShape()
        #     contour_shape.addContour()
        
        shape_bbox = main_shape.boundingBox
        draw_padding = 50
        draw_dimension = max(shape_bbox.width(), shape_bbox.height(), self.glyph.getAdvance(), fontHeight) + 2 * draw_padding
        cont_painter = QtGui.QPainter()
        cont_pixmap = QtGui.QPixmap(draw_dimension, draw_dimension)

        #background    
        cont_painter.begin(cont_pixmap)
        cont_painter.setBrush(QtGui.QBrush(color_white))
        cont_painter.drawRect(QtCore.QRectF(0, 0, draw_dimension, draw_dimension))

        #contour
        cont_painter.setBrush(QtGui.QBrush(color_black))
        cont_painter.setPen(QtGui.QPen(color_black, 2, QtCore.Qt.SolidLine))
        new_transform = main_shape.transform.translate(-shape_bbox.x() + max((draw_dimension - shape_bbox.width())/2, draw_padding), -shape_bbox.y() + max((draw_dimension - shape_bbox.height())/2, draw_padding))
        main_shape.applyTransform(new_transform)
        main_shape.ensurePaths()
        draw_path = main_shape.closedPath
        cont_painter.drawPath(draw_path)
        cont_painter.end()

        pixmap_transform = QtGui.QTransform().scale(1, -1)
        pixmap_flipped = cont_pixmap.transformed(pixmap_transform)

        return pixmap_flipped

    def layer_duplicate_mask(self):
        layer_name = self.glyph.layer().name
        srcShapes = self.glyph.shapes(layer_name)
        newMaskLayer = self.glyph.layer(layer_name).getMaskLayer(True)	    
        for shape in srcShapes:
            newMaskLayer.addShape(shape.cloneTopLevel())

    def writePreference(self):
        new_packageLib = {**flP.packageLib, "com.Minwoo.JitterGlyphs": self.inputValues}
        flP.packageLib = new_packageLib

    def readPreference(self):
        self.inputValues = {}
        try:
            self.inputValues = flP.packageLib["com.Minwoo.JitterGlyphs"]
        except KeyError :
            self.inputValues = initialValues
            NEW_INPUT_VALUE_PRESET = {**flP.packageLib, "com.Minwoo.JitterGlyphs": initialValues}
            flP.packageLib = NEW_INPUT_VALUE_PRESET

dialog = MainWindow()




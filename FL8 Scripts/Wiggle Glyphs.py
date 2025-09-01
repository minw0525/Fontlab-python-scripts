#FLM: MW: Wiggle Glyphs
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
                'components_count' : 3,
                'weight_top': 80, 
                'weight_bottom': 150, 
                'wavelength_h_from': 30, 
                'wavelength_h_to': 50, 
                'wavelength_v_from': 30, 
                'wavelength_v_to': 60, 
                'amplitude_h_from': 3,
                'amplitude_h_to': 10,
                'amplitude_v_from': 3,
                'amplitude_v_to': 10, 
                'scale_h': 50, 
                'scale_v': 100, 
                'treshold': 30, 
                'offset': 10, 
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
app_name, app_version = 'Minwoo | Wiggle Glyphs', '1.0'


# Style Sheet ====
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
        # if key in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down] and (e.modifiers() & QtCore.Qt.ShiftModifier):
        #     self.setSingleStep(10)
        # else:
        #     self.setSingleStep(1)
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
        self.simplify = True
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

        # edit
        self.edt_components_count = CustomSpinBox()
        self.edt_components_count.setRange(0,10)	
        self.edt_components_count.setValue(self.inputValues['components_count'])
        self.edt_components_count.setAlignment(0x0002) #align-right
        self.edt_components_count.setMaximumWidth(150)
        
        self.edt_weight_top = CustomSpinBox()
        self.edt_weight_top.setRange(0,500)	
        self.edt_weight_top.setValue(self.inputValues['weight_top'])
        self.edt_weight_top.setAlignment(0x0002) #align-right
        self.edt_weight_top.setMaximumWidth(150)
        self.edt_weight_top.setSuffix('%')

        self.edt_weight_bottom = CustomSpinBox()
        self.edt_weight_bottom.setRange(0,500)	
        self.edt_weight_bottom.setValue(self.inputValues['weight_bottom'])
        self.edt_weight_bottom.setAlignment(0x0002)
        self.edt_weight_bottom.setMaximumWidth(150)
        self.edt_weight_bottom.setSuffix('%')

        self.edt_wavelength_h_from = CustomSpinBox()
        self.edt_wavelength_h_from.setRange(0,500)	
        self.edt_wavelength_h_from.setValue(self.inputValues['wavelength_h_from'])
        self.edt_wavelength_h_from.setAlignment(0x0002) #align-right
        self.edt_wavelength_h_from.setMaximumWidth(60)
        self.edt_wavelength_h_from.setSuffix('u')

        self.edt_wavelength_h_to = CustomSpinBox()
        self.edt_wavelength_h_to.setRange(0,500)	
        self.edt_wavelength_h_to.setValue(self.inputValues['wavelength_h_to'])
        self.edt_wavelength_h_to.setAlignment(0x0002) #align-right
        self.edt_wavelength_h_to.setMaximumWidth(60)
        self.edt_wavelength_h_to.setSuffix('u')

        self.edt_wavelength_v_from = CustomSpinBox()
        self.edt_wavelength_v_from.setRange(0,500)	
        self.edt_wavelength_v_from.setValue(self.inputValues['wavelength_v_from'])
        self.edt_wavelength_v_from.setAlignment(0x0002)
        self.edt_wavelength_v_from.setMaximumWidth(60)
        self.edt_wavelength_v_from.setSuffix('u')

        self.edt_wavelength_v_to = CustomSpinBox()
        self.edt_wavelength_v_to.setRange(0,500)	
        self.edt_wavelength_v_to.setValue(self.inputValues['wavelength_v_to'])
        self.edt_wavelength_v_to.setAlignment(0x0002)
        self.edt_wavelength_v_to.setMaximumWidth(60)
        self.edt_wavelength_v_to.setSuffix('u')

        self.edt_amplitude_h_from = CustomSpinBox()
        self.edt_amplitude_h_from.setRange(0,500)	
        self.edt_amplitude_h_from.setValue(self.inputValues['amplitude_h_from'])
        self.edt_amplitude_h_from.setAlignment(0x0002)
        self.edt_amplitude_h_from.setMaximumWidth(60)

        self.edt_amplitude_h_to = CustomSpinBox()
        self.edt_amplitude_h_to.setRange(0,500)	
        self.edt_amplitude_h_to.setValue(self.inputValues['amplitude_h_to'])
        self.edt_amplitude_h_to.setAlignment(0x0002)
        self.edt_amplitude_h_to.setMaximumWidth(60)

        self.edt_amplitude_v_from = CustomSpinBox()
        self.edt_amplitude_v_from.setRange(0,500)	
        self.edt_amplitude_v_from.setValue(self.inputValues['amplitude_v_from'])
        self.edt_amplitude_v_from.setAlignment(0x0002)
        self.edt_amplitude_v_from.setMaximumWidth(60)

        self.edt_amplitude_v_to = CustomSpinBox()
        self.edt_amplitude_v_to.setRange(0,500)	
        self.edt_amplitude_v_to.setValue(self.inputValues['amplitude_v_to'])
        self.edt_amplitude_v_to.setAlignment(0x0002)
        self.edt_amplitude_v_to.setMaximumWidth(60)

        self.edt_scale_h = CustomSpinBox()
        self.edt_scale_h.setRange(0,300)	
        self.edt_scale_h.setValue(self.inputValues['scale_h'])
        self.edt_scale_h.setAlignment(0x0002)
        self.edt_scale_h.setMaximumWidth(150)
        self.edt_scale_h.setSuffix('%')

        self.edt_scale_v = CustomSpinBox()
        self.edt_scale_v.setRange(0,300)	
        self.edt_scale_v.setValue(self.inputValues['scale_v'])
        self.edt_scale_v.setAlignment(0x0002)
        self.edt_scale_v.setMaximumWidth(150)
        self.edt_scale_v.setSuffix('%')

        self.edt_treshold = CustomSpinBox()
        self.edt_treshold.setRange(0,100)	
        self.edt_treshold.setValue(self.inputValues['treshold'])
        self.edt_treshold.setAlignment(0x0002)
        self.edt_treshold.setMaximumWidth(150)
        self.edt_treshold.setSuffix('u')

        self.edt_offset = CustomSpinBox()
        self.edt_offset.setRange(0,100)	
        self.edt_offset.setValue(self.inputValues['offset'])
        self.edt_offset.setAlignment(0x0002)
        self.edt_offset.setMaximumWidth(150)


        self.btn_reset = CustomBtn('↺')
        self.btn_transform = CustomBtn('Transform')

        # labels
        self.lbl_components_count = QtGui.QLabel('Sine Count')

        self.lbl_weight_top = QtGui.QLabel('Weight-Top')
        self.lbl_weight_bottom = QtGui.QLabel('Weight-Bottom')

        self.lbl_wavelength_h = QtGui.QLabel('Wavelength-H')
        self.lbl_wavelength_v = QtGui.QLabel('Wavelength-V')

        self.lbl_amplitude_h = QtGui.QLabel('Amplitude-H')
        self.lbl_amplitude_v = QtGui.QLabel('Amplitude-V')

        self.lbl_scale_h = QtGui.QLabel('Scale-H')
        self.lbl_scale_v = QtGui.QLabel('Scale-V')

        self.lbl_treshold = QtGui.QLabel('Treshold')

        self.lbl_offset = QtGui.QLabel('Offset')


        self.input_GroupBox = QtGui.QGroupBox()
        self.input_GridLayout = QtGui.QGridLayout()
        self.input_GroupBox.setStyleSheet('margin: 0; padding:0 0 0 3px; border:1px solid transparent;')
        self.btn_reset.setStyleSheet('border: 1px solid #5E5E5E;')
        self.btn_transform.setStyleSheet('border: 1px solid #5E5E5E;')

#       QGridLayout.addWidget(widget, fromRow, fromCol, rowSpan, colSpan)
        self.input_GridLayout.addWidget(self.lbl_components_count,  0,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_components_count,  0,  2,  1,  2)

        self.input_GridLayout.addWidget(self.lbl_weight_top,        1,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_weight_top,        1,  2,  1,  2)
        self.input_GridLayout.addWidget(self.lbl_weight_bottom,     2,  0,  1,  1)
        self.input_GridLayout.addWidget(self.edt_weight_bottom,     2,  2,  1,  2)

        self.input_GridLayout.addWidget(self.lbl_wavelength_h,      3,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_wavelength_h_from, 3,  2,  1,  1)
        self.input_GridLayout.addWidget(self.edt_wavelength_h_to,   3,  3,  1,  1)
        self.input_GridLayout.addWidget(self.lbl_wavelength_v,      4,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_wavelength_v_from, 4,  2,  1,  1)
        self.input_GridLayout.addWidget(self.edt_wavelength_v_to,   4,  3,  1,  1)
                
        self.input_GridLayout.addWidget(self.lbl_amplitude_h,       5,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_amplitude_h_from,  5,  2,  1,  1)
        self.input_GridLayout.addWidget(self.edt_amplitude_h_to,    5,  3,  1,  1)
        self.input_GridLayout.addWidget(self.lbl_amplitude_v,       6,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_amplitude_v_from,  6,  2,  1,  1)
        self.input_GridLayout.addWidget(self.edt_amplitude_v_to,    6,  3,  1,  1)

        self.input_GridLayout.addWidget(self.lbl_scale_h,           7,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_scale_h,           7,  2,  1,  2)

        self.input_GridLayout.addWidget(self.lbl_scale_v,           8,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_scale_v,           8,  2,  1,  2)

        self.input_GridLayout.addWidget(self.lbl_treshold,          9,  0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_treshold,          9,  2,  1,  2)

        self.input_GridLayout.addWidget(self.lbl_offset,            10, 0,  1,  2)
        self.input_GridLayout.addWidget(self.edt_offset,            10, 2,  1,  2)

        self.input_GridLayout.addWidget(self.btn_transform,         11, 0,  1,  3)
        self.input_GridLayout.addWidget(self.btn_reset,             11, 3,  1,  1)

        self.input_GroupBox.setLayout(self.input_GridLayout)
        self.original_HBoxLayout.addWidget(self.input_GroupBox)

        # footer
        self.chk_showNode = QtGui.QCheckBox('Show Nodes')
        self.chk_showNode.setChecked(self.showNode)
        self.chk_showNode.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btn_simplify = CustomBtn('Simplify On')
        self.btn_simplify.setCheckable(True)
        self.btn_simplify.setChecked(self.simplify)
        self.btn_apply = CustomBtn('Apply')
        self.btn_close = CustomBtn('Close')

        self.footer_Widget = QtGui.QWidget()
        self.footer_GridLayout = QtGui.QGridLayout()
        self.footer_GridLayout.addWidget(self.chk_showNode, 0, 0, 1, 1, QtCore.Qt.AlignTop)
        self.footer_GridLayout.addItem(self.hSpacer300,     0, 1, 1, 3)
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
        self.edt_components_count.editingFinished.connect(lambda sender = self.edt_components_count, value = 'components_count': self.spinboxChanged(sender, value))
        self.edt_weight_top.editingFinished.connect(lambda sender = self.edt_weight_top, value = 'weight_top': self.spinboxChanged(sender, value))
        self.edt_weight_bottom.editingFinished.connect(lambda sender = self.edt_weight_bottom, value = 'weight_bottom': self.spinboxChanged(sender, value))
        self.edt_wavelength_h_from.editingFinished.connect(lambda sender = self.edt_wavelength_h_from, value = 'wavelength_h_from': self.spinboxChanged(sender, value))
        self.edt_wavelength_h_to.editingFinished.connect(lambda sender = self.edt_wavelength_h_to, value = 'wavelength_h_to': self.spinboxChanged(sender, value))
        self.edt_wavelength_v_from.editingFinished.connect(lambda sender = self.edt_wavelength_v_from, value = 'wavelength_v_from': self.spinboxChanged(sender, value))
        self.edt_wavelength_v_to.editingFinished.connect(lambda sender = self.edt_wavelength_v_to, value = 'wavelength_v_to': self.spinboxChanged(sender, value))
        self.edt_amplitude_h_from.editingFinished.connect(lambda sender = self.edt_amplitude_h_from, value = 'amplitude_h_from': self.spinboxChanged(sender, value))
        self.edt_amplitude_h_to.editingFinished.connect(lambda sender = self.edt_amplitude_h_to, value = 'amplitude_h_to': self.spinboxChanged(sender, value))
        self.edt_amplitude_v_from.editingFinished.connect(lambda sender = self.edt_amplitude_v_from, value = 'amplitude_v_from': self.spinboxChanged(sender, value))
        self.edt_amplitude_v_to.editingFinished.connect(lambda sender = self.edt_amplitude_v_to, value = 'amplitude_v_to': self.spinboxChanged(sender, value))
        self.edt_scale_h.editingFinished.connect(lambda sender = self.edt_scale_h, value = 'scale_h': self.spinboxChanged(sender, value))
        self.edt_scale_v.editingFinished.connect(lambda sender = self.edt_scale_v, value = 'scale_v': self.spinboxChanged(sender, value))
        self.edt_treshold.editingFinished.connect(lambda sender = self.edt_treshold, value = 'treshold': self.spinboxChanged(sender, value))
        self.edt_offset.editingFinished.connect(lambda sender = self.edt_offset, value = 'offset': self.spinboxChanged(sender, value))
        self.btn_reset.clicked.connect(self.resetValue)
        self.btn_transform.clicked.connect(self.add_tableItem)
        self.chk_showNode.clicked.connect(self.toggle_nodeVisibility)
        self.btn_simplify.toggled.connect(self.toggle_simplify)
        self.btn_apply.clicked.connect(self.apply_transform)
        self.btn_close.clicked.connect(self.closeWidget)
        self.preview_Table.currentCellChanged.connect(self.paintPreviewCanvas)
        self.preview_Table.cellClicked.connect(self.paintPreviewCanvas)

        self.setStyleSheet(style)
        self.header_Widget.setStyleSheet(style)
        self.footer_Widget.setStyleSheet(style)
        self.setWindowTitle('%s %s' %(app_name, app_version))
        self.setGeometry(300, 100, 1450, 630)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocus()

        # self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) # Always on top!!
        
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        qapp.applicationStateChanged.connect(self.setFlag)
        self.show()


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

    def toggle_simplify(self):
        self.simplify = self.btn_simplify.isChecked()
        onoff = "On" if self.simplify else "Off"
        self.btn_simplify.setText(f'Simplify {onoff}')


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
        self.edt_components_count.setValue(self.inputValues['components_count'])
        self.edt_weight_top.setValue(self.inputValues['weight_top'])
        self.edt_weight_bottom.setValue(self.inputValues['weight_bottom'])
        self.edt_wavelength_h_from.setValue(self.inputValues['wavelength_h_from'])
        self.edt_wavelength_h_to.setValue(self.inputValues['wavelength_h_to'])
        self.edt_wavelength_v_from.setValue(self.inputValues['wavelength_v_from'])
        self.edt_wavelength_v_to.setValue(self.inputValues['wavelength_v_to'])
        self.edt_amplitude_h_from.setValue(self.inputValues['amplitude_h_from'])
        self.edt_amplitude_h_to.setValue(self.inputValues['amplitude_h_to'])
        self.edt_amplitude_v_from.setValue(self.inputValues['amplitude_v_from'])
        self.edt_amplitude_v_to.setValue(self.inputValues['amplitude_v_to'])
        self.edt_scale_h.setValue(self.inputValues['scale_h'])
        self.edt_scale_v.setValue(self.inputValues['scale_v'])
        self.edt_treshold.setValue(self.inputValues['treshold'])
        self.edt_offset.setValue(self.inputValues['offset'])


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
        self.show();
    
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


    def interpolate(self, treshold):

        self.timeTable = self.glyph.mapTimes2Nodes()
        cloned_contours = [contour.clone() for contour in self.originalContours]
        for contour in cloned_contours:
            for node in contour.nodes():
                if node.isCurve(): 
                    continue
                else:
                    node.convertToCurve()

        for [cID, contour] in zip(self.timeTable.keys(), cloned_contours):
            self.splitUntil(cID, contour, cloned_contours, treshold)
        
        return cloned_contours

    #Split segment
    def splitUntil(self, cID, contour, all_contours, treshold):

        #segment[0]: CurveEx, segment[1]: flNodes
        prev = [[segmentIdx, segment] for [segmentIdx, segment] in zip(self.timeTable[cID], contour.segments())]
        # print('PREV', prev)

        while(len(prev)) > 0 :

            currSeg =  prev.pop()
            # print("CURRSEG",currSeg)
            if currSeg[1].fastLength() > treshold : 
                
                contour.insertNodeTo(currSeg[0] + .5)


                contourMap = {}		
                
                nodeMap = {}
                countOn = -1

                for node in contour.nodes():
                    countOn += node.isOn() # Hack-ish but working
                    nodeMap[node.index] = countOn
                    
                contourMap[all_contours.index(contour)] = nodeMap

                t2nMap = {}

                for cID, nodeMap in contourMap.items():
                    tempMap = {}
                    
                    for nID, time in nodeMap.items():
                        tempMap.setdefault(time, []).append(nID)

                    t2nMap[cID] = tempMap

                timeTable = t2nMap
                prev = [[segmentIdx, segment] for [segmentIdx, segment] in zip(timeTable[cID], contour.segments())]

    def transform(self, contours, transformers, isRandom=False):
        # cloned_nodes = [node.clone() for node in self.glyph.nodes()]

        # if not isRandom:
        #     for node in cloned_nodes:
        #         x = node.x
        #         y = node.y
        #         WAVELENGTH = [self.inputValues['wavelength_h'], self.inputValues['wavelength_h']]
        #         OFFSET = [self.inputValues['offset']]
        #         newPts = transformers(x, y, WAVELENGTH, OFFSET)
        #         node.x, node.y = newPts[0], newPts[1]
        #     return cloned_nodes
        WAVELENGTH_H = [self.inputValues['wavelength_h_from'], self.inputValues['wavelength_h_to']]
        WAVELENGTH_V = [self.inputValues['wavelength_v_from'], self.inputValues['wavelength_v_to']]
        AMPLITUDE_H = [self.inputValues['amplitude_h_from'], self.inputValues['amplitude_h_to']]
        AMPLITUDE_V = [self.inputValues['amplitude_v_from'], self.inputValues['amplitude_v_to']]
        #     return cloned_nodes

        COMPONENTS_COUNT = self.inputValues['components_count']
        
        for contour in contours:

            RANDOM_AMPLITUDE_H = [random.uniform(AMPLITUDE_H[0], AMPLITUDE_H[1]) for i in range(COMPONENTS_COUNT)]
            RANDOM_AMPLITUDE_V = [random.uniform(AMPLITUDE_V[0], AMPLITUDE_V[1]) for i in range(COMPONENTS_COUNT)]
            RANDOM_WAVELENGTH_H = [random.uniform(WAVELENGTH_H[0], WAVELENGTH_H[1]) * random.choice([-1, 1]) for i in range(COMPONENTS_COUNT)]
            RANDOM_WAVELENGTH_V = [random.uniform(WAVELENGTH_V[0], WAVELENGTH_V[1]) * random.choice([-1, 1]) for i in range(COMPONENTS_COUNT)]
            CONTOUR_RECT = contour.boundingBox()

            wave_params = [[RANDOM_AMPLITUDE_H, RANDOM_AMPLITUDE_V], [RANDOM_WAVELENGTH_H, RANDOM_WAVELENGTH_V], CONTOUR_RECT]
            for i in range(COMPONENTS_COUNT):
                for node in contour.nodes():
                    x = node.x
                    y = node.y
                    newPts = transformers(x, y, i, wave_params)
                    node.x, node.y = newPts[0], newPts[1]

            if self.simplify:
                contour.simplify(1, True, True)  
                
        return contours
        # self.glyph.updateObject(self.glyph.fl, 'Glyph modified')

    
    # def uniformSineTransformer(self, x, y, waveLength, offset):
    #     return [
    #         x + offset * math.sin(y / waveLength[0]) * self.inputValues['scale_h'],
    #         y + offset * math.sin(x / waveLength[1]) * self.inputValues['scale_v']
    #     ]

    def randomSineTransformer(self, x, y, randomCounter, wave_params):
        WEIGHT_TOP = self.inputValues['weight_top'] / 100
        WEIGHT_BOTTOM = self.inputValues['weight_bottom'] / 100
        SCALE_H = self.inputValues['scale_h'] / 100
        SCALE_V = self.inputValues['scale_v'] / 100
        OFFSET = self.inputValues['offset']
        COMPONENTS_COUNT = self.inputValues['components_count']

        A = wave_params[0] #Amplitude
        W = wave_params[1] #Wavelength
        R = wave_params[2] #Rect_weight
        
        # a = ( WEIGHT_TOP - WEIGHT_BOTTOM) / R.height()  # ( 0.8 - 1.5 ) * 300 = -210   /// -0.7*500 = -350 
        # a2 = ( WEIGHT_TOP - WEIGHT_BOTTOM) / (fontHeight - y)  
        # b = WEIGHT_TOP - (WEIGHT_TOP - WEIGHT_BOTTOM) / R.height() * R.bottom() # 0.8525) 
        # b2 = WEIGHT_TOP - (WEIGHT_TOP - WEIGHT_BOTTOM) / fontHeight * y

        # # print(a, a2, b, b2)
        # # weight_v_ratio = a * y + b
        # print(f'({a},{a2},{a*a2}), {y}, ({b},{b2},{b*b2})')
        # weight_v_ratio = (a/6 + a2/5)* 4 * y + (b/6 + b2/5)*4
       
        a = (WEIGHT_TOP * ((y - R.top()) / R.height())) + WEIGHT_BOTTOM * ((R.bottom() - y) / R.height())
        b = (WEIGHT_TOP ** 2.5 * ((y - yBottom) / fontHeight) + WEIGHT_BOTTOM ** 2.5 *   ((yTop - y) / fontHeight))
        # weight_v_ratio = (a * a2)/4 * y + (b * b2)/4

        weight_v_ratio = a * b / COMPONENTS_COUNT
#         print(f'''a : {a}, 
# b : {b}, 
# y : {y}, 
# COMPONENTS_COUNT : {COMPONENTS_COUNT},
# weight_v_ratio: {weight_v_ratio}''')
        x_weight = (R.right() - x) / R.width()
        W_weight = (R.bottom() - y) / R.height()

        offset_x = OFFSET * (self.xmax - x) / self.adv 
        offset_y = OFFSET * (yTop - y) / fontHeight 

        
        #컨투어 안에서 높이별 진폭 가중치 / 주파수 감산치 줄 수 있을지 고민해보기

        # return [
        #     x + A[0][randomCounter] * math.sin(y / W[0][randomCounter]-offset_weight_x) * SCALE_H,
        #     y + (A[1][randomCounter] * math.sin(x / W[1][randomCounter]-offset_weight_y) * SCALE_V) * transformation_weight
        # ]

        return [
            x + A[0][randomCounter] * math.sin(y / W[0][randomCounter]-offset_x) * SCALE_H,
            # y + A[1][randomCounter] * math.sin(x / W[1][randomCounter] * weight_v_ratio - offset_y) * SCALE_V * weight_v_ratio
            y + signInt( math.sin(x / W[1][randomCounter] - offset_y) ) * A[1][randomCounter] * abs(math.sin(x / W[1][randomCounter] - offset_y)) * SCALE_V * weight_v_ratio
        ]
       

    def getProcessedContours(self):
        TRESHOLD = self.inputValues['treshold']      
        interpolatedContours = self.interpolate(TRESHOLD)
        return_contour = self.transform(interpolatedContours, self.randomSineTransformer, True)
        return return_contour
    
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
        new_packageLib = {**flP.packageLib, "com.Minwoo.WiggleGlyphs": self.inputValues}
        flP.packageLib = new_packageLib

    def readPreference(self):
        self.inputValues = {}
        try:
            self.inputValues = flP.packageLib["com.Minwoo.WiggleGlyphs"]
        except KeyError :
            self.inputValues = initialValues
            NEW_INPUT_VALUE_PRESET = {**flP.packageLib, "com.Minwoo.WiggleGlyphs": initialValues}
            flP.packageLib = NEW_INPUT_VALUE_PRESET

dialog = MainWindow()



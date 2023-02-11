#FLM: MW: Projective Transform

import fontlab as fl6
import fontgate as fgt

from typerig.proxy.fl.objects.font import eFont
from typerig.proxy.fl.objects.glyph import eGlyph
from typerig.proxy.fl.objects.node import eNode
from typerig.proxy.fl.application.app import *

from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui
from typerig.proxy.fl.gui.widgets import getProcessGlyphs


qapp = QtGui.QApplication.instance()
app = fl6.flWorkspace.instance()
font = eFont()
fontMetrics = font.fontMetricsInfo(0)
upm = fontMetrics.upm
nT = fgt.fgNametable()
yTop, yBottom = fontMetrics.ascender, fontMetrics.descender


# init ====
app_name, app_version = 'Minwoo | Projective Transform', '1.1'

# Config ====
column_names = ['Index', 'Character', 'Name', 'Unicode', 'Tags']
fontMarkColors = [ 
    (u'None', 0, u'white'), 
    (u'Red', 1, u'red'), 
    (u'Yellow', 61, u'yellow'), 
    (u'Green', 121, u'green'), 
    (u'Cyan', 181, u'cyan'),
    (u'Blue', 241, u'blue'),
    (u'Magenta', 301, u'magenta'),
    (u'Orange', 31, u'orange'),
    (u'Sulu', 90, u'chartreuse'),
    (u'Aquamarine', 151, u'aquamarine'),
    (u'Maya blue', 210, u'cornflowerblue'),
    (u'Heliotrope', 271, u'blueviolet'),
    (u'Rose', 330, u'hotpink'),
    (u'Coral', 16, u'coral'),
    (u'Sienna', 20, u'sienna'),
    (u'Bisque', 37, u'bisque'),
    (u'Gold', 50, u'gold'),
    (u'Yellow green', 79, u'yellowgreen'),
    (u'Spring green', 145, u'springgreen'),
    (u'Turquoise', 174, u'turquoise'),
    (u'Skyblue', 195, u'skyblue'),
    (u'Indigo', 274, u'indigo'),
    (u'Pink', 350, u'pink'),
    (u'Gray', 361, u'lightgray') 
]

def get_icon_from_color(color):
    pixmap = QtGui.QPixmap(20, 20)
    pixmap.fill(color)
    icon = QtGui.QIcon(pixmap) 
    return icon


# Style Sheet ====
stlye = """
QWidget {
    background-color: #202020;
    color: #dddddd;
    margin: 0;
    padding: 0;
    font-family: Arial, Helvetica, sans-serif;
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
    padding: 0;
    margin: 0;
}
QHeaderView, QPushButton, QLabel {
    font-weight: 400;
}
QLabel{
    background: transparent;
    font-size: 15px;
}

QPushButton{
    background: transparent;
    border-radius: 5px;
    height: 30px;
    border: 1px solid #5E5E5E;
    font-size: 15px;
}
QPushButton:hover{
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 5px;
    height: 30px;
    border: 1px solid #6C6C6C;
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
    subcontrol-position: top left;
    width: 20px; 
    background: #4A4A4A;
}
QSpinBox::up-button:hover { 
    subcontrol-origin: border;
    subcontrol-position: top left;
    width: 20px; 
    background-color: #666666;
}
QSpinBox::down-button { 
    subcontrol-origin: border;
    subcontrol-position: bottom left;
    width: 20px; 
    background: #4A4A4A;
}
QSpinBox::down-button:hover { 
    subcontrol-origin: border;
    subcontrol-position: bottom left;
    width: 20px; 
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


class WTreeWidget(QtGui.QTreeWidget):
    def __init__(self, data):
        super(WTreeWidget, self).__init__()

        self.data = data[:] = [g for g in data if g.name != '.notdef']

        self.setTree(data)
        self.setAlternatingRowColors(True)
        self.sortingEnabled = True
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(4)
        self.indentation = 0

    def setTree(self, data):
        self.blockSignals(True)
        self.clear()
        self.setHeaderLabels(column_names)
        print(data)
        for eGlyph in sorted(data, key = lambda x: x.name):
            slicedName = list(eGlyph.name.partition('.')) # ex) ['uniAC00','alt'] from 'uniAC00.alt' 
            print(slicedName)
            try: 
                #           ex) ['index',   'character',    'name',         'unicode',      'tag']
                #           ex) ['10',      '가.001',       'uniAC00.001',  '0xAC00.001',   '']
                treeItemList =  [eGlyph.index, concatStr(chr(nT.unc(slicedName[0])), ''.join(slicedName[1:])), ''.join(slicedName), concatStr(format((nT.unc(slicedName[0])), '#06X'),''.join(slicedName[1:])), ','.join(eGlyph.tags)]
            except TypeError as t:
                print(t)
                uni_32bit_name = '\\U%s' %format(nT.unc(slicedName[0]), '08x')
                treeItemList =  [eGlyph.index, bytes(uni_32bit_name).decode('unicode_escape'), ''.join(slicedName), concatStr(format((nT.unc(slicedName[0])), '#08X'),''.join(slicedName[1:])), ','.join(eGlyph.tags)]

            except ValueError as v:
                print(v)
                treeItemList =  [eGlyph.index, ''.join(slicedName), ''.join(slicedName), '', ','.join(eGlyph.tags)]


            glyph = QtGui.QTreeWidgetItem(self, treeItemList)
        self.blockSignals(False)
        self.setSelectionMode(0) #QAbstractItemView::NoSelection	    

class PreviewGroupbox(QtGui.QGroupBox):
    def __init__(self, aux):#scales, aux):
        super(PreviewGroupbox, self).__init__()

        self.aux = aux
        self.transformValue = aux.transformValue
        self.rect_size = 180
        self.rect_spacing = 120
        self.arrow_length = 30
        self.arrow_head = 7
        self.ot = self.aux.ot
        self.color_white = QtGui.QColor('white')
        self.color_transparent = QtGui.QColor('transparent')


    def refresh(self):
        # print(self.transformValue)
        #self.painter.begin(self)
        self.ot = self.aux.ot
        
        rect1 = [ [self.paddingH, self.paddingT], [self.paddingH, self.paddingT + self.rect_size], [self.paddingH + self.rect_size, self.paddingT + self.rect_size], [self.paddingH + self.rect_size, self.paddingT] ]

        rect2 = self.aux.calculate_new_pts(self.rect_size, self.transformValue, self.ot, rect1)

        qPoints2 = [QtCore.QPoint(rect2[0][0] + self.rect_spacing + self.rect_size, rect2[0][1]), QtCore.QPoint(rect2[1][0] + self.rect_spacing + self.rect_size, rect2[1][1]), QtCore.QPoint(rect2[2][0] + self.rect_spacing + self.rect_size, rect2[2][1]), QtCore.QPoint(rect2[3][0] + self.rect_spacing + self.rect_size, rect2[3][1])]

        polygon2 = QtGui.QPolygon(qPoints2)
        qO = self.setOrigin(self.painter)


        self.update()

    def setOrigin(self, painter):
        oX = self.paddingH + self.ot[0] * self.rect_size
        oY = self.paddingT + self.ot[1] * self.rect_size 
        qO = QtCore.QPoint(oX, oY)
        return qO

    def paintEvent(self, event):

        # print(event.rect().width())
        self.paddingH = (event.rect().width() - (self.rect_size * 2 + self.rect_spacing)) / 2
        self.paddingT = (event.rect().height() - self.rect_size) / 2

        self.painter = QtGui.QPainter()

        self.painter.begin(self)
        self.painter.setPen(QtGui.QPen(self.color_white, 1, QtCore.Qt.SolidLine))


        rect1 = [ [self.paddingH, self.paddingT], [self.paddingH, self.paddingT + self.rect_size], [self.paddingH + self.rect_size, self.paddingT + self.rect_size], [self.paddingH + self.rect_size, self.paddingT] ]

        qPoints1 = [QtCore.QPoint(rect1[0][0], rect1[0][1]), QtCore.QPoint(rect1[1][0], rect1[2][1]), QtCore.QPoint(rect1[2][0], rect1[2][1]), QtCore.QPoint(rect1[3][0], rect1[3][1])]

        polygon1 = QtGui.QPolygon(qPoints1)
        self.painter.drawPolygon(polygon1)
        qO = self.setOrigin(self.painter)

        
        self.painter.drawEllipse(qO, 5, 5)
        self.painter.setBrush(QtGui.QBrush(self.color_white))
        self.painter.drawEllipse(qO, 2, 2)
        self.painter.setBrush(QtGui.QBrush(self.color_transparent))

        #print(self.transformValue)

        
        
        rect2 = self.aux.calculate_new_pts(self.rect_size, self.transformValue, self.ot, rect1, True)

        qPoints2 = [QtCore.QPoint(rect2[0][0] + self.rect_spacing + self.rect_size, rect2[0][1]), QtCore.QPoint(rect2[1][0] + self.rect_spacing + self.rect_size, rect2[1][1]), QtCore.QPoint(rect2[2][0] + self.rect_spacing + self.rect_size, rect2[2][1]), QtCore.QPoint(rect2[3][0] + self.rect_spacing + self.rect_size, rect2[3][1])]

        polygon2 = QtGui.QPolygon(qPoints2)
        self.painter.drawPolygon(polygon2)


        self.painter.setPen(QtGui.QPen(self.color_white, 2, QtCore.Qt.SolidLine))

        arrow_point1 = [(event.rect().width()- self.arrow_length)/2, event.rect().height()/2]
        arrow_point2 = [(event.rect().width() + self.arrow_length)/2, event.rect().height()/2]

        self.painter.drawLine(arrow_point1[0], arrow_point1[1], arrow_point2[0], arrow_point2[1])
        self.painter.drawLine(arrow_point2[0] - self.arrow_head, arrow_point2[1] - self.arrow_head, arrow_point2[0], arrow_point2[1])
        self.painter.drawLine(arrow_point2[0], arrow_point2[1], arrow_point2[0] - self.arrow_head, arrow_point2[1] + self.arrow_head)
        self.painter.end()



class MainWindow(QtGui.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()

        #Init
        self.glyphs = list({v.index:v for v in getProcessGlyphs(1)}.values()) if app.getActiveCanvas() else list({v.index:v for v in getProcessGlyphs(2)}.values())
        self.tree_glyphZones = WTreeWidget(self.glyphs)
        #self.setAttribute(55) #delete on close
        self.setStyleSheet(stlye)
        self.transformValue = []
        self.standardWidth = upm
        self.ot = [0.5, 0.5]


        # edit
        self.edt_upper_scale = QtGui.QSpinBox()
        self.edt_upper_scale.setRange(0,150)	
        self.edt_upper_scale.setValue(120)
        self.edt_upper_scale.setAlignment(0x0002) #align-right
        self.edt_upper_scale.setMaximumWidth(120)
        self.edt_upper_scale.setSuffix('  %')
        self.transformValue.append( float(self.edt_upper_scale.value) / 100)


        self.edt_lower_scale = QtGui.QSpinBox()
        self.edt_lower_scale.setRange(0,150)	
        self.edt_lower_scale.setValue(80)
        self.edt_lower_scale.setAlignment(0x0002)
        self.edt_lower_scale.setMaximumWidth(120)
        self.edt_lower_scale.setSuffix('  %')
        self.transformValue.append( float(self.edt_lower_scale.value) / 100)


        self.edt_left_scale = QtGui.QSpinBox()
        self.edt_left_scale.setRange(0,150)	
        self.edt_left_scale.setValue(100)
        self.edt_left_scale.setAlignment(0x0002)
        self.edt_left_scale.setMaximumWidth(120)
        self.edt_left_scale.setSuffix('  %')
        self.transformValue.append( float(self.edt_left_scale.value) / 100)


        self.edt_right_scale = QtGui.QSpinBox()
        self.edt_right_scale.setRange(0,150)	
        self.edt_right_scale.setValue(100)
        self.edt_right_scale.setAlignment(0x0002)
        self.edt_right_scale.setMaximumWidth(120)
        self.edt_right_scale.setSuffix('  %')
        self.transformValue.append( float(self.edt_right_scale.value) / 100)


        self.edt_top_line = QtGui.QSpinBox()
        self.edt_top_line.setRange(0,1500)	
        self.edt_top_line.setValue(yTop)
        self.edt_top_line.setAlignment(0x0002)
        self.edt_top_line.setMaximumWidth(120)
        self.edt_top_line.setSuffix('  u')

        self.edt_bottom_line = QtGui.QSpinBox()
        self.edt_bottom_line.setRange(-500,1000)	
        self.edt_bottom_line.setValue(yBottom)
        self.edt_bottom_line.setAlignment(0x0002)
        self.edt_bottom_line.setMaximumWidth(120)
        self.edt_bottom_line.setSuffix('  u')

        self.edt_ot_comboBox = QtGui.QComboBox()
        self.edt_ot_comboBox.addItem('Center', [0.5, 0.5])
        self.edt_ot_comboBox.addItem('Top Left', [0, 0])
        self.edt_ot_comboBox.addItem('Bottom Left', [0, 1])
        self.edt_ot_comboBox.addItem('Top Right', [1, 0])
        self.edt_ot_comboBox.addItem('Bottom Right', [1, 1])

  
        # footer
        self.btn_transform = QtGui.QPushButton('Run')
        self.btn_close = QtGui.QPushButton('Close')

        self.chkbox_change_flag = QtGui.QCheckBox('Flag Changed Glyphs:')
        self.cmb_select_color = QtGui.QComboBox()

        for i in range(len(fontMarkColors)):

            self.cmb_select_color.addItem(get_icon_from_color(QtGui.QColor(fontMarkColors[i][2])), '', fontMarkColors[i][1])

        self.cmb_select_color.setMaximumWidth(50)
        self.cmb_select_color.setIconSize(QtCore.QSize(30,30))
        self.cmb_select_color.setStyleSheet("font-size: 22px; padding: 0") 


        # labels

        self.lbl_h_transform = QtGui.QLabel('Horizontal Transform')
        self.lbl_upper_scale = QtGui.QLabel('Top')
        self.lbl_lower_scale = QtGui.QLabel('Bottom')

        self.lbl_v_transform = QtGui.QLabel('Vertical Transform')
        self.lbl_left_scale = QtGui.QLabel('Left')
        self.lbl_right_scale = QtGui.QLabel('Right')

        self.lbl_top_line = QtGui.QLabel('Top Line')
        self.lbl_bottom_line = QtGui.QLabel('Bottom Line')

        self.lbl_origin = QtGui.QLabel('Origin')

        # spacer
        self.vSpacer15 = QtGui.QSpacerItem(15, 1)
        self.vSpacer600 = QtGui.QSpacerItem(600, 1)
        self.hSpacer10 = QtGui.QSpacerItem(1, 20)

        # slots
        self.edt_upper_scale.editingFinished.connect(self.tSpinboxChanged)
        self.edt_lower_scale.editingFinished.connect(self.bSpinboxChanged)
        self.edt_left_scale.editingFinished.connect(self.lSpinboxChanged)
        self.edt_right_scale.editingFinished.connect(self.rSpinboxChanged)
        self.edt_ot_comboBox.currentIndexChanged.connect(self.originComboChanged)
        self.btn_transform.clicked.connect(self.process_transform)
        self.btn_close.clicked.connect(self.closeWidget)

        # groupBox
        self.selected_groupbox = QtGui.QGroupBox(concatStr(str(len(self.glyphs)),' Glyphs Selected'))
        self.manipulating_groupbox = QtGui.QGroupBox('')
        self.preview_groupbox = PreviewGroupbox(self)
        self.input_groupbox = QtGui.QGroupBox('')
        self.main_groupbox = QtGui.QWidget()
        self.footer_groupbox = QtGui.QWidget()

        #layouts
        self.layout_main = QtGui.QHBoxLayout()
        self.layout_main.addWidget(self.selected_groupbox)
        self.layout_main.addWidget(self.manipulating_groupbox)
        
        self.layout_footer = QtGui.QHBoxLayout()
        self.layout_footer.addWidget(self.chkbox_change_flag)
        self.layout_footer.addWidget(self.cmb_select_color)
        self.layout_footer.addItem(self.vSpacer600)
        self.layout_footer.addWidget(self.btn_transform)
        self.layout_footer.addWidget(self.btn_close)

        self.layout_app = QtGui.QVBoxLayout()
        self.layout_app.addWidget(self.main_groupbox)
        self.layout_app.addWidget(self.footer_groupbox)


        self.layout_input = QtGui.QGridLayout()
#       QGridLayout.addWidget(widget, fromRow, fromCol, rowSpan, colSpan)
        self.layout_input.addWidget(self.lbl_origin, 0, 6, 1, 1)
        self.layout_input.addWidget(self.edt_ot_comboBox, 0, 7, 1, 1)

        self.layout_input.addWidget(self.lbl_h_transform, 0, 0, 1, 2 )
        self.layout_input.addWidget(self.lbl_upper_scale, 1, 0, 1, 1 )
        self.layout_input.addWidget(self.lbl_lower_scale, 2, 0, 1, 1 )
        self.layout_input.addWidget(self.edt_upper_scale, 1, 1, 1, 1)
        self.layout_input.addWidget(self.edt_lower_scale, 2, 1, 1, 1)
        self.layout_input.addItem(self.vSpacer15, 0, 2)
                
        self.layout_input.addWidget(self.lbl_v_transform, 0, 3, 1, 2 )
        self.layout_input.addWidget(self.lbl_left_scale, 1, 3, 1, 1 )
        self.layout_input.addWidget(self.lbl_right_scale, 2, 3, 1, 1 )
        self.layout_input.addWidget(self.edt_left_scale, 1, 4, 1, 1)
        self.layout_input.addWidget(self.edt_right_scale, 2, 4, 1, 1)
        self.layout_input.addItem(self.vSpacer15, 0, 5)

        self.layout_input.addWidget(self.lbl_top_line, 1, 6, 1, 1 )
        self.layout_input.addWidget(self.lbl_bottom_line, 2, 6, 1, 1 )
        self.layout_input.addWidget(self.edt_top_line, 1, 7, 1, 1)
        self.layout_input.addWidget(self.edt_bottom_line, 2, 7, 1, 1)
        self.layout_input.addItem(self.hSpacer10, 3, 1)

        self.layout_selected = QtGui.QVBoxLayout()
        self.layout_selected.addWidget(self.tree_glyphZones)

        self.layout_manipulating = QtGui.QVBoxLayout()
        self.layout_manipulating.addWidget(self.preview_groupbox)
        self.layout_manipulating.addWidget(self.input_groupbox)


        self.input_groupbox.setLayout(self.layout_input)
        self.input_groupbox.setMaximumHeight(150)
        self.selected_groupbox.setLayout(self.layout_selected)
        self.selected_groupbox.setMaximumWidth(430)
        self.manipulating_groupbox.setLayout(self.layout_manipulating)
        self.main_groupbox.setLayout(self.layout_main)
        self.footer_groupbox.setLayout(self.layout_footer)
        self.setLayout(self.layout_app)
        self.setWindowTitle('%s %s' %(app_name, app_version))
        self.setGeometry(300, 100, 1200, 600)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) # Always on top!!
        self.show()
    
        pts = [500, 500, 100, 100]

        
    def tSpinboxChanged(self): 
        self.transformValue[0] = float(self.edt_upper_scale.value) / 100
        self.preview_groupbox.refresh()
    
    def bSpinboxChanged(self): 
        self.transformValue[1] = float(self.edt_lower_scale.value) / 100
        self.preview_groupbox.refresh()
        
    
    def lSpinboxChanged(self):
        self.transformValue[2] = float(self.edt_left_scale.value) / 100
        self.preview_groupbox.refresh()
    
    def rSpinboxChanged(self):
        self.transformValue[3] = float(self.edt_right_scale.value) / 100
        self.preview_groupbox.refresh()

    def originComboChanged(self):
        self.ot = self.edt_ot_comboBox.currentData
        self.preview_groupbox.refresh()

    def closeWidget(self):
        self.close()


    #getting homography Matrices=========
    def homography_from_4pt(self, p1, p2, p3, p4, arr) : 
        t1 = p1[0]
        t2 = p3[0]
        t4 = p2[1]
        t5 = t1 * t2 * t4
        t6 = p4[1]
        t7 = t1 * t6
        t8 = t2 * t7
        t9 = p3[1]
        t10 = t1 * t9
        t11 = p2[0]
        t14 = p1[1]
        t15 = p4[0]
        t16 = t14 * t15
        t18 = t16 * t11
        t20 = t15 * t11 * t9
        t21 = t15 * t4
        t24 = t15 * t9
        t25 = t2 * t4
        t26 = t6 * t2
        t27 = t6 * t11
        t28 = t9 * t11
        t30 = 0.1e1 / (-t24 + t21 - t25 + t26 - t27 + t28)
        t32 = t1 * t15
        t35 = t14 * t11
        t41 = t4 * t1
        t42 = t6 * t41
        t43 = t14 * t2
        t46 = t16 * t9
        t48 = t14 * t9 * t11
        t51 = t4 * t6 * t2
        t55 = t6 * t14

        arr[0][0] = -(-t5 + t8 + t10 * t11 - t11 * t7 - t16 * t2 + t18 - t20 + t21 * t2) * t30
        arr[0][1] = (t5 - t8 - t32 * t4 + t32 * t9 + t18 - t2 * t35 + t27 * t2 - t20) * t30
        arr[0][2] = t1
        arr[1][0] = (-t9 * t7 + t42 + t43 * t4 - t16 * t4 + t46 - t48 + t27 * t9 - t51) * t30
        arr[1][1] = (-t42 + t41 * t9 - t55 * t2 + t46 - t48 + t55 * t11 + t51 - t21 * t9) * t30
        arr[1][2] = t14
        arr[2][0] = (-t10 + t41 + t43 - t35 + t24 - t21 - t26 + t27) * t30
        arr[2][1] = (-t7 + t10 + t16 - t43 + t27 - t28 - t21 + t25) * t30

    def homography_from_4corresp(self, pts1, pts2) : 
        p1, p2, p3, p4 = pts1
        q1, q2, q3, q4 = pts2
        rows = 3
        cols = 3
        H = [[0 for j in range(cols)] for i in range(rows)]

        Hr = [[0 for j in range(cols)] for i in range(rows)]
        Hl = [[0 for j in range(cols)] for i in range(rows)]

        self.homography_from_4pt(p1, p2, p3, p4, Hr)
        self.homography_from_4pt(q1, q2, q3, q4, Hl)


        # the following code computes R = Hl * inverse Hr
        t2 = Hr[1][1] - Hr[2][1] * Hr[1][2]
        t4 = Hr[0][0] * Hr[1][1]
        t5 = Hr[0][0] * Hr[1][2]
        t7 = Hr[1][0] * Hr[0][1]
        t8 = Hr[0][2] * Hr[1][0]
        t10 = Hr[0][1] * Hr[2][0]
        t12 = Hr[0][2] * Hr[2][0]
        t15 = 1 / (t4 - t5*Hr[2][1] - t7 + t8*Hr[2][1] + t10*Hr[1][2] - t12*Hr[1][1])
        t18 = -Hr[1][0] + Hr[1][2] * Hr[2][0]
        t23 = -Hr[1][0] * Hr[2][1] + Hr[1][1] * Hr[2][0]
        t28 = -Hr[0][1] + Hr[0][2] * Hr[2][1]
        t31 = Hr[0][0] - t12
        t35 = Hr[0][0] * Hr[2][1] - t10
        t41 = -Hr[0][1] * Hr[1][2] + Hr[0][2] * Hr[1][1]
        t44 = t5 - t8
        t47 = t4 - t7
        t48 = t2*t15
        t49 = t28*t15
        t50 = t41*t15
        H[0][0] = Hl[0][0] * t48 + Hl[0][1] * (t18*t15) - Hl[0][2] * (t23*t15)
        H[0][1] = Hl[0][0] * t49 + Hl[0][1] * (t31*t15) - Hl[0][2] * (t35*t15)
        H[0][2] = -Hl[0][0] * t50 - Hl[0][1] * (t44*t15) + Hl[0][2] * (t47*t15)
        H[1][0] = Hl[1][0] * t48 + Hl[1][1] * (t18*t15) - Hl[1][2] * (t23*t15)
        H[1][1] = Hl[1][0] * t49 + Hl[1][1] * (t31*t15) - Hl[1][2] * (t35*t15)
        H[1][2] = -Hl[1][0] * t50 - Hl[1][1] * (t44*t15) + Hl[1][2] * (t47*t15)
        H[2][0] = Hl[2][0] * t48 + Hl[2][1] * (t18*t15) - t23*t15
        H[2][1] = Hl[2][0] * t49 + Hl[2][1] * (t31*t15) - t35*t15
        H[2][2] = -Hl[2][0] * t50 - Hl[2][1] * (t44*t15) + t47*t15

        return H

    def get_homography_matrix(self, width):  
        ascd = self.edt_top_line.value #760
        desc = self.edt_bottom_line.value #-128
        
        pts1 = [[0, ascd], [0, desc], [width, desc], [width, ascd]]

        upperScale = float(self.edt_upper_scale.value) / 100
        lowerScale = float(self.edt_lower_scale.value) / 100
        leftScale = float(self.edt_left_scale.value) / 100
        rightScale = float(self.edt_right_scale.value) / 100

        pts2= self.calculate_new_pts(width, [upperScale, lowerScale, leftScale, rightScale], self.ot, pts1)
        mtrxH = self.homography_from_4corresp(pts1, pts2)
        return mtrxH

    def calculate_new_pts(self, width, scaleValues, ot, pts1, isPreview=False):
#        scaleValues = [upperScale, lowerScale, leftScale, rightScale]   

        computed_ot = [ ot[0] * width + pts1[0][0], pts1[0][1] + (pts1[1][1] - pts1[0][1]) * ot[1] ]

        normalizerH = self.standardWidth / width if not isPreview else 1
        #print('\n', pts1, '\n', scaleValues, '\n', computed_ot, '\n', normalizerH)

        add_p0_x = pts1[0][0] + (pts1[0][0] - computed_ot[0]) * (scaleValues[0] - 1) * normalizerH
        add_p3_x = pts1[3][0] + (pts1[3][0] - computed_ot[0]) * (scaleValues[0] - 1) * normalizerH
        add_p1_x = pts1[1][0] + (pts1[1][0] - computed_ot[0]) * (scaleValues[1] - 1) * normalizerH
        add_p2_x = pts1[2][0] + (pts1[2][0] - computed_ot[0]) * (scaleValues[1] - 1) * normalizerH

        add_p0_y = pts1[0][1] + (pts1[0][1] - computed_ot[1]) * (scaleValues[2] - 1)
        add_p1_y = pts1[1][1] + (pts1[1][1] - computed_ot[1]) * (scaleValues[2] - 1)
        add_p3_y = pts1[3][1] + (pts1[3][1] - computed_ot[1]) * (scaleValues[3] - 1)
        add_p2_y = pts1[2][1] + (pts1[2][1] - computed_ot[1]) * (scaleValues[3] - 1)
        

        #print(add_p0_x,' = ', pts1[0][0],' + ,(', pts1[0][0] ,' - ', computed_ot[0], ') * (', scaleValues[0],' - 1) * ', normalizerH,'\n', add_p3_x,' = ',pts1[3][0],' + (',pts1[3][0],' - ',computed_ot[0],') * (',scaleValues[0],' - 1) * ', normalizerH)
        if add_p2_x - add_p1_x < 0 :
            #print(add_p0_x, add_p1_x, add_p2_x, add_p3_x)
            offset = 20 
            add_p0_x = add_p0_x - (add_p1_x - width/2) - offset
            add_p3_x = add_p3_x - (add_p2_x - width/2) + offset
            add_p1_x = pts1[0][0] + width/2 - offset
            add_p2_x = pts1[0][0] + width/2 + offset

        pts2 = [ [add_p0_x, add_p0_y], [add_p1_x, add_p1_y], [add_p2_x, add_p2_y], [add_p3_x, add_p3_y] ]

        return pts2

    def process_transform(self) :
        print('=== Process Started ===')
        data = self.glyphs

        for ind, i in enumerate(data): 
            if(ind > 0 and ind % 500 == 0):
                print('.')
            nodeList = i.nodes()
            width = i.getAdvance() 
            H = self.get_homography_matrix(width)

            for j in nodeList :
                n = eNode(j)
                x = n.asCoord().x
                y = n.asCoord().y
                newPts = [(H[0][0] * x + H[0][1] * y + H[0][2]) / (H[2][0] * x + H[2][1] * y + H[2][2]), (H[1][0] * x + H[1][1] * y + H[1][2]) / (H[2][0] * x + H[2][1] * y + H[2][2]) ]
                n.reloc(newPts[0], newPts[1])
            
            if self.chkbox_change_flag.isChecked():
                i.setMark(self.cmb_select_color.currentData)

            if len(data) == 1:
                i.updateObject(i.fl, '%s Modified' %i.name)

        if len(data) > 1:
            font.updateObject(font.fl,'%s Glyphs Modified' %len(data))	
                
        self.btn_transform.setEnabled(False)

        print('=== Process Completed ===')


dialog = MainWindow()



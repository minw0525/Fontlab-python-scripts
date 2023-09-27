#FLM: MW: Colorize Glyphs

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


# init ====
app_name, app_version = 'Minwoo | Colorize Glyphs', '1.0'

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
    font-size: 20px;
}

QPushButton{
    background: transparent;
    border-radius: 5px;
    height: 30px;
    min-width: 50px;
    border: 1px solid #5E5E5E;
    font-size: 20px;
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
        for eGlyph in sorted(data, key = lambda x: x.name):
            slicedName = list(eGlyph.name.partition('.')) # ex) ['uniAC00','alt'] from 'uniAC00.alt' 
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

        # footer
        self.btn_transform = QtGui.QPushButton('Run')
        self.btn_close = QtGui.QPushButton('Close')
        self.lbl_change_flag = QtGui.QLabel('Flag Glyphs:')
        self.cmb_select_color = QtGui.QComboBox()

        for i in range(len(fontMarkColors)):

            self.cmb_select_color.addItem(get_icon_from_color(QtGui.QColor(fontMarkColors[i][2])), '', fontMarkColors[i][1])

        self.cmb_select_color.setMaximumWidth(50)
        self.cmb_select_color.setIconSize(QtCore.QSize(30,30))


        # labels

        # spacer
        self.vSpacer15 = QtGui.QSpacerItem(15, 1)
        self.vSpacer100 = QtGui.QSpacerItem(100, 1)
        self.hSpacer10 = QtGui.QSpacerItem(1, 20)

        # slots
        self.btn_transform.clicked.connect(self.process_transform)
        self.btn_close.clicked.connect(self.closeWidget)

        # groupBox
        self.selected_groupbox = QtGui.QGroupBox(concatStr(str(len(self.glyphs)),' Glyphs Selected'))
        self.main_groupbox = QtGui.QWidget()
        self.footer_groupbox = QtGui.QWidget()

        #layouts
        self.layout_main = QtGui.QHBoxLayout()
        self.layout_main.addWidget(self.selected_groupbox)
        
        self.layout_footer = QtGui.QHBoxLayout()
        self.layout_footer.addWidget(self.lbl_change_flag)
        self.layout_footer.addWidget(self.cmb_select_color)
        self.layout_footer.addItem(self.vSpacer100)
        self.layout_footer.addWidget(self.btn_transform)
        self.layout_footer.addWidget(self.btn_close)

        self.layout_app = QtGui.QVBoxLayout()
        self.layout_app.addWidget(self.main_groupbox)
        self.layout_app.addWidget(self.footer_groupbox)
          
        self.layout_selected = QtGui.QVBoxLayout()
        self.layout_selected.addWidget(self.tree_glyphZones)

        self.selected_groupbox.setLayout(self.layout_selected)
        self.selected_groupbox.setMaximumWidth(430)
        self.main_groupbox.setLayout(self.layout_main)
        self.footer_groupbox.setLayout(self.layout_footer)
        self.setLayout(self.layout_app)
        self.setWindowTitle('%s %s' %(app_name, app_version))
        self.setGeometry(300, 100, 430, 500)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) # Always on top!!
        self.show()
    

    def closeWidget(self):
        self.close()

    def process_transform(self) :
        print('=== Process Started ===')
        data = self.glyphs

        for ind, i in enumerate(data): 
            if(ind > 0 and ind % 500 == 0):
                print('.')
            
            i.setMark(self.cmb_select_color.currentData)

            if len(data) == 1:
                i.updateObject(i.fl, '%s Colorized' %i.name)

        if len(data) > 1:
            font.updateObject(font.fl,'%s Glyphs Colorized' %len(data))	
                
        print('=== Process Completed ===')


dialog = MainWindow()



#FLM: MW: Smart Component Widget
import inspect, sys

import fontlab as fl6
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.objects.glyph import pGlyph
from typerig.proxy.fl.application.app import pWorkspace

from typerig.proxy.fl.gui.widgets import *
from typerig.proxy.fl.gui import QtGui

from PythonQt import QtCore

app_version = '1.0.0'
app_name = 'Minwoo | Smart Component Widget'

os = sys.platform
qapp = QtGui.QApplication.instance()
ws = pWorkspace()
main = ws.main
menuObject = main.findChild('QMenu','menuObject')
viewport = ws.getCanvas().viewPort if ws.getCanvas() else main.findChild('GlyphWindow', 'GlyphWindow') or main.findChild('FontWindow', 'FontWindow') or main

##Easy Debug
def printL(*args):
    line = inspect.getframeinfo(inspect.stack()[1][0]).lineno
    print(f'line {line} : \t', ', '.join([str(x) for x in args[0:]]))

###########################################################


g = pGlyph()
QSS = '''
QLineEdit{
    background-color: white;
    height: 10px;
    width: 35px;
    padding: 0 5px;
    font-size: 14px;
}
QSlider::groove:horizontal {
    border: 1px dotted #505050;
    height: 0px;
    margin: 1px 0;
}
QSlider::handle:horizontal {
    background-color: white;
    border: 1px solid #404040;
    width: 14px;
    height: 14px;
    margin: -8px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */
    border-radius: 8px;
}
QLabel{
    font-size: 15px;
    font-weight: bold;
}
'''

QSS2 = '''
QPushButton{
    width: 14px;
    height: 20px;
    font-size: 13px;
    margin: 0;
    border:none;
    background:transparent;
    border-radius: 5px;
    font-weight: bold;
}
QPushButton:pressed{
    background-color: #ffffff;
    color: #333333;
}
QPushButton:checked{
    background-color: #bfbfbf;
    color: #333333;
}
'''
class CustomSlider(QtGui.QSlider):
    def __init__(self, orientation, aux):
        super(CustomSlider, self).__init__()
        self.orientation = orientation
        self.isDrag = False
        self.aux = aux
        # self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        # self.setMaximumHeight(30)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            e.accept()
            x = e.pos().x()
            value = (self.maximum - self.minimum) * x / self.width + self.minimum
            self.setValue(int(value))

    def mouseMoveEvent(self, e):
        if e.buttons() & QtCore.Qt.LeftButton:
            e.accept()
            x = e.pos().x()
            value = (self.maximum - self.minimum) * x / self.width + self.minimum
            self.setValue(int(value))

            if not self.isDrag:
                self.isDrag = True

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton and self.isDrag:
            e.accept()
            self.isDrag = False
            x = e.pos().x()
            value = (self.maximum - self.minimum) * x / self.width + self.minimum
            self.aux.updateChange()

class CustomLineEdit(QtGui.QLineEdit):
    def __init__(self, aux):
        super(CustomLineEdit, self).__init__()

        self.aux = aux
        self.setValidator(QtGui.QDoubleValidator(0, 1000, 2) )
        self.setMaximumHeight(30)
        self.increment = 1 

    def keyPressEvent(self, e):
        # modifiers = QtGui.QApplication.keyboardModifiers()
        if e.modifiers() & QtCore.Qt.ControlModifier :
            multiply = 100
        elif e.modifiers() & QtCore.Qt.ShiftModifier :
            multiply = 10
        else :
            multiply = 1
            
        if e.key() == QtCore.Qt.Key_Up:
            self.setText(int(self.text) + self.increment * multiply)
            self.aux.onLineEditChange()
        if e.key() == QtCore.Qt.Key_Down:
            self.setText(int(self.text) - self.increment * multiply)
            self.aux.onLineEditChange()
        
        QtGui.QLineEdit.keyPressEvent(self, e)


        
class SliderControl(QtGui.QWidget):
    def __init__(self, data, aux):
        super(SliderControl, self).__init__()
        
        self.aux = aux
        self.data = data
        self.axis = data[0]
        self.location = data[1]
        self.setStyleSheet(QSS)
    
        #Widget
        self.labelAxis = QtGui.QLabel(self.axis)
        self.locSlider = CustomSlider(QtCore.Qt.Horizontal, self)
        self.locSlider.setMinimum(0) 
        self.locSlider.setMaximum(1000) 
        self.locSlider.setSingleStep(1) 
        self.locSlider.setTickPosition(3) 
        self.locSlider.sliderReleased.connect(self.updateChange)

        # self.locSlider.setMinimumWidth(self.locSlider.width)
        self.locEdit = CustomLineEdit(self)

        #Layout
        self.vLayout = QtGui.QVBoxLayout()
        self.vLayout.addWidget(self.labelAxis)
        self.vLayout.setSpacing(0)
        self.vLayout.setContentsMargins(0, 20, 0, 0)
        self.hLayout = QtGui.QHBoxLayout()
        self.hLayout.addWidget(self.locSlider, 7)
        self.hLayout.addWidget(self.locEdit, 1)
        self.vLayout.setSpacing(10)
        self.setLayout(self.vLayout)
        self.vLayout.addLayout(self.hLayout)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.vLayout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self.setMaximumSize(250, 73)

        self.locSlider.setValue(int(float(self.location))) 
        self.locEdit.setText(int(float(self.location)))

        #Trigger
        self.locSlider.valueChanged.connect(self.onSliderChange)
        self.locEdit.editingFinished.connect(self.onLineEditChange)

    def updateValue(self, value):
        if self.aux.glyph.id == pGlyph().id:
            self.location = value
            self.locSlider.setValue(int(self.location)) 
            self.locEdit.setText(int(self.location))
        # printL(93, self.axis , self.location)
            self.aux.updateShapeData()
            return
        print('Refresh Widget!')
        
        
    def onSliderChange(self):
        self.updateValue(self.locSlider.value)

    def onLineEditChange(self):
        self.updateValue(int(self.locEdit.text))
        self.updateChange()

    def mousePressEvent(self, e):
        # printL('Slidercontrol press')
        if e.buttons() == QtCore.Qt.LeftButton:
            e.accept()
            value = e.globalPos()
            self.aux.dragPos = value
            # printL(108, value)

    def mouseReleaseEvent(self, e):
        self.updateChange()

    def updateChange(self):
        self.aux.glyph.updateObject(self.aux.glyph.fl, 'Set Component Location', False) 

class StatusWidget(QtGui.QWidget):
    def __init__(self, aux):
        super(StatusWidget, self).__init__()
        self.aux = aux
        self.isPinned = False

        self.pinBtn = QtGui.QPushButton('📍')
        self.hspacer = QtGui.QSpacerItem(20, 24, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.refreshBtn = QtGui.QPushButton('↻')
        self.closeBtn = QtGui.QPushButton('☓')
 
        self.pinBtn.setCheckable(True)
        self.pinBtn.toggled.connect(self.pinWidget)
        
        self.closeBtn.clicked.connect(self.aux.closeWidget)
        self.refreshBtn.clicked.connect(self.aux.aux.refreshWidget)

        self.hLayout = QtGui.QHBoxLayout()
        self.hLayout.addWidget(self.pinBtn)
        self.hLayout.addItem(self.hspacer)
        self.hLayout.addWidget(self.refreshBtn)
        self.hLayout.addWidget(self.closeBtn)
        self.hLayout.setMargin(0)
        self.hLayout.setSpacing(0)
        self.setLayout(self.hLayout)
        self.setStyleSheet(QSS2)
        self.setMinimumSize(250, 24)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)

    def pinWidget(self):
        if self.isPinned == False:
            printL('pinned!')
        else: 
            printL('unpinned!')
        self.aux.isDraggable = self.isPinned
        self.isPinned = not self.isPinned 



class Controls(QtGui.QWidget):
    #초기 세팅: 글립 / 선택 컴포넌트 / 축 / 위치 지정
    def __init__(self, aux):
        super(Controls, self).__init__()
        self.isDraggable = True
        self.aux = aux

        #widgets
        self.title = QtGui.QLabel("Select Smart Component")
        self.closeBtn = QtGui.QPushButton('×')
        self.status = StatusWidget(self)

        #layout
        self.vLayout = QtGui.QVBoxLayout()
        # self.vLayout.addWidget(self.title)
        # self.vLayout.addWidget(self.closeBtn)
        self.vLayout.addWidget(self.status)
        self.vLayout.setContentsMargins(20, 10, 20, 20)
        self.vLayout.setSpacing(0)
        self.setLayout(self.vLayout)
        self.setGeometry(0, 0, 250, 70)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        self.currWidgetShape = None
        self.isSmartComponent = False
        self.controllers = [] #SliderControl 리스트
        self.setData() #글립 / 선택 컴포넌트 / 축 / 위치 초기화, 스마트컴포넌트면 위치 parse
        self.buildWidget() #위젯 초기 렌더


    def setData(self):
        self.currfont = pFont() 
        self.glyph = pGlyph() #선택 글립
        self.components = self.glyph.components() #현재 글립의 컴포넌트 리스트
        self.layer = self.glyph.layer() #현재 레이어
        self.selectedShape = self.layer.getActiveShape() and self.layer.getActiveShape()[0] or None # 선택한 shape (없으면 None)
        self.locString = '' #초기화
        self.locData = {} #초기화
        self.allContoursInGlyph = self.layer and self.layer.getContours() or [] # 글립 전체 컨투어
        self.checkSmart(self.selectedShape)
        if  self.isSmartComponent : #선택한 shape이 스마트컴포넌트라면  => locString parse 
            self.parseLocations(self.locString) #locData 저장



    def checkSmart(self, selectedShape): #선택한 shape
        if not selectedShape :
            printL('Select Shape')
            self.isSmartComponent = False
            return

        #컴포넌트 아니면 return
        if not selectedShape in self.components:
            self.isSmartComponent = False
            printL('Select Component')
            return
            
        #컴포넌트면 locstring 저장
        self.locString = selectedShape.shapeData.componentLayer
        # printL(169, self.locString)

        #스마트 컴포넌트가 아니네요 => 위치 레이어
        if '#' not in self.locString and ':' not in self.locString:
            self.isSmartComponent = False
            printL('Select Smart Component')
            return
        #스마트 컴포넌트네요
        self.isSmartComponent = True

            

    def buildWidget(self): #새로운 컴포넌트 선택했을 경우만 재렌더 
        #이미 선택한 컴포넌트면 return
        # printL( getattr(self.currWidgetShape, 'id', None) , getattr(self.selectedShape, 'id', None), getattr(self.currWidgetShape, 'id', None) == getattr(self.selectedShape, 'id', None))
        # printL(183, self.locString)
        if getattr(self.currWidgetShape, 'id', None) == getattr(self.selectedShape, 'id', None):
            return

        #위젯 내용 있다면 비우기
        if len(self.controllers):
            for controller in self.controllers :
                self.vLayout.removeWidget(controller)
                controller.setParent(None)
                controller.deleteLater()
                del controller
            self.controllers = []
        self.currWidgetShape = self.selectedShape #선택이 스마트컴포넌트면 위젯 표시 컴포넌트 동기화


        #위젯 내용 없음 - locData 비어있으면 (스마트 컴포넌트 아님) return
        if not self.isSmartComponent and len(self.locData.items()) == 0:
            return

        #locData로 SliderControl 생성
        for data in self.locData.items():
            # printL(204, data)
            controller = SliderControl(data, self)
            self.controllers.append(controller)
            self.vLayout.addWidget(controller)

        self.adjustSize()

    def resetWidget(self): #위젯 재렌더
        self.setData()
        self.buildWidget()


    def updateShapeData(self): #SliderControl 데이터 수합해 컴포넌트 업데이트
        # printL(214, self.controllers)
        self.locData = {controller.axis : controller.location for controller in self.controllers} #locData 업데이트
        # printL(216, self.locData)
        self.composeLocations(self.locData) #locString 업데이트
        # printL(218, self.locString)
        # printL(220, self.selectedShape.shapeData.componentLayer)
        self.selectedShape.shapeData.componentLayer = self.locString #컴포넌트 새 위치 적용
        self.selectedShape.update()
		

    def parseLocations(self, locString): #locString -> locData
        # printL('217 parseLocation : ', locString)
        if (':' in locString) : 
            locString = locString.split(':')[1]
        if ('#' in locString) : 
            locString = locString.split('#')[1]
        locValues = locString.split(',')
        printL(locValues)
        # printL(225, locString)
        self.locData = dict([axis.split('=') for axis in locValues])


    def composeLocations(self, locData): #locData -> locString 
        # printL(self.locData)
        self.locString = '#'+','.join([f'{key}={value}'for (key, value) in locData.items()])
        # printL(self.locData)


    def mousePressEvent(self, e):
        #printL('Controls Clicked')
        if e.buttons() == QtCore.Qt.LeftButton and self.isDraggable:
            # printL(265, e.globalPos())
            self.dragPos = e.globalPos()


    def mouseMoveEvent(self, e):
        if e.buttons() == QtCore.Qt.LeftButton and self.isDraggable:
            # printL(self.aux.pos, e.globalPos(),  self.dragPos)
            # self.aux.move(self.pos + e.globalPos() - self.dragPos)
            self.aux.move(self.aux.pos + e.globalPos() - self.dragPos)
            self.dragPos = e.globalPos()
            e.accept()

    def closeWidget(self):
        self.aux.hideWidget()
    



class FloatingWindow(QtGui.QDockWidget):
    # - Split/Break contour 
    def __init__(self, *args):
        super(FloatingWindow, self).__init__(args)

        #Data
        self.setObjectName('SCW')
        self.controlWidget = Controls(self)
        self.setWidget(self.controlWidget)
        self.setAttribute(55) # Qt::WA_DeleteOnClose	
        self.setTitleBarWidget(QtGui.QWidget())
        self.setWindowOpacity(0.945)
        self.setStyleSheet('''QWidget{
    background-color: #f0f1f2;
}''')
    # border: 1px solid black;
        #Geometry
        self.w = 250
        self.h = 200
        self.setWindowTitle('%s %s' %(app_name, app_version))
        # self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | ~QtCore.Qt.WindowTitleHint ) 
        self.dragPos = QtCore.QPoint()

        self.setFloating(True)
        self.setGeometry(0, 0, self.w, self.h)
        self.setMinimumSize(250,60)
        # self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        self.adjustSize()

        self.move(viewport.mapToGlobal(viewport.pos).x()+20, viewport.mapToGlobal(viewport.geometry.bottomRight()).y() - self.height -3 )
        # self.move(84, 261)
        # printL(self.mapToGlobal(self.pos))

        self.setCornerMask(10)

        menuObject.addSeparator()
        self.actiondata = ['Edit Smart Component Location', self.revealSelf,'Alt+s'] 
        self.action = Action(self.actiondata, menuObject)
        self.action.addSelf()
        
        if os != 'darwin' :
            main.addDockWidget(0x2, self) 
        else:
            self.revealSelf()

    def setCornerMask(self, radius):
        path = QtGui.QPainterPath() 
        path.addRoundedRect(QtCore.QRectF(self.rect), radius, radius)
        self.cornermask = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(self.cornermask)

    def mousePressEvent(self, e):
        # printL('FloatingWindow Clicked', self.pos, e.globalPos())
        if e.buttons() == QtCore.Qt.LeftButton:
            self.dragPos = e.globalPos()

    def refreshWidget(self):
        self.controlWidget.resetWidget()

        newheight = 0
        margintop = self.controlWidget.layout().contentsMargins().top()
        marginbottom = self.controlWidget.layout().contentsMargins().bottom()
        sliders = [x for x in self.controlWidget.children() if isinstance(x, SliderControl)]

        newheight = self.controlWidget.status.height + margintop + marginbottom + 73 * len(sliders)


        self.h = self.height
        self.setFixedSize(self.width,newheight)
        self.setCornerMask(10)
        self.move(self.pos.x(), self.pos.y() - self.height + self.h )


    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.hideWidget()

    def hideWidget(self):
        main.removeDockWidget(self)
        self.hide()

    def revealSelf(self):
        #이미 켜져있을 때 (컴포넌트 / 글립 선택 바뀔 때 ): 현재 선택 컴포넌트 정보 표시 
        if self.visible : 
            printL('-------------------')
            self.refreshWidget()
            return
        #꺼져 있을 때 : 켜고 선택 shape 정보 표시
        self.show()
        # printL('show')




class Action(QtGui.QAction):
    def __init__(self, data, actions) :
        super().__init__(Action, actions)
        
        self.actionData = data
        self.actions = actions
        self.setText(self.actionData[0])
        self.triggered.connect(self.actionData[1])
        self.setShortcut(QtGui.QKeySequence(self.actionData[2]))

    def addSelf(self) :
        for action in self.actions.actions():
            if action.text == self.actionData[0]:
                action.setShortcut(QtGui.QKeySequence())
                action.removeSelf()
        self.actions.addAction(self)
        self.setShortcut(QtGui.QKeySequence(self.actionData[2]))

    
    def removeSelf(self) :
        self.actions.removeAction(self)
        return


if main.findChild('QDockWidget', 'SCW') or 'SCW' in map(lambda x: x.objectName,qapp.allWidgets()):
    prev = main.findChild('QDockWidget', 'SCW') or list(filter(lambda x:x.objectName == 'SCW',qapp.allWidgets()))[0]
    prev.close()
    FloatingWindow = FloatingWindow('SCW', main)
# # 
#     FloatingWindow.revealSelf()
else:   
    FloatingWindow = FloatingWindow('SCW', main)
    printL(FloatingWindow.parentWidget())






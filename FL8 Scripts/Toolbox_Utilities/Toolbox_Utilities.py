#FLM: MW: Toolbox Utilities
from math import radians, dist, pi, atan 
# from collections import OrderedDict
# from itertools import groupby

import fontlab as fl6

from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui
from typerig.proxy.fl.application.app import pWorkspace
from typerig.proxy.fl.gui.widgets import getTRIconFont
from typerig.proxy.fl.objects.node import eNode, eNodesContainer




qapp = QtGui.QApplication.instance()
ws = pWorkspace()
fp = ws.fl.currentPackage
main = ws.main
TRToolFont = getTRIconFont()
#TRToolFont.setPixelSize(20)
TRToolFont.setWeight(400)
menuContour = main.findChild('QMenu','menuContour')


class Util:
    def __init__(self):
        self.distance = 5
        self.selectedNodes = []
        self.nodePairs = {}
        self.isItalic = fp.italic
        self.glyph = fl6.flGlyph(fl6.CurrentGlyph(), fl6.CurrentFont())
        self.currLayer = self.glyph.activeLayer
        self.contourClipboard = []
        self.allContoursInGlyph = self.currLayer and self.currLayer.getContours() or []

        self.actionData = {
            "text" : ["metrics_advance","metrics_advance_vertical", "node_add", "corner_round", "sync"],
            "title" : ["Set X Distance","Set Y Distance", "Duplicate Nodes", "Select Entire Contour", "Form Symmetrical Circle"],
            "tooltip" : ['Set X Distance (Shift+X): Set distance between duplicated nodes to 10.', 'Set Y Distance (Shift+Y): Set distance between duplicated nodes to 10.', 'Duplicate Nodes (Ctrl+Alt+D): Duplicate selected nodes.', 'Select Contour (`): Select Entire Contour to Which Selected Nodes or Handles Belong.', 'Form Symmetrical Circle (Shift+O): Copy, Flip, Paste Nodes to Form a Symmetrical Circle.'],
            "slot" : [self.setXDistance, self.setYDistance, self.duplicateNodes, self.selectEntireContour, self.flipToSymmetricCircle],
            "shortcut" : ['Shift+x', 'Shift+y', 'Ctrl+Alt+d', '`', 'Shift+o']
        }
    def setNodeSelection(func):
        def setter(self):
            self.selectedNodes = ws.getSelectedNodes()
            return func(self)
        return setter 

    def checkNodePairs(self) :
        self.selectedNodes = [node for node in ws.getSelectedNodes() if node.isOn()]
        self.nodePairs = {}
        try: 
            if len(self.selectedNodes) % 2 != 0:
                raise IndexError(len(self.selectedNodes))

            for idx, node in enumerate(self.selectedNodes):
                pairIdx, nodeIdx = divmod(idx, 2)
                self.nodePairs.setdefault(pairIdx, []).append(node)

        except IndexError as e:
            print(f"Odd number of nodes selected. ({e} nodes)")
            

    def setXDistance(self) :
        self.checkNodePairs()
        for pair in self.nodePairs.values() : 
            try:             
                if pair[0].x != pair[1].x :
                    raise ValueError("X coordinates are not equal.")
                    
                indicator = True if (pair[0].prevNode().x - pair[0].x) < 0 else False
                    ##if True = Outer Contour
                pair[0].x = pair[0].x - self.distance if indicator else pair[0].x + self.distance 
                pair[1].x = pair[1].x + self.distance if indicator else pair[1].x - self.distance 
                pair[0].setPrevSmooth()
                pair[1].setNextSmooth()
                #print(pair[0].x, pair[0].x - self.distance if indicator else pair[0].x + self.distance )
                #print(pair[1].x, pair[1].x + self.distance if indicator else pair[1].x - self.distance )

                self.updateObject(self.glyph, 'Set X Distance')

            except ValueError as e:
                print("Select nodes with duplicate coordinates.", e)

                
    def setYDistance(self) :
        self.checkNodePairs()
        
        for pair in self.nodePairs.values() : 
            try:         
                if pair[0].y != pair[1].y :
                    raise ValueError("Y coordinates are not equal.")
                    
                indicator = True if (pair[0].prevNode().y - pair[0].y) < 0 else False
                    ##if True = Outer Contour
                pair[0].y = pair[0].y - self.distance if indicator else pair[0].y + self.distance 
                pair[1].y = pair[1].y + self.distance if indicator else pair[1].y - self.distance 

                #if self.isItalic :
                #    distanceX = atan(radians(fp.italicAngle_value)) * self.distance
                #    pair[0].x = pair[0].x + distanceX if indicator else pair[0].x - distanceX
                #    pair[1].x = pair[1].x - distanceX if indicator else pair[1].x + distanceX 

                pair[0].setPrevSmooth()
                pair[1].setNextSmooth()
                #print(pair[0].y, pair[0].y - self.distance if indicator else pair[0].y + self.distance )
                #print(pair[1].y, pair[1].y + self.distance if indicator else pair[1].y - self.distance )

                self.updateObject(self.glyph, 'Set Y Distance')

            except ValueError as e:
                print("Select nodes with duplicate coordinates.", e)
            
                
    @setNodeSelection
    def duplicateNodes(self):
        try:
            for node in self.selectedNodes:
                contour = node.contour
                onNodes = [node.index for node in contour.nodes() if node.isOn()]
                nId = node.index
                onNodeIdx = onNodes.index(nId)
                contour.insertNodeTo(onNodeIdx)

            self.updateObject(self.glyph, 'Duplicate Nodes')

        except ValueError as e:
            print("Curve handle can't be duplicated")

    @setNodeSelection
    def selectEntireContour(self):
        try:
            self.canvas = ws.getCanvas()
            self.vp = self.canvas.viewPort
            if self.selectedNodes:
                for i, selectedNode in enumerate(self.selectedNodes):
                    if selectedNode.contour.isAllNodesSelected() : continue
                    for j, node in enumerate(selectedNode.contour.nodes()):
                        node.selected = True
            self.updateObject(self.glyph, 'Select contour')

        except AttributeError:
            print('No Canvas Opened')

    def flipToSymmetricCircle(self):
        try:
            self.copyNodes()
            self.pasteNodes()

        except ValueError as e:
            print(f"Must select at least 2 nodes. {e} nodes selected." )

        except Exception as e:
            print(e)

    @setNodeSelection
    def copyNodes(self):
        if len(self.selectedNodes) < 2:
            raise ValueError(len(self.selectedNodes))

        layer = self.currLayer.name
        startNode = self.selectedNodes[0]
        prevNode = self.selectedNodes[0]
        
        for node in self.selectedNodes:
            startNode = node if node.index != (prevNode.index + 1) else startNode
            prevNode = node
            
        print(f'Nodes Copied. {self.selectedNodes[0].index} to {self.selectedNodes[-1].index}')

        startNode.contour.setStartPoint(startNode.index)

        self.selectedNodes = sorted(self.selectedNodes, key=lambda x:x.index)
        self.node_bank = {layer : eNodesContainer([node.clone() for node in self.selectedNodes], extend=eNode)}

        

    def pasteNodes(self):
        layer = self.currLayer.name
        
        if layer in self.node_bank.keys():
            dst_container = eNodesContainer(self.selectedNodes, extend=eNode)

            if len(dst_container):
                src_container = self.node_bank[layer].clone()
                src_transform = QtGui.QTransform()
                                                            
                # - Transform
                scaleX = -1 
                scaleY = -1
                dX = src_container.x() + src_container.width()/2
                dY = src_container.y() + src_container.height()/2


                #src_transform.translate(dX, dY)
                src_transform.scale(scaleX, scaleY)
                src_transform.translate(-dX, -dY)
                src_container.applyTransform(src_transform)
                    
                # - Align source
                #if self.copy_align_state is None:
                src_container.shift(*src_container[-1].diffTo(dst_container[0]))

                insert_index = dst_container[-1].index + 1
                insert_contour = dst_container[0].contour
                insert_contour.removeNodesBetween(dst_container[-1].fl, dst_container[0].fl)
                insert_contour.insert(insert_index, [node.fl for node in src_container.nodes])

                
                insert_contour.removeAt(insert_index + len(src_container)-1)
                insert_contour.removeAt(insert_index)

        self.updateObject(insert_contour, 'Paste contours')

    # @setNodeSelection
    # def getSelectedContourIndices(self):
    #     self.allContoursInGlyph = self.currLayer.getContours()
    #     selectedIndices = []
    #     for node in self.selectedNodes:
    #         if self.allContoursInGlyph.index(node.contour) not in selectedIndices:
    #             selectedIndices.append(self.allContoursInGlyph.index(node.contour))
    #     return selectedIndices

    # @setNodeSelection
    # def getSelectedShapeIndex(self):
    #     self.allShapesInGlyph = self.currLayer.shapes
    #     selectedIndex = [self.allShapesInGlyph.index(shape) for shape in self.allShapesInGlyph for contour in shape.contours for node in contour.nodes() if node in self.selectedNodes][0]
    #     return selectedIndex

    # def closeContour(self):
    #     selectedContourIdx = self.getSelectedContourIndices()
    #     for cID in selectedContourIdx:
    #         if not self.allContoursInGlyph[cID].closed: self.allContoursInGlyph[cID].closed = True
 
    # @setNodeSelection
    # def copyContour(self):
    #     # - Init
    #     self.allContoursInGlyph = self.currLayer.getContours()
    #     self.allNodesInGlyph = [node for contour in self.currLayer.getContours() for node in contour.nodes()]
    #     export_clipboard = OrderedDict()

    #     # - Build initial contour information
    #     selectionTuples = [(self.allContoursInGlyph.index(node.contour), node.index) for node in self.selectedNodes]
    #     selection = {key:[index[1] for index in value] if not self.allContoursInGlyph[key].isAllNodesSelected() else [] for key, value in groupby(selectionTuples, lambda x:x[0])}
    #     print(selectionTuples, selection)
    #     # - Process
    #     if len(selection.keys()):
    #         # -- Add to clipboard
    #         wLayer = self.currLayer.name
    #         export_clipboard[wLayer] = []

    #         for cid, nList in selection.items():
    #             # print(cid, nList)
    #             if len(nList):
    #                     export_clipboard[wLayer].append(fl6.flContour([self.allContoursInGlyph[cid].nodes()[nid].clone() for nid in nList]))
    #             else:
    #                 export_clipboard[wLayer].append(self.allContoursInGlyph[cid].clone())
    #         # print([contour.nodes() for contour in export_clipboard[wLayer]])
    #         self.contourClipboard.append(export_clipboard)

    #     print(f'Contour Copied. {self.contourClipboard}')

    # def pasteContour(self):
    #     # - Init
    #     wGlyph = eGlyph()

    #     # - Process
    #     paste_data = self.contourClipboard[0]
    #     for layerName, contours in paste_data.items():
    #         wLayer = layerName
    #         if wLayer is not None:	
    #             # - Process transform
    #             # print([contour.nodes() for contour in contours])
    #             cloned_contours = [contour.clone() for contour in contours]

    #             # - Insert contours into currently selected shape
    #             try:
    #                 selected_shape = self.currLayer.shapes[self.getSelectedShapeIndex()]
                
    #             except IndexError:
    #                 print('indexerror')
    #                 selected_shape = fl6.flShape()
    #                 self.currLayer.addShape(selected_shape)

    #             selected_shape.addContours(cloned_contours, True)
                
        
    #         self.updateObject(self.glyph, 'Paste contours')


        
    def updateObject(self, flObject, undoMessage, verbose=True):
        fl6.flItems.notifyChangesApplied(undoMessage[:20], flObject, True)
        if verbose: print(f'DONE:{undoMessage}')
        
        # - New from 6774 on
        for contour in self.allContoursInGlyph:
            contour.changed()

        fl6.flItems.notifyPackageContentUpdated(self.glyph.fgPackage.id)


class Button(QtGui.QToolButton):
    def __init__(self, idx, widget) :
        super(Button,self).__init__()
        
        self.idx = idx
        self.widget = widget
        self.setText(UtilClass.actionData["text"][self.idx])
        self.setFont(TRToolFont)
        self.setToolTip(UtilClass.actionData["tooltip"][self.idx])
        self.clicked.connect(UtilClass.actionData["slot"][self.idx])
        self.setShortcut(QtGui.QKeySequence(UtilClass.actionData["shortcut"][self.idx]))
        self.setStyleSheet('''
        QToolButton{
            border-radius: 13; 
            margin: 3 1 3 1; 
            width: 23px; 
            height: 23px; 
            font-weight: 400;
        }
        ''')

    def insertSelf(self):
        for child in self.widget.findChildren('QToolButton'):
            if child.text == UtilClass.actionData["text"][self.idx]:
                return
        widgetLayout = self.widget.layout()
        spacer = QtGui.QSpacerItem(2,20)
        if not widgetLayout.itemAt(widgetLayout.count() - 2).spacerItem() :
            widgetLayout.insertItem(widgetLayout.count() - 2, spacer)
            widgetLayout.insertWidget(widgetLayout.count() - 2, self)


class Action(QtGui.QAction):
    def __init__(self, idx, actions) :
        super().__init__(Action, actions)
        
        self.idx = idx
        self.actions = actions
        self.setText(UtilClass.actionData["title"][self.idx])
        self.triggered.connect(UtilClass.actionData["slot"][self.idx])
        self.setShortcut(QtGui.QKeySequence(UtilClass.actionData["shortcut"][self.idx]))

    def addSelf(self) :
        for action in self.actions.actions():
            if action.text == UtilClass.actionData["title"][self.idx]:
                return
        self.actions.addAction(self)

# class Toobar(QtGui.QToolBar):
#     def __init__(self) -> None:
#         super(Toobar, self).__init__()
        
#         self.util = Util()
        
#         self.chk_Select_Node1 = QtGui.QAction("metrics_advance", self)
#         self.addAction(self.chk_Select_Node1)
#         self.chk_Select_Node1.setToolTip('Set X Distance (Shift+x): Set distance between duplicated nodes to 6.')
#         self.setMenuRole(TextHeuristicRole)
#         self.chk_Select_Node1.triggered.connect(self.util.setXDistance)
#         self.chk_Select_Node1.setFont(TRToolFont)
#         self.chk_Select_Node1.setShortcut(QtGui.QKeySequence('Shift+x'))
        
#         self.chk_Select_Node2 = QtGui.QAction("metrics_advance_vertical", self)
#         self.addAction(self.chk_Select_Node2)
#         self.chk_Select_Node2.setToolTip('Set Y Distance (Shift+y): Set distance between duplicated nodes to 6.')
#         self.chk_Select_Node2.triggered.connect(self.util.setYDistance)
#         self.chk_Select_Node2.setFont(TRToolFont)
#         self.chk_Select_Node2.setShortcut(QtGui.QKeySequence('Shift+y'))

#         self.chk_Select_Node3 = QtGui.QAction("node_add", self)
#         self.addAction(self.chk_Select_Node3)
#         self.chk_Select_Node3.setToolTip('Duplicate Nodes (Ctrl+Alt+d): Duplicate selected nodes.')
#         self.chk_Select_Node3.triggered.connect(self.util.duplicateNodes)
#         self.chk_Select_Node3.setFont(TRToolFont)
#         self.chk_Select_Node3.setShortcut(QtGui.QKeySequence('Ctrl+Alt+d'))


#     def contextMenuEvent(self, e):
#         return False 

#     def keyPressEvent(self, e):
#         if e.key() == QtCore.Qt.Key_Escape:
#             self.close()

def run() :
    if main.findChild('WidgetNodes','WidgetNodes') :
        widgetnodes = main.findChild('WidgetNodes','WidgetNodes')

        for i in range(len(UtilClass.actionData["text"])):
            btn = Button(i, widgetnodes)
            btn.insertSelf()

        widgetnodes.setMaximumSize(1000,16777215)
        widgetnodes.resize(widgetnodes.minimumWidth + 125 + 25,38)
        widgetnodes.setWindowFlags(widgetnodes.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        widgetnodes.show()
    # else:    
    #     buttonWidget = Toobar()    
    #     main.addToolBar(QtCore.Qt.TopToolBarArea, buttonWidget)

    menuContour.addSeparator()
    for i in range(len(UtilClass.actionData["text"])):
        action = Action(i, menuContour)
        action.addSelf()
        

if fl6.CurrentFont() :
    UtilClass = Util()
    run()
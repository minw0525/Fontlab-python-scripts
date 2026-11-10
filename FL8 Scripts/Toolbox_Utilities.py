#FLM: MW: Toolbox Utilities
import builtins

from math import radians, dist, pi, atan 
# from collections import OrderedDict
# from itertools import groupby

import fontlab as fl6

from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui
from typerig.proxy.fl.application.app import pWorkspace
from typerig.proxy.fl.gui.widgets import getTRIconFont
from typerig.proxy.fl.objects.node import eNode, eNodesContainer



app_version = "1.5.0"
qapp = QtGui.QApplication.instance()
ws = pWorkspace()
main = ws.main
TRToolFont = getTRIconFont()
#TRToolFont.setPixelSize(20)
TRToolFont.setWeight(400)
menuContour = main.findChild('QMenu','menuContour')


def memberValue(obj, name):
    # FontLab/TypeRig builds expose some members as properties, others as methods.
    value = getattr(obj, name)
    return value() if callable(value) else value


class Util:
    def __init__(self):
        self.distance = 5
        self.selectedNodes = []
        self.nodePairs = {}
        self.glyph = None
        self.currLayer = None
        self.contourClipboard = []
        self.allContoursInGlyph = []

        self.actionData = {
            "text" : ["metrics_advance","metrics_advance_vertical", "node_add", "corner_round", "sync"],
            "title" : ["Set X Distance","Set Y Distance", "Duplicate Nodes", "Select Entire Contour", "Form Symmetrical Circle"],
            "tooltip" : ['Set distance between duplicated nodes to 10 on X.', 'Set distance between duplicated nodes to 10 on Y.', 'Duplicate selected nodes.', 'Select the entire contour containing selected nodes or handles.', 'Copy, flip and paste nodes to form a symmetrical circle.'],
            "slot" : [self.setXDistance, self.setYDistance, self.duplicateNodes, self.selectEntireContour, self.flipToSymmetricCircle],
            "shortcut" : ['Ctrl+Alt+Shift+X', 'Ctrl+Alt+Shift+Y', 'Ctrl+Alt+Shift+D', 'Ctrl+Alt+Shift+E', 'Ctrl+Alt+Shift+R']
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
                onNodes = [memberValue(node, 'index') for node in contour.nodes() if node.isOn()]
                nId = memberValue(node, 'index')
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
            startNode = node if memberValue(node, 'index') != (memberValue(prevNode, 'index') + 1) else startNode
            prevNode = node
            
        print('Nodes Copied. {} to {}'.format(memberValue(self.selectedNodes[0], 'index'), memberValue(self.selectedNodes[-1], 'index')))

        startNode.contour.setStartPoint(memberValue(startNode, 'index'))

        self.selectedNodes = sorted(self.selectedNodes, key=lambda x:memberValue(x, 'index'))
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
                dX = memberValue(src_container, 'x') + memberValue(src_container, 'width')/2
                dY = memberValue(src_container, 'y') + memberValue(src_container, 'height')/2


                #src_transform.translate(dX, dY)
                src_transform.scale(scaleX, scaleY)
                src_transform.translate(-dX, -dY)
                src_container.applyTransform(src_transform)
                    
                # - Align source
                #if self.copy_align_state is None:
                src_container.shift(*src_container[-1].diffTo(dst_container[0]))

                insert_index = memberValue(dst_container[-1], 'index') + 1
                insert_contour = dst_container[0].contour
                insert_contour.removeNodesBetween(dst_container[-1].fl, dst_container[0].fl)
                insert_contour.insert(insert_index, [node.fl for node in src_container.nodes])

                
                insert_contour.removeAt(insert_index + len(src_container)-1)
                insert_contour.removeAt(insert_index)

        self.updateObject(insert_contour, 'Paste contours')

        
    def updateObject(self, flObject, undoMessage, verbose=True):
        fl6.flItems.notifyChangesApplied(undoMessage[:20], flObject, True)
        if verbose: print(f'DONE:{undoMessage}')
        
        # - New from 6774 on
        for contour in self.allContoursInGlyph:
            contour.changed()

        fl6.flItems.notifyPackageContentUpdated(self.glyph.fgPackage.id)


CONTROLLER_KEY = '_minwoo_toolbox_utilities'
ROW_NAME = 'MinwooToolboxUtilitiesRow'


class ToolboxUtilities:
    lifecycleVersion = 1
    codeVersion = app_version

    def __init__(self):
        self.util = Util()
        self.actions = []
        self.separator = None
        if menuContour is not None:
            self.separator = menuContour.addSeparator()
        for idx, title in enumerate(self.util.actionData['title']):
            action = QtGui.QAction(title, main)
            action.setObjectName('MinwooToolboxUtilitiesAction{}'.format(idx))
            action.setShortcutContext(QtCore.Qt.WindowShortcut)
            action.triggered.connect(lambda checked=False, index=idx: self.invoke(index))
            sequence = QtGui.QKeySequence(self.util.actionData['shortcut'][idx])
            conflicts = []
            for widget in qapp.allWidgets():
                for other in widget.actions():
                    if any(sequence.matches(key) != QtGui.QKeySequence.NoMatch
                           or key.matches(sequence) != QtGui.QKeySequence.NoMatch
                           for key in other.shortcuts()):
                        conflicts.append(str(other.text))
                for other in widget.findChildren('QShortcut'):
                    if sequence.matches(other.key) != QtGui.QKeySequence.NoMatch:
                        conflicts.append(str(other.objectName) or 'QShortcut')
            tooltip = self.util.actionData['tooltip'][idx]
            if conflicts:
                print('Shortcut skipped: {} ({}) conflicts with {}'.format(
                    title, sequence.toString(), ', '.join(sorted(set(conflicts)))))
            else:
                action.setShortcut(sequence)
                tooltip += ' ({})'.format(sequence.toString(QtGui.QKeySequence.NativeText))
            action.setToolTip(tooltip)
            main.addAction(action)
            if menuContour is not None:
                menuContour.addAction(action)
            self.actions.append(action)
            print('Toolbox Utilities: {} -> {} [Contour menu: {}]'.format(
                title, memberValue(action, 'shortcut').toString(QtGui.QKeySequence.NativeText) or 'unassigned',
                'yes' if menuContour is not None else 'not found'))
        # Queue one update after FontLab finishes changing the tool panel.
        self.toolTimer = QtCore.QTimer(main)
        self.toolTimer.setSingleShot(True)
        self.toolTimer.setInterval(0)
        self.toolTimer.timeout.connect(self.attachButtons)
        nodesAction = main.findChild('QAction', 'actionNodes_tool')
        toolGroup = nodesAction.actionGroup() if nodesAction is not None else None
        self.toolActions = list(toolGroup.actions()) if toolGroup is not None else []
        for action in self.toolActions:
            action.toggled.connect(self.toolChanged)
        # Fallback for panel recreation that does not change the active tool.
        self.timer = QtCore.QTimer(main)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.attachButtons)
        self.attachButtons()
        self.timer.start()

    def toolChanged(self, checked):
        if checked:
            self.toolTimer.start()

    def invoke(self, idx):
        # Resolve the active glyph on every invocation, not at script startup.
        font = fl6.CurrentFont()
        glyph = fl6.CurrentGlyph()
        if font is None or glyph is None or ws.getCanvas() is None:
            print('Open a glyph window before using Toolbox Utilities.')
            return
        self.util.glyph = fl6.flGlyph(glyph, font)
        self.util.currLayer = self.util.glyph.activeLayer
        if self.util.currLayer is None:
            return
        self.util.allContoursInGlyph = self.util.currLayer.getContours()
        self.util.actionData['slot'][idx]()

    def attachButtons(self):
        # macOS WidgetNodes is a top-level widget; Windows may parent it.
        # FontLab can replace/reset this panel when switching tools.
        for widget in qapp.allWidgets():
            if widget.objectName != 'WidgetNodes' or widget.layout() is None:
                continue
            row = widget.findChild('QWidget', ROW_NAME)
            if row is None:
                row = QtGui.QWidget(widget)
                row.setObjectName(ROW_NAME)
                layout = QtGui.QHBoxLayout(row)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
                for idx, action in enumerate(self.actions):
                    button = QtGui.QToolButton(row)
                    # Keep icon-font text independent of QAction state updates.
                    button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
                    button.setText(self.util.actionData['text'][idx])
                    button.setFont(TRToolFont)
                    button.setToolTip(memberValue(action, 'toolTip'))
                    button.clicked.connect(lambda checked=False, index=idx: self.invoke(index))
                    button.setFocusPolicy(QtCore.Qt.NoFocus)
                    button.setFixedSize(27, 30)
                    layout.addWidget(button)
                hostLayout = widget.layout()
                close = widget.findChild('QToolButton', 'buttonClose')
                position = hostLayout.indexOf(close) if close is not None else hostLayout.count()
                hostLayout.insertWidget(position, row)
            row.show()
            width = widget.layout().sizeHint().width()
            widget.setMinimumWidth(width)
            widget.setMaximumWidth(16777215)
            if widget.width < width:
                widget.resize(width, widget.height)

def run():
    previous = getattr(builtins, CONTROLLER_KEY, None)
    if previous is not None:
        if (getattr(previous, 'lifecycleVersion', None) != 1
                or getattr(previous, 'codeVersion', None) != app_version
                or not getattr(previous, 'ready', False)):
            print(f'Toolbox Utilities: restart FontLab before running version {app_version}. Existing actions were not changed.')
            return
        # Keep the same actions, callbacks and timers for the entire session.
        previous.attachButtons()
        print('Toolbox Utilities is already loaded. Restart FontLab to apply code or shortcut changes.')
        return

    # An older script may have registered actions without keeping a controller.
    titles = Util().actionData['title']
    for action in main.findChildren('QAction'):
        if str(action.objectName).startswith('MinwooToolboxUtilitiesAction') or action.text in titles:
            print(f'Toolbox Utilities: existing actions found. Restart FontLab before running version {app_version}.')
            return

    # Retain even a partially initialized controller: a failed startup must not
    # leave registered actions behind and then create a second set on retry.
    controller = ToolboxUtilities.__new__(ToolboxUtilities)
    controller.ready = False
    setattr(builtins, CONTROLLER_KEY, controller)
    controller.__init__()
    controller.ready = True


run()

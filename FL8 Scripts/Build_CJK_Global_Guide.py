#FLM: MW: Build CJK Global Guide

import fontlab as fl6
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui.widgets import getProcessGlyphs
from PythonQt import QtCore
from PythonQt.QtGui import QApplication, QInputDialog, QColor

qapp = QApplication.instance()
app_version = '1.0.1'
app_name = 'Minwoo | Build CJK Global Guide'

font = pFont()
workspace = fl6.flWorkspace.instance()

if workspace.getActiveCanvas() is not None:
    pMode = 1
else :
    pMode = 2

# if mode == 0: [selected glyph]
# if mode == 1: [glyphs in edit window]
# if mode == 2: [selected glyphs in font window]
# if mode == 3: [all glyphs in font]

gs = getProcessGlyphs(pMode)

EM = font.fl.upm
ASC = font.fl.ascender_value
DESC = font.fl.descender_value

IDEO_LIST = ["ga-ko", "uniAC00", "ideographicspace", "uni3000", "filler-ko", "uni3164"]
for i in IDEO_LIST:
    try :
        ADV = font.glyph(i).getAdvance()
        break
    except:
        ADV = EM
        continue
    
V_MID = (ASC + DESC) / 2
H_MID = ADV / 2
TOP = V_MID + EM / 2
BOTTOM = V_MID - EM / 2
OFFSET = 50
BG_NAME = "_global"


margin_dlg = QInputDialog()
margin_dlg.setInputMode(QInputDialog.IntInput)
margin_dlg.setWindowTitle(f"{app_name} {app_version}")
margin_dlg.setLabelText("여백: ")
margin_dlg.setIntRange(1, EM)
margin_dlg.setIntValue(100)
margin_dlg.setIntStep(1)

margin_dlg_w = 340
margin_dlg_h = 120
desktop_geo = qapp.desktop().geometry

center_x = desktop_geo.x() + int(desktop_geo.width() / 2) - int(margin_dlg_w / 2)
center_y = desktop_geo.y() + int(desktop_geo.height() / 2) - int(margin_dlg_h / 2)
margin_dlg.setGeometry(center_x, center_y, margin_dlg_w, margin_dlg_h)

if margin_dlg.exec_():
    MARGIN = margin_dlg.intValue()
        
    PLACEHOLDER_DATA = [
        [{'coord': (MARGIN, BOTTOM + MARGIN), 'nodeType': 'on'}, {'coord': (ADV - MARGIN, BOTTOM + MARGIN), 'nodeType': 'on'}, {'coord': (ADV - MARGIN, TOP - MARGIN), 'nodeType': 'on'}, {'coord': (MARGIN, TOP - MARGIN), 'nodeType': 'on'}],
        [{'coord': (0.0, BOTTOM), 'nodeType': 'on'}, {'coord': (ADV, BOTTOM), 'nodeType': 'on'}, {'coord': (ADV, TOP), 'nodeType': 'on'}, {'coord': (0.0, TOP), 'nodeType': 'on'}],
        [{'coord': (-OFFSET, V_MID), 'nodeType': 'on'}, {'coord': (ADV + OFFSET, V_MID), 'nodeType': 'on'}],
        [{'coord': (H_MID, TOP + OFFSET), 'nodeType': 'on'}, {'coord': (H_MID, BOTTOM-OFFSET), 'nodeType': 'on'}]
    ]


    # if font.hasGlyph(BG_NAME):
    #     pass
    #     bg = font.glyph(BG_NAME)
    # else:
    #     bg = font.newGlyph(BG_NAME, font.masters())
    #     bg.setAdvance(ADV)
    def __dict_elements_to_flNodes(elements):
        """
        Converts a list of dicts (from get_painter_path_elements_dict) to a list of flNode objects.
        """
        node_list = []
        for elem in elements:
            pt = QtCore.QPointF(*elem["coord"])
            nodeType = elem["nodeType"]
            node_list.append(fl6.flNode(pt, nodeType=nodeType))
        return node_list
    
    new_shape = fl6.flShape()
    new_shape.shapeData.name = f"{BG_NAME}.{MARGIN}"
    new_contours = []  

    for elements in PLACEHOLDER_DATA:
        node_list = __dict_elements_to_flNodes(elements)
        contour = fl6.flContour(node_list, closed=True)
        new_contours.append(contour)
    
    new_shape.contours = new_contours
#    bg.layer().addShape(new_shape)


    for g in gs:
        layer_name = g.fl.activeLayer.name

        if g.layer().isImgLayer:
            targetLayer = g.layer()
        else:
            targetLayer = g.layer().getImgLayer(True)
            targetLayer.isLocked = True
            targetLayer.isService = True
            targetLayer.isWireframe = True
            targetLayer.wireframeColor = QColor("#4eaa4e")
        targetLayer.addShape(new_shape)
        
    gs[0].updateObject(font.fl, 'Global Guide Pasted', False)
    font.update()
else:
    pass



#FLM: MW: Build Asterisk

import fontlab as fl6
from typerig.proxy.fl.objects.glyph import pGlyph
from PythonQt.QtGui import QApplication, QTransform, QInputDialog

qapp = QApplication.instance()
app_version = '1.0.1'
app_name = 'Minwoo | Build Asterisk'


def rounded_int(value):
    # Round half away from zero
    value = float(value)
    if value >= 0:
        return int(value + 0.5)
    return -int(-value + 0.5)

def rotation_transform(angle, pivot):
    transform = QTransform()

    transform.translate(pivot.x(), pivot.y())
    transform.rotate(angle)
    transform.translate(-pivot.x(), -pivot.y())

    return transform

def get_source_shapes(pGlyph):
    original_shapes = pGlyph.shapes()

    if pGlyph.selected():
        original_shapes = pGlyph.selectedShapes()
    return original_shapes
    
def main():
    font = fl6.flPackage(fl6.CurrentFont())
    glyph = pGlyph()
    adv = glyph.getAdvance()


    ref_coord = [adv / 2 , font.xHeight_value + (font.capsHeight_value - font.xHeight_value) / 3 ]
    pivot = None

    hasPivot = False
    for anchor in glyph.anchors():
        if anchor.name == "asterisk":
            pivot = anchor.point
            hasPivot = True
    if hasPivot == False:
        newAnchor = glyph.addAnchor(ref_coord, 'asterisk')
        pivot = newAnchor.point
        hasPivot = True

    countDlg = QInputDialog()
    countDlg.setInputMode(QInputDialog.IntInput)
    countDlg.setWindowTitle(f"{app_name} {app_version}")
    countDlg.setLabelText("반복 횟수:")
    countDlg.setIntValue(5)
    countDlg.setIntRange(2, 100)
    countDlg.setIntStep(1)

    countDlg_w = 270
    countDlg_h = 120
    desktop_geo = qapp.desktop().geometry

    center_x = desktop_geo.x() + int(desktop_geo.width() / 2) - int(countDlg_w / 2)
    center_y = desktop_geo.y() + int(desktop_geo.height() / 2) - int(countDlg_h / 2)
    countDlg.setGeometry(center_x, center_y, countDlg_w, countDlg_h)
    
    if countDlg.exec_():
        count = countDlg.intValue()
        source_shapes = get_source_shapes(glyph)
        print(source_shapes)
        if not source_shapes:
            print("ERROR: No source shapes.")
            return
        
        for i in range(count - 1):
            for shape in source_shapes:
                newShape = glyph.layer().addShape(shape)
                rotation = rotation_transform(360 / count * (i + 1), pivot)
                newShape.transform = rotation
        
        glyph.updateObject(glyph.fl, 'Asterisk Built', False)
        glyph.update()
    else:
        pass
        
main()
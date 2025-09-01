import fontlab as fl6
import fontgate as fgt

from typerig.proxy.fl.objects.font import eFont
from typerig.proxy.fl.objects.glyph import pGlyph
from typerig.proxy.fl.objects.node import eNode
from typerig.proxy.fl.objects.contour import pContour
from typerig.proxy.fl.application.app import *
from typerig.proxy.fl.application.app import pWorkspace

from PythonQt import QtCore
from typerig.proxy.fl.gui import QtGui
from typerig.proxy.fl.gui.widgets import getProcessGlyphs

glyphs = getProcessGlyphs(1)
#0: Current Glyph
#1: All Glyphs in Edit Window
#2: Selected Glyphs in Font Window
#3: All Glyphs in Font

for glyph in glyphs:
    layer = glyph.layer()
    print(layer.name)
    for shape in layer.shapes:
        shape.shapeData.componentLayer = layer.name

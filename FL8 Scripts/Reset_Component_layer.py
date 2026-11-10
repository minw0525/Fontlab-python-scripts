#FLM: MW: Reset Component Layer

import fontlab as fl6
from typerig.proxy.fl.gui.widgets import getProcessGlyphs

app_version = '1.0.1'
workspace = fl6.flWorkspace.instance()

if workspace.getActiveCanvas() is not None:
    pMode = 1
else :
    pMode = 2

# if mode == 0: [selected glyph]
# if mode == 1: [glyphs in edit window]
# if mode == 2: [selected glyphs in font window]
# if mode == 3: [all glyphs in font]

glyphs = getProcessGlyphs(pMode)

for glyph in glyphs:
    layer = glyph.layer()
    for shape in layer.shapes:
        if shape.shapeData.componentLayer != layer.name:
            shape.shapeData.componentLayer = layer.name
            print(f"{glyph.name} :: Component({shape.shapeData.componentGlyph}) Location Reset")

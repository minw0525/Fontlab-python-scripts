#FLM: MW: Edit Component Sources

import fontlab as fl6
import fontgate as fgt
import FL as legacy 

from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui.widgets import getProcessGlyphs

pMode = 1
# if mode == 0: [selected glyph]
# if mode == 1: [glyphs in edit window]
# if mode == 2: [selected glyphs in font window]
# if mode == 3: [all glyphs in font]

font = pFont()
font_masters = font.masters()
textblock = set()

glyphs = getProcessGlyphs(pMode)
print(len(glyphs))
for glyph in glyphs:
    for shapeName in glyph.getCompositionNames():
        textblock.add(shapeName)
textblock = sorted(textblock)

def setTextblock(charArr):
    symbolLists = fl6.fgSymbolList([fl6.fgSymbol(chr) for chr in charArr])   
    fl6.flItems().requestContent(symbolLists, 0)

def editOnCanvas(charArr, onNewTab=True):
    if onNewTab:
        legacy.fl.EditGlyph()
    setTextblock(charArr)
    
def editOnNewTab(charArr):
    if len(charArr):
        editOnCanvas(charArr, True)
    else: 
        print('문자열이 없습니다.')
        return
        
editOnNewTab(textblock)
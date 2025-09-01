#FLM: MW: Check Negative Side-bearing

from typerig.proxy.fl.objects.font import pFont
import FL as legacy
import fontlab as fl6
import fontgate as fgt

nT = fgt.fgNametable()

font = pFont()

errors = []
for glyph in font.pGlyphs() :
    if glyph.getLSB() < 0 :
        if glyph.name not in errors:
            errors.append(glyph.name)
    if glyph.getRSB() < 0 :
        if glyph.name not in errors:
            errors.append(glyph.name)

def setTextblock(charArr):
    symbolLists = fl6.fgSymbolList([fl6.fgSymbol(char) for char in charArr])   
    fl6.flItems().requestContent(symbolLists, 0)

def editOnCanvas(charArr, onNewTab=True):
    print(charArr)
    if onNewTab:
        legacy.fl.EditGlyph()
    setTextblock(charArr)
    
editOnCanvas(errors)
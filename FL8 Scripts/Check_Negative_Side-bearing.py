#FLM: MW: Check Negative Side-bearing

from typerig.proxy.fl.objects.font import pFont
import FL as legacy
import fontlab as fl6
import fontgate as fgt

app_version = '1.0.1'

nT = fgt.fgNametable()
font = pFont()

errors = []
for glyph in font.pGlyphs() :
    try:
        if glyph.getLSB() < 0 :
            if glyph.name not in errors:
                errors.append(glyph.name)
                print(f"{glyph.name}:: LSB less than 0 !!!")
        if glyph.getRSB() < 0 :
            if glyph.name not in errors:
                errors.append(glyph.name)
                print(f"{glyph.name}:: RSB less than 0 !!!")
    except Exception as e:
        print(f"{glyph.name}:: {e}")
        
def setTextblock(charArr):
    symbolLists = fl6.fgSymbolList([fl6.fgSymbol(char) for char in charArr])   
    fl6.flItems().requestContent(symbolLists, 0)

def editOnCanvas(charArr, onNewTab=True):
    if onNewTab:
        legacy.fl.EditGlyph()
    setTextblock(charArr)
    
editOnCanvas(errors)
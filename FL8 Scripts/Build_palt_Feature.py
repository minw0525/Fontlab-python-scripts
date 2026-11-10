#FLM: MW: Build palt Feature

import fontlab as fl6
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui.widgets import getProcessGlyphs

app_version = '1.0.0'

def findGlyphsWithAnchor(findAnchorNames, targetScope):
    foundGlyphs = []
    for glyph in targetScope:
        anchorNames = []
        for anchor in glyph.anchors():
            anchorNames.append(anchor.name)
        if set(findAnchorNames) & set(anchorNames):
            foundGlyphs.append(glyph)
    return foundGlyphs

def rounded_int(value):
    # Round half away from zero
    value = float(value)
    if value >= 0:
        return int(value + 0.5)
    return -int(-value + 0.5)

def get_anchor_x(glyph, name):
    # pGlyph.anchors() returns flPinPoint objects
    for anchor in glyph.anchors():
        if anchor.name == name:
            return float(anchor.point.x())
    return None

def generate_record(glyph):

    left_x = get_anchor_x(glyph, 'lsb')
    right_x = get_anchor_x(glyph, 'rsb')

    if left_x is None and right_x is None:
        return None, "missing both anchors"
    
    advance = float(glyph.getAdvance())

    if left_x is None:
        left_x = 0

    if right_x is None:
        right_x = advance

    if right_x <= left_x:
        return None, "invalid anchor order"

    x_placement = rounded_int(-left_x)
    x_advance = rounded_int(right_x - left_x - advance)

    if x_placement == 0 and x_advance == 0:
        return None, "zero adjustment"

    return (x_placement, x_advance), None

    record = (
        f"    pos {glyph.name} "
        f"<{x_placement} 0 {x_advance} 0>;"
    )

    return record, None

def main():
    font = pFont()
    workspace = fl6.flWorkspace.instance()

    pMode = 3
    # if mode == 0: [selected glyph]
    # if mode == 1: [glyphs in edit window]
    # if mode == 2: [selected glyphs in font window]
    # if mode == 3: [all glyphs in font]
    
    targetScope = getProcessGlyphs(pMode)

    ANCHOR_TAGS = ('lsb','rsb')
    FEATURE_TAG = 'palt'

    targetGlyphs = findGlyphsWithAnchor(ANCHOR_TAGS, targetScope)

    if not targetGlyphs:
        print("No glyphs found.")
        return

    groups = {}
    skipped = []
    seen = set()

    for glyph in targetGlyphs:
        if glyph.name in seen:
            continue

        seen.add(glyph.name)

        try:
            adjustment, reason = generate_record(glyph)
            
            if adjustment is not None:
                groups.setdefault(adjustment, []).append(glyph.name)
            else:
                skipped.append((glyph.name, reason))
        
        except Exception as e:
            skipped.append((glyph.name, str(e)))
        
        records = []
        for (x_placement, x_advance), glyph_names in groups.items():

            if len(glyph_names) == 1:
                target = glyph_names[0]
            else:
                target = "[" + " ".join(glyph_names) + "]"

            records.append(
                f"    pos {target} "
                f"<{x_placement} 0 {x_advance} 0>;"
            )

        lines = [
            f"feature {FEATURE_TAG} {{",
            *records,
            f"}} {FEATURE_TAG};",
        ]

    output = "\n".join(lines) + "\n"

    print(output)
    
    font.setFeature(FEATURE_TAG, output)
    font.update()
    
    if skipped:
        print("\nSkipped glyphs:")
        for name, reason in skipped:
            print(f"  {name}: {reason}")

main()



#FLM: MW: Sort Text By Form

import string
import fontlab as fl6
import fontgate as fgt
from PythonQt import QtGui

qapp = QtGui.QApplication.instance()
app_version = '1.1.1'
app_name = 'Minwoo | Build Asterisk'

items = fl6.flItems
app = fl6.flWorkspace.instance() # active workspace
nT = fgt.fgNametable()

class NotHangulException(Exception):
    pass

class NotHangulException(Exception):
    pass

class NotLetterException(Exception):
    pass

CHO = (
    u'ㄱ', u'ㄲ', u'ㄴ', u'ㄷ', u'ㄸ', u'ㄹ', u'ㅁ', u'ㅂ', u'ㅃ', u'ㅅ',
    u'ㅆ', u'ㅇ', u'ㅈ', u'ㅉ', u'ㅊ', u'ㅋ', u'ㅌ', u'ㅍ', u'ㅎ'
)

JUNG = (
    u'ㅏ', u'ㅐ', u'ㅑ', u'ㅒ', u'ㅓ', u'ㅔ', u'ㅕ', u'ㅖ', u'ㅗ', u'ㅘ',
    u'ㅙ', u'ㅚ', u'ㅛ', u'ㅜ', u'ㅝ', u'ㅞ', u'ㅟ', u'ㅠ', u'ㅡ', u'ㅢ', u'ㅣ'
)

JUNG_BY_TYPE = (
    u'ㅏ', u'ㅑ', u'ㅓ', u'ㅕ', u'ㅣ', u'ㅐ', u'ㅒ', u'ㅔ', u'ㅖ', u'ㅗ',
    u'ㅛ', u'ㅜ', u'ㅠ', u'ㅡ', u'ㅘ', u'ㅚ', u'ㅢ', u'ㅙ', u'ㅝ', u'ㅟ', u'ㅞ'
)

JONG = (
    u'', u'ㄱ', u'ㄲ', u'ㄳ', u'ㄴ', u'ㄵ', u'ㄶ', u'ㄷ', u'ㄹ', u'ㄺ',
    u'ㄻ', u'ㄼ', u'ㄽ', u'ㄾ', u'ㄿ', u'ㅀ', u'ㅁ', u'ㅂ', u'ㅄ', u'ㅅ',
    u'ㅆ', u'ㅇ', u'ㅈ', u'ㅊ', u'ㅋ', u'ㅌ', u'ㅍ', u'ㅎ'
)

JAMO = CHO + JUNG + JONG[1:]

NUM_CHO = 19
NUM_JUNG = 21
NUM_JONG = 28

FIRST_HANGUL_UNICODE = 0xAC00  # '가'
LAST_HANGUL_UNICODE = 0xD7A3  # '힣'


def is_jamo(letter):
    if letter in JAMO: 
        return letter
    else: return ''

def is_cho(charArr):
    for i in range(len(charArr)):
        if charArr[i] in CHO: 
            continue
        else:
            charArr[i] = u''
    return charArr

def is_jung(charArr):
    for i in range(len(charArr)):
        if charArr[i] in JUNG: 
            continue
        else:
            charArr[i] = u''
    return charArr

def is_jong(charArr):
    for i in range(len(charArr)):
        if charArr[i] in JONG: 
            continue
        elif charArr[i] == u'·':
            charArr[i] = u''
        else:
            return ''
    return charArr

def is_hangul(phrase):
    """Check whether the phrase is Hangul.
    This method ignores white spaces, punctuations, and numbers.
    @param phrase a target string
    @return True if the phrase is Hangul. False otherwise."""
    
    # If the input is only one character, test whether the character is Hangul.
    if len(phrase) == 1: return is_all_hangul(phrase)
    
    # Remove all white spaces, punctuations, numbers.
    exclude = set(string.whitespace + string.punctuation + '0123456789')
    phrase = ''.join(ch for ch in phrase if ch not in exclude)
    
    return is_all_hangul(phrase)

def is_all_hangul(phrase):
    """Check whether the phrase contains all Hangul letters
    @param phrase a target string
    @return True if the phrase only consists of Hangul. False otherwise."""
    
    for unicode_value in map(lambda letter:ord(letter), phrase):
        if unicode_value < FIRST_HANGUL_UNICODE or unicode_value > LAST_HANGUL_UNICODE:
            # Check whether the letter is chosungs, jungsungs, or jongsungs.
            if unicode_value not in map(lambda v: ord(v), CHO + JUNG + JONG[1:]):
                return False
    return True

def decompose(hangul_letter):
    """This function returns letters by decomposing the specified Hangul letter."""
    
    if len(hangul_letter) < 1:
        raise NotLetterException(hangul_letter)
    elif not is_hangul(hangul_letter):
        raise NotHangulException(hangul_letter)
    
    code = ord(hangul_letter) - FIRST_HANGUL_UNICODE
    jongsung_index = code % NUM_JONG
    code //= NUM_JONG
    jungsung_index = code % NUM_JUNG
    code //= NUM_JUNG
    chosung_index = code
    return (CHO[chosung_index], JUNG[jungsung_index], JONG[jongsung_index])

SORT_ORDERS = (
    ('초성-중성-종성', (0, 1, 2)),
    ('초성-종성-중성', (0, 2, 1)),
    ('중성-초성-종성', (1, 0, 2)),
    ('중성-종성-초성', (1, 2, 0)),
    ('종성-초성-중성', (2, 0, 1)),
    ('종성-중성-초성', (2, 1, 0)),
)


def processLine(line, order, jung_rank):
    hangul = []
    for index, symbol in enumerate(line):
        if symbol.space:
            continue
        code = symbol.unicode
        if code <= 0 and symbol.name:
            code = nT.unc(symbol.name.split('.', 1)[0])
        if FIRST_HANGUL_UNICODE <= code <= LAST_HANGUL_UNICODE:
            cho, jung, jong = decompose(chr(code))
            parts = (cho, jung_rank[jung], jong)
            hangul.append((index, symbol, tuple(parts[axis] for axis in order)))

    # Refill the Hangul positions with the original symbols in sorted order.
    for original, sorted_entry in zip(hangul, sorted(hangul, key=lambda entry: entry[2])):
        line[original[0]] = sorted_entry[1]
    return line


def processSymbols(symbols, order):
    jung_rank = {jung: index for index, jung in enumerate(JUNG_BY_TYPE)}
    result = list(symbols)
    start = 0
    for index, symbol in enumerate(symbols):
        if symbol.cr:
            result[start:index] = processLine(result[start:index], order, jung_rank)
            start = index + 1
    result[start:] = processLine(result[start:], order, jung_rank)
    return result


class SortTextDialog(QtGui.QDialog):
    def __init__(self):
        super(SortTextDialog, self).__init__()
        self.setWindowTitle(f"{app_name} {app_version}")
        dlg_width = 340
        dlg_height = 100
        desktop_geo = qapp.desktop().geometry

        center_x = desktop_geo.x() + int(desktop_geo.width() / 2) - int(dlg_width / 2)
        center_y = desktop_geo.y() + int(desktop_geo.height() / 2) - int(dlg_height / 2)
        self.setGeometry(center_x, center_y, dlg_width, dlg_height)
        
        layout = QtGui.QFormLayout(self)

        self.sort_order = QtGui.QComboBox()
        for label, _ in SORT_ORDERS:
            self.sort_order.addItem(label)
        self.sort_order.setCurrentIndex(1)
        layout.addRow('정렬 순서', self.sort_order)

        self.example = QtGui.QLabel()
        layout.addRow('정렬 예시', self.example)
        self.sort_order.currentIndexChanged.connect(self.update_example)
        self.update_example()

        sort_button = QtGui.QPushButton('정렬하기')
        sort_button.clicked.connect(lambda checked=False: self.accept())
        layout.addRow(sort_button)

    def update_example(self):
        order = SORT_ORDERS[self.sort_order.currentIndex][1]
        sample = [fl6.fgSymbol(ord(char)) for char in '가각개객갸갹내낵냐냑하햐학햑해핵']
        sorted_sample = processSymbols(sample, order)
        self.example.setText(''.join(chr(symbol.unicode) for symbol in sorted_sample))


def main():
    canvas = app.getActiveCanvas()
    blocks = canvas.textBlocks() if canvas is not None else []
    if not blocks:
        print('정렬할 텍스트가 있는 글리프 편집 창을 열어 주세요.')
        return

    symbols = list(blocks[0].symbolList().symbols())
    dialog = SortTextDialog()
    if dialog.exec_() != QtGui.QDialog.Accepted:
        return

    order = SORT_ORDERS[dialog.sort_order.currentIndex][1]
    sorted_symbols = processSymbols(symbols, order)
    if any(before is not after for before, after in zip(symbols, sorted_symbols)):
        items.requestContent(fl6.fgSymbolList(sorted_symbols), 0)


main()

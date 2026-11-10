#FLM: MW: Generate Shuffled String

import random
import fontlab as fl6
import FL as legacy

import PythonQt.QtGui as QtGui
from typerig.proxy.fl.gui.widgets import getProcessGlyphs

qapp = QtGui.QApplication.instance()
app_version = '1.0.1'
app_name = 'Minwoo | Generate Shuffled String'

class ShuffleDialog:
    @staticmethod
    def get_length(default=50):
        dialog = QtGui.QInputDialog()
        dialog.setWindowTitle('%s %s' %(app_name, app_version))
        dialog.setLabelText('출력할 문자열 길이를 입력하세요:')
        dialog.setIntValue(default)
        dialog.setIntRange(1, 5000)
        dialog.setIntStep(1)
        
        dialog_w = 340
        dialog_h = 120
        desktop_geo = qapp.desktop().geometry

        center_x = desktop_geo.x() + int(desktop_geo.width() / 2) - int(dialog_w / 2)
        center_y = desktop_geo.y() + int(desktop_geo.height() / 2) - int(dialog_h / 2)
        dialog.setGeometry(center_x, center_y, dialog_w, dialog_h)
        
        if dialog.exec_() == QtGui.QDialog.Accepted:
            return dialog.intValue()
        
        return None

def generate_fair_random_string(input_list, length):
    if not input_list:
        return []
    
    unique_elements = list(set(input_list))
    return random.choices(unique_elements, k=length)

def edit_on_new_tab(char_list):
    if not char_list:
        print("[-] 생성된 문자열이 없습니다.")
        return

    legacy.fl.EditGlyph()
    
    symbols = [fl6.fgSymbol(name) for name in char_list]
    symbol_list = fl6.fgSymbolList(symbols)
    
    fl6.flItems().requestContent(symbol_list, 0)

def run_script():
    target_length = ShuffleDialog.get_length(50)
    if target_length is None:
        return 

    pMode = 1
    # if mode == 0: [selected glyph]
    # if mode == 1: [glyphs in edit window]
    # if mode == 2: [selected glyphs in font window]
    # if mode == 3: [all glyphs in font]
    process_glyphs = getProcessGlyphs(pMode)
    
    if not process_glyphs:
        print("[-] 현재 편집 창에 글리프가 없습니다.")
        return

    forbidden_names = ['space', '.notdef', 'NULL', 'CR', 'nonmarkingreturn']
    
    glyph_names = [
        g.name for g in process_glyphs 
        if g.name not in forbidden_names and not g.name.isspace()
    ]

    if not glyph_names:
        print("[-] 공백을 제외한 유효한 글리프가 없습니다.")
        return

    shuffled_names = generate_fair_random_string(glyph_names, target_length)

    edit_on_new_tab(shuffled_names)
    print(f"[+] 성공: {target_length}개의 글리프를 나열했습니다.")

if __name__ == "__main__":
    run_script()
#FLM: MW: Adhesiontext Hangeul for Fontlab
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from adhesiontext_korean import app

app.show_dialog()

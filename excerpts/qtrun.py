import sys
from PySide6.QtWidgets import QApplication
from pathlib import Path
from .qtgui.mainwindow import MainUI
from .sqlutils import SqlDataManager

def run(*, file_name:str = "", tags: list[str] = None, excerpts: list[dict] = None):
    app = QApplication(sys.argv)
    win = MainUI(Path(__file__).parent.parent/"data/", file_name = file_name)
    if tags:
        SqlDataManager.instance().insert_tags_names(tags)
        win.on_db_changed()
    if excerpts:
        SqlDataManager.instance().insert_excerpts_dict(excerpts)
        win.on_db_changed()
    win.show()
    sys.exit(app.exec())

import sys
from PySide6.QtWidgets import QApplication
from .qtgui.mainwindow import MainUI
from .sqlutils import SqlDataManager, get_sql_path



def run(*, file_name:str = "", tags: list[str] = None, excerpts: list[dict] = None):
    app = QApplication(sys.argv)
    win = MainUI(get_sql_path(), file_name = file_name)
    if tags:
        SqlDataManager.instance().insert_tags_names(tags)
        win.on_db_changed()
    if excerpts:
        SqlDataManager.instance().insert_excerpts_dict(excerpts)
        win.on_db_changed()
    win.show()
    sys.exit(app.exec())


from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QColor, QPalette
from pathlib import Path

from .panels import SideBar, Topbar, ContentPanel, MColor, SqlReaderDialog
from ..sqlutils import SqlDataManager




class MainUI(QWidget):
    """主窗口，包括响应式列数、顶部/侧栏/主内容区域的布局细节"""
    def __init__(self, path: Path, file_name:str = "", ):
        super().__init__()
        self.setWindowTitle("文字摘录工具")
        self.path:Path = path
        self.file_name:str = file_name
        self.db_manager: SqlDataManager = None
        self._on_tag = "default"
        # 全局滚动条样式
        self.setStyleSheet('''
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #aaa;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        ''')
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(MColor.color_bg))
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)
        self.sidebar = SideBar()
        root.addWidget(self.sidebar)
        self.sidebar.sig_tag_selected.connect(self.on_tag_selected)
        self.sidebar.db_changed.connect(self.on_db_changed)
        right = QVBoxLayout()
        right.setSpacing(20)
        top = Topbar()
        right.addWidget(top)
        top.search_bar.sig_search_changed.connect(self.on_search_changed)
        top.search_bar.sig_search_clicked.connect(self.on_search_clicked)
        self.content = ContentPanel(self.width)
        self.content.tags_changed.connect(self.on_tags_changed)
        right.addWidget(self.content)
        root.addLayout(right)
        self.setMinimumSize(800, 400)
        self.resize(1400, 800)
        if self.file_name:
            self.init_data()
        else:
            sql_reader = SqlReaderDialog(self.path, self)
            sql_reader.exec()

    def init_data(self, /, path = "", file_name = ""):
        if self.db_manager:
            self.db_manager.close()
        if path: self.path = path
        if file_name: self.file_name = file_name
        self.setWindowTitle(f"文字摘录工具-{self.file_name}")
        self.db_manager = SqlDataManager(self.path/self.file_name)
        self.db_manager.set_instance()
        self.content.update_columns(init_load=True)
        self.sidebar.listw.reload_tags()

    def on_search_changed(self, text):
        '''实时搜索'''
        if not text:
            self.on_tag_selected(self._on_tag)
        pass

    def on_search_clicked(self, text):
        '''点击按钮确认搜索'''
        if (not SqlDataManager.instance()) or (not text):
            return
        data = self.db_manager.get_excerpts_helper().search(text)
        self.content.masonry.rebuild_cards(data)
        self.content.tag_title.setText(text)
    
    def on_tag_selected(self, tag_cid: str):
        '''根据 tag 显示该标签的摘录'''
        if not SqlDataManager.instance():
            return
        self._on_tag = tag_cid
        excerpt_ids = self.db_manager.get_tags_helper().get_excerpt_cids(tag_cid)
        excerpts = self.db_manager.get_excerpts_helper().get_excerpts(excerpt_ids)
        self.content.masonry.rebuild_cards(excerpts)
        self.content.tag_title.setText(self.db_manager.get_tag(tag_cid).name)
    
    def on_tags_changed(self):
        self.sidebar.listw.reset_tags()
    
    def on_db_changed(self):
        self.sidebar.listw.reload_tags()
        if SqlDataManager.instance():
            self.content.masonry.rebuild_cards(SqlDataManager.instance().get_all_excerpts())
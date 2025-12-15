
import uuid, datetime, json, shutil
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, QTextEdit, QGridLayout,
                               QListWidget, QListWidgetItem, QScrollArea, QDialog, QMessageBox,
                               QStyledItemDelegate, QStyle, QFrame, QLabel, QLineEdit, QComboBox, 
                               QGroupBox, QFileDialog, QAbstractItemView, QStyleOptionViewItem)
from PySide6.QtCore import Qt, Signal, QEvent, QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QPainter
from typing import Callable, Optional
from pathlib import Path

from .cards import CardWidget, DataTagItem, TagButton, QPushButton, MColor, DataTagWidget
from ..sqlutils import SqlDataManager, TagData, ExcerptData, get_db_list



class ColumnsArea(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(200)
        self.layout:QVBoxLayout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignTop)  # 确保顶端对齐
        self.cards: list[CardWidget] = []

    def add_card(self, card: CardWidget) -> int:
        card.setParent(self)
        self.layout.addWidget(card)
        self.cards.append(card)
    
    def pop_card(self) -> CardWidget:
        card = self.cards.pop()
        card.setParent(None)
        return card
    
    def find_card(self, cid: str) -> None:
        for i, card in enumerate(self.cards):
            if card.data.cid == cid:
                return i
        return -1
    
    def destroy_card(self, cid: str) -> None:
        index = self.find_card(cid)
        if index >= 0:
            card = self.cards.pop(index)
            card.setParent(None)
            card.deleteLater()

    def update_card(self, cid: str, new: CardWidget) -> None:
        index = self.find_card(cid)
        if index >= 0:
            old: CardWidget = self.cards[index]
            self.cards[index] = new
            old.setParent(None)
            old.deleteLater()
            self.layout.insertWidget(index, new)

    def clear_cards(self) -> None:
        """只删除card，不删除ColumnsArea"""
        for card in self.cards:
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self.layout.invalidate()

    def get_height(self):
        return sum([card.height() for card in self.cards])


class MasonryArea(QWidget):
    """
    稳定的瀑布流布局：
    - 自适应列数
    - 不会崩溃
    - 支持右侧 spacer 防止滚动条遮挡
    """
    def __init__(self, column_gap: int = 10, parentw: QWidget = None):
        super().__init__()
        self.sqldata = None
        self.parentw: ContentPanel = parentw
        self.temp_cards: list[CardWidget] = []
        self.column_count = 0
        self.column_gap = column_gap if column_gap > 0 else 10
        self.column_widgets: list[ColumnsArea] = []
        self.all_excerpts = []  # 保存所有数据
        self.loaded_count = 0   # 当前已创建的卡片数量
        self.batch_size = 20    # 每次加载 20 张，可调整
        # 主布局：水平（列 + 最右侧 spacer）
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(column_gap)
        # 右侧 spacer（用于预留滚动条宽度）
        self.right_spacer = QWidget()
        self.right_spacer.setFixedWidth(0)
        self.right_spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def rebuild_cards(self, excerpts: list[ExcerptData]):
        '''清空 masonry 并重新渲染'''
        self.all_excerpts = excerpts      # 保存所有数据
        self.clear_cards()
        self.temp_cards.clear()
        self.loaded_count = 0             # 当前已创建的卡片数量
        self.batch_size = 20              # 每次加载 20 张，可调整
        self.load_more_cards()
    
    def load_more_cards(self):
        end = min(self.loaded_count + self.batch_size, len(self.all_excerpts))
        for i in range(self.loaded_count, end):
            self.create_card(self.all_excerpts[i])
        self.loaded_count = end
        self.reflow()

    def reflow(self):
        """重新排列"""
        column_count2 = len(self.column_widgets)
        if (not self.temp_cards) and self.column_count == column_count2 :
            return
        # 将多余的列移入temp
        if column_count2 > self.column_count:
            for i in range(self.column_count, column_count2):
                w = self.column_widgets[i]
                self.temp_cards.extend(w.cards)
                self.main_layout.removeWidget(w)
                w.deleteLater()
            self.column_widgets = self.column_widgets[:self.column_count]
        if column_count2 < self.column_count:
            for i in range(column_count2, self.column_count):
                cw = ColumnsArea()
                self.main_layout.insertWidget(i, cw)
                self.column_widgets.append(cw)
        self._to_average_column()
        # 将temp添加到列
        for card in self.temp_cards:
            self._add_card_to_column(card)
        self.temp_cards.clear()

    def _add_card_to_column(self, card: CardWidget):
        """将卡片添加到列"""
        heights = [column.get_height() for column in self.column_widgets]
        column: ColumnsArea = self.column_widgets[heights.index(min(heights))]
        column.add_card(card)
    
    def _to_average_column(self):
        """平均列"""
        average = sum([len(column.cards) for column in self.column_widgets])//len(self.column_widgets)
        average = 1 if average <= 2 else average - 1
        for column in self.column_widgets:
            while len(column.cards) > average:
                self.temp_cards.append(column.pop_card())
    
    def create_card(self, excerpt: ExcerptData) -> CardWidget:
        card = CardWidget(excerpt)
        card.sig_edit_requested.connect(self.open_edit_excerpt_dialog)
        card.sig_delete_requested.connect(self.destroy_changed)
        card.sig_select_card.connect(self.parentw.show_big_card)
        self.temp_cards.append(card)

    def add_card(self, excerpt: ExcerptData):
        self.create_card(excerpt)
        self.reflow()

    def update_card(self, cid: str, excerpt: ExcerptData):
        self.create_card(excerpt)
        card = self.temp_cards.pop()
        for column in self.column_widgets:
            column.update_card(cid, card)
    
    def destroy_changed(self, cid: str):
        if not self.sqldata:
            return
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除摘录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                for w in self.column_widgets:
                    w.destroy_card(cid)
                self.parentw.tags_changed.emit()
                self.sqldata.get_excerpts_helper().delete_excerpt(cid)
                self.sqldata.commit()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除标签失败: {str(e)}")

    def load_refresh(self, viewport_width: int):
        self.column_count = viewport_width//400 +1
        # 创建新列
        for _ in range(self.column_count):
            cw = ColumnsArea()
            self.main_layout.addWidget(cw)
            self.column_widgets.append(cw)
        self.main_layout.addWidget(self.right_spacer)
        self.sqldata = SqlDataManager.instance()
        if not self.sqldata:
            return
        self.rebuild_cards(self.sqldata.get_all_excerpts())

    def refresh(self, viewport_width: int):
        cols = viewport_width//400 +1
        if cols != self.column_count:
            self.column_count = cols
            self.reflow()

    def clear_cards(self):
        for col in self.column_widgets:
            col.clear_cards()

    def open_edit_excerpt_dialog(self, excerpt: ExcerptData):
        if not self.sqldata:
            return
        dialog = ExcerptDataDialog(excerpt, self.parentw)
        if dialog.exec():
            if self.parentw.big_card_area.isVisible():
                # 刷新大卡片
                self.parentw.hide_big_card()
                card_data = self.sqldata.get_excerpt(excerpt.cid)
                if card_data:
                    self.parentw.show_big_card(card_data)



class NoSelectionDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex | QPersistentModelIndex):
        if option.state & QStyle.State_Selected:
            option.state &= ~QStyle.State_Selected
        super().paint(painter, option, index)



class TagList(QListWidget):
    def __init__(self):
        super().__init__()
        self.current_tag: str = "default"       # 当前标签
        self.mode = 0 # 0: 显示部分，1: 显示全部
        self.setFrameShape(QFrame.NoFrame)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setItemDelegate(NoSelectionDelegate(self))
        # 关键确保标签宽度正常自适应
        self.setUniformItemSizes(False)
        self.setResizeMode(QListWidget.Adjust)
        self.setStyleSheet("""
            outline: none;
            border: none;
            background: transparent;
        """)
        # 关键：禁用水平滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.reload_tags()
        self.currentItemChanged.connect(self.update_tag_selection)
    
    def update_tag_selection(self, cur: QListWidgetItem, prev: QListWidgetItem) -> None:
        """
        当列表选中项变化时调用：
        - 清理 prev 的样式
        - 设置 cur 的选中样式（包括文字加粗、颜色）
        """
        if prev is not None:
            w_prev: DataTagItem = self.itemWidget(prev)
            if w_prev:
                w_prev.setSelected(False)
        if cur is not None:
            w_cur: DataTagItem = self.itemWidget(cur)
            if w_cur:
                w_cur.setSelected(True)

    def reload_tags(self):
        self.clear()
        if not SqlDataManager.instance():
            return
        tags = SqlDataManager.instance().get_all_tags()
        for tag in tags:
            DataTagItem(tag).add_to(self)
        for i in range(self.count()):
            item = self.item(i)
            tag_widget = self.itemWidget(item)
            if tag_widget.cid == self.current_tag:
                self.setCurrentRow(i)
                tag_widget.setSelected(True)
                break

    def reset_tags(self):
        for i in range(self.count()):
            self.itemWidget(self.item(i)).reset_tagnum()

    def show_all(self):
        if self.mode != 1:
            self.mode = 1
            self.reload_tags()
    
    def show_data(self, tags: list[TagData]):
        self.mode = 0
        self.clear()
        for tag in tags:
            DataTagItem(tag).add_to(self)
        if tags:
            self.current_tag = tags[0].cid
            tag_widget = self.itemWidget(self.item(0))
            self.setCurrentRow(0)
            tag_widget.setSelected(True)



class SearchBar(QHBoxLayout):
    sig_search_changed = Signal(str)
    sig_search_clicked = Signal(str)
    def __init__(self, width_s: int, width_b: int):
        super().__init__()
        self.search_edit = QLineEdit()
        self.search_edit.setFixedSize(width_s, 34)
        self.search_edit.setClearButtonEnabled(True)
        # 详细的样式表设置
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {MColor.color_light};
                border-radius: 15px;
                padding: 0px 14px;
                background-color: {MColor.color_white};
            }}
            QLineEdit:hover {{
                border: 2px solid {MColor.color_bright};
            }}
        """)
        self.addWidget(self.search_edit)
        self.search_edit.textChanged.connect(self.sig_search_changed)
        if width_b > 0:
            self.btn_search = TagButton("🗒️搜索", MColor.color_bright, MColor.color_white, 14)
            self.btn_search.setFixedSize(width_b, 34)
            self.addWidget(self.btn_search)
            self.btn_search.clicked.connect(lambda: self.sig_search_clicked.emit(self.search_edit.text()))





class SideBar(QFrame):
    db_changed = Signal()
    sig_tag_selected = Signal(str)
    def __init__(self):
        super().__init__()
        self.setFixedWidth(220)
        self.setStyleSheet(f"background:{MColor.color_white}; border-radius:10px;")
        slay = QVBoxLayout(self)
        slay.setContentsMargins(20, 20, 20, 20)
        slay.setSpacing(10)

        head = QHBoxLayout()
        tt = QLabel("📑标签分类")
        tt.setStyleSheet(f"color:{MColor.color_bright}; font-size:18px; font-weight:bold;")
        head.addWidget(tt)
        head.addStretch()
        self.btn_setting = TagButton("⚙️", "transparent", MColor.color_dark, 18)
        head.addWidget(self.btn_setting)
        slay.addLayout(head)

        self.search_bar = SearchBar(self.width() - 40, 0)
        self.search_bar.search_edit.setPlaceholderText("搜索标签...")
        self.search_bar.sig_search_changed.connect(self.on_search_changed)
        slay.addLayout(self.search_bar)
        self.listw = TagList()
        slay.addWidget(self.listw)

        self.btn_export = QPushButton("💾数据管理")
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet(f"""border:1px solid {MColor.color_bright};
                                      color:{MColor.color_bright};
                                      border-radius:8px;
                                      font-size:14px""")
        self.btn_export.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        slay.addWidget(self.btn_export)

        self.btn_setting.clicked.connect(self.open_tag_manager)
        self.btn_export.clicked.connect(self.open_data_manager)
        self.listw.currentItemChanged.connect(self.on_tag_selected)
    
    def on_tag_selected(self, cur: DataTagItem, prev: DataTagItem):
        if cur:
            self.sig_tag_selected.emit(cur.tag.cid)

    def open_tag_manager(self):
        if not SqlDataManager.instance():
            return
        dialog = TagManagerDialog(self)
        if dialog.exec():
            # 标签更新后刷新侧栏
            self.listw.reload_tags()

    def open_data_manager(self):
        dialog = DataManagerDialog(self)
        dialog.exec()

    def on_search_changed(self, text):
        '''实时搜索'''
        if not SqlDataManager.instance():
            return
        if not text:
            self.listw.show_all()
            return
        data = SqlDataManager.instance().get_tags_helper().search(text)
        self.listw.show_data(data)



class Topbar(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        tlay = QHBoxLayout(self)
        tlay.setContentsMargins(16, 8, 16, 8)

        icon = QLabel("📝")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f'''background:{MColor.color_bright};
                           border-radius:6px;
                           font-size:24px;''')
        name = QLabel("文字摘录工具")
        name.setStyleSheet(f"font-size:20px; color:{MColor.color_bright}; font-weight:700;")
        tlay.addWidget(icon)
        tlay.addWidget(name)
        tlay.addStretch()
        self.search_bar = SearchBar(210, 80)
        self.search_bar.search_edit.setPlaceholderText("搜索摘录内容...")
        tlay.addLayout(self.search_bar)




class ContentPanel(QFrame):
    tags_changed = Signal()
    sig_scroll_to_bottom = Signal()
    sig_layout_changed = Signal()
    def __init__(self, window_width: Callable[[], int]):
        super().__init__()
        self.window_width = window_width
        self._is_load = False
        self.big_card = None
        self.setStyleSheet(f"background:{MColor.color_white}; border-radius:10px;")
        cly = QVBoxLayout(self)
        cly.setContentsMargins(16, 14, 16, 14)
        cly.setSpacing(12)

        # header
        header = QHBoxLayout()
        self.tag_title = QLabel("所有摘录")
        self.tag_title.setStyleSheet(f"color:{MColor.color_black}; font-size:20px; font-weight:bold;")
        header.addWidget(self.tag_title)
        header.addStretch()
        self.btn_new = TagButton("✏️ 创建新摘录", MColor.color_bright, MColor.color_white, 12)
        self.btn_new.setFixedSize(100, 34)
        header.addWidget(self.btn_new)
        end = QWidget() # 占位符
        end.setFixedWidth(6)
        header.addWidget(end)
        cly.addLayout(header)

        self.masonry = MasonryArea(column_gap=10, parentw=self)
        self.scrollp = QScrollArea()
        self.scrollp.setWidgetResizable(True)
        self.scrollp.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollp.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollp.setFrameShape(QFrame.NoFrame)
        self.scrollp.setWidget(self.masonry)
        cly.addWidget(self.scrollp)

        self.big_card_area = QWidget()
        self.big_card_area.hide()
        self.big_card_layout = QVBoxLayout(self.big_card_area)
        self.big_card_layout.setAlignment(Qt.AlignTop)
        self.big_card_layout.setContentsMargins(0,0,0,0)
        self.big_card_layout.setSpacing(0)
        cly.addWidget(self.big_card_area)

        self.sig_scroll_to_bottom.connect(self.masonry.load_more_cards)
        # 连接滚动条变化
        self.scrollp.viewport().installEventFilter(self)
        self.btn_new.clicked.connect(self.open_new_excerpt_dialog)
        sb = self.scrollp.verticalScrollBar()
        sb.valueChanged.connect(self._check_scroll_bottom)

    def _check_scroll_bottom(self, v):
        sb = self.scrollp.verticalScrollBar()
        if v == sb.maximum():
            self.sig_scroll_to_bottom.emit()

    def update_columns(self, init_load: bool) -> None:
        """
        根据 scroll viewport 宽度决定列数
        同时会设置每列最小/最大宽度（per_col），以实现 3/2/1 列响应式。
        """
        # 获取 scroll 可视宽度（容错）
        viewport_width = self.scrollp.viewport().width()
        if viewport_width <= 0:
            viewport_width = max(800, self.window_width() - 240)
        if init_load:
            self.masonry.load_refresh(viewport_width)
        else:
            self.masonry.refresh(viewport_width)

    def open_new_excerpt_dialog(self):
        if not SqlDataManager.instance():
            return
        dialog = ExcerptDataDialog(None, self)
        dialog.exec()

    def showEvent(self, event):
        self._is_load = True
        super().showEvent(event)
        self.update_columns(init_load=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._is_load:
            self.update_columns(init_load=False)

    def show_big_card(self, excerpt: ExcerptData):
        self.scrollp.hide()
        # 清空旧卡片
        self.delete_big_card()
        card = CardWidget(excerpt, factor = 1.5)
        card.sig_edit_requested.connect(self.masonry.open_edit_excerpt_dialog)
        card.sig_delete_requested.connect(self.masonry.destroy_changed)
        card.sig_delete_requested.connect(lambda *p: self.hide_big_card())
        card.sig_select_card.connect(lambda *p: self.hide_big_card())
        self.big_card_layout.addWidget(card)
        self.big_card_layout.addStretch()
        self.big_card_area.show()

    def hide_big_card(self):
        self.big_card_area.hide()
        self.delete_big_card()
        self.scrollp.show()

    def delete_big_card(self):
        while self.big_card_layout.count():
            item = self.big_card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()



class ExcerptDataDialog(QDialog):
    def __init__(self, data: Optional[ExcerptData], parent: ContentPanel=None):
        super().__init__(parent)
        self.sqldata = SqlDataManager.instance()
        self.data = data
        self.selected_tags: set[str] = set()
        self._btns_by_cid: dict[str, TagButton] = {}
        self.build_ui()

    def build_ui(self):
        # 标题（有边框窗口）
        self.setWindowTitle("添加新摘录" if not self.data else "编辑摘录")
        self.setFixedWidth(550)
        # self.setMinimumHeight(620)

        # 主样式（浅蓝背景，与主窗口一致）
        self.setStyleSheet(f"""
            QDialog {{ background: {MColor.color_bg}; }}
            QLineEdit {{
                border: 1px solid {MColor.color_light};
                border-radius: 8px;
                padding: 6px 10px;
                background: {MColor.color_white};
            }}
            QLineEdit:hover {{
                border: 1.5px solid {MColor.color_bright};
            }}
            QFrame {{
                background: {MColor.color_bg}; border-radius:10px;
            }}
        """)

        main = QVBoxLayout(self)
        main.setContentsMargins(20, 18, 20, 18)
        main.setSpacing(12)

        # 大标题
        title = QLabel("✏️ 添加新摘录" if not self.data else "📝 编辑摘录")
        title.setStyleSheet(f"font-size:18px; color:{MColor.color_bright}; font-weight:700; background: transparent; ")
        main.addWidget(title)

        # 内容卡片区
        card = QFrame()
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(6, 6, 6, 6)
        card_l.setSpacing(8)

        # 标题
        card_l.addWidget(QLabel("❤️ 标题"))
        self.title_edit = QLineEdit()
        card_l.addWidget(self.title_edit)

        # 作者
        card_l.addWidget(QLabel("🙍 作者"))
        self.author_edit = QLineEdit()
        card_l.addWidget(self.author_edit)

        # 摘录内容（更宽、更高）
        card_l.addWidget(QLabel("🔤 摘录内容 *"))
        self.content_edit = QTextEdit()
        self.content_edit.viewport().setStyleSheet(f"""
            background: {MColor.color_white};
            border: 1px solid {MColor.color_light2};
            border-radius: 8px;
            padding: 6px 10px;
        """)
        # self.content_edit.setStyleSheet("""QLineEdit:hover {
        #         border: 1.5px solid {MColor.color_bright};
        #     }""")
        self.content_edit.setMinimumHeight(150)
        card_l.addWidget(self.content_edit)

        # 来源
        card_l.addWidget(QLabel("📙 来源"))
        self.source_edit = QLineEdit()
        card_l.addWidget(self.source_edit)

        # 标签区
        card_l.addWidget(QLabel("🏷️ 选择标签"))
        self.tag_buttons_grid = QGridLayout()
        self.tag_buttons_grid.setSpacing(8)
        # 创建标签按钮（在填充旧数据后调用，能根据 selected_tags 初始状态设置样式）
        self.load_tag_buttons()
        card_l.addLayout(self.tag_buttons_grid)

        main.addWidget(card)

        # 操作按钮
        btn_row = QHBoxLayout()
        self.btn_save = TagButton("保存", MColor.color_bright, MColor.color_white, 14)
        self.btn_save.clicked.connect(self.save)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save)
        main.addLayout(btn_row)

        # 填充旧数据（如果有）
        if self.data:
            self.title_edit.setText(self.data.title)
            self.author_edit.setText(self.data.author)
            self.content_edit.setText(self.data.content)
            self.source_edit.setText(self.data.source)
            self.selected_tags = set(self.data.tag_cids)


    def load_tag_buttons(self):
        # 清空旧按钮（如果有）
        while self.tag_buttons_grid.count():
            itm = self.tag_buttons_grid.takeAt(0)
            w = itm.widget()
            if w:
                w.deleteLater()
        self._btns_by_cid.clear()

        # 从数据库读取标签列表并创建 TagButton
        tags = self.sqldata.get_all_tags()
        for i, tag in enumerate(tags):
            # 创建按钮时仍用 tag 的颜色作为参考，但初始我们会覆盖为灰色或真实色取决于 selected_tags
            btn = TagButton(tag.name, tag.color, MColor.color_white, 12)
            btn.setCheckable(True)
            # 绑定切换：使用 toggled 信号，这样 checked 状态自动同步
            btn.cid = tag.cid
            btn.color = tag.color
            btn.toggled.connect(lambda checked, b = btn: self._on_btn_toggled(b, checked))
            # 将按钮实例放到容器
            self.tag_buttons_grid.addWidget(btn, i//5, i%5)
            self._btns_by_cid[tag.cid] = btn
            # 根据当前是否在 selected_tags 初始化样式与 checked
            if tag.cid in self.selected_tags:
                btn.setChecked(True)
                # 选中时显示标签颜色背景，文字为白色，稍微加粗
                btn.setStyleSheet(self._make_btn_style(bg=tag.color, text_color=MColor.color_white, bold=True))
            else:
                btn.setChecked(False)
                # 未选中时用灰色背景、深色文字
                btn.setStyleSheet(self._make_btn_style(bg=MColor.color_light2, text_color=MColor.color_dark, bold=False))

    def _make_btn_style(self, bg: str, text_color: str, bold: bool):
        """
        返回一个适合直接 setStyleSheet 的字符串，覆盖 TagButton 内部样式。
        用 instance stylesheet 替换，而不是全局 QSS，以确保覆盖优先级。
        """
        weight = "700" if bold else "500"
        # 使用 padding 与 border-radius 保持和 cards.TagButton 视觉一致
        return f"""
            QPushButton {{
                background: {bg};
                color: {text_color};
                border: 1px solid rgba(0,0,0,0.06);
                padding: 6px 12px;
                border-radius: 10px;
                font-weight: {weight};
            }}
            QPushButton:hover {{
                border: 1px solid rgba(0,0,0,0.12);
            }}
        """

    def _on_btn_toggled(self, btn: TagButton, checked: bool):
        """
        当某个标签按钮被切换时，更新 selected_tags 集合并立即替换该按钮的 stylesheet
        这样能保证视觉效果可靠。
        """
        if checked:
            self.selected_tags.add(btn.cid)
            # 选中：真实标签颜色、白字、加粗
            btn.setStyleSheet(self._make_btn_style(bg=btn.color, text_color=MColor.color_white, bold=True))
        else:
            self.selected_tags.discard(btn.cid)
            # 未选中：灰底、深色文字、正常字体
            btn.setStyleSheet(self._make_btn_style(bg=MColor.color_light2, text_color=MColor.color_dark, bold=False))
        # 同步按钮 checked 属性（通常 PySide 会自动处理，但确保无歧义）
        btn.setChecked(checked)

    def save(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "错误", "摘录内容不能为空")
            return
        try:
            self.selected_tags.add("default")
            new_excerpt = ExcerptData.from_dict({
                "cid"       : self.data.cid if self.data else '',
                "content"   : content,
                "source"    : self.source_edit.text().strip(),
                "title"     : self.title_edit.text().strip(),
                "author"    : self.author_edit.text().strip(),
                "note"      : self.data.note if self.data else '',
                "tag_cids"  : list(self.selected_tags)
            })
            excerpt = self.sqldata.update_excerpt(new = new_excerpt, old = self.data)
            self.parent().tags_changed.emit()
            if self.data:
                self.parent().masonry.update_card(self.data.cid, excerpt)
            else:
                self.parent().masonry.add_card(excerpt)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def closeEvent(self, event) -> None:
        """重置数据库"""
        reply = QMessageBox.question(
            self, "是否保存", 
            "确定要关闭窗口吗？关闭后将不会自动保存数据。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()




class TagManagerDialog(QDialog):
    """标签管理对话框类"""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        初始化标签管理对话框
        Args:
            db_manager: 数据库管理器实例
            parent: 父控件
        """
        super().__init__(parent)
        self.sqldata = SqlDataManager.instance()
        self.tags: list[TagData] = self.sqldata.get_all_tags()
        for i, tag in enumerate(self.tags):
            if tag.cid == "default":
                self.tags.pop(i)
        self.del_tags: list[TagData] = []
        self.new_tags: list[TagData] = []
        self.temp_tag: DataTagWidget = None
        self.tag_index: int = -1
        self.init_ui()
        self.show_tags()
        self.tag_list.currentItemChanged.connect(self.update_tag_selection)
    
    def init_ui(self) -> None:
        """初始化UI界面"""
        self.setWindowTitle("标签管理")
        self.setFixedSize(500, 500)
        self.setStyleSheet(f"""
            QDialog, QGroupBox {{
                background: {MColor.color_bg};
            }}
            QLabel{{
                background: {MColor.color_bg};
                font-size: 14px; font-weight:400;;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background: {MColor.color_white};
                border: 1px solid {MColor.color_light2}; /* 浅描边 */
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:hover, QTextEdit:hover, QComboBox:hover {{
                border: 1px solid {MColor.color_bright};
            }}

        """)
        layout = QVBoxLayout(self)
        # 标题
        title_group = QGroupBox()
        title_layout = QHBoxLayout(title_group)
        
        # 现有标签列表
        self.tag_list = TagList()
        self.tag_list.setStyleSheet(f"""
            TagList{{
                outline: none;
                border: none;
                background: {MColor.color_white};
            }}
            TagList QWidget{{
                background: transparent;
            }}
        """)
        self.tag_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.tag_list.setDefaultDropAction(Qt.MoveAction)
        self.tag_list.setDragEnabled(True)
        self.tag_list.setAcceptDrops(True)
        self.tag_list.setDropIndicatorShown(True)
        self.tag_list.model().rowsMoved.connect(self.on_tag_row_changed)

        # 添加新标签区域
        add_group = QGroupBox()
        add_layout = QHBoxLayout(add_group)
        add_layout.addWidget(QLabel("添加："))
        self.new_tag_name = QLineEdit()
        self.new_tag_name.setPlaceholderText("输入标签名称...")
        add_layout.addWidget(self.new_tag_name)
        self.add_btn = TagButton("添加", MColor.color_bright, MColor.color_white, 14)
        self.add_btn.clicked.connect(self.add_tag)
        add_layout.addWidget(self.add_btn)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.delete_btn = TagButton("删除", MColor.color_reminder, MColor.color_white, 14)
        self.delete_btn.clicked.connect(self.delete_tag)
        self.save_btn = TagButton("保存", MColor.color_light2, MColor.color_dark, 14)
        self.save_btn.clicked.connect(self.save)
        
        title_layout.addWidget(QLabel("📑现有标签:"))
        title_layout.addStretch()
        title_layout.addWidget(self.delete_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        
        layout.addWidget(title_group)
        layout.addWidget(self.tag_list)
        layout.addWidget(add_group)
        layout.addLayout(button_layout)
    
    def show_tags(self) -> None:
        """加载标签列表"""
        self.tag_list.clear()
        for tag in self.tags:
            DataTagItem(tag).add_to(self.tag_list)
    
    def update_tag_selection(self, cur: QListWidgetItem, prev: QListWidgetItem) -> None:
        """
        当列表选中项变化时调用：
        - 清理 prev 的样式
        - 设置 cur 的选中样式（包括文字加粗、颜色）
        """
        if prev is not None:
            w_prev: DataTagWidget = self.tag_list.itemWidget(prev)
            if w_prev:
                w_prev.setSelected(False)
                w_prev.editable = False
                self.temp_tag = None
        if cur is not None:
            w_cur: DataTagWidget = self.tag_list.itemWidget(cur)
            if w_cur:
                w_cur.setSelected(True)
                self.temp_tag = w_cur
                w_cur.editable = True
                w_cur.edit_func = self.save_edit
    
    def add_tag(self) -> None:
        """添加新标签"""
        name = self.new_tag_name.text().strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入标签名称")
            return
        # 检查名称是否重复
        if name == "default":
            QMessageBox.warning(self, "输入错误", "标签名称已存在")
            return
        for tag in self.tags:
            if tag.name == name:
                QMessageBox.warning(self, "输入错误", "标签名称已存在")
                return
        new = TagData.new(str(uuid.uuid4()), name, len(self.tags))
        self.tags.append(new)
        self.new_tags.append(new)
        self.show_tags()
        self.new_tag_name.clear()
    
    def delete_tag(self) -> None:
        """删除选中标签"""
        selected_items = self.tag_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "选择错误", "请选择要删除的标签")
            return
        tag_data: DataTagItem = selected_items[0]
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除标签 '{tag_data.tag.name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.tags.remove(tag_data.tag)
                self.del_tags.append(tag_data.tag)
                self.show_tags()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除标签失败: {str(e)}")
    
    def save_edit(self):
        tag_w = self.temp_tag
        new_name = tag_w.edit_line.text().strip()
        if not new_name:
            tag_w.exit_edit_mode("")
            return
        for tag_data in self.tags:
            if tag_data.cid == tag_w.cid:
                tag_data.name = new_name
                self.new_tags.append(tag_data)
                break
        tag_w.exit_edit_mode(new_name)

    def save(self):
        tags_helper = self.sqldata.get_tags_helper()
        try:
            # 删除
            for tag in self.del_tags:
                tags_helper.delete_tag(tag.cid)
            # 获取改动的标签
            for tag in self.new_tags:
                tags_helper.insert_or_update_upsert([tag.to_dict() for tag in self.new_tags])
            # 获取新顺序
            new_order = [self.tag_list.item(i).tag.cid for i in range(self.tag_list.count())]
            if "default" in new_order:
                new_order.remove("default")
            new_order.insert(0, "default")
            tags_helper.update_order(new_order)
            self.sqldata.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def closeEvent(self, event: QEvent) -> None:
        """重置数据库"""
        reply = QMessageBox.question(
            self, "是否保存", 
            "确定要关闭窗口吗？关闭后将不会自动保存数据。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def on_tag_row_changed(self):
        # 更新标签顺序
        current_items = []
        for i in range(self.tag_list.count()):
            current_items.append(self.tag_list.item(i).tag)
        self.tags = current_items



class DataManagerDialog(QDialog):
    """数据管理对话框类"""
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        初始化数据管理对话框
        Args:
            db_manager: 数据库管理器实例
            parent: 父控件
        """
        super().__init__(parent)
        self.sqldata = SqlDataManager.instance()
        self.mainui: QWidget = self.parent().parent()
        self.init_ui()
    
    def init_ui(self) -> None:
        """初始化UI界面"""
        self.setWindowTitle("数据管理")
        self.setFixedSize(300, 300)
        self.setStyleSheet(f"""
            QDialog {{
                background: {MColor.color_bg};
            }}
            QPushButton {{
                font-size: 12px;
                padding: 6px 14px;
                border-radius: 14px;
                font-weight: 600;
                border: 1px solid rgba(0,0,0,0.08);
                background: {MColor.color_light2};
                color: {MColor.color_black};
            }}
            QPushButton:hover {{
                background: {MColor.color_bright};
            }}
            QPushButton:pressed {{
                background: {MColor.color_bright};
            }}
            QGroupBox:title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: {MColor.color_bright};
                font-weight: 600;
                font-size: 13px;
            }}
            QFileDialog {{
                background: {MColor.color_bg};
            }}
        """)
        layout = QVBoxLayout(self)
        
        # 新建数据库
        self.new_btn = QPushButton("新建数据库")
        self.new_btn.clicked.connect(self.new_db)
        # 切换数据库
        self.change_btn = QPushButton("切换数据库")
        self.change_btn.clicked.connect(self.change_db)
        # 另存数据库
        self.saveas_btn = QPushButton("另存为...")
        # 导出按钮
        self.export_btn = QPushButton("导出数据")
        # 导入按钮
        self.import_btn = QPushButton("导入数据")
        # 重置按钮
        self.reset_btn = QPushButton("重置数据库")
        self.reset_btn.setStyleSheet(f"color: {MColor.color_reminder};")
        # 关闭按钮
        self.close_btn = QPushButton("关闭")

        if self.sqldata:
            self.saveas_btn.clicked.connect(self.saveas_db)
            self.export_btn.clicked.connect(self.export_data)
            self.import_btn.clicked.connect(self.import_data)
            self.reset_btn.clicked.connect(self.reset_data)
        
        layout.addWidget(self.new_btn)
        layout.addWidget(self.change_btn)
        layout.addWidget(self.saveas_btn)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.import_btn)
        layout.addWidget(self.reset_btn)
        layout.addStretch()
        layout.addWidget(self.close_btn)
        
        self.close_btn.clicked.connect(self.accept)
    
    def export_data(self) -> None:
        """导出数据到JSON文件"""
        path = f"{self.mainui.path}/摘录备份_{datetime.date.today()}.json"
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出数据", path, "JSON Files (*.json)"
        )
        if not filename: return
        if not self.cover(filename): return
        excerpts:list[ExcerptData] = self.sqldata.get_all_excerpts()
        tags:list[TagData] = self.sqldata.get_all_tags()
        # 转换为可序列化的字典
        export_data = {
            'excerpts': [ex.to_dict() for ex in excerpts],
            'tags': [tag.to_dict() for tag in tags],
            'export_date': datetime.datetime.now().isoformat()
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", "数据导出成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def import_data(self) -> None:
        """从JSON文件导入数据"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入数据", str(self.mainui.path), "JSON Files (*.json)"
        )
        if not filename:
            return
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            excerpts_data = import_data.get('excerpts', [])
            tags_data = import_data.get('tags', [])
            # 导入标签
            existing_tags = self.sqldata.get_tags_helper()
            existing_tags.insert_or_update_upsert(tags_data)
            # 导入摘录
            existing_excerpts = self.sqldata.get_excerpts_helper()
            excerpts = ExcerptData.from_dict_list(excerpts_data)
            existing_excerpts.insert_or_update_excerpts(excerpts)
            self.sqldata.commit()
            QMessageBox.information(self, "成功", "导入成功!")
            self.parent().db_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
    
    def reset_data(self) -> None:
        """重置数据库"""
        reply = QMessageBox.question(
            self, "确认重置", 
            "确定要重置所有数据吗？此操作将永久删除所有摘录和标签，且不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # 删除数据库文件并重新初始化
                self.sqldata.reset_data()
                QMessageBox.information(self, "成功", "数据库已重置")
                self.parent().db_changed.emit()
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重置失败: {str(e)}")

    def change_db(self):
        sql_reader = SqlReaderDialog(self.mainui.path, self.mainui)
        if sql_reader.exec():
            self.accept()

    def new_db(self):
        path = f"{self.mainui.path}/新建数据库_{datetime.date.today()}.db"
        filename, _ = QFileDialog.getSaveFileName(
            self, "新建数据库", path, "sqlite Files (*.db)"
        )
        if not filename:
            return
        try:
            db_path = self.cover(filename)
            if not db_path: return
            # 打开新数据库
            self.mainui.init_data(path = db_path.parent, file_name = db_path.name)
            QMessageBox.information(self, "成功", "新数据库已创建并切换")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建失败: {str(e)}")

    def saveas_db(self):
        path = f"{self.mainui.path/self.mainui.file_name}_{datetime.date.today()}.db"
        filename, _ = QFileDialog.getSaveFileName(
            self, "数据库另存为", path, "sqlite Files (*.db)"
        )
        if not filename:
            return
        try:
            target_path = self.cover(filename)
            if not target_path: return
            # 先确保数据已提交
            self.sqldata.commit()
            # 直接复制数据库文件
            shutil.copy2(self.mainui.path/self.mainui.file_name, target_path)
            QMessageBox.information(self, "成功", f"数据库已另存为：\n{target_path}")
            self.mainui.init_data(path = target_path.parent, file_name = target_path.name)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"另存为失败: {str(e)}")

    def cover(self, filename: str) -> Path:
        path = Path(filename)
        # 如果文件已存在，询问是否覆盖
        if path.exists():
            reply = QMessageBox.question(
                self,
                "确认覆盖",
                f"数据库文件已存在，是否覆盖？\n{path.name}",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return None
            path.unlink()  # 删除旧文件
        return path


class SqlReaderDialog(QDialog):
    """标签管理对话框类"""
    def __init__(self, file_path:Path, parent = None):
        super().__init__(parent)
        self.file_path = file_path  # 使用Path对象表示文件路径
        self.file_list = []         # 存储文件列表
        self.init_ui()
        self.load_files()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("打开数据库")
        self.setMinimumWidth(300)
        self.setStyleSheet(f"""
            QDialog {{
                background: {MColor.color_bg};
            }}
            QComboBox {{
                background: {MColor.color_light2};
            }}
            QPushButton {{
                font-size: 14px;
                border-radius: 8px;
                border: 1px solid {MColor.color_bright};
                color: {MColor.color_bright};
            }}
            QPushButton:hover {{
                background: {MColor.color_light2};
            }}
        """)
        # 创建布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        # 下拉列表
        self.combo_box = QComboBox()
        self.combo_box.setMinimumHeight(40)
        main_layout.addWidget(QLabel("请选择文件:"))
        main_layout.addWidget(self.combo_box)
        isr= QWidget()
        isr.setFixedHeight(14)
        main_layout.addWidget(isr)
        # 按钮布局=
        self.ok_button = QPushButton("确定")
        self.ok_button.setFixedHeight(34)
        self.ok_button.clicked.connect(self.accept_selection)
        self.ok_button.setDefault(True)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedHeight(34)
        self.cancel_button.clicked.connect(self.reject)
        main_layout.addWidget(self.ok_button)
        main_layout.addWidget(self.cancel_button)
        isr= QWidget()
        isr.setFixedHeight(10)
        main_layout.addWidget(isr)
    
    def load_files(self):
        """加载指定路径下的文件"""
        try:
            if not self.file_path.exists():
                QMessageBox.warning(self, "警告", f"路径不存在: {self.file_path}")
                return
            self.file_list = get_db_list(self.file_path)
            if not self.file_list:
                QMessageBox.information(self, "提示", "该目录下没有文件")
                self.combo_box.addItem("无文件")
                self.ok_button.setEnabled(False)
            else:
                self.combo_box.addItems(self.file_list)
                self.combo_box.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载文件时出错: {str(e)}")
    
    def accept_selection(self):
        """处理确定按钮点击"""
        if self.file_list:
            selected_index = self.combo_box.currentIndex()
            if selected_index >= 0:
                self.parent().init_data(file_name = self.file_list[selected_index])
                self.accept()  # 关闭对话框并返回QDialog.Accepted

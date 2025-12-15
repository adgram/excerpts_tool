
import random
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton,
                               QWidget, QListWidgetItem, QListWidget,
                               QLineEdit, QPushButton, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QRect, QSize
from PySide6.QtGui import (QMouseEvent, QColor, QFont, QPen, QPainter,
                         QFontMetrics, QMouseEvent, QLinearGradient)
from enum import StrEnum

from ..sqlutils import TagData, ExcerptData, SqlDataManager


class MColor(StrEnum):
    color_bright = "#4381ff"
    color_light = "#d7d7d7"
    color_light2 = "#e7e7e7"
    color_dark = "#484848"
    color_white = "#ffffff"
    color_black = "#222222"
    color_bg = "#f5faff"
    color_reminder = "#f72585"


def random_pastel() -> QColor:
    """
    生成柔和的随机颜色（16进制带透明度）
    返回:
        16进制颜色字符串，格式: "#AARRGGBB"
    """
    # 柔和颜色：每个通道在180-240之间，避免太亮或太暗
    r = random.randint(180, 240)
    g = random.randint(180, 240)
    b = random.randint(180, 240)
    return QColor(r, g, b)


class TagButton(QPushButton):
    """卡片上的小标签"""
    def __init__(self, text: str, color: str, text_color: str, text_size: int = 12):
        super().__init__(text)
        self.setStyleSheet(f'''background:{color}; color:{text_color}; border:0px;
                           padding:4px 10px; border-radius:10px; font-size:{text_size}px;''')


class CardWidget(QWidget):
    sig_edit_requested = Signal(object)
    sig_delete_requested = Signal(str)
    sig_select_card = Signal(object)

    def __init__(self, data: ExcerptData, factor=1):
        super().__init__()
        self.data: ExcerptData = data
        self.factor = factor
        self.bg_color = random_pastel()
        self.font_tag = QFont("Microsoft YaHei", 9 * self.factor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.cached_height = None
        self.rect_btn_edit = QRect()
        self.rect_btn_delete = QRect()

    def draw_tag(self, painter, x, y, text, color):
        '''标签'''
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        fm = QFontMetrics(self.font_tag)
        w = fm.horizontalAdvance(text) + 16 * self.factor
        h = 22 * self.factor

        rect = QRect(x, y, w, h)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

        painter.setPen(QColor(MColor.color_white))
        painter.setFont(self.font_tag)
        painter.drawText(rect, Qt.AlignCenter, text)

        painter.restore()
        return w, h

    def draw_button(self, painter, rect, text):
        '''底部按钮'''
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(MColor.color_light2))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10* self.factor, 10* self.factor)
        painter.setPen(QColor(MColor.color_dark))
        painter.setFont(self.font_tag)
        painter.drawText(rect, Qt.AlignCenter, text)
        painter.restore()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.rect_btn_edit.contains(event.pos()):
                self.sig_edit_requested.emit(self.data)
                return
            if self.rect_btn_delete.contains(event.pos()):
                self.sig_delete_requested.emit(self.data.cid)
                return
            self.sig_select_card.emit(self.data)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        w_margin = 14 * self.factor
        w_spacing = 12 * self.factor
        w_radius = 24 * self.factor
        shadow_offset = 3 * self.factor
    
        # 渐变阴影（右下角）
        shadow_rect = self.rect().adjusted(shadow_offset, shadow_offset, 0, 0)
        gradient = QLinearGradient(shadow_rect.topLeft(), shadow_rect.bottomRight())
        gradient.setColorAt(0, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(0, 0, 0, 20))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, w_radius, w_radius)

        # 背景（圆角矩形）
        full = self.rect().adjusted(0, 0, -shadow_offset, -shadow_offset)
        painter.setBrush(self.bg_color)
        painter.setPen(QPen(QColor(MColor.color_light), 1))
        painter.drawRoundedRect(full, w_radius, w_radius)

        # 内部样式
        x = w_margin
        y = w_margin + 5
        max_w = full.width() - 2 * w_margin

        # 1. 日期（灰色）
        if self.data.created_at:
            y = w_margin + w_spacing - 5
            painter.setFont(QFont("Microsoft YaHei", 8 * self.factor))
            painter.setPen(QColor(MColor.color_dark))
            painter.drawText(x, y, self.data.created_at[:10])
            y += w_spacing

        # 2. 标题（自动换行）
        if self.data.title and self.data.title != "无":
            font_title = QFont("Microsoft YaHei", 12 * self.factor)
            painter.setFont(font_title)
            painter.setPen(QColor(MColor.color_black))
            rect_title = QRect(x, y, max_w, 400)
            painter.drawText(rect_title, Qt.TextWordWrap, self.data.title)
            fm_title = QFontMetrics(font_title)
            h_title = fm_title.boundingRect(rect_title, Qt.TextWordWrap, self.data.title).height()
            y += h_title # + w_spacing

        # 3. 正文（自动换行）
        font_text = QFont("Microsoft YaHei", 10 * self.factor)
        painter.setFont(font_text)
        painter.setPen(QColor(MColor.color_dark))
        rect_text = QRect(x, y, max_w, 99999)
        painter.drawText(rect_text, Qt.TextWordWrap, self.data.content)
        fm_text = QFontMetrics(font_text)
        h_text = fm_text.boundingRect(rect_text, Qt.TextWordWrap, self.data.content).height()
        y += h_text# + w_spacing

        # 4. 作者（右对齐）
        if self.data.author and self.data.author != "佚名":
            painter.setFont(self.font_tag)
            painter.setPen(QColor(MColor.color_dark))
            painter.drawText(x, y, max_w, 15 * self.factor, Qt.AlignRight, f'——{self.data.author}')
            y += 10 * self.factor #+ w_spacing
        y += 5 * self.factor

        # 5. 标签（自动换行）
        if len(self.data.tag_cids) >= 2:
            x_tag = x
            line_h = 0
            for cid in self.data.tag_cids:
                if cid == "default":
                    continue
                tag = SqlDataManager.instance().get_tag(cid)
                fm = QFontMetrics(self.font_tag)
                w = fm.horizontalAdvance(tag.name) + 10 * self.factor
                h = 18 * self.factor
                # 换行逻辑
                if x_tag + w > x + max_w:
                    x_tag = x
                    y += line_h + 6 * self.factor
                    line_h = 0
                self.draw_tag(painter, x_tag, y, tag.name, tag.color)
                line_h = max(line_h, h)
                x_tag += w + 8 * self.factor
            y += line_h
        y += w_spacing

        # 6. 来源
        if self.data.source and self.data.source != "未知":
            y += w_spacing
            painter.setFont(self.font_tag)
            painter.setPen(QColor(MColor.color_dark))
            painter.drawText(x, y, f'摘自：{self.data.source}')
            y += 10 * self.factor #+ w_spacing

        # 7. 两个底部按钮（右对齐）
        btn_w = 40 * self.factor
        btn_h = 20 * self.factor
        x_btn = x + max_w - (btn_w * 2 + 4)
        self.rect_btn_edit = QRect(x_btn, y, btn_w, btn_h)
        self.rect_btn_delete = QRect(x_btn + btn_w + 4, y, btn_w, btn_h)
        self.draw_button(painter, self.rect_btn_edit, "编辑")
        self.draw_button(painter, self.rect_btn_delete, "删除")
        y += btn_h + w_margin

        # 高度更新
        self.cached_height = y
        if self.minimumHeight() != self.cached_height:
            self.setMinimumHeight(self.cached_height)
            self.updateGeometry()

    def sizeHint(self):
        if self.cached_height:
            return QSize(self.width(), self.cached_height)
        return QSize(self.width(), 100)


class DataTagWidget(QWidget):
    """
    标签控件：颜色点 + 标签名 + 计数
    支持：
      - hover 高亮，只作用于本控件，不影响子控件
      - selected 状态（由外部 setSelected 控制）
    """
    def __init__(self, tag: TagData, tag_num: int) -> None:
        super().__init__()
        self.cid = tag.cid
        self.edit_mode = False
        self.edit_line = None
        self.btn_save = None
        self.editable = False
        self.edit_func = lambda: None
        # 设置唯一 objectName，作为样式选择器的目标
        self.setObjectName("DataTagWidget")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 颜色点
        self.color_label = QLabel()
        self.color_label.setFixedSize(12, 12)
        self.color_label.setStyleSheet(
            f"background-color: {tag.color}; border-radius: 6px;"
        )

        # 标签名称
        self.name_label = QLabel(tag.name)
        self.name_label.setStyleSheet("font-size: 14px;")

        # 数量
        self.count_label = QLabel(f"({tag_num})")
        self.count_label.setStyleSheet(f"color: {MColor.color_dark}; font-size: 12px;")

        layout.addWidget(self.color_label)
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.count_label)

        # 初始状态
        self.setProperty("selected", False)

        # 统一控制 hover 与选中状态的样式 —— 不再使用 QWidget:hover！
        self._apply_style()

    def _apply_style(self):
        """
        通过 objectName + 属性过滤严格控制 hover 与 selected。
        子控件不会继承这些 hover 样式，不会再出现“子控件也变色”的问题。
        """
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            /* 默认状态 */
            #DataTagWidget {{
                border-radius: 12px;
                background-color: transparent;
            }}
            /* 悬停 —— 注意必须精确到 objectName，不能使用 QWidget:hover */
            #DataTagWidget:hover {{
                background-color: {MColor.color_light};
            }}
            /* 选中状态（来自 setProperty("selected", True)） */
            #DataTagWidget[selected="true"] {{
                background-color: {MColor.color_bright};
            }}
        """)

    def setSelected(self, selected: bool):
        """选中/取消选中状态（由 QListWidget 的 currentItemChanged 调用）"""
        self.setProperty("selected", selected)
        # 重应用样式，让 Qt 解析属性变化
        self.style().unpolish(self)
        self.style().polish(self)
        # 字体粗体切换
        if selected:
            self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        else:
            self.name_label.setStyleSheet("font-size: 14px; font-weight: normal;")

    def enter_edit_mode(self):
        if self.edit_mode or not self.editable:
            return
        self.edit_mode = True
        old_name = self.name_label.text()
        # 隐藏原标签名称
        self.name_label.hide()
        self.count_label.hide()

        # 创建输入框
        self.edit_line = QLineEdit(old_name, self)
        self.edit_line.setFixedHeight(22)
        self.edit_line.setStyleSheet(f"""
            QLineEdit {{
                background: {MColor.color_white};
                border: 1px solid {MColor.color_light};
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {MColor.color_black};
            }}
        """)
        self.layout().insertWidget(1, self.edit_line)

        # 添加保存按钮
        self.btn_save = QPushButton("✔", self)
        self.btn_save.setFixedSize(26, 24)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {MColor.color_light2};
                color: {MColor.color_dark};
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {MColor.color_reminder}
            }}
        """)
        self.layout().insertWidget(2, self.btn_save)
        self.btn_save.clicked.connect(self.edit_func)
        self.edit_line.returnPressed.connect(self.edit_func)
        self.edit_line.setFocus()

    def exit_edit_mode(self, new_name):
        self.edit_mode = False
        # 删除编辑控件
        if self.edit_line:
            self.edit_line.deleteLater()
            self.edit_line = None
        if self.btn_save:
            self.btn_save.deleteLater()
            self.btn_save = None
        # 恢复原标签名
        if new_name:
            self.name_label.setText(new_name)
        self.name_label.show()
        self.count_label.show()
        # 重绘样式
        self._apply_style()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.enter_edit_mode()
        super().mouseDoubleClickEvent(event)
    
    def reset_tagnum(self):
        self.count_label.setText(f'({SqlDataManager.instance().get_tag_excerpts_count(self.cid)})')



class DataTagItem(QListWidgetItem):
    """轻量化数据项，不负责 UI，仅存储值"""
    def __init__(self, tag: TagData) -> None:
        super().__init__()
        self.tag = tag
    
    def add_to(self, listw: QListWidget) -> DataTagWidget:
        widget = DataTagWidget(self.tag, self.tag_num)
        listw.addItem(self)
        listw.setItemWidget(self, widget)
        self.setSizeHint(widget.sizeHint())
        return widget

    @property
    def tag_num(self):
        return SqlDataManager.instance().get_tag_excerpts_count(self.tag.cid)
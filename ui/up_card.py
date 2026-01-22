"""
UP主卡片Widget V2 - 带右键菜单
"""
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QCursor
import webbrowser
from core.bilibili_api import BilibiliAPI


class UPCardWidgetV2(QFrame):
    """UP主卡片Widget V2 - 带右键菜单"""

    clicked = pyqtSignal(int)  # 点击卡片信号
    add_to_blacklist_signal = pyqtSignal(int, str)  # 添加到过滤名单信号 (mid, name)

    def __init__(self, up_info: dict, rank: int, parent=None):
        super().__init__(parent)
        self.up_info = up_info
        self.rank = rank
        self.mid = up_info['mid']

        self.setup_ui()
        self.setup_style()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 标题行
        title_layout = QHBoxLayout()

        rank_label = QLabel(f"#{self.rank}")
        rank_label.setFont(QFont("Arial", 11, QFont.Bold))
        rank_label.setStyleSheet("color: #00a1d6;")
        rank_label.setFixedWidth(40)
        title_layout.addWidget(rank_label)

        name_label = QLabel(self.up_info['name'])
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        name_label.setStyleSheet("color: #212529;")
        title_layout.addWidget(name_label)

        title_layout.addStretch()

        if self.up_info.get('official'):
            official_label = QLabel("✓ 认证")
            official_label.setStyleSheet("""
                background-color: #ffc107;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 9px;
            """)
            title_layout.addWidget(official_label)

        layout.addLayout(title_layout)

        # 信息行
        info_label = QLabel(
            f"👥 粉丝: {BilibiliAPI.format_number(self.up_info['fans'])}  |  "
            f"📹 投稿: {self.up_info['videos']}  |  "
            f"⭐ Lv{self.up_info['level']}"
        )
        info_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        layout.addWidget(info_label)

        # 签名
        if self.up_info.get('sign'):
            sign_text = self.up_info['sign'][:60] + ("..." if len(self.up_info['sign']) > 60 else "")
            sign_label = QLabel(f"📝 {sign_text}")
            sign_label.setStyleSheet("color: #6c757d; font-size: 9px;")
            sign_label.setWordWrap(True)
            layout.addWidget(sign_label)

        # 按钮行
        btn_layout = QHBoxLayout()

        space_btn = QPushButton("🏠 访问主页")
        space_btn.setCursor(QCursor(Qt.PointingHandCursor))
        space_btn.setStyleSheet("""
            QPushButton {
                background-color: #00a1d6;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #0087b3;
            }
        """)
        space_btn.clicked.connect(self.open_space)
        btn_layout.addWidget(space_btn)

        msg_btn = QPushButton("✉️ 发私信")
        msg_btn.setCursor(QCursor(Qt.PointingHandCursor))
        msg_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        msg_btn.clicked.connect(self.open_message)
        btn_layout.addWidget(msg_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def setup_style(self):
        """设置样式"""
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("""
            UPCardWidgetV2 {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
            UPCardWidgetV2:hover {
                background-color: #e9ecef;
                border: 1px solid: #00a1d6;
            }
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def show_context_menu(self, pos: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)

        # 添加到过滤名单
        blacklist_action = QAction("🚫 添加到过滤名单", self)
        blacklist_action.triggered.connect(self.add_to_blacklist)
        menu.addAction(blacklist_action)

        menu.addSeparator()

        # 访问主页
        space_action = QAction("🏠 访问主页", self)
        space_action.triggered.connect(self.open_space)
        menu.addAction(space_action)

        # 发私信
        message_action = QAction("✉️ 发私信", self)
        message_action.triggered.connect(self.open_message)
        menu.addAction(message_action)

        menu.addSeparator()

        # 复制UID
        copy_action = QAction("📋 复制UID", self)
        copy_action.triggered.connect(self.copy_mid)
        menu.addAction(copy_action)

        # 显示菜单
        menu.exec_(self.mapToGlobal(pos))

    def add_to_blacklist(self):
        """添加到过滤名单"""
        self.add_to_blacklist_signal.emit(self.mid, self.up_info['name'])

    def copy_mid(self):
        """复制UID到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(str(self.mid))

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.mid)
            self.open_space()

    def open_space(self):
        """打开UP主空间"""
        webbrowser.open(f"https://space.bilibili.com/{self.mid}")

    def open_message(self):
        """打开私信"""
        webbrowser.open(f"https://message.bilibili.com/#/whisper/mid{self.mid}")

    def update_rank(self, new_rank: int):
        """更新排名显示"""
        self.rank = new_rank
        # 找到排名标签并更新
        # 假设排名标签是第一个QLabel
        layout = self.layout()
        if layout and layout.count() > 0:
            title_layout = layout.itemAt(0)
            if title_layout and title_layout.layout():
                rank_label = title_layout.layout().itemAt(0).widget()
                if isinstance(rank_label, QLabel):
                    rank_label.setText(f"#{new_rank}")
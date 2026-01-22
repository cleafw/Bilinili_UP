"""
UP主卡片Widget
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor
import webbrowser
from core.bilibili_api import BilibiliAPI


class UPCardWidget(QFrame):
    """UP主卡片Widget"""
    
    clicked = pyqtSignal(int)  # 点击卡片信号，传递mid
    
    def __init__(self, up_info: dict, rank: int, parent=None):
        super().__init__(parent)
        self.up_info = up_info
        self.rank = rank
        self.mid = up_info['mid']
        
        self.setup_ui()
        self.setup_style()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题行：排名 + 名称 + 认证
        title_layout = QHBoxLayout()
        
        # 排名
        rank_label = QLabel(f"#{self.rank}")
        rank_label.setFont(QFont("Arial", 11, QFont.Bold))
        rank_label.setStyleSheet("color: #00a1d6;")
        rank_label.setFixedWidth(40)
        title_layout.addWidget(rank_label)
        
        # 名称
        name_label = QLabel(self.up_info['name'])
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        name_label.setStyleSheet("color: #212529;")
        title_layout.addWidget(name_label)
        
        title_layout.addStretch()
        
        # 认证标签
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
        
        # 访问主页按钮
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
        
        # 发私信按钮
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
            UPCardWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
            UPCardWidget:hover {
                background-color: #e9ecef;
                border: 1px solid #00a1d6;
            }
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))
    
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

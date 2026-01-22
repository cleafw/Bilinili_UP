"""
过滤名单管理对话框 - 增强版
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QPushButton,
                             QMessageBox, QLineEdit, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor
from utils.config_manager import ConfigManager
from core.bilibili_api import BilibiliAPI
import webbrowser


class BlacklistItemWidget(QWidget):
    """过滤名单项Widget"""

    def __init__(self, mid: int, name: str = None, fans: int = None, parent=None):
        super().__init__(parent)
        self.mid = mid
        self.name = name or f"UP主 {mid}"
        self.fans = fans or 0
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 左侧信息
        info_layout = QVBoxLayout()

        # 名称
        name_label = QLabel(self.name)
        name_label.setFont(QFont("Arial", 11, QFont.Bold))
        name_label.setStyleSheet("color: #212529;")
        info_layout.addWidget(name_label)

        # UID和粉丝数
        detail_label = QLabel(f"UID: {self.mid}  |  👥 {BilibiliAPI.format_number(self.fans)}粉丝")
        detail_label.setStyleSheet("color: #6c757d; font-size: 9px;")
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, 1)

        # 右侧按钮
        visit_btn = QPushButton("🏠")
        visit_btn.setToolTip("访问主页")
        visit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        visit_btn.setFixedSize(30, 30)
        visit_btn.setStyleSheet("""
            QPushButton {
                background-color: #00a1d6;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0087b3;
            }
        """)
        visit_btn.clicked.connect(self.open_space)
        layout.addWidget(visit_btn)

    def open_space(self):
        """打开UP主空间"""
        webbrowser.open(f"https://space.bilibili.com/{self.mid}")


class BlacklistDialog(QDialog):
    """过滤名单管理对话框 - 增强版"""

    blacklist_updated = pyqtSignal()  # 过滤名单更新信号

    def __init__(self, config_manager: ConfigManager, all_ups_data: dict = None, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.all_ups_data = all_ups_data or {}  # 所有UP主的详细信息
        self.setup_ui()
        self.load_blacklist()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("过滤UP 名单管理")
        self.setGeometry(200, 200, 700, 600)

        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("🚫 过滤UP 名单")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("padding: 10px; background-color: #dc3545; color: white; border-radius: 5px;")
        layout.addWidget(title)

        # 说明
        desc = QLabel("已添加到过滤名单的UP主将不会出现在搜索结果中。支持多选移除。")
        desc.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        layout.addWidget(desc)

        # 统计信息
        self.stats_label = QLabel("共 0 个UP主")
        self.stats_label.setStyleSheet("font-size: 8px; color: #666; padding: 45px;")
        layout.addWidget(self.stats_label)

        # 过滤名单列表
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)  # 支持多选
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
            QListWidget::item:selected {
                background-color: #e9ecef;
                color: black;
            }
        """)
        layout.addWidget(self.list_widget)

        # 操作按钮
        btn_layout = QHBoxLayout()

        # 手动添加
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("手动添加UID:"))
        self.mid_input = QLineEdit()
        self.mid_input.setPlaceholderText("输入UP主的UID")
        add_layout.addWidget(self.mid_input)

        add_btn = QPushButton("➕ 添加")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_btn.clicked.connect(self.add_manual)
        add_layout.addWidget(add_btn)

        layout.addLayout(add_layout)

        # 底部按钮
        remove_btn = QPushButton("🗑️ 移除选中")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        remove_btn.clicked.connect(self.remove_selected)
        btn_layout.addWidget(remove_btn)

        clear_btn = QPushButton("🧹 清空全部")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn)

        close_btn = QPushButton("✓ 关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def load_blacklist(self):
        """加载过滤名单"""
        self.list_widget.clear()
        blacklist = self.config.get_blacklist()

        self.stats_label.setText(f"共 {len(blacklist)} 个UP主")

        for mid in blacklist:
            # 获取UP主详细信息
            up_data = self.all_ups_data.get(mid, {})
            name = up_data.get('name', None)
            fans = up_data.get('fans', None)

            # 创建自定义Widget
            item_widget = BlacklistItemWidget(mid, name, fans)

            # 创建列表项
            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.UserRole, mid)
            item.setSizeHint(item_widget.sizeHint())

            # 设置Widget
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)

    def add_manual(self):
        """手动添加UP主到过滤名单"""
        mid_text = self.mid_input.text().strip()
        if not mid_text:
            QMessageBox.warning(self, "警告", "请输入UP主的UID")
            return

        try:
            mid = int(mid_text)
            if self.config.add_to_blacklist(mid):
                self.load_blacklist()
                self.blacklist_updated.emit()
                self.mid_input.clear()
                QMessageBox.information(self, "成功", f"已添加 UID {mid} 到过滤名单")
            else:
                QMessageBox.information(self, "提示", "该UP主已在过滤名单中")
        except ValueError:
            QMessageBox.warning(self, "错误", "UID必须是数字")

    def remove_selected(self):
        """移除选中的UP主（支持多选）"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要移除的UP主")
            return

        reply = QMessageBox.question(
            self, "确认",
            f"确定要移除选中的 {len(selected_items)} 个UP主吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for item in selected_items:
                mid = item.data(Qt.UserRole)
                self.config.remove_from_blacklist(mid)

            self.load_blacklist()
            self.blacklist_updated.emit()
            QMessageBox.information(self, "成功", f"已移除 {len(selected_items)} 个UP主")
    
    def clear_all(self):
        """清空所有过滤名单"""
        blacklist = self.config.get_blacklist()
        if not blacklist:
            QMessageBox.information(self, "提示", "过滤名单已经是空的")
            return
        
        reply = QMessageBox.question(
            self, "确认", 
            f"确定要清空全部 {len(blacklist)} 个UP主吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for mid in blacklist.copy():
                self.config.remove_from_blacklist(mid)
            
            self.load_blacklist()
            self.blacklist_updated.emit()
            QMessageBox.information(self, "成功", "已清空过滤名单")
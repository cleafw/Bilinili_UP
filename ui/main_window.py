"""
主窗口UI V3 - 完整功能版
支持：实时显示、断点续搜、过滤名单过滤、搜索进度保存
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QScrollArea, QFrame, QMessageBox, QFileDialog,
                             QProgressBar, QListWidget, QListWidgetItem,
                             QSplitter, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from core.search_worker import SearchWorker
from ui.blacklist_dialog import BlacklistDialog
from core.bilibili_api import BilibiliAPI
from ui.up_card import UPCardWidgetV2
from utils.excel_exporter import ExcelExporter
from utils.config_manager import ConfigManager
from datetime import datetime
import webbrowser
import re


class MainWindowV3(QMainWindow):
    """主窗口V3 - 完整功能版"""

    def __init__(self):
        super().__init__()
        self.api = BilibiliAPI()
        self.config = ConfigManager()
        self.search_worker = None

        # 数据
        self.all_videos = []
        self.all_ups = {}
        self.filtered_ups = {}

        # 搜索状态
        self.current_keyword = ""
        self.current_page = 1
        self.searched_mids = set()
        self.is_searching = False

        # 配置
        self.apply_blacklist = True

        # UI组件字典（用于管理卡片）
        self.up_cards = {}  # {mid: UPCardWidget}

        self.setup_ui()
        self.setup_connections()
        self.load_last_search_state()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("B站UP主筛选工具 V3 - 实时搜索版")
        self.setGeometry(50, 50, 1600, 900)

        # 中央Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局：上下结构
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # 顶部控制面板
        top_panel = self.create_top_panel()
        main_layout.addWidget(top_panel)

        # 三列内容区域
        content_splitter = self.create_content_area()
        main_layout.addWidget(content_splitter, 1)

    def create_top_panel(self) -> QWidget:
        """创建顶部控制面板"""
        panel = QWidget()
        panel.setMaximumHeight(300)
        layout = QVBoxLayout(panel)

        # 第一行：搜索条件
        search_layout = QHBoxLayout()

        # 关键词
        keyword_group = QGroupBox("视频关键词")
        keyword_layout = QVBoxLayout(keyword_group)
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("例如: 开箱测评、美食探店")
        keyword_layout.addWidget(self.keyword_input)
        search_layout.addWidget(keyword_group)

        # 播放量
        play_group = QGroupBox("播放量范围")
        play_layout = QHBoxLayout(play_group)
        self.min_play_input = QLineEdit("10000")
        self.min_play_input.setPlaceholderText("最低")
        play_layout.addWidget(QLabel("最低:"))
        play_layout.addWidget(self.min_play_input)
        self.max_play_input = QLineEdit("10000000")
        self.max_play_input.setPlaceholderText("最高")
        play_layout.addWidget(QLabel("最高:"))
        play_layout.addWidget(self.max_play_input)
        search_layout.addWidget(play_group)

        # 粉丝数
        fans_group = QGroupBox("粉丝数范围")
        fans_layout = QHBoxLayout(fans_group)
        self.min_fans_input = QLineEdit("10000")
        self.min_fans_input.setPlaceholderText("最低")
        fans_layout.addWidget(QLabel("最低:"))
        fans_layout.addWidget(self.min_fans_input)
        self.max_fans_input = QLineEdit("1000000")
        self.max_fans_input.setPlaceholderText("最高")
        fans_layout.addWidget(QLabel("最高:"))
        fans_layout.addWidget(self.max_fans_input)
        search_layout.addWidget(fans_group)

        # 页数和按钮
        control_group = QGroupBox("搜索控制")
        control_layout = QVBoxLayout(control_group)

        pages_layout = QHBoxLayout()
        pages_layout.addWidget(QLabel("页数:"))
        self.pages_input = QLineEdit("5")
        self.pages_input.setFixedWidth(60)
        pages_layout.addWidget(self.pages_input)
        pages_layout.addStretch()
        control_layout.addLayout(pages_layout)

        # 搜索按钮
        self.search_btn = QPushButton("🔍 开始搜索")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #00a1d6;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0087b3; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        control_layout.addWidget(self.search_btn)

        # 继续搜索按钮
        self.continue_btn = QPushButton("🔄 继续搜索")
        self.continue_btn.setEnabled(False)
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e0a800; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        control_layout.addWidget(self.continue_btn)

        search_layout.addWidget(control_group)

        layout.addLayout(search_layout)

        # 第二行：进度、统计和操作
        bottom_layout = QHBoxLayout()

        # 进度信息
        progress_group = QGroupBox("进度信息")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("等待搜索...")
        self.progress_label.setStyleSheet("color: #0087b3; font-size: 10px;")
        progress_layout.addWidget(self.progress_label)
        bottom_layout.addWidget(progress_group, 2)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel("尚未搜索")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("font-size: 10px;")
        stats_layout.addWidget(self.stats_label)
        bottom_layout.addWidget(stats_group, 1)

        # 操作按钮
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout(action_group)

        # 过滤名单过滤复选框
        self.blacklist_checkbox = QCheckBox("☑️ 应用过滤名单过滤")
        self.blacklist_checkbox.setChecked(True)
        self.blacklist_checkbox.setStyleSheet("font-size: 10px;")
        action_layout.addWidget(self.blacklist_checkbox)

        # 管理过滤名单按钮
        self.manage_blacklist_btn = QPushButton("🚫 管理过滤名单")
        self.manage_blacklist_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #c82333; }
        """)
        action_layout.addWidget(self.manage_blacklist_btn)

        # 导出Excel按钮
        self.export_btn = QPushButton("📊 导出Excel")
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #218838; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        action_layout.addWidget(self.export_btn)

        # 清空按钮
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #5a6268; }
        """)
        action_layout.addWidget(self.clear_btn)

        bottom_layout.addWidget(action_group, 1)

        layout.addLayout(bottom_layout)

        return panel

    def create_content_area(self) -> QSplitter:
        """创建三列内容区域"""
        splitter = QSplitter(Qt.Horizontal)

        # 第一列：视频列表
        video_panel = self.create_video_panel()
        splitter.addWidget(video_panel)

        # 第二列：所有UP主
        all_up_panel = self.create_all_up_panel()
        splitter.addWidget(all_up_panel)

        # 第三列：筛选后的UP主
        filtered_up_panel = self.create_filtered_up_panel()
        splitter.addWidget(filtered_up_panel)

        # 设置初始宽度比例
        splitter.setSizes([400, 400, 400])

        return splitter

    def create_video_panel(self) -> QWidget:
        """创建视频列表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题
        header = QLabel("📹 搜索到的视频（实时）")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setStyleSheet("""
            background-color: #00a1d6;
            color: white;
            padding: 10px;
            border-radius: 5px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # 二次筛选
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("播放量:"))
        self.video_min_play = QLineEdit()
        self.video_min_play.setPlaceholderText("最低")
        self.video_min_play.setFixedWidth(80)
        filter_layout.addWidget(self.video_min_play)
        filter_layout.addWidget(QLabel("-"))
        self.video_max_play = QLineEdit()
        self.video_max_play.setPlaceholderText("最高")
        self.video_max_play.setFixedWidth(80)
        filter_layout.addWidget(self.video_max_play)

        video_filter_btn = QPushButton("筛选")
        video_filter_btn.setFixedWidth(60)
        video_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #00a1d6;
                color: white;
                border: none;
                padding: 4px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #0087b3; }
        """)
        video_filter_btn.clicked.connect(self.filter_videos)
        filter_layout.addWidget(video_filter_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 计数标签
        self.video_count_label = QLabel("共 0 个视频")
        self.video_count_label.setStyleSheet("font-size: 10px; color: #666; padding: 5px;")
        layout.addWidget(self.video_count_label)

        # 视频列表
        self.video_list = QListWidget()
        self.video_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover { background-color: #f0f8ff; }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
        """)
        self.video_list.itemDoubleClicked.connect(self.on_video_double_clicked)
        layout.addWidget(self.video_list)

        return panel

    def create_all_up_panel(self) -> QWidget:
        """创建所有UP主面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题
        header = QLabel("👥 所有UP主（实时）")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setStyleSheet("""
            background-color: #ffc107;
            color: white;
            padding: 10px;
            border-radius: 5px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # 二次筛选
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("粉丝数:"))
        self.all_up_min_fans = QLineEdit()
        self.all_up_min_fans.setPlaceholderText("最低")
        self.all_up_min_fans.setFixedWidth(80)
        filter_layout.addWidget(self.all_up_min_fans)
        filter_layout.addWidget(QLabel("-"))
        self.all_up_max_fans = QLineEdit()
        self.all_up_max_fans.setPlaceholderText("最高")
        self.all_up_max_fans.setFixedWidth(80)
        filter_layout.addWidget(self.all_up_max_fans)

        all_up_filter_btn = QPushButton("筛选")
        all_up_filter_btn.setFixedWidth(60)
        all_up_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: white;
                border: none;
                padding: 4px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #e0a800; }
        """)
        all_up_filter_btn.clicked.connect(self.filter_all_ups)
        filter_layout.addWidget(all_up_filter_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 计数标签
        self.all_up_count_label = QLabel("共 0 个UP主")
        self.all_up_count_label.setStyleSheet("font-size: 10px; color: #666; padding: 5px;")
        layout.addWidget(self.all_up_count_label)

        # UP主列表
        self.all_up_list = QListWidget()
        self.all_up_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover { background-color: #fffbf0; }
            QListWidget::item:selected {
                background-color: #fff3cd;
                color: black;
            }
        """)
        self.all_up_list.itemDoubleClicked.connect(self.on_all_up_double_clicked)
        layout.addWidget(self.all_up_list)

        return panel

    def create_filtered_up_panel(self) -> QWidget:
        """创建筛选后UP主面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题
        header = QLabel("✅ 符合条件的UP主（实时）")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setStyleSheet("""
            background-color: #28a745;
            color: white;
            padding: 10px;
            border-radius: 5px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # 二次筛选
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("粉丝数:"))
        self.filtered_up_min_fans = QLineEdit()
        self.filtered_up_min_fans.setPlaceholderText("最低")
        self.filtered_up_min_fans.setFixedWidth(80)
        filter_layout.addWidget(self.filtered_up_min_fans)
        filter_layout.addWidget(QLabel("-"))
        self.filtered_up_max_fans = QLineEdit()
        self.filtered_up_max_fans.setPlaceholderText("最高")
        self.filtered_up_max_fans.setFixedWidth(80)
        filter_layout.addWidget(self.filtered_up_max_fans)

        filtered_up_filter_btn = QPushButton("筛选")
        filtered_up_filter_btn.setFixedWidth(60)
        filtered_up_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 4px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        filtered_up_filter_btn.clicked.connect(self.filter_filtered_ups)
        filter_layout.addWidget(filtered_up_filter_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 计数标签
        self.filtered_up_count_label = QLabel("共 0 个UP主")
        self.filtered_up_count_label.setStyleSheet("font-size: 10px; color: #666; padding: 5px;")
        layout.addWidget(self.filtered_up_count_label)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
        """)

        # 内容容器
        self.filtered_up_content = QWidget()
        self.filtered_up_layout = QVBoxLayout(self.filtered_up_content)
        self.filtered_up_layout.setSpacing(10)
        self.filtered_up_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(self.filtered_up_content)
        layout.addWidget(scroll_area)

        return panel

    def setup_connections(self):
        """设置信号连接"""
        self.search_btn.clicked.connect(lambda: self.start_search(is_continue=False))
        self.continue_btn.clicked.connect(lambda: self.start_search(is_continue=True))
        self.export_btn.clicked.connect(self.export_excel)
        self.clear_btn.clicked.connect(self.clear_results)
        self.blacklist_checkbox.stateChanged.connect(self.toggle_blacklist_filter)
        self.manage_blacklist_btn.clicked.connect(self.show_blacklist_dialog)

    def start_search(self, is_continue=False):
        """开始搜索"""
        # 验证输入
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "警告", "请输入视频关键词")
            return

        try:
            min_play = int(self.min_play_input.text())
            max_play = int(self.max_play_input.text())
            min_fans = int(self.min_fans_input.text())
            max_fans = int(self.max_fans_input.text())
            pages = int(self.pages_input.text())
        except ValueError:
            QMessageBox.warning(self, "警告", "播放量、粉丝数和页数必须是数字")
            return

        # 继续搜索的检查
        if is_continue:
            if keyword != self.current_keyword:
                reply = QMessageBox.question(
                    self, "提示",
                    "关键词已改变，继续搜索将从新关键词的第1页开始。\n是否继续？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                is_continue = False
                self.current_page = 1
                self.searched_mids.clear()
        else:
            # 新搜索，清空之前的结果
            self.clear_results()
            self.current_page = 1
            self.searched_mids.clear()

        # 保存当前关键词
        self.current_keyword = keyword

        # 禁用按钮
        self.search_btn.setEnabled(False)
        self.continue_btn.setEnabled(False)
        self.search_btn.setText("搜索中...")
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("开始搜索...")
        self.is_searching = True

        # 创建并启动工作线程
        self.search_worker = SearchWorker()

        # 设置参数
        start_page = self.current_page if is_continue else 1
        self.search_worker.set_params(
            keyword, min_play, max_play, min_fans, max_fans,
            start_page, pages, self.searched_mids.copy()
        )

        # 连接信号
        self.search_worker.progress_updated.connect(self.update_progress)
        self.search_worker.video_found.connect(self.on_video_found)
        self.search_worker.up_found.connect(self.on_up_found)
        self.search_worker.page_completed.connect(self.on_page_completed)
        self.search_worker.search_completed.connect(self.on_search_completed)
        self.search_worker.error_occurred.connect(self.on_search_error)

        # 启动线程
        self.search_worker.start()

    def update_progress(self, message: str):
        """更新进度信息"""
        self.progress_label.setText(message)

    def on_video_found(self, video: dict):
        """实时接收到视频"""
        self.all_videos.append(video)

        # 添加到列表
        title = video.get('title', '未知标题')
        title = re.sub('<[^<]+?>', '', title)  # 移除HTML标签

        play = video.get('play', 0)
        if isinstance(play, str):
            try:
                play = int(play)
            except:
                play = 0

        author = video.get('author', '未知UP主')

        item_text = f"{len(self.all_videos)}. {title}\n   👁️ {BilibiliAPI.format_number(play)}播放 | 👤 {author}"

        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, video)
        self.video_list.addItem(item)

        # 更新计数
        self.video_count_label.setText(f"共 {len(self.all_videos)} 个视频")

        # 自动滚动到底部
        self.video_list.scrollToBottom()

    def on_up_found(self, up_data: dict, is_qualified: bool):
        """实时接收到UP主"""
        mid = up_data['mid']

        # 添加到所有UP主
        if mid not in self.all_ups:
            self.all_ups[mid] = up_data

            # 检查是否在过滤名单
            is_blacklisted = self.config.is_in_blacklist(mid)

            # 添加到列表（标记过滤名单）
            name = up_data.get('name', '未知')
            fans = up_data.get('fans', 0)
            videos = up_data.get('videos', 0)

            blacklist_mark = " 🚫" if is_blacklisted else ""
            item_text = f"{len(self.all_ups)}. {name}{blacklist_mark}\n   👥 {BilibiliAPI.format_number(fans)}粉丝 | 📹 {videos}投稿"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, mid)
            self.all_up_list.addItem(item)

            # 更新计数
            self.all_up_count_label.setText(f"共 {len(self.all_ups)} 个UP主")

            # 自动滚动
            self.all_up_list.scrollToBottom()

        # 如果符合粉丝条件
        if is_qualified:
            # 检查过滤名单
            if self.apply_blacklist and self.config.is_in_blacklist(mid):
                return

            # 添加到符合条件列表
            if mid not in self.filtered_ups:
                self.filtered_ups[mid] = up_data

                # 创建卡片
                rank = len(self.filtered_ups)
                card = UPCardWidgetV2(up_data, rank)
                card.add_to_blacklist_signal.connect(self.add_up_to_blacklist)

                # 保存卡片引用
                self.up_cards[mid] = card

                # 添加到布局
                self.filtered_up_layout.addWidget(card)

                # 更新计数
                self.filtered_up_count_label.setText(f"共 {len(self.filtered_ups)} 个UP主")

    def on_page_completed(self, page: int):
        """完成一页"""
        self.current_page = page + 1
        # 自动保存搜索进度
        self.save_search_state()

    def on_search_completed(self, result: dict):
        """搜索完成"""
        # 更新已搜索的mid列表
        self.searched_mids = result.get('searched_mids', set())

        # 更新统计信息
        stats_text = f"""✅ 搜索完成！

📹 总视频: {result['total_videos']} 个
🎬 符合播放量: {result['filtered_videos_count']} 个
👥 所有UP主: {result['all_ups_count']} 个
✅ 符合条件UP: {result['qualified_ups_count']} 个
📄 当前页: {result['last_page']}
"""
        self.stats_label.setText(stats_text)

        # 恢复按钮状态
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 开始搜索")
        self.continue_btn.setEnabled(True)
        self.export_btn.setEnabled(len(self.filtered_ups) > 0)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("搜索完成！")
        self.is_searching = False

        # 保存最终状态
        self.save_search_state()

        if result['qualified_ups_count'] == 0:
            QMessageBox.information(self, "提示", "没有找到符合条件的UP主，请尝试调整筛选条件或继续搜索")

    def on_search_error(self, error_message: str):
        """搜索出错"""
        QMessageBox.critical(self, "错误", f"搜索出错:\n{error_message}")

        # 恢复按钮状态
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 开始搜索")
        self.continue_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("搜索出错")
        self.is_searching = False

    def add_up_to_blacklist(self, mid: int, name: str):
        """添加UP主到过滤名单"""
        reply = QMessageBox.question(
            self, "确认",
            f"确定要将 {name} (UID: {mid}) 添加到过滤名单吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.config.add_to_blacklist(mid)

            # 如果应用过滤，从列表移除
            if self.apply_blacklist:
                self.remove_up_card(mid)

            # 在"所有UP主"列表中标记
            for i in range(self.all_up_list.count()):
                item = self.all_up_list.item(i)
                if item.data(Qt.UserRole) == mid:
                    text = item.text()
                    if "🚫" not in text:
                        item.setText(text.replace("\n", " 🚫\n"))
                    break

            QMessageBox.information(self, "成功", f"已将 {name} 添加到过滤名单")

    def remove_up_card(self, mid: int):
        """从符合条件列表移除UP主卡片"""
        if mid in self.up_cards:
            card = self.up_cards[mid]
            self.filtered_up_layout.removeWidget(card)
            card.deleteLater()
            del self.up_cards[mid]

            # 从数据中移除
            if mid in self.filtered_ups:
                del self.filtered_ups[mid]

            # 更新计数
            self.filtered_up_count_label.setText(f"共 {len(self.filtered_ups)} 个UP主")

            # 重新编号
            self.refresh_card_ranks()

    def refresh_card_ranks(self):
        """刷新卡片排名"""
        # 按粉丝数重新排序
        sorted_ups = sorted(self.filtered_ups.values(), key=lambda x: x.get('fans', 0), reverse=True)

        for idx, up in enumerate(sorted_ups, 1):
            mid = up['mid']
            if mid in self.up_cards:
                self.up_cards[mid].rank = idx
                # 更新卡片上的排名显示
                # 注意：这需要在UPCardWidgetV2中添加update_rank方法

    def toggle_blacklist_filter(self, state):
        """切换过滤名单过滤"""
        self.apply_blacklist = (state == Qt.Checked)

        if self.apply_blacklist:
            # 应用过滤：移除过滤名单UP主
            blacklist = self.config.get_blacklist()
            for mid in blacklist:
                if mid in self.up_cards:
                    self.remove_up_card(mid)
        else:
            # 不应用过滤：重新显示所有符合条件的UP主
            self.refresh_filtered_ups()

    def refresh_filtered_ups(self):
        """刷新符合条件的UP主列表"""
        # 清空当前显示
        while self.filtered_up_layout.count():
            item = self.filtered_up_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.up_cards.clear()

        # 重新显示（根据过滤名单过滤设置）
        sorted_ups = sorted(self.filtered_ups.values(), key=lambda x: x.get('fans', 0), reverse=True)

        for idx, up in enumerate(sorted_ups, 1):
            mid = up['mid']

            # 如果应用过滤名单过滤且在过滤名单中，跳过
            if self.apply_blacklist and self.config.is_in_blacklist(mid):
                continue

            # 创建卡片
            card = UPCardWidgetV2(up, idx)
            card.add_to_blacklist_signal.connect(self.add_up_to_blacklist)

            self.up_cards[mid] = card
            self.filtered_up_layout.addWidget(card)

        # 更新计数
        visible_count = len(self.up_cards)
        self.filtered_up_count_label.setText(f"共 {visible_count} 个UP主")

    def show_blacklist_dialog(self):
        """显示过滤名单管理对话框"""
        dialog = BlacklistDialog(self.config, self)
        dialog.blacklist_updated.connect(self.on_blacklist_updated)
        dialog.exec_()

    def on_blacklist_updated(self):
        """过滤名单更新后的回调"""
        # 如果正在应用过滤，刷新列表
        if self.apply_blacklist:
            self.refresh_filtered_ups()

    def save_search_state(self):
        """保存搜索状态"""
        if not self.current_keyword:
            return

        try:
            params = {
                "min_play": int(self.min_play_input.text()),
                "max_play": int(self.max_play_input.text()),
                "min_fans": int(self.min_fans_input.text()),
                "max_fans": int(self.max_fans_input.text()),
            }
        except:
            params = {}

        self.config.save_search_state(
            self.current_keyword,
            self.current_page,
            self.searched_mids,
            params
        )

    def load_last_search_state(self):
        """加载上次搜索状态"""
        state = self.config.search_state
        if state and state.get("keyword"):
            # 提示是否恢复
            reply = QMessageBox.question(
                self, "恢复搜索",
                f"检测到上次未完成的搜索:\n关键词: {state.get('keyword')}\n页码: {state.get('current_page')}\n\n是否恢复？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.keyword_input.setText(state.get("keyword", ""))
                self.current_keyword = state.get("keyword", "")
                self.current_page = state.get("current_page", 1)
                self.searched_mids = set(state.get("searched_mids", []))

                params = state.get("params", {})
                if params:
                    self.min_play_input.setText(str(params.get("min_play", 10000)))
                    self.max_play_input.setText(str(params.get("max_play", 10000000)))
                    self.min_fans_input.setText(str(params.get("min_fans", 10000)))
                    self.max_fans_input.setText(str(params.get("max_fans", 1000000)))

                self.continue_btn.setEnabled(True)
                QMessageBox.information(self, "提示", "已恢复上次搜索状态，点击\"继续搜索\"按钮继续")

    def on_video_double_clicked(self, item):
        """双击视频项"""
        video_data = item.data(Qt.UserRole)
        if video_data:
            bvid = video_data.get('bvid', '')
            if bvid:
                webbrowser.open(f"https://www.bilibili.com/video/{bvid}")

    def on_all_up_double_clicked(self, item):
        """双击UP主项"""
        mid = item.data(Qt.UserRole)
        if mid:
            webbrowser.open(f"https://space.bilibili.com/{mid}")

    def filter_videos(self):
        """二次筛选视频"""
        try:
            min_play = int(self.video_min_play.text()) if self.video_min_play.text() else 0
            max_play = int(self.video_max_play.text()) if self.video_max_play.text() else 999999999
        except ValueError:
            QMessageBox.warning(self, "警告", "播放量必须是数字")
            return

        # 清空列表
        self.video_list.clear()

        # 从原始数据筛选并重新显示
        count = 0
        for video in self.all_videos:
            play = video.get('play', 0)
            if isinstance(play, str):
                try:
                    play = int(play)
                except:
                    play = 0

            if min_play <= play <= max_play:
                count += 1
                title = video.get('title', '未知标题')
                title = re.sub('<[^<]+?>', '', title)
                author = video.get('author', '未知UP主')

                item_text = f"{count}. {title}\n   👁️ {BilibiliAPI.format_number(play)}播放 | 👤 {author}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, video)
                self.video_list.addItem(item)

        self.video_count_label.setText(f"共 {count} 个视频")

    def filter_all_ups(self):
        """二次筛选所有UP主"""
        try:
            min_fans = int(self.all_up_min_fans.text()) if self.all_up_min_fans.text() else 0
            max_fans = int(self.all_up_max_fans.text()) if self.all_up_max_fans.text() else 999999999
        except ValueError:
            QMessageBox.warning(self, "警告", "粉丝数必须是数字")
            return

        # 清空列表
        self.all_up_list.clear()

        # 从原始数据筛选并重新显示
        filtered = {mid: up for mid, up in self.all_ups.items()
                    if min_fans <= up.get('fans', 0) <= max_fans}

        sorted_ups = sorted(filtered.values(), key=lambda x: x.get('fans', 0), reverse=True)

        for idx, up in enumerate(sorted_ups, 1):
            name = up.get('name', '未知')
            fans = up.get('fans', 0)
            videos = up.get('videos', 0)
            mid = up.get('mid')

            is_blacklisted = self.config.is_in_blacklist(mid)
            blacklist_mark = " 🚫" if is_blacklisted else ""

            item_text = f"{idx}. {name}{blacklist_mark}\n   👥 {BilibiliAPI.format_number(fans)}粉丝 | 📹 {videos}投稿"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, mid)
            self.all_up_list.addItem(item)

        self.all_up_count_label.setText(f"共 {len(filtered)} 个UP主")

    def filter_filtered_ups(self):
        """二次筛选符合条件的UP主"""
        try:
            min_fans = int(self.filtered_up_min_fans.text()) if self.filtered_up_min_fans.text() else 0
            max_fans = int(self.filtered_up_max_fans.text()) if self.filtered_up_max_fans.text() else 999999999
        except ValueError:
            QMessageBox.warning(self, "警告", "粉丝数必须是数字")
            return

        # 清空当前显示
        while self.filtered_up_layout.count():
            item = self.filtered_up_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.up_cards.clear()

        # 从原始数据筛选
        filtered = {mid: up for mid, up in self.filtered_ups.items()
                    if min_fans <= up.get('fans', 0) <= max_fans}

        sorted_ups = sorted(filtered.values(), key=lambda x: x.get('fans', 0), reverse=True)

        for idx, up in enumerate(sorted_ups, 1):
            mid = up['mid']

            # 如果应用过滤名单过滤且在过滤名单中，跳过
            if self.apply_blacklist and self.config.is_in_blacklist(mid):
                continue

            card = UPCardWidgetV2(up, idx)
            card.add_to_blacklist_signal.connect(self.add_up_to_blacklist)

            self.up_cards[mid] = card
            self.filtered_up_layout.addWidget(card)

        self.filtered_up_count_label.setText(f"共 {len(self.up_cards)} 个UP主")

    def export_excel(self):
        """导出Excel"""
        if not self.filtered_ups:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return

        # 选择保存路径
        default_filename = f"bilibili_up_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出Excel", default_filename, "Excel文件 (*.xlsx)"
        )

        if filepath:
            exporter = ExcelExporter()
            success = exporter.export_ups(self.filtered_ups, filepath)

            if success:
                QMessageBox.information(self, "成功", f"已成功导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "错误", "导出失败")

    def clear_results(self):
        """清空结果"""
        reply = QMessageBox.question(
            self, "确认",
            "确定要清空所有搜索结果吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 清空视频列表
            self.video_list.clear()
            self.video_count_label.setText("共 0 个视频")

            # 清空所有UP主列表
            self.all_up_list.clear()
            self.all_up_count_label.setText("共 0 个UP主")

            # 清空筛选后的UP主卡片
            while self.filtered_up_layout.count():
                item = self.filtered_up_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.filtered_up_count_label.setText("共 0 个UP主")

            # 清空数据
            self.all_videos = []
            self.all_ups = {}
            self.filtered_ups = {}
            self.up_cards = {}
            self.stats_label.setText("尚未搜索")
            self.export_btn.setEnabled(False)
            self.progress_label.setText("等待搜索...")

            # 清除搜索状态
            self.config.clear_search_state()
            self.current_keyword = ""
            self.current_page = 1
            self.searched_mids.clear()
            self.continue_btn.setEnabled(False)

    def closeEvent(self, event):
        """关闭事件"""
        # 如果正在搜索，提示用户
        if self.is_searching:
            reply = QMessageBox.question(
                self, "确认",
                "搜索正在进行中，确定要关闭吗？\n搜索进度已自动保存。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

            # 停止搜索线程
            if self.search_worker and self.search_worker.isRunning():
                self.search_worker.stop()
                self.search_worker.wait()

        event.accept()
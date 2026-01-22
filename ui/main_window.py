"""
主窗口UI - 三列布局版本
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QScrollArea, QFrame, QMessageBox, QFileDialog,
                             QProgressBar, QTextEdit, QListWidget, QListWidgetItem,
                             QSplitter)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from ui.up_card import UPCardWidget
from core.search_worker import SearchWorker
from core.bilibili_api import BilibiliAPI
from utils.excel_exporter import ExcelExporter
from datetime import datetime
import webbrowser


class MainWindow(QMainWindow):
    """主窗口 - 三列布局"""
    
    def __init__(self):
        super().__init__()
        self.api = BilibiliAPI()
        self.search_worker = None
        self.all_videos = []
        self.all_ups = {}
        self.filtered_ups = {}
        
        # 保存原始数据用于二次筛选
        self.original_videos = []
        self.original_all_ups = {}
        self.original_filtered_ups = {}

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("B站UP主筛选工具 - 三列视图")
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
        panel.setMaximumHeight(250)
        layout = QVBoxLayout(panel)

        # 搜索条件行
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
            QPushButton:hover {
                background-color: #0087b3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_layout.addWidget(self.search_btn)

        search_layout.addWidget(control_group)

        layout.addLayout(search_layout)

        # 进度和操作行
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

        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setStyleSheet("""
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
        header = QLabel("📹 搜索到的视频")
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
            QPushButton:hover {
                background-color: #0087b3;
            }
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
            QListWidget::item:hover {
                background-color: #f0f8ff;
            }
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
        header = QLabel("👥 所有UP主")
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
            QPushButton:hover {
                background-color: #e0a800;
            }
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
            QListWidget::item:hover {
                background-color: #fffbf0;
            }
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
        header = QLabel("✅ 符合条件的UP主")
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
            QPushButton:hover {
                background-color: #218838;
            }
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
        self.search_btn.clicked.connect(self.start_search)
        self.export_btn.clicked.connect(self.export_excel)
        self.clear_btn.clicked.connect(self.clear_results)

    def on_video_double_clicked(self, item):
        """双击视频项"""
        video_data = item.data(Qt.UserRole)
        if video_data:
            # 打开视频页面
            bvid = video_data.get('bvid', '')
            if bvid:
                webbrowser.open(f"https://www.bilibili.com/video/{bvid}")

    def on_all_up_double_clicked(self, item):
        """双击UP主项"""
        mid = item.data(Qt.UserRole)
        if mid:
            webbrowser.open(f"https://space.bilibili.com/{mid}")


    def start_search(self):
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

        # 清空之前的结果
        self.clear_results()

        # 禁用搜索按钮
        self.search_btn.setEnabled(False)
        self.search_btn.setText("搜索中...")
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("开始搜索...")

        # 创建并启动工作线程
        self.search_worker = SearchWorker()
        self.search_worker.set_params(keyword, min_play, max_play, min_fans, max_fans, pages)

        # 连接信号
        self.search_worker.progress_updated.connect(self.update_progress)
        self.search_worker.video_found.connect(self.on_videos_found)
        self.search_worker.up_found.connect(self.on_ups_found)
        self.search_worker.search_completed.connect(self.on_search_completed)
        self.search_worker.error_occurred.connect(self.on_search_error)

        # 启动线程
        self.search_worker.start()

    def update_progress(self, message: str):
        """更新进度信息"""
        self.progress_label.setText(message)

    def on_videos_found(self, current, total):
        """视频找到时的回调"""
        # 这个在worker中会实时更新，这里先不处理
        pass

    def on_ups_found(self, qualified, total):
        """UP主找到时的回调"""
        # 这个在worker中会实时更新，这里先不处理
        pass


    def on_search_completed(self, result: dict):
        """搜索完成"""
        # 保存原始数据用于二次筛选
        self.original_videos = result.get('filtered_videos', [])
        self.original_all_ups = result.get('all_ups', {})
        self.original_filtered_ups = result.get('ups', {})

        # 保存当前显示数据
        self.all_videos = self.original_videos.copy()
        self.all_ups = self.original_all_ups.copy()
        self.filtered_ups = self.original_filtered_ups.copy()

        # 显示视频列表（第一列）
        self.display_videos(self.all_videos)

        # 显示所有UP主（第二列）
        self.display_all_ups(self.all_ups)

        # 显示筛选后的UP主（第三列）
        self.display_filtered_ups(self.filtered_ups)

        # 更新统计信息
        stats_text = f"""✅ 搜索完成！

📹 视频: {result['total_videos']} 个
🎬 播放量符合: {result['filtered_videos_count']} 个
👥 所有UP主: {result['total_ups']} 个
✅ 符合条件UP: {result['qualified_ups']} 个
"""
        self.stats_label.setText(stats_text)

        # 恢复按钮状态
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 开始搜索")
        self.export_btn.setEnabled(len(self.filtered_ups) > 0)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("搜索完成！")

        if result['qualified_ups'] == 0:
            QMessageBox.information(self, "提示", "没有找到符合条件的UP主，请尝试调整筛选条件")

    def display_videos(self, videos: list):
        """显示视频列表"""
        self.video_list.clear()
        self.video_count_label.setText(f"共 {len(videos)} 个视频")

        for idx, video in enumerate(videos, 1):
            title = video.get('title', '未知标题')
            # 移除HTML标签
            import re
            title = re.sub('<[^<]+?>', '', title)

            # 获取播放量 - 可能是整数或字符串
            play = video.get('play', 0)
            if isinstance(play, str):
                # 如果是字符串，尝试解析
                try:
                    play = int(play)
                except:
                    play = 0

            author = video.get('author', '未知UP主')

            item_text = f"{idx}. {title}\n   👁️ {BilibiliAPI.format_number(play)}播放 | 👤 {author}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, video)
            self.video_list.addItem(item)

    def display_all_ups(self, ups: dict):
        """显示所有UP主"""
        self.all_up_list.clear()
        self.all_up_count_label.setText(f"共 {len(ups)} 个UP主")

        # 调试信息
        print(f"[DEBUG] display_all_ups 被调用，UP主数量: {len(ups)}")

        if not ups:
            # 如果为空，显示提示
            item = QListWidgetItem("暂无UP主数据（可能还在获取中...）")
            self.all_up_list.addItem(item)
            return

        # 按粉丝数排序
        sorted_ups = sorted(ups.values(), key=lambda x: x.get('fans', 0), reverse=True)

        for idx, up in enumerate(sorted_ups, 1):
            name = up.get('name', '未知')
            fans = up.get('fans', 0)
            videos = up.get('videos', 0)

            item_text = f"{idx}. {name}\n   👥 {BilibiliAPI.format_number(fans)}粉丝 | 📹 {videos}投稿"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, up.get('mid'))
            self.all_up_list.addItem(item)

    def display_filtered_ups(self, ups: dict):
        """显示筛选后的UP主（卡片形式）"""
        # 清空之前的卡片
        while self.filtered_up_layout.count():
            item = self.filtered_up_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.filtered_up_count_label.setText(f"共 {len(ups)} 个UP主")

        # 按粉丝数排序
        sorted_ups = sorted(ups.values(), key=lambda x: x['fans'], reverse=True)

        for idx, up in enumerate(sorted_ups, 1):
            card = UPCardWidget(up, idx)
            self.filtered_up_layout.addWidget(card)

    def on_search_error(self, error_msg: str):
        """搜索出错"""
        QMessageBox.critical(self, "错误", error_msg)
        self.search_btn.setEnabled(True)
        self.search_btn.setText("🔍 开始搜索")
        self.progress_bar.setVisible(False)


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
        self.stats_label.setText("尚未搜索")
        self.export_btn.setEnabled(False)
        self.progress_label.setText("等待搜索...")

    def filter_videos(self):
        """二次筛选视频"""
        try:
            min_play = int(self.video_min_play.text()) if self.video_min_play.text() else 0
            max_play = int(self.video_max_play.text()) if self.video_max_play.text() else 999999999
        except ValueError:
            QMessageBox.warning(self, "警告", "播放量必须是数字")
            return

        # 从原始数据筛选
        filtered = [v for v in self.original_videos if min_play <= v.get('play', 0) <= max_play]
        self.display_videos(filtered)

    def filter_all_ups(self):
        """二次筛选所有UP主"""
        try:
            min_fans = int(self.all_up_min_fans.text()) if self.all_up_min_fans.text() else 0
            max_fans = int(self.all_up_max_fans.text()) if self.all_up_max_fans.text() else 999999999
        except ValueError:
            QMessageBox.warning(self, "警告", "粉丝数必须是数字")
            return

        # 从原始数据筛选
        filtered = {mid: up for mid, up in self.original_all_ups.items()
                    if min_fans <= up.get('fans', 0) <= max_fans}
        self.display_all_ups(filtered)

    def filter_filtered_ups(self):
        """二次筛选符合条件的UP主"""
        try:
            min_fans = int(self.filtered_up_min_fans.text()) if self.filtered_up_min_fans.text() else 0
            max_fans = int(self.filtered_up_max_fans.text()) if self.filtered_up_max_fans.text() else 999999999
        except ValueError:
            QMessageBox.warning(self, "警告", "粉丝数必须是数字")
            return

        # 从原始数据筛选
        filtered = {mid: up for mid, up in self.original_filtered_ups.items()
                    if min_fans <= up.get('fans', 0) <= max_fans}
        self.display_filtered_ups(filtered)

    def closeEvent(self, event):
        """关闭事件"""
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.stop()
            self.search_worker.wait()
        event.accept()
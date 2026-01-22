"""
搜索工作线程 - 支持实时更新和断点续搜
"""
from PyQt5.QtCore import QThread, pyqtSignal
from core.bilibili_api import BilibiliAPI
from typing import Dict, Set
import time


class SearchWorker(QThread):
    """搜索工作线程 - 实时更新版"""

    # 信号定义
    progress_updated = pyqtSignal(str)  # 进度更新
    video_found = pyqtSignal(dict)  # 找到单个视频
    up_found = pyqtSignal(dict, bool)  # 找到UP主 (UP信息, 是否符合粉丝条件)
    search_completed = pyqtSignal(dict)  # 搜索完成
    error_occurred = pyqtSignal(str)  # 发生错误
    page_completed = pyqtSignal(int)  # 完成一页

    def __init__(self):
        super().__init__()
        self.api = BilibiliAPI()
        self.keyword = ""
        self.min_play = 0
        self.max_play = 999999999
        self.min_fans = 0
        self.max_fans = 999999999
        self.start_page = 1
        self.total_pages = 1
        self._is_running = True
        self.searched_mids: Set[int] = set()  # 已搜索的UP主ID

    def set_params(self, keyword: str, min_play: int, max_play: int,
                   min_fans: int, max_fans: int, start_page: int, total_pages: int,
                   searched_mids: Set[int] = None):
        """设置搜索参数"""
        self.keyword = keyword
        self.min_play = min_play
        self.max_play = max_play
        self.min_fans = min_fans
        self.max_fans = max_fans
        self.start_page = start_page
        self.total_pages = total_pages
        self.searched_mids = searched_mids if searched_mids else set()

    def stop(self):
        """停止搜索"""
        self._is_running = False

    def run(self):
        """执行搜索任务 - 实时更新版本"""
        try:
            self._is_running = True
            all_videos = []
            filtered_videos_count = 0
            all_ups_count = 0
            qualified_ups_count = 0

            # 逐页搜索
            for page in range(self.start_page, self.start_page + self.total_pages):
                if not self._is_running:
                    break

                self.progress_updated.emit(f"正在搜索第 {page} 页...")

                # 搜索视频
                videos = self.api.search_videos(self.keyword, page)
                if not videos:
                    self.progress_updated.emit(f"第 {page} 页没有找到视频")
                    continue

                all_videos.extend(videos)

                # 筛选播放量并实时发送视频
                for video in videos:
                    if not self._is_running:
                        break

                    play_count = video.get("play", 0)
                    if isinstance(play_count, str):
                        play_count = self.api._parse_play_count(play_count)

                    # 检查播放量
                    if self.min_play <= play_count <= self.max_play:
                        filtered_videos_count += 1
                        # 实时发送视频信息
                        self.video_found.emit(video)

                        # 提取UP主
                        mid = video.get("mid")
                        if mid and mid not in self.searched_mids:
                            self.searched_mids.add(mid)
                            all_ups_count += 1

                            # 获取UP主信息
                            self.progress_updated.emit(f"获取UP主信息: {video.get('author', '未知')}...")
                            user_info = self.api.get_user_info(mid)

                            if user_info:
                                fans = user_info.get("follower", 0)

                                # 构建UP主数据
                                up_data = {
                                    "mid": mid,
                                    "name": user_info.get("name", "未知"),
                                    "fans": fans,
                                    "videos": user_info.get("video", 0),
                                    "sign": user_info.get("sign", "无签名"),
                                    "level": user_info.get("level", 0),
                                    "official": user_info.get("official", {}).get("title", ""),
                                    "face": user_info.get("face", ""),
                                }

                                # 判断是否符合粉丝条件
                                is_qualified = self.min_fans <= fans <= self.max_fans
                                if is_qualified:
                                    qualified_ups_count += 1

                                # 实时发送UP主信息
                                self.up_found.emit(up_data, is_qualified)

                            # 延迟避免请求过快
                            time.sleep(0.5)

                # 完成一页
                self.page_completed.emit(page)
                self.progress_updated.emit(f"第 {page} 页完成")

            # 搜索完成
            result = {
                "keyword": self.keyword,
                "total_videos": len(all_videos),
                "filtered_videos_count": filtered_videos_count,
                "all_ups_count": all_ups_count,
                "qualified_ups_count": qualified_ups_count,
                "last_page": self.start_page + self.total_pages - 1,
                "searched_mids": self.searched_mids,
            }

            self.search_completed.emit(result)

        except Exception as e:
            self.error_occurred.emit(f"搜索过程出错: {str(e)}")
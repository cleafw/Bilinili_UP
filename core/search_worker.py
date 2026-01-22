"""
搜索工作线程 - 支持实时更新和断点续搜 - 修复版
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

            print(f"[SearchWorker] 开始搜索: 关键词={self.keyword}, 起始页={self.start_page}, 页数={self.total_pages}")

            # 逐页搜索
            for page in range(self.start_page, self.start_page + self.total_pages):
                if not self._is_running:
                    print("[SearchWorker] 搜索被中断")
                    break

                self.progress_updated.emit(f"正在搜索第 {page} 页...")
                print(f"[SearchWorker] 正在搜索第 {page} 页...")

                # 搜索视频
                videos = self.api.search_videos(self.keyword, page)
                print(f"[SearchWorker] 第 {page} 页找到 {len(videos)} 个视频")

                if not videos:
                    self.progress_updated.emit(f"第 {page} 页没有找到视频")
                    print(f"[SearchWorker] 第 {page} 页没有找到视频")
                    continue

                all_videos.extend(videos)

                # 筛选播放量并实时发送视频
                for video in videos:
                    if not self._is_running:
                        break

                    play_count = video.get("play", 0)
                    if isinstance(play_count, str):
                        play_count = self.api._parse_play_count(play_count)

                    # 确保play_count不为None
                    if play_count is None:
                        play_count = 0

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
                            author_name = video.get('author', '未知')
                            self.progress_updated.emit(f"获取UP主信息: {author_name}...")
                            print(f"[SearchWorker] 获取UP主 {author_name} (mid={mid}) 的详细信息...")

                            user_info = self.api.get_user_info(mid)

                            if user_info:
                                # 获取粉丝数，确保不为None
                                fans = user_info.get("follower", 0)
                                if fans is None:
                                    fans = 0
                                    print(f"[SearchWorker] 警告: UP主 {mid} 的粉丝数为None，设为0")

                                print(f"[SearchWorker] 获取到UP主: {user_info.get('name', '未知')}, mid={mid}, 粉丝={fans}")

                                # 构建UP主数据
                                up_data = {
                                    "mid": mid,
                                    "name": user_info.get("name", "未知"),
                                    "fans": fans,  # 确保不为None
                                    "videos": user_info.get("vr", user_info.get("archive_count", user_info.get("video", 0))) or 0,
                                    "sign": user_info.get("sign", "无签名"),
                                    "level": user_info.get("level", 0) or 0,
                                    "official": user_info.get("official", {}).get("title", "") if isinstance(user_info.get("official"), dict) else "",
                                    "face": user_info.get("face", ""),
                                }

                                # 判断是否符合粉丝条件（确保fans不为None）
                                try:
                                    is_qualified = self.min_fans <= fans <= self.max_fans
                                    if is_qualified:
                                        qualified_ups_count += 1
                                        print(f"[SearchWorker] UP主 {up_data['name']} 符合粉丝条件")
                                except TypeError as e:
                                    print(f"[SearchWorker] 粉丝数比较错误: fans={fans}, 错误={e}")
                                    is_qualified = False

                                # 实时发送UP主信息
                                self.up_found.emit(up_data, is_qualified)
                            else:
                                print(f"[SearchWorker] 无法获取 mid={mid} 的用户信息")

                            # 延迟避免请求过快
                            time.sleep(0.5)

                # 完成一页
                self.page_completed.emit(page)
                self.progress_updated.emit(f"第 {page} 页完成")
                print(f"[SearchWorker] 第 {page} 页完成")

                # 页间延迟
                if page < self.start_page + self.total_pages - 1:
                    time.sleep(1)

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

            print(f"[SearchWorker] 搜索完成统计:")
            print(f"  - 总视频数: {result['total_videos']}")
            print(f"  - 筛选后视频数: {result['filtered_videos_count']}")
            print(f"  - 所有UP主数: {result['all_ups_count']}")
            print(f"  - 符合条件UP主数: {result['qualified_ups_count']}")

            self.search_completed.emit(result)

        except Exception as e:
            error_msg = f"搜索过程出错: {str(e)}"
            print(f"[SearchWorker] {error_msg}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)
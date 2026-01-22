"""
搜索工作线程
"""
from PyQt5.QtCore import QThread, pyqtSignal
from core.bilibili_api import BilibiliAPI
from typing import Dict
import time


class SearchWorker(QThread):
    """搜索工作线程"""

    # 信号定义
    progress_updated = pyqtSignal(str)  # 进度更新
    video_found = pyqtSignal(int, int)  # 找到视频 (当前数, 总数)
    up_found = pyqtSignal(int, int)  # 找到UP主 (符合条件数, 总UP数)
    search_completed = pyqtSignal(dict)  # 搜索完成
    error_occurred = pyqtSignal(str)  # 发生错误

    def __init__(self):
        super().__init__()
        self.api = BilibiliAPI()
        self.keyword = ""
        self.min_play = 0
        self.max_play = 999999999
        self.min_fans = 0
        self.max_fans = 999999999
        self.pages = 1
        self._is_running = True

    def set_params(self, keyword: str, min_play: int, max_play: int,
                   min_fans: int, max_fans: int, pages: int):
        """设置搜索参数"""
        self.keyword = keyword
        self.min_play = min_play
        self.max_play = max_play
        self.min_fans = min_fans
        self.max_fans = max_fans
        self.pages = pages

    def stop(self):
        """停止搜索"""
        self._is_running = False

    def run(self):
        """执行搜索任务"""
        try:
            self._is_running = True
            all_videos = []

            # 步骤1: 搜索视频
            self.progress_updated.emit(f"开始搜索关键词: {self.keyword}")

            for page in range(1, self.pages + 1):
                if not self._is_running:
                    return

                self.progress_updated.emit(f"正在搜索第 {page}/{self.pages} 页...")
                videos = self.api.search_videos(self.keyword, page)
                all_videos.extend(videos)
                self.video_found.emit(len(all_videos), len(all_videos))

            if not all_videos:
                self.error_occurred.emit("未找到任何视频")
                return

            # 步骤2: 根据播放量筛选视频
            self.progress_updated.emit(f"根据播放量筛选视频...")
            filtered_videos = self.api.filter_videos_by_play_count(
                all_videos, self.min_play, self.max_play
            )

            if not filtered_videos:
                self.error_occurred.emit(f"播放量在 {self.min_play}-{self.max_play} 范围内的视频为0")
                return

            self.progress_updated.emit(
                f"找到 {len(filtered_videos)} 个符合播放量要求的视频"
            )

            # 步骤3: 提取所有UP主信息（不筛选粉丝数）
            self.progress_updated.emit("开始提取所有UP主信息...")

            all_ups_dict = {}
            processed_mids = set()

            for index, video in enumerate(filtered_videos):
                if not self._is_running:
                    return

                mid = video.get("mid")
                if not mid or mid in processed_mids:
                    continue

                processed_mids.add(mid)

                self.progress_updated.emit(f"正在获取UP主信息... ({index + 1}/{len(filtered_videos)})")

                # 获取UP主详细信息
                user_info = self.api.get_user_info(mid)
                if not user_info:
                    print(f"[DEBUG] 无法获取 mid={mid} 的用户信息")
                    continue

                fans = user_info.get("follower", 0)
                name = user_info.get("name", "未知")

                print(f"[DEBUG] 获取到UP主: {name}, mid={mid}, 粉丝={fans}")

                # 添加到所有UP主字典
                all_ups_dict[mid] = {
                    "mid": mid,
                    "name": name,
                    "fans": fans,
                    "videos": user_info.get("video", 0),
                    "sign": user_info.get("sign", "无签名"),
                    "level": user_info.get("level", 0),
                    "official": user_info.get("official", {}).get("title", ""),
                    "face": user_info.get("face", ""),
                }

                time.sleep(0.3)

            # 步骤4: 根据粉丝数筛选UP主
            self.progress_updated.emit("根据粉丝数筛选UP主...")
            filtered_ups_dict = {
                mid: up_info for mid, up_info in all_ups_dict.items()
                if self.min_fans <= up_info['fans'] <= self.max_fans
            }

            print(f"[DEBUG] 搜索完成统计:")
            print(f"  - 总视频数: {len(all_videos)}")
            print(f"  - 筛选后视频数: {len(filtered_videos)}")
            print(f"  - 所有UP主数: {len(all_ups_dict)}")
            print(f"  - 符合条件UP主数: {len(filtered_ups_dict)}")

            # 步骤5: 返回结果
            result = {
                "total_videos": len(all_videos),
                "all_videos": all_videos,
                "filtered_videos": filtered_videos,
                "filtered_videos_count": len(filtered_videos),
                "all_ups": all_ups_dict,
                "total_ups": len(all_ups_dict),
                "ups": filtered_ups_dict,
                "qualified_ups": len(filtered_ups_dict),
            }

            self.search_completed.emit(result)

        except Exception as e:
            self.error_occurred.emit(f"搜索过程出错: {str(e)}")
"""
B站API交互核心模块 - 最终修复版
"""
import requests
import time
import urllib.parse
from typing import List, Dict, Optional
import json


class BilibiliAPI:
    """B站API封装类"""

    def __init__(self):
        # 完整的浏览器请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://www.bilibili.com",
            "Connection": "keep-alive",
        }

        # 创建session以保持连接
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def open_bilibili(self, search_query: str = None, browser: str = None) -> dict:
        """
        打开 Bilibili（B站）
        """
        if search_query:
            encoded_query = urllib.parse.quote(search_query)
            url = f"https://search.bilibili.com/all?keyword={encoded_query}"
        else:
            url = "https://www.bilibili.com"

        import webbrowser
        webbrowser.open(url)
        return {"success": True, "url": url}

    def search_videos(self, keyword: str, page: int = 1, pagesize: int = 30) -> List[Dict]:
        """
        搜索B站视频
        """
        url = "https://api.bilibili.com/x/web-interface/search/type"
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "pagesize": pagesize,
            "order": "totalrank"
        }

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data", {}).get("result", [])
        except Exception as e:
            print(f"[API] 搜索视频出错: {e}")

        return []

    def get_user_info(self, mid: int) -> Optional[Dict]:
        """
        获取UP主详细信息 - 使用多种方法获取
        """
        # 方法1: 尝试card接口（通常更稳定）
        user_info = self._get_user_card(mid)
        if user_info:
            return user_info

        # 方法2: 尝试旧的info接口
        user_info = self._get_user_info_old(mid)
        if user_info:
            return user_info

        # 方法3: 尝试从空间接口获取
        user_info = self._get_user_from_space(mid)
        if user_info:
            return user_info

        print(f"[API] 所有方法都无法获取 mid={mid} 的信息")
        return None

    def _get_user_card(self, mid: int) -> Optional[Dict]:
        """
        方法1: 使用card接口获取用户信息（推荐）
        """
        url = "https://api.bilibili.com/x/web-interface/card"
        params = {"mid": mid}

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    card = data.get("data", {}).get("card", {})
                    if card:
                        # 统一格式
                        return {
                            "mid": card.get("mid"),
                            "name": card.get("name"),
                            "follower": card.get("fans", 0),
                            "video": card.get("archive_count", card.get("vr", 0)),  # 修改这里
                            "sign": card.get("sign", "无签名"),
                            "level": card.get("level_info", {}).get("current_level", 0),
                            "official": card.get("official_verify", {}),
                            "face": card.get("face", ""),
                        }
        except Exception as e:
            pass

        return None

    def _get_user_info_old(self, mid: int) -> Optional[Dict]:
        """
        方法2: 使用旧的acc/info接口
        """
        url = "https://api.bilibili.com/x/space/acc/info"
        params = {"mid": mid}

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data", {})
        except Exception as e:
            pass

        return None

    def _get_user_from_space(self, mid: int) -> Optional[Dict]:
        """
        方法3: 从空间navnum接口获取基本信息
        """
        url = "https://api.bilibili.com/x/space/navnum"
        params = {"mid": mid}

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    nav_data = data.get("data", {})

                    # 再获取upstat以获取粉丝数
                    stat_url = "https://api.bilibili.com/x/relation/stat"
                    stat_response = self.session.get(stat_url, params=params, timeout=15)

                    follower = 0
                    if stat_response.status_code == 200:
                        stat_data = stat_response.json()
                        if stat_data.get("code") == 0:
                            follower = stat_data.get("data", {}).get("follower", 0)

                    return {
                        "mid": mid,
                        "name": f"UP主{mid}",  # 无法获取名字时的备用
                        "follower": follower,
                        "video": nav_data.get("video", 0),
                        "sign": "无签名",
                        "level": 0,
                        "official": {},
                        "face": "",
                    }
        except Exception as e:
            pass

        return None

    def filter_videos_by_play_count(self, videos: List[Dict], min_play: int, max_play: int) -> List[Dict]:
        """
        根据播放量筛选视频
        """
        filtered = []
        for video in videos:
            play_count = video.get("play", 0)
            if isinstance(play_count, str):
                play_count = self._parse_play_count(play_count)

            if min_play <= play_count <= max_play:
                filtered.append(video)

        return filtered

    def _parse_play_count(self, play_str) -> int:
        """
        解析播放量字符串或整数
        """
        try:
            if isinstance(play_str, int):
                return play_str

            if isinstance(play_str, str):
                if "万" in play_str:
                    return int(float(play_str.replace("万", "")) * 10000)
                elif "亿" in play_str:
                    return int(float(play_str.replace("亿", "")) * 100000000)
                else:
                    return int(play_str)
            return 0
        except:
            return 0

    def extract_unique_ups(self, videos: List[Dict], min_fans: int, max_fans: int,
                          callback=None) -> Dict[int, Dict]:
        """
        从视频列表中提取UP主并去重
        """
        up_dict = {}
        processed_mids = set()
        total = len(videos)

        for index, video in enumerate(videos):
            mid = video.get("mid")
            if not mid or mid in processed_mids:
                continue

            processed_mids.add(mid)

            if callback:
                callback(index + 1, total, f"正在获取UP主信息...")

            # 获取UP主详细信息
            user_info = self.get_user_info(mid)
            if not user_info:
                continue

            fans = user_info.get("follower", 0)

            # 筛选粉丝数
            if min_fans <= fans <= max_fans:
                up_dict[mid] = {
                    "mid": mid,
                    "name": user_info.get("name", "未知"),
                    "fans": fans,
                    "videos": user_info.get("video", 0),
                    "sign": user_info.get("sign", "无签名"),
                    "level": user_info.get("level", 0),
                    "official": user_info.get("official", {}).get("title", ""),
                    "face": user_info.get("face", ""),
                }

            # 避免请求过快 - 增加延迟
            time.sleep(0.5)

        return up_dict

    @staticmethod
    def format_number(num: int) -> str:
        """
        格式化数字显示
        """
        if num >= 100000000:
            return f"{num/100000000:.1f}亿"
        elif num >= 10000:
            return f"{num/10000:.1f}万"
        return str(num)
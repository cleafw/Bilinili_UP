"""
配置和数据持久化管理模块
"""
import json
import os
from typing import Set, Dict, List
from datetime import datetime


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = config_dir
        self.blacklist_file = os.path.join(config_dir, "blacklist.json")
        self.search_state_file = os.path.join(config_dir, "search_state.json")
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 加载数据
        self.blacklist: Set[int] = self._load_blacklist()
        self.search_state: Dict = self._load_search_state()
    
    def _load_blacklist(self) -> Set[int]:
        """加载过滤名单"""
        if os.path.exists(self.blacklist_file):
            try:
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get("blacklist", []))
            except Exception as e:
                print(f"[Config] 加载过滤名单失败: {e}")
        return set()
    
    def _save_blacklist(self):
        """保存过滤名单"""
        try:
            data = {
                "blacklist": list(self.blacklist),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[Config] 过滤名单已保存: {len(self.blacklist)} 个UP主")
        except Exception as e:
            print(f"[Config] 保存过滤名单失败: {e}")
    
    def add_to_blacklist(self, mid: int) -> bool:
        """添加到过滤名单"""
        if mid not in self.blacklist:
            self.blacklist.add(mid)
            self._save_blacklist()
            return True
        return False
    
    def remove_from_blacklist(self, mid: int) -> bool:
        """从过滤名单移除"""
        if mid in self.blacklist:
            self.blacklist.remove(mid)
            self._save_blacklist()
            return True
        return False
    
    def is_in_blacklist(self, mid: int) -> bool:
        """检查是否在过滤名单中"""
        return mid in self.blacklist
    
    def get_blacklist(self) -> List[int]:
        """获取过滤名单列表"""
        return list(self.blacklist)
    
    def _load_search_state(self) -> Dict:
        """加载搜索状态"""
        if os.path.exists(self.search_state_file):
            try:
                with open(self.search_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Config] 加载搜索状态失败: {e}")
        return {}
    
    def save_search_state(self, keyword: str, current_page: int, 
                          searched_mids: Set[int], params: Dict):
        """保存搜索状态"""
        try:
            state = {
                "keyword": keyword,
                "current_page": current_page,
                "searched_mids": list(searched_mids),
                "params": params,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.search_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"[Config] 搜索状态已保存: 关键词={keyword}, 页码={current_page}")
        except Exception as e:
            print(f"[Config] 保存搜索状态失败: {e}")
    
    def get_search_state(self, keyword: str) -> Dict:
        """获取搜索状态"""
        if self.search_state.get("keyword") == keyword:
            return self.search_state
        return {}
    
    def clear_search_state(self):
        """清除搜索状态"""
        self.search_state = {}
        if os.path.exists(self.search_state_file):
            os.remove(self.search_state_file)
        print("[Config] 搜索状态已清除")
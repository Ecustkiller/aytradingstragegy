"""
智能数据管理器
实现缓存、限流、重试等机制，平衡速度和稳定性
"""

import time
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd
import os
from functools import wraps

class SmartDataManager:
    """智能数据管理器"""
    
    def __init__(self, cache_dir="data_cache", max_requests_per_minute=15):
        self.cache_dir = cache_dir
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = []
        self.lock = threading.Lock()
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
        
        # 缓存配置
        self.cache_config = {
            'stock_basic': 24 * 60,      # 基础信息缓存24小时
            'daily_data': 30,            # 日线数据缓存30分钟
            'realtime_data': 1,          # 实时数据缓存1分钟
            'financial_data': 60 * 24,   # 财务数据缓存1天
            'news_data': 10,             # 新闻数据缓存10分钟
        }
    
    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _is_cache_valid(self, cache_path: str, cache_minutes: int) -> bool:
        """检查缓存是否有效"""
        if not os.path.exists(cache_path):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        expire_time = file_time + timedelta(minutes=cache_minutes)
        return datetime.now() < expire_time
    
    def _load_cache(self, cache_path: str) -> Optional[Any]:
        """加载缓存数据"""
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'dataframe' in data:
                    return pd.read_json(data['dataframe'])
                return data['result']
        except Exception as e:
            print(f"缓存加载失败: {e}")
            return None
    
    def _save_cache(self, cache_path: str, result: Any):
        """保存缓存数据"""
        try:
            cache_data = {}
            if isinstance(result, pd.DataFrame):
                cache_data['dataframe'] = result.to_json()
            else:
                cache_data['result'] = result
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"缓存保存失败: {e}")
    
    def _wait_for_rate_limit(self):
        """等待满足限流要求"""
        with self.lock:
            now = time.time()
            # 清理1分钟前的请求记录
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # 如果请求过多，等待
            if len(self.request_times) >= self.max_requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0]) + 1
                print(f"⏳ 达到限流阈值，等待 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)
                self.request_times = []
            
            # 记录本次请求时间
            self.request_times.append(now)
    
    def cached_request(self, cache_type: str = 'daily_data', retry_times: int = 3):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = self._get_cache_key(func.__name__, *args, **kwargs)
                cache_path = self._get_cache_path(cache_key)
                cache_minutes = self.cache_config.get(cache_type, 30)
                
                # 检查缓存
                if self._is_cache_valid(cache_path, cache_minutes):
                    cached_result = self._load_cache(cache_path)
                    if cached_result is not None:
                        print(f"📦 使用缓存数据: {func.__name__}")
                        return cached_result
                
                # 缓存无效，发起请求
                print(f"🌐 发起网络请求: {func.__name__}")
                
                # 限流控制
                self._wait_for_rate_limit()
                
                # 重试机制
                last_error = None
                for attempt in range(retry_times):
                    try:
                        result = func(*args, **kwargs)
                        
                        # 保存缓存
                        if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                            self._save_cache(cache_path, result)
                        
                        return result
                        
                    except Exception as e:
                        last_error = e
                        if attempt < retry_times - 1:
                            wait_time = (attempt + 1) * 2  # 指数退避
                            print(f"❌ 请求失败，{wait_time}秒后重试 (第{attempt+1}次): {e}")
                            time.sleep(wait_time)
                        else:
                            print(f"❌ 请求最终失败: {e}")
                
                # 所有重试都失败，尝试返回过期缓存
                if os.path.exists(cache_path):
                    print("🔄 使用过期缓存数据")
                    return self._load_cache(cache_path)
                
                raise last_error
            
            return wrapper
        return decorator
    
    def clear_cache(self, older_than_hours: int = 24):
        """清理过期缓存"""
        try:
            cutoff_time = time.time() - (older_than_hours * 3600)
            cleared_count = 0
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        cleared_count += 1
            
            print(f"🧹 清理了 {cleared_count} 个过期缓存文件")
            
        except Exception as e:
            print(f"缓存清理失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)
            
            return {
                'cache_files': len(cache_files),
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'recent_requests': len(self.request_times),
                'rate_limit': self.max_requests_per_minute
            }
        except Exception as e:
            return {'error': str(e)}

# 全局实例
smart_data_manager = SmartDataManager()

# 使用示例装饰器
def cached_stock_data(cache_type='daily_data'):
    """股票数据缓存装饰器"""
    return smart_data_manager.cached_request(cache_type=cache_type)

def cached_realtime_data():
    """实时数据缓存装饰器"""
    return smart_data_manager.cached_request(cache_type='realtime_data')

def cached_financial_data():
    """财务数据缓存装饰器"""
    return smart_data_manager.cached_request(cache_type='financial_data')
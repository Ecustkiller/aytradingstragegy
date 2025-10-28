"""
缓存管理模块
为各个功能模块提供持久化存储和缓存管理
"""

import os
import pickle
import json
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from typing import Any, Optional, Dict
import hashlib

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = "data_cache"):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def generate_cache_key(self, module_name: str, params: Dict) -> str:
        """生成缓存键"""
        # 将参数转换为字符串并生成哈希
        params_str = json.dumps(params, sort_keys=True, default=str)
        hash_obj = hashlib.md5(f"{module_name}_{params_str}".encode())
        return hash_obj.hexdigest()
    
    def save_cache(self, cache_key: str, data: Any, metadata: Dict = None) -> bool:
        """保存缓存数据"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            
            cache_data = {
                'data': data,
                'timestamp': datetime.now(),
                'metadata': metadata or {}
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            return True
        except Exception as e:
            st.error(f"保存缓存失败: {str(e)}")
            return False
    
    def load_cache(self, cache_key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """加载缓存数据"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            
            if not os.path.exists(cache_file):
                return None
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 检查缓存是否过期
            if max_age_hours > 0:
                cache_time = cache_data.get('timestamp', datetime.min)
                if datetime.now() - cache_time > timedelta(hours=max_age_hours):
                    return None
            
            return cache_data
        except Exception as e:
            st.warning(f"加载缓存失败: {str(e)}")
            return None
    
    def clear_cache(self, pattern: str = None) -> int:
        """清理缓存"""
        try:
            cleared_count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    if pattern is None or pattern in filename:
                        os.remove(os.path.join(self.cache_dir, filename))
                        cleared_count += 1
            return cleared_count
        except Exception as e:
            st.error(f"清理缓存失败: {str(e)}")
            return 0
    
    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)
            
            return {
                'file_count': len(cache_files),
                'total_size_mb': total_size / (1024 * 1024),
                'cache_dir': self.cache_dir
            }
        except Exception as e:
            return {'error': str(e)}

# 全局缓存管理器实例
cache_manager = CacheManager()

def cached_function(module_name: str, cache_hours: int = 24):
    """缓存装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            params = {'args': args, 'kwargs': kwargs}
            cache_key = cache_manager.generate_cache_key(module_name, params)
            
            # 尝试加载缓存
            cached_data = cache_manager.load_cache(cache_key, cache_hours)
            
            if cached_data is not None:
                st.info(f"📋 使用缓存数据 (查询时间: {cached_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')})")
                return cached_data['data']
            
            # 执行函数并缓存结果
            with st.spinner("正在获取最新数据..."):
                result = func(*args, **kwargs)
            
            # 保存到缓存
            cache_manager.save_cache(cache_key, result, {'function': func.__name__})
            st.success(f"✅ 数据已更新 (查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            
            return result
        return wrapper
    return decorator

def display_cache_controls(module_name: str):
    """显示缓存控制面板"""
    with st.expander("🗂️ 缓存管理", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 强制刷新", help="清除缓存并重新获取数据"):
                cleared = cache_manager.clear_cache(module_name)
                st.success(f"已清除 {cleared} 个缓存文件")
                st.rerun()
        
        with col2:
            if st.button("📊 缓存信息", help="查看缓存统计信息"):
                cache_info = cache_manager.get_cache_info()
                st.json(cache_info)
        
        with col3:
            if st.button("🗑️ 清理全部", help="清理所有缓存文件"):
                cleared = cache_manager.clear_cache()
                st.success(f"已清除 {cleared} 个缓存文件")
                st.rerun()

def get_cached_data_info(cache_key: str) -> Optional[str]:
    """获取缓存数据信息"""
    cached_data = cache_manager.load_cache(cache_key, max_age_hours=0)  # 不检查过期时间
    if cached_data:
        timestamp = cached_data['timestamp']
        return f"缓存时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    return None
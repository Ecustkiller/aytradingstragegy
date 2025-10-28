"""
异步数据处理器
实现异步数据获取、并发处理、进度显示等功能
"""

import asyncio
import aiohttp
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
import pandas as pd
import streamlit as st
from functools import wraps
import queue
import json

class AsyncDataProcessor:
    """异步数据处理器"""
    
    def __init__(self, max_workers=5, timeout=30):
        self.max_workers = max_workers
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.progress_queue = queue.Queue()
        self.results_cache = {}
        
    def async_wrapper(self, show_progress=True):
        """异步处理装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if show_progress:
                    return self._run_with_progress(func, *args, **kwargs)
                else:
                    return self._run_async(func, *args, **kwargs)
            return wrapper
        return decorator
    
    def _run_with_progress(self, func, *args, **kwargs):
        """带进度条的异步执行"""
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 启动异步任务
        future = self.executor.submit(func, *args, **kwargs)
        
        # 模拟进度更新
        progress = 0
        while not future.done():
            progress = min(progress + 0.1, 0.9)
            progress_bar.progress(progress)
            status_text.text(f"正在处理数据... {int(progress*100)}%")
            time.sleep(0.1)
        
        # 获取结果
        result = future.result()
        
        # 完成进度
        progress_bar.progress(1.0)
        status_text.text("数据处理完成！")
        time.sleep(0.5)
        
        # 清理UI
        progress_bar.empty()
        status_text.empty()
        
        return result
    
    def _run_async(self, func, *args, **kwargs):
        """简单异步执行"""
        future = self.executor.submit(func, *args, **kwargs)
        return future.result()
    
    def batch_process(self, tasks: List[Dict], progress_callback=None):
        """批量处理任务"""
        results = []
        total_tasks = len(tasks)
        
        if progress_callback:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # 提交所有任务
        futures = []
        for i, task in enumerate(tasks):
            func = task['func']
            args = task.get('args', ())
            kwargs = task.get('kwargs', {})
            future = self.executor.submit(func, *args, **kwargs)
            futures.append((i, future, task.get('name', f'Task {i+1}')))
        
        # 收集结果
        completed = 0
        for i, future, name in futures:
            try:
                result = future.result(timeout=self.timeout)
                results.append({
                    'index': i,
                    'name': name,
                    'result': result,
                    'success': True,
                    'error': None
                })
            except Exception as e:
                results.append({
                    'index': i,
                    'name': name,
                    'result': None,
                    'success': False,
                    'error': str(e)
                })
            
            completed += 1
            if progress_callback:
                progress = completed / total_tasks
                progress_bar.progress(progress)
                status_text.text(f"已完成 {completed}/{total_tasks} 个任务")
        
        if progress_callback:
            progress_bar.empty()
            status_text.empty()
        
        return results
    
    def parallel_data_fetch(self, symbols: List[str], fetch_func: Callable, **kwargs):
        """并行获取多个股票数据"""
        tasks = []
        for symbol in symbols:
            tasks.append({
                'func': fetch_func,
                'args': (symbol,),
                'kwargs': kwargs,
                'name': f'获取{symbol}数据'
            })
        
        return self.batch_process(tasks, progress_callback=True)
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

class DataCache:
    """高性能数据缓存"""
    
    def __init__(self, max_size=1000, ttl=300):
        self.max_size = max_size
        self.ttl = ttl  # 生存时间(秒)
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def _generate_key(self, *args, **kwargs):
        """生成缓存键"""
        key_data = {'args': args, 'kwargs': kwargs}
        return hash(json.dumps(key_data, sort_keys=True, default=str))
    
    def get(self, key):
        """获取缓存"""
        with self.lock:
            if key in self.cache:
                # 检查是否过期
                if time.time() - self.access_times[key] < self.ttl:
                    self.access_times[key] = time.time()  # 更新访问时间
                    return self.cache[key]
                else:
                    # 过期，删除
                    del self.cache[key]
                    del self.access_times[key]
            return None
    
    def set(self, key, value):
        """设置缓存"""
        with self.lock:
            # 如果缓存满了，删除最旧的
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.access_times.keys(), 
                               key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def cached_call(self, func):
        """缓存装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self._generate_key(*args, **kwargs)
            
            # 尝试从缓存获取
            result = self.get(key)
            if result is not None:
                return result
            
            # 缓存未命中，执行函数
            result = func(*args, **kwargs)
            self.set(key, result)
            return result
        
        return wrapper
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def stats(self):
        """获取缓存统计"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_count', 1), 1)
            }

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, name):
        """开始计时"""
        self.start_times[name] = time.time()
    
    def end_timer(self, name):
        """结束计时"""
        if name in self.start_times:
            duration = time.time() - self.start_times[name]
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(duration)
            del self.start_times[name]
            return duration
        return None
    
    def timer(self, name):
        """计时装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.start_timer(name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.end_timer(name)
            return wrapper
        return decorator
    
    def get_stats(self):
        """获取性能统计"""
        stats = {}
        for name, times in self.metrics.items():
            if times:
                stats[name] = {
                    'count': len(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'total': sum(times)
                }
        return stats
    
    def display_stats(self):
        """显示性能统计"""
        stats = self.get_stats()
        if not stats:
            st.info("暂无性能数据")
            return
        
        st.markdown("### ⚡ 性能统计")
        
        for name, data in stats.items():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(f"{name} - 调用次数", data['count'])
            with col2:
                st.metric("平均耗时", f"{data['avg']:.3f}s")
            with col3:
                st.metric("最快", f"{data['min']:.3f}s")
            with col4:
                st.metric("最慢", f"{data['max']:.3f}s")

# 全局实例
async_processor = AsyncDataProcessor()
data_cache = DataCache()
performance_monitor = PerformanceMonitor()

# 便捷装饰器
def async_data_fetch(show_progress=True):
    """异步数据获取装饰器"""
    return async_processor.async_wrapper(show_progress=show_progress)

def cached_data(ttl=300):
    """数据缓存装饰器"""
    cache = DataCache(ttl=ttl)
    return cache.cached_call

def monitor_performance(name):
    """性能监控装饰器"""
    return performance_monitor.timer(name)

# 组合装饰器
def optimized_data_fetch(cache_ttl=300, show_progress=True, monitor_name=None):
    """组合优化装饰器：缓存 + 异步 + 性能监控"""
    def decorator(func):
        # 应用缓存
        cached_func = cached_data(ttl=cache_ttl)(func)
        
        # 应用性能监控
        if monitor_name:
            monitored_func = monitor_performance(monitor_name)(cached_func)
        else:
            monitored_func = cached_func
        
        # 应用异步处理
        async_func = async_data_fetch(show_progress=show_progress)(monitored_func)
        
        return async_func
    
    return decorator
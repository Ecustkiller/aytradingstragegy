"""
优化的数据加载器
集成异步处理、缓存、性能监控等功能
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .async_data_processor import (
    optimized_data_fetch, 
    async_processor, 
    performance_monitor,
    data_cache
)
from .data_loader import (
    get_stock_data_ak, 
    get_stock_data_ashare,
    get_stock_data_tushare,
    get_stock_data_csv,
    has_ashare,
    has_tushare,
    has_csv
)

class OptimizedDataLoader:
    """优化的数据加载器"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.cache_stats = {'hits': 0, 'misses': 0}
        
    @optimized_data_fetch(cache_ttl=1800, show_progress=True, monitor_name="stock_data_fetch")
    def get_stock_data_optimized(self, symbol: str, start, end, period_type: str, data_source: str = "AKShare"):
        """优化的股票数据获取"""
        if data_source == "Ashare" and has_ashare:
            return get_stock_data_ashare(symbol, start, end, period_type)
        elif data_source == "Tushare" and has_tushare:
            return get_stock_data_tushare(symbol, start, end, period_type)
        elif data_source == "本地CSV" and has_csv:
            return get_stock_data_csv(symbol, start, end, period_type)
        else:
            return get_stock_data_ak(symbol, start, end, period_type)
    
    def batch_get_stock_data(self, symbols: List[str], start, end, period_type: str, data_source: str = "AKShare"):
        """批量获取股票数据"""
        if not symbols:
            return {}
        
        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = {}
        completed = 0
        total = len(symbols)
        
        # 使用线程池并行获取
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任务
            future_to_symbol = {
                executor.submit(self.get_stock_data_optimized, symbol, start, end, period_type, data_source): symbol
                for symbol in symbols
            }
            
            # 收集结果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result(timeout=30)
                    results[symbol] = data
                    completed += 1
                    
                    # 更新进度
                    progress = completed / total
                    progress_bar.progress(progress)
                    status_text.text(f"已获取 {completed}/{total} 只股票数据")
                    
                except Exception as e:
                    st.warning(f"获取 {symbol} 数据失败: {e}")
                    results[symbol] = pd.DataFrame()
                    completed += 1
        
        # 清理进度显示
        progress_bar.empty()
        status_text.empty()
        
        return results
    
    @optimized_data_fetch(cache_ttl=3600, show_progress=False, monitor_name="technical_indicators")
    def calculate_technical_indicators_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """批量计算技术指标（优化版）"""
        if df.empty:
            return df
        
        # 使用向量化操作计算指标
        df = df.copy()
        
        # 并行计算不同类型的指标
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                'ma': executor.submit(self._calculate_ma_indicators, df),
                'boll': executor.submit(self._calculate_boll_indicators, df),
                'macd': executor.submit(self._calculate_macd_indicators, df),
                'rsi': executor.submit(self._calculate_rsi_indicators, df)
            }
            
            # 收集结果并合并
            for name, future in futures.items():
                try:
                    result_df = future.result()
                    df = pd.concat([df, result_df], axis=1)
                except Exception as e:
                    st.warning(f"计算{name}指标失败: {e}")
        
        return df
    
    def _calculate_ma_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算移动平均线指标"""
        ma_df = pd.DataFrame(index=df.index)
        periods = [5, 10, 20, 30, 60]
        
        for period in periods:
            ma_df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
        
        return ma_df
    
    def _calculate_boll_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算布林带指标"""
        boll_df = pd.DataFrame(index=df.index)
        
        # 20日移动平均
        ma20 = df['Close'].rolling(window=20).mean()
        # 20日标准差
        std20 = df['Close'].rolling(window=20).std()
        
        boll_df['UPPER'] = ma20 + 2 * std20
        boll_df['LOWER'] = ma20 - 2 * std20
        
        return boll_df
    
    def _calculate_macd_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算MACD指标"""
        macd_df = pd.DataFrame(index=df.index)
        
        # 计算EMA
        ema12 = df['Close'].ewm(span=12).mean()
        ema26 = df['Close'].ewm(span=26).mean()
        
        # MACD线
        macd_df['MACD'] = ema12 - ema26
        # 信号线
        macd_df['SIGNAL'] = macd_df['MACD'].ewm(span=9).mean()
        # 柱状图
        macd_df['HISTOGRAM'] = macd_df['MACD'] - macd_df['SIGNAL']
        
        return macd_df
    
    def _calculate_rsi_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算RSI指标"""
        rsi_df = pd.DataFrame(index=df.index)
        
        # 价格变化
        delta = df['Close'].diff()
        
        # 上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 平均收益和损失
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        # RSI
        rs = avg_gain / avg_loss
        rsi_df['RSI'] = 100 - (100 / (1 + rs))
        
        return rsi_df
    
    def preload_popular_stocks(self, symbols: List[str]):
        """预加载热门股票数据"""
        st.info("🚀 正在预加载热门股票数据...")
        
        # 异步预加载
        def preload_task():
            for symbol in symbols:
                try:
                    # 预加载最近30天的日线数据
                    end_date = pd.Timestamp.now()
                    start_date = end_date - pd.Timedelta(days=30)
                    
                    self.get_stock_data_optimized(
                        symbol, start_date, end_date, 'daily', 'AKShare'
                    )
                except Exception as e:
                    print(f"预加载 {symbol} 失败: {e}")
        
        # 在后台线程中执行预加载
        threading.Thread(target=preload_task, daemon=True).start()
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return {
            'data_cache_stats': data_cache.stats(),
            'performance_stats': performance_monitor.get_stats(),
            'loader_stats': self.cache_stats
        }
    
    def clear_cache(self):
        """清空缓存"""
        data_cache.clear()
        self.cache_stats = {'hits': 0, 'misses': 0}
        st.success("缓存已清空！")

# 全局实例
optimized_loader = OptimizedDataLoader()

# 便捷函数
def get_optimized_stock_data(symbol: str, start, end, period_type: str, data_source: str = "AKShare"):
    """获取优化的股票数据"""
    return optimized_loader.get_stock_data_optimized(symbol, start, end, period_type, data_source)

def batch_get_stocks(symbols: List[str], start, end, period_type: str, data_source: str = "AKShare"):
    """批量获取股票数据"""
    return optimized_loader.batch_get_stock_data(symbols, start, end, period_type, data_source)

def preload_hot_stocks():
    """预加载热门股票"""
    hot_stocks = [
        '600519',  # 贵州茅台
        '000858',  # 五粮液
        '002415',  # 海康威视
        '000001',  # 平安银行
        '600036',  # 招商银行
        '000002',  # 万科A
        '600276',  # 恒瑞医药
        '002594',  # 比亚迪
        '600900',  # 长江电力
        '601318'   # 中国平安
    ]
    
    optimized_loader.preload_popular_stocks(hot_stocks)
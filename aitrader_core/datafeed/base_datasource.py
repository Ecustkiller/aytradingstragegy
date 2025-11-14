#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据源抽象基类
定义统一的数据源接口，所有数据源适配器必须实现此接口
"""

from abc import ABC, abstractmethod
from typing import Optional, List
import pandas as pd
from datetime import datetime
from loguru import logger


class BaseDataSource(ABC):
    """
    数据源抽象基类
    
    所有数据源适配器必须继承此类并实现所有抽象方法
    """
    
    def __init__(self, name: str):
        """
        初始化数据源
        
        Args:
            name: 数据源名称
        """
        self.name = name
        self._is_available = False
        self._initialize()
    
    @abstractmethod
    def _initialize(self) -> bool:
        """
        初始化数据源（子类实现）
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取股票日线数据
        
        Args:
            symbol: 股票代码（统一格式：'600519.SH'）
            start_date: 开始日期（格式：'YYYY-MM-DD' 或 'YYYYMMDD'）
            end_date: 结束日期（格式：'YYYY-MM-DD' 或 'YYYYMMDD'）
            **kwargs: 其他参数
        
        Returns:
            DataFrame: 包含以下标准列的数据
                - date: 日期（datetime类型）
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - symbol: 股票代码
            失败返回None
        """
        pass
    
    @abstractmethod
    def get_index_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取指数日线数据
        
        Args:
            symbol: 指数代码（统一格式：'000001.SH'）
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数
        
        Returns:
            DataFrame: 标准格式数据，失败返回None
        """
        pass
    
    @abstractmethod
    def get_fund_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取基金/ETF日线数据
        
        Args:
            symbol: 基金代码（统一格式：'510300.SH'）
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数
        
        Returns:
            DataFrame: 标准格式数据，失败返回None
        """
        pass
    
    def get_data_auto(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        自动识别类型并获取数据
        
        Args:
            symbol: 证券代码
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数
        
        Returns:
            DataFrame: 标准格式数据，失败返回None
        """
        # 根据代码判断类型
        data_type = self._detect_symbol_type(symbol)
        
        try:
            if data_type == 'index':
                return self.get_index_data(symbol, start_date, end_date, **kwargs)
            elif data_type == 'fund':
                return self.get_fund_data(symbol, start_date, end_date, **kwargs)
            else:
                return self.get_stock_data(symbol, start_date, end_date, **kwargs)
        except Exception as e:
            logger.error(f"[{self.name}] 获取数据失败: {e}")
            return None
    
    def get_multiple_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        **kwargs
    ) -> pd.DataFrame:
        """
        批量获取多个证券的数据
        
        Args:
            symbols: 证券代码列表
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数
        
        Returns:
            DataFrame: 合并后的数据，包含所有证券
        """
        dfs = []
        
        for symbol in symbols:
            df = self.get_data_auto(symbol, start_date, end_date, **kwargs)
            if df is not None and not df.empty:
                dfs.append(df)
            else:
                logger.warning(f"[{self.name}] 未获取到 {symbol} 的数据")
        
        if not dfs:
            logger.warning(f"[{self.name}] 未获取到任何数据")
            return pd.DataFrame()
        
        # 合并所有数据
        result = pd.concat(dfs, axis=0, ignore_index=True)
        result.sort_values(by='date', ascending=True, inplace=True)
        
        return result
    
    @staticmethod
    def _detect_symbol_type(symbol: str) -> str:
        """
        检测证券类型
        
        Args:
            symbol: 证券代码
        
        Returns:
            str: 'stock', 'index', 'fund'
        """
        code = symbol.split('.')[0]
        
        # 指数判断
        if code.startswith('000') or code.startswith('399') or code.startswith('880'):
            return 'index'
        
        # ETF/基金判断
        if code.startswith('51') or code.startswith('15') or code.startswith('16'):
            return 'fund'
        
        # 默认为股票
        return 'stock'
    
    @staticmethod
    def normalize_date(date_str: str, output_format: str = '%Y%m%d') -> str:
        """
        标准化日期格式
        
        Args:
            date_str: 输入日期字符串（支持多种格式）
            output_format: 输出格式（默认：'%Y%m%d'）
        
        Returns:
            str: 标准化后的日期字符串
        """
        if not date_str:
            return datetime.now().strftime(output_format)
        
        # 尝试多种日期格式
        formats = ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime(output_format)
            except ValueError:
                continue
        
        # 如果都失败，返回原字符串
        logger.warning(f"无法解析日期格式: {date_str}")
        return date_str
    
    @staticmethod
    def standardize_dataframe(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        标准化DataFrame格式
        
        Args:
            df: 原始DataFrame
            symbol: 证券代码
        
        Returns:
            DataFrame: 标准化后的DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 确保包含必要的列
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"缺少必要列: {col}")
                return pd.DataFrame()
        
        # 确保date是datetime类型
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])
        
        # 添加symbol列
        if 'symbol' not in df.columns:
            df['symbol'] = symbol
        
        # 选择标准列
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        # 排序
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def is_available(self) -> bool:
        """
        检查数据源是否可用
        
        Returns:
            bool: 数据源是否可用
        """
        return self._is_available
    
    def __str__(self) -> str:
        """字符串表示"""
        status = "✅ 可用" if self._is_available else "❌ 不可用"
        return f"{self.name} 数据源 [{status}]"
    
    def __repr__(self) -> str:
        """对象表示"""
        return f"<{self.__class__.__name__}(name='{self.name}', available={self._is_available})>"

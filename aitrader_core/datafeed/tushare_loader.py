#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tushare数据加载器
提供基于Tushare专业版的数据获取功能
"""

import pandas as pd
import tushare as ts
from loguru import logger
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from aitrader_core.datafeed.base_datasource import BaseDataSource

# 延迟获取Token，避免在导入时抛出异常
def _get_tushare_token():
    """获取Tushare Token（延迟检查，不抛出异常）"""
    try:
        from modules.config_manager import Config
        # 使用raise_on_missing=False，避免抛出异常
        return Config.get_tushare_token(raise_on_missing=False)
    except ImportError:
        # 如果配置模块不可用，尝试从环境变量获取
        import os
        return os.getenv('TUSHARE_TOKEN')

TUSHARE_TOKEN = None  # 延迟初始化


class TushareDataSource(BaseDataSource):
    """Tushare数据源适配器"""
    
    def __init__(self):
        self.pro = None
        super().__init__(name="Tushare")
    
    def _initialize(self) -> bool:
        """初始化Tushare API"""
        try:
            # 延迟获取Token
            global TUSHARE_TOKEN
            if TUSHARE_TOKEN is None:
                TUSHARE_TOKEN = _get_tushare_token()
            
            if TUSHARE_TOKEN:
                ts.set_token(TUSHARE_TOKEN)
                self.pro = ts.pro_api()
                self._is_available = True
                logger.info("✅ Tushare API初始化成功")
                return True
            else:
                self._is_available = False
                logger.warning("⚠️ Tushare Token未配置，Tushare数据源不可用")
                return False
        except Exception as e:
            self._is_available = False
            logger.error(f"❌ Tushare API初始化失败: {e}")
            return False


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
            symbol: 股票代码 (如 '600519.SH')
            start_date: 开始日期 (格式: 'YYYY-MM-DD' 或 'YYYYMMDD')
            end_date: 结束日期
        
        Returns:
            DataFrame: 标准格式数据
        """
        if not self._is_available:
            logger.error("[Tushare] API未初始化")
            return None
        
        try:
            # 标准化日期格式
            start_date = self.normalize_date(start_date, '%Y%m%d')
            end_date = self.normalize_date(end_date, '%Y%m%d')
            
            # 获取日线数据
            df = self.pro.daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or len(df) == 0:
                logger.warning(f"[Tushare] 未获取到 {symbol} 的数据")
                return None
            
            # 重命名列以匹配项目标准格式
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            
            # 标准化DataFrame
            df = self.standardize_dataframe(df, symbol)
            
            logger.info(f"[Tushare] ✅ 成功获取 {symbol} 数据: {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"[Tushare] 获取 {symbol} 数据失败: {e}")
            return None


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
            symbol: 指数代码 (如 '000001.SH')
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 标准格式数据
        """
        if not self._is_available:
            logger.error("[Tushare] API未初始化")
            return None
        
        try:
            # 标准化日期格式
            start_date = self.normalize_date(start_date, '%Y%m%d')
            end_date = self.normalize_date(end_date, '%Y%m%d')
            
            # 获取指数日线数据
            df = self.pro.index_daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or len(df) == 0:
                logger.warning(f"[Tushare] 未获取到指数 {symbol} 的数据")
                return None
            
            # 重命名和处理
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            
            # 标准化DataFrame
            df = self.standardize_dataframe(df, symbol)
            
            logger.info(f"[Tushare] ✅ 成功获取指数 {symbol} 数据: {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"[Tushare] 获取指数 {symbol} 数据失败: {e}")
            return None


    def get_fund_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取ETF基金日线数据
        
        Args:
            symbol: 基金代码 (如 '518880.SH')
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 标准格式数据
        """
        if not self._is_available:
            logger.error("[Tushare] API未初始化")
            return None
        
        try:
            # 标准化日期格式
            start_date = self.normalize_date(start_date, '%Y%m%d')
            end_date = self.normalize_date(end_date, '%Y%m%d')
            
            # 获取基金日线数据
            df = self.pro.fund_daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or len(df) == 0:
                logger.warning(f"[Tushare] 未获取到基金 {symbol} 的数据")
                return None
            
            # 重命名和处理
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            
            # 标准化DataFrame
            df = self.standardize_dataframe(df, symbol)
            
            logger.info(f"[Tushare] ✅ 成功获取基金 {symbol} 数据: {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"[Tushare] 获取基金 {symbol} 数据失败: {e}")
            return None




# ==================== 向后兼容的全局实例和函数 ====================

# 创建全局实例
_tushare_instance = TushareDataSource()

# 向后兼容的函数
def get_stock_data(symbol, start_date='20150101', end_date='20231231'):
    """向后兼容的函数"""
    return _tushare_instance.get_stock_data(symbol, start_date, end_date)

def get_index_data(symbol, start_date='20150101', end_date='20231231'):
    """向后兼容的函数"""
    return _tushare_instance.get_index_data(symbol, start_date, end_date)

def get_fund_data(symbol, start_date='20150101', end_date='20231231'):
    """向后兼容的函数"""
    return _tushare_instance.get_fund_data(symbol, start_date, end_date)

def get_data_auto(symbol, start_date='20150101', end_date='20231231'):
    """向后兼容的函数"""
    return _tushare_instance.get_data_auto(symbol, start_date, end_date)

# 向后兼容的pro对象
pro = _tushare_instance.pro if _tushare_instance._is_available else None


if __name__ == "__main__":
    # 测试
    print("测试Tushare数据加载器...")
    print(f"数据源状态: {_tushare_instance}")
    
    if _tushare_instance.is_available():
        # 测试ETF
        df = get_data_auto('518880.SH', start_date='20200101', end_date='20231231')
        if df is not None:
            print(f"\n✅ 黄金ETF数据:")
            print(df.head())
            print(f"共 {len(df)} 条记录")
        
        # 测试股票
        df = get_data_auto('600519.SH', start_date='20200101', end_date='20231231')
        if df is not None:
            print(f"\n✅ 贵州茅台数据:")
            print(df.head())
            print(f"共 {len(df)} 条记录")
    else:
        print("❌ Tushare数据源不可用，请检查Token配置")


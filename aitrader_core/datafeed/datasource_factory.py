#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据源工厂
统一管理所有数据源，提供简单的接口获取数据
"""

from typing import Optional, Dict, List
import pandas as pd
from loguru import logger
from enum import Enum


class DataSourceType(Enum):
    """数据源类型枚举"""
    TUSHARE = "Tushare"
    AKSHARE = "AKShare"
    CSV = "CSV"
    ASHARE = "Ashare"


class DataSourceFactory:
    """
    数据源工厂类
    
    负责创建和管理所有数据源实例，提供统一的数据获取接口
    """
    
    _instances: Dict[str, any] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """初始化所有数据源"""
        if cls._initialized:
            return
        
        logger.info("🔧 初始化数据源工厂...")
        
        # 初始化Tushare
        try:
            from aitrader_core.datafeed.tushare_loader import TushareDataSource
            cls._instances[DataSourceType.TUSHARE.value] = TushareDataSource()
            logger.info(f"  {cls._instances[DataSourceType.TUSHARE.value]}")
        except Exception as e:
            logger.warning(f"  ⚠️ Tushare数据源初始化失败: {e}")
        
        # 初始化AKShare
        try:
            from aitrader_core.datafeed.akshare_loader import get_stock_data
            # AKShare暂时使用旧接口，后续重构
            cls._instances[DataSourceType.AKSHARE.value] = "legacy"
            logger.info(f"  ✅ AKShare 数据源 [可用]")
        except Exception as e:
            logger.warning(f"  ⚠️ AKShare数据源初始化失败: {e}")
        
        # 初始化CSV
        try:
            from aitrader_core.datafeed.csv_dataloader import CsvDataLoader
            cls._instances[DataSourceType.CSV.value] = CsvDataLoader()
            logger.info(f"  ✅ CSV 数据源 [可用]")
        except Exception as e:
            logger.warning(f"  ⚠️ CSV数据源初始化失败: {e}")
        
        # 初始化Ashare
        try:
            from aitrader_core.datafeed.Ashare import get_price
            cls._instances[DataSourceType.ASHARE.value] = "legacy"
            logger.info(f"  ✅ Ashare 数据源 [可用]")
        except Exception as e:
            logger.warning(f"  ⚠️ Ashare数据源初始化失败: {e}")
        
        cls._initialized = True
        logger.info("✅ 数据源工厂初始化完成\n")
    
    @classmethod
    def get_datasource(cls, source_type: str):
        """
        获取指定类型的数据源实例
        
        Args:
            source_type: 数据源类型 ('Tushare', 'AKShare', 'CSV', 'Ashare')
        
        Returns:
            数据源实例，如果不存在返回None
        """
        if not cls._initialized:
            cls.initialize()
        
        return cls._instances.get(source_type)
    
    @classmethod
    def get_data(
        cls,
        symbols: List[str],
        start_date: str,
        end_date: str,
        source_type: str = "Tushare",
        **kwargs
    ) -> pd.DataFrame:
        """
        统一的数据获取接口
        
        Args:
            symbols: 证券代码列表
            start_date: 开始日期
            end_date: 结束日期
            source_type: 数据源类型
            **kwargs: 其他参数
        
        Returns:
            DataFrame: 标准格式的数据
        """
        if not cls._initialized:
            cls.initialize()
        
        logger.info(f"📊 使用 {source_type} 数据源获取数据...")
        
        # Tushare数据源
        if source_type == DataSourceType.TUSHARE.value:
            datasource = cls._instances.get(DataSourceType.TUSHARE.value)
            if datasource and hasattr(datasource, 'get_multiple_data'):
                return datasource.get_multiple_data(symbols, start_date, end_date, **kwargs)
            else:
                logger.error("Tushare数据源不可用")
                return pd.DataFrame()
        
        # CSV数据源
        elif source_type == DataSourceType.CSV.value:
            datasource = cls._instances.get(DataSourceType.CSV.value)
            if datasource:
                path = kwargs.get('path', 'quotes')
                return datasource.read_df(symbols, start_date, end_date, path=path)
            else:
                logger.error("CSV数据源不可用")
                return pd.DataFrame()
        
        # AKShare数据源（使用旧接口）
        elif source_type == DataSourceType.AKSHARE.value:
            if DataSourceType.AKSHARE.value in cls._instances:
                from aitrader_core.datafeed.akshare_loader import get_data_auto
                dfs = []
                for symbol in symbols:
                    df = get_data_auto(symbol, start_date, end_date)
                    if df is not None and not df.empty:
                        dfs.append(df)
                
                if dfs:
                    result = pd.concat(dfs, axis=0, ignore_index=True)
                    result.sort_values(by='date', ascending=True, inplace=True)
                    return result
                return pd.DataFrame()
            else:
                logger.error("AKShare数据源不可用")
                return pd.DataFrame()
        
        # Ashare数据源（使用旧接口）
        elif source_type == DataSourceType.ASHARE.value:
            if DataSourceType.ASHARE.value in cls._instances:
                from aitrader_core.datafeed.Ashare import get_price
                import pandas as pd
                from datetime import datetime
                
                dfs = []
                for symbol in symbols:
                    try:
                        # 计算需要的数据条数（粗略估算）
                        days = (datetime.strptime(end_date[:10], '%Y-%m-%d') - 
                               datetime.strptime(start_date[:10], '%Y-%m-%d')).days
                        count = max(int(days * 0.7), 100)  # 考虑非交易日
                        
                        df = get_price(symbol, end_date=end_date, count=count, frequency='1d')
                        if df is not None and not df.empty:
                            # 转换为标准格式
                            df = df.reset_index()
                            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume']
                            df['symbol'] = symbol
                            df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
                            
                            # 过滤日期范围
                            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                            dfs.append(df)
                    except Exception as e:
                        logger.warning(f"获取 {symbol} 数据失败: {e}")
                        continue
                
                if dfs:
                    result = pd.concat(dfs, axis=0, ignore_index=True)
                    result.sort_values(by='date', ascending=True, inplace=True)
                    return result
                return pd.DataFrame()
            else:
                logger.error("Ashare数据源不可用")
                return pd.DataFrame()
        
        else:
            logger.error(f"不支持的数据源类型: {source_type}")
            return pd.DataFrame()
    
    @classmethod
    def list_available_sources(cls) -> List[str]:
        """
        列出所有可用的数据源
        
        Returns:
            List[str]: 可用数据源名称列表
        """
        if not cls._initialized:
            cls.initialize()
        
        available = []
        for source_type, instance in cls._instances.items():
            if instance is not None:
                # 检查是否真正可用
                if hasattr(instance, 'is_available'):
                    if instance.is_available():
                        available.append(source_type)
                else:
                    # 旧接口默认可用
                    available.append(source_type)
        
        return available
    
    @classmethod
    def get_source_info(cls) -> Dict[str, dict]:
        """
        获取所有数据源的详细信息
        
        Returns:
            Dict: 数据源信息字典
        """
        if not cls._initialized:
            cls.initialize()
        
        info = {}
        for source_type, instance in cls._instances.items():
            if hasattr(instance, 'is_available'):
                info[source_type] = {
                    'available': instance.is_available(),
                    'name': instance.name if hasattr(instance, 'name') else source_type,
                    'type': 'new_api'
                }
            elif instance == "legacy":
                info[source_type] = {
                    'available': True,
                    'name': source_type,
                    'type': 'legacy_api'
                }
            else:
                info[source_type] = {
                    'available': instance is not None,
                    'name': source_type,
                    'type': 'unknown'
                }
        
        return info


# 自动初始化
DataSourceFactory.initialize()


if __name__ == "__main__":
    print("=" * 60)
    print("数据源工厂测试")
    print("=" * 60)
    
    # 列出可用数据源
    print("\n可用数据源:")
    for source in DataSourceFactory.list_available_sources():
        print(f"  ✅ {source}")
    
    # 获取详细信息
    print("\n数据源详细信息:")
    for name, info in DataSourceFactory.get_source_info().items():
        status = "✅" if info['available'] else "❌"
        print(f"  {status} {name}: {info['type']}")
    
    # 测试获取数据
    print("\n测试获取数据...")
    df = DataSourceFactory.get_data(
        symbols=['600519.SH'],
        start_date='2023-01-01',
        end_date='2023-12-31',
        source_type='Tushare'
    )
    
    if not df.empty:
        print(f"✅ 成功获取数据: {len(df)} 条记录")
        print(df.head())
    else:
        print("❌ 获取数据失败")
    
    print("\n" + "=" * 60)

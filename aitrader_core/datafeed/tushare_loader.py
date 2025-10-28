#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tushare数据加载器
提供基于Tushare专业版的数据获取功能
"""

import pandas as pd
import tushare as ts
from loguru import logger

# Tushare Token配置
TUSHARE_TOKEN = "ad56243b601d82fd5c4aaf04b72d4d9d567401898d46c20f4d905d59"

# 初始化Tushare
try:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    logger.info("✅ Tushare API初始化成功")
except Exception as e:
    logger.error(f"❌ Tushare API初始化失败: {e}")
    pro = None


def convert_code(symbol):
    """
    转换股票代码格式
    从 '600519.SH' 转为 '600519.SH' (Tushare格式相同)
    """
    return symbol


def get_stock_data(symbol, start_date='20150101', end_date='20231231'):
    """
    获取股票日线数据
    
    参数:
        symbol: 股票代码 (如 '600519.SH')
        start_date: 开始日期 (格式: '20150101')
        end_date: 结束日期
    
    返回:
        DataFrame: 包含date, open, high, low, close, volume等字段
    """
    if pro is None:
        logger.error("Tushare API未初始化")
        return None
    
    try:
        ts_code = convert_code(symbol)
        
        # 获取日线数据
        df = pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or len(df) == 0:
            logger.warning(f"未获取到 {symbol} 的数据")
            return None
        
        # 重命名列以匹配项目标准格式
        df = df.rename(columns={
            'trade_date': 'date',
            'vol': 'volume'
        })
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        # 排序
        df = df.sort_values('date').reset_index(drop=True)
        
        # 添加symbol列
        df['symbol'] = symbol
        
        # 选择需要的列
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        logger.info(f"✅ 成功获取 {symbol} 数据: {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"获取 {symbol} 数据失败: {e}")
        return None


def get_index_data(symbol, start_date='20150101', end_date='20231231'):
    """
    获取指数日线数据
    
    参数:
        symbol: 指数代码 (如 '510300.SH')
        start_date: 开始日期
        end_date: 结束日期
    
    返回:
        DataFrame
    """
    if pro is None:
        logger.error("Tushare API未初始化")
        return None
    
    try:
        ts_code = convert_code(symbol)
        
        # 获取指数日线数据
        df = pro.index_daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or len(df) == 0:
            logger.warning(f"未获取到指数 {symbol} 的数据")
            return None
        
        # 重命名和处理
        df = df.rename(columns={
            'trade_date': 'date',
            'vol': 'volume'
        })
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        df['symbol'] = symbol
        
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        logger.info(f"✅ 成功获取指数 {symbol} 数据: {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"获取指数 {symbol} 数据失败: {e}")
        return None


def get_fund_data(symbol, start_date='20150101', end_date='20231231'):
    """
    获取ETF基金日线数据
    
    参数:
        symbol: 基金代码 (如 '518880.SH')
        start_date: 开始日期
        end_date: 结束日期
    
    返回:
        DataFrame
    """
    if pro is None:
        logger.error("Tushare API未初始化")
        return None
    
    try:
        ts_code = convert_code(symbol)
        
        # 获取基金日线数据
        df = pro.fund_daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or len(df) == 0:
            logger.warning(f"未获取到基金 {symbol} 的数据")
            return None
        
        # 重命名和处理
        df = df.rename(columns={
            'trade_date': 'date',
            'vol': 'volume'
        })
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        df['symbol'] = symbol
        
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        logger.info(f"✅ 成功获取基金 {symbol} 数据: {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"获取基金 {symbol} 数据失败: {e}")
        return None


def get_data_auto(symbol, start_date='20150101', end_date='20231231'):
    """
    自动识别类型并获取数据
    优先尝试: ETF基金 -> 股票 -> 指数
    
    参数:
        symbol: 代码
        start_date: 开始日期
        end_date: 结束日期
    
    返回:
        DataFrame
    """
    # 1. 尝试ETF基金
    df = get_fund_data(symbol, start_date, end_date)
    if df is not None and len(df) > 0:
        return df
    
    # 2. 尝试股票
    df = get_stock_data(symbol, start_date, end_date)
    if df is not None and len(df) > 0:
        return df
    
    # 3. 尝试指数
    df = get_index_data(symbol, start_date, end_date)
    if df is not None and len(df) > 0:
        return df
    
    logger.error(f"无法获取 {symbol} 的数据 (尝试了基金/股票/指数)")
    return None


if __name__ == "__main__":
    # 测试
    print("测试Tushare数据加载器...")
    
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


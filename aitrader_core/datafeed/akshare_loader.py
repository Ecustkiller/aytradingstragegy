#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AKShare数据加载器
提供基于AKShare的在线数据获取功能
"""

import pandas as pd
import akshare as ak
from loguru import logger


def convert_code_for_akshare(symbol):
    """
    转换股票代码为AKShare格式
    '600519.SH' -> 'sh600519'
    '000001.SZ' -> 'sz000001'
    """
    if '.' not in symbol:
        return symbol
    
    code, exchange = symbol.split('.')
    if exchange.upper() == 'SH':
        return f'sh{code}'
    elif exchange.upper() == 'SZ':
        return f'sz{code}'
    else:
        return symbol


def get_stock_data(symbol, start_date='2015-01-01', end_date='2023-12-31'):
    """
    获取A股日线数据
    
    参数:
        symbol: 股票代码 (如 '600519.SH')
        start_date: 开始日期 (格式: '2015-01-01')
        end_date: 结束日期
    
    返回:
        DataFrame
    """
    try:
        # 转换代码格式
        ak_code = convert_code_for_akshare(symbol)
        
        # 获取日线数据
        df = ak.stock_zh_a_hist(
            symbol=ak_code,
            period="daily",
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust="qfq"  # 前复权
        )
        
        if df is None or len(df) == 0:
            logger.warning(f"未获取到 {symbol} 的数据")
            return None
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        })
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 添加symbol列
        df['symbol'] = symbol
        
        # 选择需要的列
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        # 排序
        df = df.sort_values('date').reset_index(drop=True)
        
        logger.info(f"✅ 成功获取 {symbol} 数据: {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"获取 {symbol} 数据失败: {e}")
        return None


def get_fund_data(symbol, start_date='2015-01-01', end_date='2023-12-31'):
    """
    获取ETF基金日线数据
    
    参数:
        symbol: 基金代码 (如 '518880.SH')
        start_date: 开始日期
        end_date: 结束日期
    
    返回:
        DataFrame
    """
    try:
        # ETF代码格式处理
        code = symbol.split('.')[0]
        
        # 使用AKShare的ETF数据接口
        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust="qfq"
        )
        
        if df is None or len(df) == 0:
            logger.warning(f"未获取到基金 {symbol} 的数据")
            return None
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        })
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        
        # 添加symbol列
        df['symbol'] = symbol
        
        # 选择需要的列
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        # 排序
        df = df.sort_values('date').reset_index(drop=True)
        
        logger.info(f"✅ 成功获取基金 {symbol} 数据: {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"获取基金 {symbol} 数据失败: {e}")
        return None


def get_index_data(symbol, start_date='2015-01-01', end_date='2023-12-31'):
    """
    获取指数日线数据
    
    参数:
        symbol: 指数代码 (如 '510300.SH')
        start_date: 开始日期
        end_date: 结束日期
    
    返回:
        DataFrame
    """
    try:
        # 指数代码映射
        index_map = {
            '000001.SH': '上证指数',
            '399001.SZ': '深证成指',
            '399006.SZ': '创业板指',
            '000300.SH': '沪深300',
            '000905.SH': '中证500',
        }
        
        index_name = index_map.get(symbol, '上证指数')
        
        # 获取指数数据
        df = ak.stock_zh_index_daily(symbol=index_name)
        
        if df is None or len(df) == 0:
            logger.warning(f"未获取到指数 {symbol} 的数据")
            return None
        
        # 日期过滤
        df['date'] = pd.to_datetime(df['date'])
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        df = df[(df['date'] >= start) & (df['date'] <= end)]
        
        # 添加symbol列
        df['symbol'] = symbol
        
        # 选择需要的列
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        logger.info(f"✅ 成功获取指数 {symbol} 数据: {len(df)} 条记录")
        return df
        
    except Exception as e:
        logger.error(f"获取指数 {symbol} 数据失败: {e}")
        return None


def get_data_auto(symbol, start_date='2015-01-01', end_date='2023-12-31'):
    """
    自动识别类型并获取数据
    优先尝试: ETF基金 -> 股票 -> 指数
    
    参数:
        symbol: 代码
        start_date: 开始日期 (格式: '2015-01-01')
        end_date: 结束日期
    
    返回:
        DataFrame
    """
    # 1. 判断是否为ETF (5开头或1开头)
    code = symbol.split('.')[0]
    if code.startswith('5') or code.startswith('1'):
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
    print("测试AKShare数据加载器...")
    
    # 测试ETF
    df = get_data_auto('518880.SH', start_date='2020-01-01', end_date='2023-12-31')
    if df is not None:
        print(f"\n✅ 黄金ETF数据:")
        print(df.head())
        print(f"共 {len(df)} 条记录")
    
    # 测试股票
    df = get_data_auto('600519.SH', start_date='2020-01-01', end_date='2023-12-31')
    if df is not None:
        print(f"\n✅ 贵州茅台数据:")
        print(df.head())
        print(f"共 {len(df)} 条记录")


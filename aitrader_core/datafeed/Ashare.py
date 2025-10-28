#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ashare 股票行情数据双核心版
来源：https://github.com/mpquant/Ashare

支持获取A股实时行情数据：
- 日线、周线、月线
- 分钟线（1m, 5m, 15m, 30m, 60m）
- 支持多种证券代码格式（通达信、同花顺、聚宽）
"""

import json
import requests
import datetime
import pandas as pd


# ==================== 腾讯接口 ====================

def get_price_day_tx(code, end_date='', count=10, frequency='1d'):
    """腾讯日线获取"""
    unit = 'week' if frequency in '1w' else 'month' if frequency in '1M' else 'day'
    
    if end_date:
        end_date = end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime.date) else end_date.split(' ')[0]
    end_date = '' if end_date == datetime.datetime.now().strftime('%Y-%m-%d') else end_date
    
    URL = f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{unit},,{end_date},{count},qfq'
    st = json.loads(requests.get(URL).content)
    ms = 'qfq' + unit
    stk = st['data'][code]
    buf = stk[ms] if ms in stk else stk[unit]
    
    df = pd.DataFrame(buf, columns=['time', 'open', 'close', 'high', 'low', 'volume'], dtype='float')
    df.time = pd.to_datetime(df.time)
    df.set_index(['time'], inplace=True)
    df.index.name = ''
    
    return df


def get_price_min_tx(code, end_date=None, count=10, frequency='1d'):
    """腾讯分钟线获取"""
    ts = int(frequency[:-1]) if frequency[:-1].isdigit() else 1
    
    if end_date:
        end_date = end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime.date) else end_date.split(' ')[0]
    
    URL = f'http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code},m{ts},,{count}'
    st = json.loads(requests.get(URL).content)
    buf = st['data'][code]['m' + str(ts)]
    
    df = pd.DataFrame(buf, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'n1', 'n2'])
    df = df[['time', 'open', 'close', 'high', 'low', 'volume']]
    df[['open', 'close', 'high', 'low', 'volume']] = df[['open', 'close', 'high', 'low', 'volume']].astype('float')
    df.time = pd.to_datetime(df.time)
    df.set_index(['time'], inplace=True)
    df.index.name = ''
    
    # 修复：只在有实时数据时更新最后一行
    try:
        if 'qt' in st['data'][code] and code in st['data'][code]['qt']:
            df.loc[df.index[-1], 'close'] = float(st['data'][code]['qt'][code][3])
    except:
        pass
    
    return df


# ==================== 新浪接口 ====================

def get_price_sina(code, end_date='', count=10, frequency='60m'):
    """新浪全周期获取函数，分钟线 5m,15m,30m,60m  日线1d=240m   周线1w=1200m  1月=7200m"""
    frequency = frequency.replace('1d', '240m').replace('1w', '1200m').replace('1M', '7200m')
    mcount = count
    ts = int(frequency[:-1]) if frequency[:-1].isdigit() else 1
    
    if (end_date != '') & (frequency in ['240m', '1200m', '7200m']):
        end_date = pd.to_datetime(end_date) if not isinstance(end_date, datetime.date) else end_date
        unit = 4 if frequency == '1200m' else 29 if frequency == '7200m' else 1
        count = count + (datetime.datetime.now() - end_date).days // unit
    
    URL = f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale={ts}&ma=5&datalen={count}'
    dstr = json.loads(requests.get(URL).content)
    
    df = pd.DataFrame(dstr, columns=['day', 'open', 'high', 'low', 'close', 'volume'])
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df.day = pd.to_datetime(df.day)
    df.set_index(['day'], inplace=True)
    df.index.name = ''
    
    if (end_date != '') & (frequency in ['240m', '1200m', '7200m']):
        return df[df.index <= end_date][-mcount:]
    
    return df


# ==================== 统一接口 ====================

def get_price(code, end_date='', count=10, frequency='1d', fields=[]):
    """
    统一的获取行情数据接口
    
    参数：
        code: 证券代码，支持多种格式
              - 通达信格式：sh000001, sz399006, sh600519
              - 聚宽格式：000001.XSHG, 399006.XSHE, 600519.XSHG
        end_date: 结束日期，格式'YYYY-MM-DD'或datetime对象
        count: 获取数据条数
        frequency: 周期
                  - 日线周期：'1d'(日), '1w'(周), '1M'(月)
                  - 分钟周期：'1m', '5m', '15m', '30m', '60m'
        fields: 字段列表（暂未使用，保留兼容）
    
    返回：
        DataFrame，包含 open, high, low, close, volume
    """
    # 证券代码编码兼容处理
    xcode = code.replace('.XSHG', '').replace('.XSHE', '')
    xcode = 'sh' + xcode if ('XSHG' in code) else 'sz' + xcode if ('XSHE' in code) else code
    
    # 日线、周线、月线
    if frequency in ['1d', '1w', '1M']:
        try:
            return get_price_sina(xcode, end_date=end_date, count=count, frequency=frequency)
        except:
            return get_price_day_tx(xcode, end_date=end_date, count=count, frequency=frequency)
    
    # 分钟线
    if frequency in ['1m', '5m', '15m', '30m', '60m']:
        if frequency in '1m':
            return get_price_min_tx(xcode, end_date=end_date, count=count, frequency=frequency)
        try:
            return get_price_sina(xcode, end_date=end_date, count=count, frequency=frequency)
        except:
            return get_price_min_tx(xcode, end_date=end_date, count=count, frequency=frequency)
    
    raise ValueError(f"不支持的周期: {frequency}")


# ==================== 测试代码 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("Ashare 数据接口测试")
    print("=" * 60)
    
    # 测试1：上证指数日线
    print("\n【测试1】上证指数日线行情（最近10天）")
    df = get_price('sh000001', frequency='1d', count=10)
    print(df)
    
    # 测试2：上证指数分钟线
    print("\n【测试2】上证指数15分钟线（最近10条）")
    df = get_price('000001.XSHG', frequency='15m', count=10)
    print(df)
    
    # 测试3：贵州茅台历史数据
    print("\n【测试3】贵州茅台历史周线（2018年）")
    df = get_price('600519.XSHG', frequency='1w', count=5, end_date='2018-06-15')
    print(df)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


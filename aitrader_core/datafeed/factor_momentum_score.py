#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于年化收益和R²的动量评分因子
来源：聚宽社区 https://www.joinquant.com/post/26142

评分公式：
  score = 年化收益率 × R²
  
其中：
  - 年化收益率 = (e^斜率)^250 - 1
  - R² = 判定系数，衡量线性拟合的优度
  - 斜率通过对数收益率的线性回归得到
"""

import numpy as np
import pandas as pd
import math


def momentum_score(close, period=25):
    """
    计算基于年化收益和R²的动量评分
    
    参数:
        close: Series，收盘价序列
        period: int，回看周期（默认25天）
    
    返回:
        Series，动量评分
    """
    scores = []
    
    for i in range(len(close)):
        if i < period - 1:
            scores.append(np.nan)
            continue
        
        # 获取最近period天的数据
        recent_close = close.iloc[i - period + 1:i + 1]
        
        try:
            # 计算对数收益
            log_close = np.log(recent_close.values)
            
            # 创建x轴（时间序列）
            x = np.arange(len(log_close))
            y = log_close
            
            # 线性回归
            slope, intercept = np.polyfit(x, y, 1)
            
            # 计算年化收益率
            annualized_returns = math.pow(math.exp(slope), 250) - 1
            
            # 计算R²（判定系数）
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)  # 残差平方和
            ss_tot = np.sum((y - np.mean(y)) ** 2)  # 总平方和
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # 评分 = 年化收益率 × R²
            score = annualized_returns * r_squared
            scores.append(score)
            
        except Exception as e:
            scores.append(np.nan)
    
    return pd.Series(scores, index=close.index)


def annualized_return(close, period=25):
    """
    计算年化收益率
    
    参数:
        close: Series，收盘价序列
        period: int，回看周期
    
    返回:
        Series，年化收益率
    """
    returns = []
    
    for i in range(len(close)):
        if i < period - 1:
            returns.append(np.nan)
            continue
        
        recent_close = close.iloc[i - period + 1:i + 1]
        
        try:
            log_close = np.log(recent_close.values)
            x = np.arange(len(log_close))
            slope, _ = np.polyfit(x, log_close, 1)
            ann_ret = math.pow(math.exp(slope), 250) - 1
            returns.append(ann_ret)
        except:
            returns.append(np.nan)
    
    return pd.Series(returns, index=close.index)


def r_squared(close, period=25):
    """
    计算R²判定系数
    
    参数:
        close: Series，收盘价序列
        period: int，回看周期
    
    返回:
        Series，R²值
    """
    r2_values = []
    
    for i in range(len(close)):
        if i < period - 1:
            r2_values.append(np.nan)
            continue
        
        recent_close = close.iloc[i - period + 1:i + 1]
        
        try:
            log_close = np.log(recent_close.values)
            x = np.arange(len(log_close))
            y = log_close
            slope, intercept = np.polyfit(x, y, 1)
            
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            r2_values.append(r2)
        except:
            r2_values.append(np.nan)
    
    return pd.Series(r2_values, index=close.index)


if __name__ == '__main__':
    # 测试代码
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from datafeed.csv_dataloader import CsvDataLoader
    
    # 加载数据
    dfs = CsvDataLoader().read_dfs(symbols=['159915.SZ'])
    df = dfs['159915.SZ']
    df.set_index('date', inplace=True)
    
    # 计算因子
    df['momentum_score'] = momentum_score(df['close'], period=25)
    df['ann_return'] = annualized_return(df['close'], period=25)
    df['r2'] = r_squared(df['close'], period=25)
    
    print("动量评分因子测试：")
    print(df[['close', 'momentum_score', 'ann_return', 'r2']].tail(10))
    print(f"\n最新评分: {df['momentum_score'].iloc[-1]:.4f}")
    print(f"最新年化收益: {df['ann_return'].iloc[-1]:.2%}")
    print(f"最新R²: {df['r2'].iloc[-1]:.4f}")


"""
Z哥战法选股器
集成5个核心策略：少妇战法、SuperB1战法、补票战法、填坑战法、上穿60放量战法
"""
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List, Optional, Tuple
import streamlit as st

# ======================== 通用指标计算 ========================

def compute_kdj(df: pd.DataFrame, n: int = 9) -> pd.DataFrame:
    """计算KDJ指标"""
    if df.empty:
        return df.assign(K=np.nan, D=np.nan, J=np.nan)

    low_n = df["Low"].rolling(window=n, min_periods=1).min()
    high_n = df["High"].rolling(window=n, min_periods=1).max()
    rsv = (df["Close"] - low_n) / (high_n - low_n + 1e-9) * 100

    K = np.zeros_like(rsv, dtype=float)
    D = np.zeros_like(rsv, dtype=float)
    for i in range(len(df)):
        if i == 0:
            K[i] = D[i] = 50.0
        else:
            K[i] = 2 / 3 * K[i - 1] + 1 / 3 * rsv.iloc[i]
            D[i] = 2 / 3 * D[i - 1] + 1 / 3 * K[i]
    J = 3 * K - 2 * D
    return df.assign(K=K, D=D, J=J)


def compute_bbi(df: pd.DataFrame) -> pd.Series:
    """计算BBI指标（多空指标）"""
    ma3 = df["Close"].rolling(3).mean()
    ma6 = df["Close"].rolling(6).mean()
    ma12 = df["Close"].rolling(12).mean()
    ma24 = df["Close"].rolling(24).mean()
    return (ma3 + ma6 + ma12 + ma24) / 4


def compute_ma(df: pd.DataFrame, windows: List[int] = [5, 10, 20, 60, 120, 250]) -> pd.DataFrame:
    """计算多个周期的均线"""
    for w in windows:
        df[f'MA{w}'] = df['Close'].rolling(window=w).mean()
    return df


# ======================== 策略1: 少妇战法 (BBIKDJSelector) ========================

def bbikdj_selector(df: pd.DataFrame, config: Dict = None) -> Tuple[bool, str]:
    """
    少妇战法
    
    条件：
    1. 昨日: close > BBI
    2. 今日: KDJ金叉(J>D且D>K, 或J上穿D)
    3. 知行约束: 若为短线，要求MA5>MA10>MA20
    """
    if config is None:
        config = {
            'window_kdj': 9,
            'check_zhixing': False,
            'is_shortterm': True
        }
    
    if len(df) < 30:
        return False, "数据不足"
    
    # 计算指标
    df = compute_kdj(df, config['window_kdj'])
    df['BBI'] = compute_bbi(df)
    df = compute_ma(df, [5, 10, 20])
    
    # 获取最近两天数据
    yesterday = df.iloc[-2]
    today = df.iloc[-1]
    
    # 条件1: 昨日收盘价 > BBI
    if yesterday['Close'] <= yesterday['BBI']:
        return False, "昨日收盘价未站上BBI"
    
    # 条件2: KDJ金叉
    kdj_golden = (today['J'] > today['D'] > today['K']) or \
                 (yesterday['J'] <= yesterday['D'] and today['J'] > today['D'])
    
    if not kdj_golden:
        return False, "KDJ未金叉"
    
    # 条件3: 知行约束
    if config['check_zhixing'] and config['is_shortterm']:
        if not (today['MA5'] > today['MA10'] > today['MA20']):
            return False, "不符合短线知行约束(MA5>MA10>MA20)"
    
    reason = f"✅ 少妇战法: BBI={yesterday['BBI']:.2f}, J={today['J']:.2f}, D={today['D']:.2f}, K={today['K']:.2f}"
    return True, reason


# ======================== 策略2: SuperB1战法 ========================

def superb1_selector(df: pd.DataFrame, config: Dict = None) -> Tuple[bool, str]:
    """
    SuperB1战法
    
    条件：
    1. 今日收盘价在MA5和MA10之间
    2. 成交量 > 5日均量 * 1.2
    3. 涨幅 < 5%
    """
    if config is None:
        config = {
            'volume_ratio': 1.2,
            'max_pct_change': 5.0
        }
    
    if len(df) < 20:
        return False, "数据不足"
    
    df = compute_ma(df, [5, 10])
    df['VOL_MA5'] = df['Volume'].rolling(5).mean()
    
    today = df.iloc[-1]
    
    # 计算涨幅
    yesterday_close = df.iloc[-2]['Close']
    pct_change = (today['Close'] - yesterday_close) / yesterday_close * 100
    
    # 条件1: 价格在MA5和MA10之间
    if not (min(today['MA5'], today['MA10']) <= today['Close'] <= max(today['MA5'], today['MA10'])):
        return False, "价格不在MA5和MA10之间"
    
    # 条件2: 放量
    if today['Volume'] <= today['VOL_MA5'] * config['volume_ratio']:
        return False, "成交量不足"
    
    # 条件3: 涨幅限制
    if pct_change >= config['max_pct_change']:
        return False, f"涨幅过大({pct_change:.2f}%)"
    
    reason = f"✅ SuperB1: 价格={today['Close']:.2f}, MA5={today['MA5']:.2f}, MA10={today['MA10']:.2f}, 量比={today['Volume']/today['VOL_MA5']:.2f}, 涨幅={pct_change:.2f}%"
    return True, reason


# ======================== 策略3: 补票战法 (BBIShortLongSelector) ========================

def bbi_shortlong_selector(df: pd.DataFrame, config: Dict = None) -> Tuple[bool, str]:
    """
    补票战法
    
    条件：
    1. BBI向上趋势(今日BBI > 昨日BBI)
    2. 今日收盘价回落到BBI附近(close在BBI的0.98-1.02倍之间)
    3. 成交量萎缩(< 5日均量)
    """
    if config is None:
        config = {
            'bbi_range_lower': 0.98,
            'bbi_range_upper': 1.02,
            'volume_shrink': True
        }
    
    if len(df) < 30:
        return False, "数据不足"
    
    df['BBI'] = compute_bbi(df)
    df['VOL_MA5'] = df['Volume'].rolling(5).mean()
    
    yesterday = df.iloc[-2]
    today = df.iloc[-1]
    
    # 条件1: BBI向上
    if today['BBI'] <= yesterday['BBI']:
        return False, "BBI未向上"
    
    # 条件2: 价格回落到BBI附近
    price_ratio = today['Close'] / today['BBI']
    if not (config['bbi_range_lower'] <= price_ratio <= config['bbi_range_upper']):
        return False, f"价格未回落到BBI附近(比值={price_ratio:.4f})"
    
    # 条件3: 量能萎缩
    if config['volume_shrink'] and today['Volume'] >= today['VOL_MA5']:
        return False, "成交量未萎缩"
    
    reason = f"✅ 补票战法: Close={today['Close']:.2f}, BBI={today['BBI']:.2f}, 比值={price_ratio:.4f}, 量比={today['Volume']/today['VOL_MA5']:.2f}"
    return True, reason


# ======================== 策略4: 填坑战法 (PeakKDJSelector) ========================

def peak_kdj_selector(df: pd.DataFrame, config: Dict = None) -> Tuple[bool, str]:
    """
    填坑战法
    
    条件：
    1. 找到最近的价格波峰
    2. 今日价格回调到波峰价格的95%以内
    3. KDJ底部金叉(J<30且J上穿D)
    """
    if config is None:
        config = {
            'lookback': 60,
            'peak_distance': 5,
            'peak_prominence': 2.0,
            'retracement_pct': 0.95,
            'kdj_low': 30
        }
    
    if len(df) < config['lookback']:
        return False, "数据不足"
    
    df = compute_kdj(df)
    
    # 寻找波峰
    recent_df = df.tail(config['lookback'])
    peaks, properties = find_peaks(
        recent_df['Close'].values,
        distance=config['peak_distance'],
        prominence=config['peak_prominence']
    )
    
    if len(peaks) == 0:
        return False, "未找到明显波峰"
    
    # 最近的波峰
    last_peak_idx = peaks[-1]
    peak_price = recent_df.iloc[last_peak_idx]['Close']
    
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    
    # 条件1: 价格回调到波峰附近
    if today['Close'] > peak_price * config['retracement_pct']:
        return False, f"价格未回调(当前={today['Close']:.2f}, 波峰={peak_price:.2f})"
    
    # 条件2: KDJ底部金叉
    if today['J'] >= config['kdj_low']:
        return False, f"J值过高({today['J']:.2f})"
    
    if not (yesterday['J'] <= yesterday['D'] and today['J'] > today['D']):
        return False, "KDJ未金叉"
    
    reason = f"✅ 填坑战法: 波峰价={peak_price:.2f}, 当前价={today['Close']:.2f}, J={today['J']:.2f}"
    return True, reason


# ======================== 策略5: 上穿60放量战法 ========================

def ma60_cross_volume_selector(df: pd.DataFrame, config: Dict = None) -> Tuple[bool, str]:
    """
    上穿60放量战法
    
    条件：
    1. 今日收盘价上穿MA60(昨日<= MA60, 今日> MA60)
    2. 成交量 > 5日均量 * 1.5
    3. 涨幅 < 7%
    """
    if config is None:
        config = {
            'volume_ratio': 1.5,
            'max_pct_change': 7.0
        }
    
    if len(df) < 70:
        return False, "数据不足"
    
    df = compute_ma(df, [60])
    df['VOL_MA5'] = df['Volume'].rolling(5).mean()
    
    yesterday = df.iloc[-2]
    today = df.iloc[-1]
    
    # 计算涨幅
    pct_change = (today['Close'] - yesterday['Close']) / yesterday['Close'] * 100
    
    # 条件1: 上穿MA60
    if not (yesterday['Close'] <= yesterday['MA60'] and today['Close'] > today['MA60']):
        return False, "未上穿MA60"
    
    # 条件2: 放量
    if today['Volume'] <= today['VOL_MA5'] * config['volume_ratio']:
        return False, f"成交量不足(量比={today['Volume']/today['VOL_MA5']:.2f})"
    
    # 条件3: 涨幅限制
    if pct_change >= config['max_pct_change']:
        return False, f"涨幅过大({pct_change:.2f}%)"
    
    reason = f"✅ 上穿60放量: Close={today['Close']:.2f}, MA60={today['MA60']:.2f}, 量比={today['Volume']/today['VOL_MA5']:.2f}, 涨幅={pct_change:.2f}%"
    return True, reason


# ======================== 统一选股接口 ========================

STRATEGY_MAP = {
    '少妇战法': bbikdj_selector,
    'SuperB1战法': superb1_selector,
    '补票战法': bbi_shortlong_selector,
    '填坑战法': peak_kdj_selector,
    '上穿60放量战法': ma60_cross_volume_selector
}


def run_zgzf_selector(df: pd.DataFrame, strategy_name: str, config: Dict = None) -> Tuple[bool, str]:
    """
    运行指定的Z哥战法策略
    
    Args:
        df: 股票数据，需包含 Open, High, Low, Close, Volume 列
        strategy_name: 策略名称
        config: 策略参数配置
    
    Returns:
        (是否通过, 原因说明)
    """
    if strategy_name not in STRATEGY_MAP:
        return False, f"未知策略: {strategy_name}"
    
    try:
        selector_func = STRATEGY_MAP[strategy_name]
        return selector_func(df, config)
    except Exception as e:
        return False, f"策略执行出错: {str(e)}"


def batch_select_stocks(stock_data_dict: Dict[str, pd.DataFrame], 
                        strategy_name: str, 
                        config: Dict = None) -> pd.DataFrame:
    """
    批量选股
    
    Args:
        stock_data_dict: {股票代码: DataFrame} 字典
        strategy_name: 策略名称
        config: 策略配置
    
    Returns:
        选股结果 DataFrame
    """
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(stock_data_dict)
    for idx, (code, df) in enumerate(stock_data_dict.items()):
        status_text.text(f"正在分析: {code} ({idx+1}/{total})")
        progress_bar.progress((idx + 1) / total)
        
        passed, reason = run_zgzf_selector(df, strategy_name, config)
        
        if passed:
            results.append({
                '股票代码': code,
                '策略': strategy_name,
                '信号': reason,
                '最新价': df.iloc[-1]['Close'],
                '涨幅%': (df.iloc[-1]['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100
            })
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)


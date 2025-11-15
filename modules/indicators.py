"""
指标计算模块 - 负责计算各种技术指标
"""
import pandas as pd
import numpy as np
# 使用 ta 库替代 talib
import ta

def calculate_technical_indicators(df):
    """计算基本技术指标"""
    # 复制DataFrame以避免修改原始数据
    df_copy = df.copy()
    
    # 确保列名统一 - 转换为大写开头的列名以保持一致性
    # 首先检查是否有小写的列名
    if 'open' in df_copy.columns:
        # 来自Ashare的数据，将小写列名转换为大写
        df_copy.rename(columns={
            'open': 'Open',
            'close': 'Close',
            'high': 'High',
            'low': 'Low',
            'volume': 'Volume'
        }, inplace=True)
    elif '开盘' in df_copy.columns:
        # 来自AKShare的数据，将中文列名转换为英文
        df_copy.rename(columns={
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume'
        }, inplace=True)
    
    # 确保所有必要的列都存在
    required_cols = ['Open', 'Close', 'High', 'Low', 'Volume']
    for col in required_cols:
        if col not in df_copy.columns:
            print(f"警告: 数据中缺少 {col} 列")
            # 如果缺少关键列，尝试创建默认值
            if col == 'Volume':
                df_copy[col] = 0
            else:
                # 使用其他列填充缺失值
                if 'Close' in df_copy.columns:
                    df_copy[col] = df_copy['Close']
                else:
                    # 最后的备选方案：使用常数值
                    df_copy[col] = 0.0
    
    # 计算均线
    df_copy['MA5'] = df_copy['Close'].rolling(window=5).mean()
    df_copy['MA10'] = df_copy['Close'].rolling(window=10).mean()
    df_copy['MA20'] = df_copy['Close'].rolling(window=20).mean()
    df_copy['MA30'] = df_copy['Close'].rolling(window=30).mean()
    df_copy['MA60'] = df_copy['Close'].rolling(window=60).mean()
    
    # 布林带
    df_copy['MA20'] = df_copy['Close'].rolling(window=20).mean()
    std = df_copy['Close'].rolling(window=20).std()
    df_copy['UPPER'] = df_copy['MA20'] + 2 * std
    df_copy['LOWER'] = df_copy['MA20'] - 2 * std
    
    # 成交量均线
    df_copy['VOL_MA5'] = df_copy['Volume'].rolling(window=5).mean()
    df_copy['VOL_MA10'] = df_copy['Volume'].rolling(window=10).mean()
    
    # MACD
    exp1 = df_copy['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df_copy['Close'].ewm(span=26, adjust=False).mean()
    df_copy['MACD'] = exp1 - exp2
    df_copy['MACD_signal'] = df_copy['MACD'].ewm(span=9, adjust=False).mean()
    df_copy['MACD_hist'] = df_copy['MACD'] - df_copy['MACD_signal']
    
    # RSI
    delta = df_copy['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    # 避免除以零
    rs = avg_gain / avg_loss.replace(0, 0.000001)
    df_copy['RSI'] = 100 - (100 / (1 + rs))
    
    # KDJ
    low_min = df_copy['Low'].rolling(window=9).min()
    high_max = df_copy['High'].rolling(window=9).max()
    
    df_copy['RSV'] = 100 * ((df_copy['Close'] - low_min) / (high_max - low_min).replace(0, 0.000001))
    df_copy['K'] = df_copy['RSV'].ewm(com=2, adjust=False).mean()
    df_copy['D'] = df_copy['K'].ewm(com=2, adjust=False).mean()
    df_copy['J'] = 3 * df_copy['K'] - 2 * df_copy['D']
    
    return df_copy

def calculate_advanced_indicators(df):
    """计算高级技术指标，使用ta库"""
    # 确保输入数据有正确的列名
    df_copy = df.copy()
    
    # 标准化列名
    if 'open' in df_copy.columns:
        df_copy.rename(columns={
            'open': 'Open',
            'close': 'Close',
            'high': 'High',
            'low': 'Low',
            'volume': 'Volume'
        }, inplace=True)
    elif '开盘' in df_copy.columns:
        df_copy.rename(columns={
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume'
        }, inplace=True)
    
    # 确保数据类型正确
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
    
    # 计算更多指标
    try:
        # 趋势指标
        df_copy['ADX'] = ta.trend.adx(df_copy['High'], df_copy['Low'], df_copy['Close'], window=14)
        df_copy['CCI'] = ta.trend.cci(df_copy['High'], df_copy['Low'], df_copy['Close'], window=14)
        
        # 动量指标
        df_copy['MOM'] = ta.momentum.roc(df_copy['Close'], window=10, fillna=True)
        df_copy['ROC'] = ta.momentum.roc(df_copy['Close'], window=10, fillna=True)
        
        # 波动率指标
        df_copy['ATR'] = ta.volatility.average_true_range(df_copy['High'], df_copy['Low'], df_copy['Close'], window=14)
        
        # 成交量指标
        df_copy['OBV'] = ta.volume.on_balance_volume(df_copy['Close'], df_copy['Volume'])
        
        # 其他常用指标
        df_copy['WILLR'] = ta.momentum.williams_r(df_copy['High'], df_copy['Low'], df_copy['Close'], lbp=14)
        
    except Exception as e:
        print(f"计算高级指标时出错: {e}")
    
    return df_copy

def analyze_market_status(df):
    """分析市场状态，返回技术指标状态信息"""
    if df.empty or len(df) < 2:
        return {}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 确保所有必要的指标都已计算
    required_indicators = ['MA5', 'MA10', 'MA20', 'MACD', 'MACD_signal', 'MACD_hist', 'RSI', 'K', 'D', 'J', 'Volume']
    for indicator in required_indicators:
        if indicator not in df.columns:
            return {}
    
    # 分析均线状态
    ma5_last = latest['MA5']
    ma10_last = latest['MA10']
    ma20_last = latest['MA20']
    ma_status = "看涨" if ma5_last > ma10_last > ma20_last else "看跌" if ma5_last < ma10_last < ma20_last else "中性"
    
    # 分析MACD状态 - 使用MACD线和信号线的交叉判断金叉死叉
    macd_last = latest['MACD']
    macd_signal_last = latest['MACD_signal']
    macd_prev = prev['MACD']
    macd_signal_prev = prev['MACD_signal']
    
    # 计算MACD柱状图(histogram)值
    macd_hist_last = latest['MACD_hist']
    macd_prev_hist = prev['MACD_hist']
    
    # 初始化变量
    is_golden_cross = False
    is_death_cross = False
    
    # 检查数据是否有效（不是NaN）
    if pd.isna(macd_last) or pd.isna(macd_signal_last) or pd.isna(macd_prev) or pd.isna(macd_signal_prev):
        macd_status = "数据不足"
    else:
        # 金叉：MACD线从下方穿过信号线
        is_golden_cross = macd_prev <= macd_signal_prev and macd_last > macd_signal_last
        # 死叉：MACD线从上方穿过信号线
        is_death_cross = macd_prev >= macd_signal_prev and macd_last < macd_signal_last
        
        if is_golden_cross:
            macd_status = "金叉"
        elif is_death_cross:
            macd_status = "死叉"
        else:
            # 改进的判断逻辑：综合考虑MACD线、信号线和柱状图
            # 1. 如果MACD线和信号线都在零轴上方，且柱状图为正且增大，为多头
            # 2. 如果MACD线和信号线都在零轴下方，且柱状图为负且减小，为空头
            # 3. 否则根据MACD线和信号线的相对位置以及柱状图趋势判断
            
            # 检查是否在零轴上方
            above_zero = macd_last > 0 and macd_signal_last > 0
            below_zero = macd_last < 0 and macd_signal_last < 0
            
            # 柱状图趋势（增大或减小）
            hist_increasing = macd_hist_last > macd_prev_hist
            hist_decreasing = macd_hist_last < macd_prev_hist
            
            # 综合判断
            if above_zero and macd_last > macd_signal_last and macd_hist_last > 0:
                # 零轴上方，MACD线在信号线上方，柱状图为正
                if hist_increasing:
                    macd_status = "多头趋势"
                else:
                    macd_status = "多头减弱"
            elif below_zero and macd_last < macd_signal_last and macd_hist_last < 0:
                # 零轴下方，MACD线在信号线下方，柱状图为负
                if hist_decreasing:
                    macd_status = "空头趋势"
                else:
                    macd_status = "空头减弱"
            elif macd_last > macd_signal_last:
                # MACD线在信号线上方，但不在零轴上方或柱状图为负
                if macd_hist_last > 0:
                    macd_status = "多头趋势"
                else:
                    macd_status = "空头趋势"  # 柱状图为负，即使MACD线在上方也是空头
            else:
                # MACD线在信号线下方
                if macd_hist_last < 0:
                    macd_status = "空头趋势"
                else:
                    macd_status = "多头趋势"  # 柱状图为正，即使MACD线在下方也是多头
    
    # 分析RSI状态
    rsi_last = latest['RSI']
    rsi_status = "超买" if rsi_last > 70 else "超卖" if rsi_last < 30 else "中性"
    rsi_prev = prev['RSI']
    rsi_delta = rsi_last - rsi_prev
    
    # 分析KDJ状态
    k_last = latest['K']
    d_last = latest['D']
    j_last = latest['J']
    kdj_status = "超买" if k_last > 80 and d_last > 80 else "超卖" if k_last < 20 and d_last < 20 else "金叉" if k_last > d_last and prev['K'] <= prev['D'] else "死叉" if k_last < d_last and prev['K'] >= prev['D'] else "中性"
    
    # 分析成交量状态
    vol_last = latest['Volume']
    vol_ma5 = df['Volume'].rolling(5).mean().iloc[-1]
    vol_status = "放量" if vol_last > vol_ma5 * 1.5 else "缩量" if vol_last < vol_ma5 * 0.5 else "平稳"
    vol_change = (vol_last / prev['Volume'] - 1) * 100
    
    # 分析价格位置
    close_last = latest['Close']
    high_20 = df['High'].rolling(20).max().iloc[-1]
    low_20 = df['Low'].rolling(20).min().iloc[-1]
    price_position = (close_last - low_20) / (high_20 - low_20) * 100 if high_20 != low_20 else 50
    position_status = "高位" if price_position > 80 else "低位" if price_position < 20 else "中位"
    price_change = (latest['Close'] / prev['Close'] - 1) * 100
    
    # 返回分析结果
    return {
        "ma": {
            "status": ma_status,
            "ma5": ma5_last,
            "ma10": ma10_last,
            "ma20": ma20_last
        },
        "macd": {
            "status": macd_status,
            "dif": macd_last,
            "dea": macd_signal_last,
            "hist": macd_hist_last,
            "hist_change": macd_hist_last - macd_prev_hist,
            "is_golden_cross": is_golden_cross,
            "is_death_cross": is_death_cross
        },
        "rsi": {
            "status": rsi_status,
            "value": rsi_last,
            "change": rsi_delta
        },
        "kdj": {
            "status": kdj_status,
            "k": k_last,
            "d": d_last,
            "j": j_last
        },
        "volume": {
            "status": vol_status,
            "value": vol_last,
            "change": vol_change
        },
        "price": {
            "status": position_status,
            "position": price_position,
            "value": close_last,
            "change": price_change
        }
    }
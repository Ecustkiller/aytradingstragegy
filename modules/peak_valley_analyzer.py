"""
峰级线趋势分析模块
基于峰级交易理论，识别峰点、谷点、支撑位、压力位
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime


class PeakValleyAnalyzer:
    """峰级线趋势分析器"""

    def __init__(self, lookback_bars: int = 3):
        """
        初始化峰级线分析器

        Args:
            lookback_bars: 峰谷判定的左右K线数量（默认3根）
        """
        self.lookback_bars = lookback_bars

    def identify_peaks_valleys(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        识别峰点和谷点

        峰点判定：当前K线最高价高于前后N根K线的最高价
        谷点判定：当前K线最低价低于前后N根K线的最低价

        Args:
            df: 包含OHLC数据的DataFrame

        Returns:
            添加了峰谷标记的DataFrame
        """
        df = df.copy()
        n = self.lookback_bars

        # 初始化峰谷标记列
        df['is_peak'] = False
        df['is_valley'] = False
        df['peak_price'] = np.nan
        df['valley_price'] = np.nan

        # 需要足够的数据才能判定
        if len(df) < 2 * n + 1:
            return df

        # 从第n+1根K线开始判定（确保左右各有n根K线）
        for i in range(n, len(df) - n):
            current_high = df['High'].iloc[i]
            current_low = df['Low'].iloc[i]

            # 获取左右各n根K线的最高价和最低价
            left_highs = df['High'].iloc[i-n:i]
            right_highs = df['High'].iloc[i+1:i+n+1]
            left_lows = df['Low'].iloc[i-n:i]
            right_lows = df['Low'].iloc[i+1:i+n+1]

            # 判定峰点：当前最高价 > 左右各n根K线的最高价
            if current_high > left_highs.max() and current_high > right_highs.max():
                df.iloc[i, df.columns.get_loc('is_peak')] = True
                df.iloc[i, df.columns.get_loc('peak_price')] = current_high

            # 判定谷点：当前最低价 < 左右各n根K线的最低价
            if current_low < left_lows.min() and current_low < right_lows.min():
                df.iloc[i, df.columns.get_loc('is_valley')] = True
                df.iloc[i, df.columns.get_loc('valley_price')] = current_low

        return df

    def get_recent_peaks_valleys(self, df: pd.DataFrame, n_recent: int = 5) -> Dict:
        """
        获取最近的峰点和谷点

        Args:
            df: 包含峰谷标记的DataFrame
            n_recent: 获取最近N个峰谷点

        Returns:
            包含最近峰谷点信息的字典
        """
        df_marked = self.identify_peaks_valleys(df)

        # 提取峰点
        peaks = df_marked[df_marked['is_peak']].copy()
        peaks = peaks[['peak_price']].rename(columns={'peak_price': 'price'})
        peaks['type'] = 'peak'

        # 提取谷点
        valleys = df_marked[df_marked['is_valley']].copy()
        valleys = valleys[['valley_price']].rename(columns={'valley_price': 'price'})
        valleys['type'] = 'valley'

        # 合并并按时间排序
        all_points = pd.concat([peaks, valleys]).sort_index()

        # 获取最近的N个点
        recent_points = all_points.tail(n_recent)

        return {
            'recent_peaks': peaks.tail(n_recent),
            'recent_valleys': valleys.tail(n_recent),
            'recent_all': recent_points,
            'all_peaks': peaks,
            'all_valleys': valleys
        }

    def calculate_support_resistance(self, df: pd.DataFrame) -> Dict:
        """
        计算当前的支撑位和压力位

        支撑位：最近的谷点价格
        压力位：最近的峰点价格

        Args:
            df: 包含OHLC数据的DataFrame

        Returns:
            支撑位和压力位信息
        """
        points = self.get_recent_peaks_valleys(df, n_recent=10)

        current_price = df['Close'].iloc[-1]

        # 获取所有峰点和谷点价格
        all_peaks = points['all_peaks']['price'].values if len(points['all_peaks']) > 0 else []
        all_valleys = points['all_valleys']['price'].values if len(points['all_valleys']) > 0 else []

        # 压力位：高于当前价的峰点（从近到远排序）
        resistance_levels = sorted([p for p in all_peaks if p > current_price])

        # 支撑位：低于当前价的谷点（从近到远排序，降序）
        support_levels = sorted([v for v in all_valleys if v < current_price], reverse=True)

        # 获取最近的3个支撑位和压力位
        primary_resistance = resistance_levels[:3] if resistance_levels else []
        primary_support = support_levels[:3] if support_levels else []

        return {
            'current_price': current_price,
            'resistance_levels': primary_resistance,
            'support_levels': primary_support,
            'all_resistance': resistance_levels,
            'all_support': support_levels,
            'nearest_resistance': resistance_levels[0] if resistance_levels else None,
            'nearest_support': support_levels[0] if support_levels else None
        }

    def analyze_trend(self, df: pd.DataFrame) -> Dict:
        """
        分析当前趋势

        趋势向上：突破前高（创新高）
        趋势向下：跌破前低（创新低）

        Args:
            df: 包含峰谷标记的DataFrame

        Returns:
            趋势分析结果
        """
        points = self.get_recent_peaks_valleys(df, n_recent=10)

        if len(points['recent_all']) < 2:
            return {
                'trend': 'unknown',
                'confidence': 0,
                'description': '数据不足，无法判断趋势'
            }

        current_price = df['Close'].iloc[-1]

        # 获取最近的峰谷点
        recent_peaks = points['recent_peaks']
        recent_valleys = points['recent_valleys']

        if len(recent_peaks) == 0 or len(recent_valleys) == 0:
            return {
                'trend': 'unknown',
                'confidence': 0,
                'description': '峰谷点不足，无法判断趋势'
            }

        # 获取最近的峰点和谷点价格
        latest_peak = recent_peaks['price'].iloc[-1]
        latest_valley = recent_valleys['price'].iloc[-1]

        # 判断趋势
        if len(recent_peaks) >= 2:
            prev_peak = recent_peaks['price'].iloc[-2]
            # 突破前高 -> 上涨趋势
            if current_price > latest_peak and latest_peak > prev_peak:
                return {
                    'trend': 'up',
                    'confidence': 0.8,
                    'description': f'突破前高({latest_peak:.2f})，趋势向上',
                    'latest_peak': latest_peak,
                    'prev_peak': prev_peak
                }

        if len(recent_valleys) >= 2:
            prev_valley = recent_valleys['price'].iloc[-2]
            # 跌破前低 -> 下跌趋势
            if current_price < latest_valley and latest_valley < prev_valley:
                return {
                    'trend': 'down',
                    'confidence': 0.8,
                    'description': f'跌破前低({latest_valley:.2f})，趋势向下',
                    'latest_valley': latest_valley,
                    'prev_valley': prev_valley
                }

        # 震荡趋势
        return {
            'trend': 'sideways',
            'confidence': 0.6,
            'description': f'在峰点({latest_peak:.2f})和谷点({latest_valley:.2f})之间震荡',
            'latest_peak': latest_peak,
            'latest_valley': latest_valley
        }

    def identify_trading_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        识别6种定式交易形态

        1. 挫棍：阳线后跟阴线，阴线低点不破前一根阳线低点
        2. 阳吃阴：阳线吃掉前面的阴线
        3. 24棒：连续2-4根阳线
        4. 阳夹棍：阳线夹着阴线
        5. 指形：长上影或长下影
        6. 外扩峰：突破前高创新高

        Args:
            df: 包含OHLC数据的DataFrame

        Returns:
            识别到的交易形态列表
        """
        patterns = []

        if len(df) < 5:
            return patterns

        # 获取最近5根K线
        recent_bars = df.tail(5)

        # 辅助函数
        def is_bullish(bar):
            """判断是否阳线"""
            return bar['Close'] > bar['Open']

        def is_bearish(bar):
            """判断是否阴线"""
            return bar['Close'] < bar['Open']

        # 1. 挫棍形态
        if len(recent_bars) >= 2:
            bar1 = recent_bars.iloc[-2]
            bar2 = recent_bars.iloc[-1]

            if is_bullish(bar1) and is_bearish(bar2) and bar2['Low'] >= bar1['Low']:
                patterns.append({
                    'pattern': '挫棍',
                    'type': 'bullish',
                    'confidence': 0.7,
                    'description': '阳线后缩量阴线，阴线低点未破阳线低点，看涨信号',
                    'entry_price': bar2['Close'],
                    'stop_loss': bar1['Low']
                })

        # 2. 阳吃阴形态
        if len(recent_bars) >= 2:
            bar1 = recent_bars.iloc[-2]
            bar2 = recent_bars.iloc[-1]

            if is_bearish(bar1) and is_bullish(bar2):
                if bar2['Close'] > bar1['Open'] and bar2['Open'] < bar1['Close']:
                    patterns.append({
                        'pattern': '阳吃阴',
                        'type': 'bullish',
                        'confidence': 0.75,
                        'description': '阳线完全吞没前一根阴线，强势看涨信号',
                        'entry_price': bar2['Close'],
                        'stop_loss': bar2['Low']
                    })

        # 3. 24棒形态（2-4根连续阳线）
        consecutive_bullish = 0
        for i in range(len(recent_bars)-1, -1, -1):
            if is_bullish(recent_bars.iloc[i]):
                consecutive_bullish += 1
            else:
                break

        if 2 <= consecutive_bullish <= 4:
            patterns.append({
                'pattern': f'{consecutive_bullish}连阳',
                'type': 'bullish',
                'confidence': 0.65,
                'description': f'连续{consecutive_bullish}根阳线，多头强势',
                'entry_price': recent_bars.iloc[-1]['Close'],
                'stop_loss': recent_bars.iloc[-consecutive_bullish]['Low']
            })

        # 4. 阳夹棍形态
        if len(recent_bars) >= 3:
            bar1 = recent_bars.iloc[-3]
            bar2 = recent_bars.iloc[-2]
            bar3 = recent_bars.iloc[-1]

            if is_bullish(bar1) and is_bearish(bar2) and is_bullish(bar3):
                if bar3['Close'] > bar1['Close']:
                    patterns.append({
                        'pattern': '阳夹棍',
                        'type': 'bullish',
                        'confidence': 0.8,
                        'description': '两根阳线夹一根阴线，突破前高，强力看涨信号',
                        'entry_price': bar3['Close'],
                        'stop_loss': bar2['Low']
                    })

        # 5. 指形形态（长上影或长下影）
        latest_bar = recent_bars.iloc[-1]
        body_size = abs(latest_bar['Close'] - latest_bar['Open'])
        upper_shadow = latest_bar['High'] - max(latest_bar['Open'], latest_bar['Close'])
        lower_shadow = min(latest_bar['Open'], latest_bar['Close']) - latest_bar['Low']

        # 长下影线（看涨）
        if lower_shadow > 2 * body_size and upper_shadow < body_size:
            patterns.append({
                'pattern': '长下影线',
                'type': 'bullish',
                'confidence': 0.7,
                'description': '长下影线，下方支撑强劲，看涨信号',
                'entry_price': latest_bar['Close'],
                'stop_loss': latest_bar['Low']
            })

        # 长上影线（看跌）
        if upper_shadow > 2 * body_size and lower_shadow < body_size:
            patterns.append({
                'pattern': '长上影线',
                'type': 'bearish',
                'confidence': 0.7,
                'description': '长上影线，上方压力沉重，看跌信号',
                'entry_price': latest_bar['Close'],
                'stop_loss': latest_bar['High']
            })

        # 6. 外扩峰形态（创新高）
        df_marked = self.identify_peaks_valleys(df)
        recent_peaks = df_marked[df_marked['is_peak']].tail(2)

        if len(recent_peaks) >= 2:
            prev_peak = recent_peaks['peak_price'].iloc[-2]
            latest_peak = recent_peaks['peak_price'].iloc[-1]
            current_price = df['Close'].iloc[-1]

            if latest_peak > prev_peak and current_price >= latest_peak * 0.98:
                patterns.append({
                    'pattern': '外扩峰',
                    'type': 'bullish',
                    'confidence': 0.85,
                    'description': f'突破前高({prev_peak:.2f})创新高({latest_peak:.2f})，强力上涨信号',
                    'entry_price': current_price,
                    'stop_loss': prev_peak
                })

        return patterns

    def generate_trade_advice(self, df: pd.DataFrame) -> Dict:
        """
        生成交易建议

        综合峰谷分析、支撑压力位、趋势判断和形态识别

        Args:
            df: 包含OHLC数据的DataFrame

        Returns:
            交易建议字典
        """
        # 计算支撑压力位
        sr_levels = self.calculate_support_resistance(df)

        # 分析趋势
        trend_info = self.analyze_trend(df)

        # 识别交易形态
        patterns = self.identify_trading_patterns(df)

        # 综合判断
        current_price = df['Close'].iloc[-1]

        # 初始化建议
        advice = {
            'action': 'hold',
            'confidence': 0.5,
            'description': '观望等待更好的交易机会',
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None,
            'support_levels': sr_levels['support_levels'],
            'resistance_levels': sr_levels['resistance_levels'],
            'trend': trend_info,
            'patterns': patterns
        }

        # 根据形态和趋势生成建议
        bullish_patterns = [p for p in patterns if p['type'] == 'bullish']
        bearish_patterns = [p for p in patterns if p['type'] == 'bearish']

        # 看涨信号
        if trend_info['trend'] == 'up' and len(bullish_patterns) > 0:
            best_pattern = max(bullish_patterns, key=lambda x: x['confidence'])
            advice.update({
                'action': 'buy',
                'confidence': (trend_info['confidence'] + best_pattern['confidence']) / 2,
                'description': f"趋势向上且出现{best_pattern['pattern']}形态，建议买入",
                'entry_price': current_price,
                'stop_loss': best_pattern['stop_loss'],
                'take_profit': sr_levels['nearest_resistance'] if sr_levels['nearest_resistance'] else current_price * 1.05,
                'pattern_info': best_pattern
            })

        # 看跌信号
        elif trend_info['trend'] == 'down' and len(bearish_patterns) > 0:
            best_pattern = max(bearish_patterns, key=lambda x: x['confidence'])
            advice.update({
                'action': 'sell',
                'confidence': (trend_info['confidence'] + best_pattern['confidence']) / 2,
                'description': f"趋势向下且出现{best_pattern['pattern']}形态，建议卖出或观望",
                'entry_price': current_price,
                'stop_loss': best_pattern['stop_loss'],
                'pattern_info': best_pattern
            })

        # 震荡市场但有强力形态
        elif len(bullish_patterns) > 0:
            best_pattern = max(bullish_patterns, key=lambda x: x['confidence'])
            if best_pattern['confidence'] >= 0.75:
                advice.update({
                    'action': 'buy',
                    'confidence': best_pattern['confidence'] * 0.8,  # 震荡市降低信心
                    'description': f"震荡市场但出现强力{best_pattern['pattern']}形态，可轻仓试多",
                    'entry_price': current_price,
                    'stop_loss': best_pattern['stop_loss'],
                    'take_profit': sr_levels['nearest_resistance'] if sr_levels['nearest_resistance'] else current_price * 1.03,
                    'pattern_info': best_pattern
                })

        return advice


# 全局实例
peak_valley_analyzer = PeakValleyAnalyzer()


def analyze_stock_peaks_valleys(df: pd.DataFrame) -> Dict:
    """
    便捷函数：分析股票的峰谷情况

    Args:
        df: 包含OHLC数据的DataFrame

    Returns:
        分析结果字典
    """
    return peak_valley_analyzer.generate_trade_advice(df)

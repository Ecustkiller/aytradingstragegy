"""
交易日历工具
用于过滤非交易日，确保K线图连续显示
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TradingCalendar:
    """交易日历类"""
    
    def __init__(self):
        # 中国股市节假日（需要定期更新）
        self.holidays_2024 = [
            # 元旦
            '2024-01-01',
            # 春节
            '2024-02-10', '2024-02-11', '2024-02-12', '2024-02-13', 
            '2024-02-14', '2024-02-15', '2024-02-16', '2024-02-17',
            # 清明节
            '2024-04-04', '2024-04-05', '2024-04-06',
            # 劳动节
            '2024-05-01', '2024-05-02', '2024-05-03',
            # 端午节
            '2024-06-10',
            # 中秋节
            '2024-09-15', '2024-09-16', '2024-09-17',
            # 国庆节
            '2024-10-01', '2024-10-02', '2024-10-03', '2024-10-04',
            '2024-10-05', '2024-10-06', '2024-10-07'
        ]
        
        self.holidays_2025 = [
            # 元旦
            '2025-01-01',
            # 春节
            '2025-01-28', '2025-01-29', '2025-01-30', '2025-01-31',
            '2025-02-01', '2025-02-02', '2025-02-03', '2025-02-04',
            # 清明节
            '2025-04-05', '2025-04-06', '2025-04-07',
            # 劳动节
            '2025-05-01', '2025-05-02', '2025-05-03',
            # 端午节
            '2025-06-09',
            # 中秋节
            '2025-10-06',
            # 国庆节
            '2025-10-01', '2025-10-02', '2025-10-03', '2025-10-04',
            '2025-10-05', '2025-10-07', '2025-10-08'
        ]
        
        # 合并所有节假日
        self.holidays = set(self.holidays_2024 + self.holidays_2025)
        
        # 转换为日期对象
        self.holiday_dates = set(pd.to_datetime(list(self.holidays)).date)
    
    def is_trading_day(self, date):
        """判断是否为交易日"""
        if isinstance(date, str):
            date = pd.to_datetime(date).date()
        elif isinstance(date, pd.Timestamp):
            date = date.date()
        elif isinstance(date, datetime):
            date = date.date()
        
        # 周末不是交易日
        if date.weekday() >= 5:  # 5=周六, 6=周日
            return False
        
        # 节假日不是交易日
        if date in self.holiday_dates:
            return False
        
        return True
    
    def filter_trading_days(self, df):
        """过滤DataFrame，只保留交易日的数据"""
        if df.empty:
            return df
        
        # 确保索引是日期时间类型
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except:
                return df
        
        # 创建交易日掩码
        trading_mask = df.index.to_series().apply(
            lambda x: self.is_trading_day(x.date())
        )
        
        # 过滤数据
        filtered_df = df[trading_mask]
        
        print(f"📅 交易日过滤: {len(df)} → {len(filtered_df)} 条数据")
        
        return filtered_df
    
    def get_trading_days_in_range(self, start_date, end_date):
        """获取指定日期范围内的所有交易日"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # 生成日期范围
        date_range = pd.date_range(start=start, end=end, freq='D')
        
        # 过滤出交易日
        trading_days = [
            date for date in date_range 
            if self.is_trading_day(date.date())
        ]
        
        return trading_days
    
    def get_latest_trading_day(self, date=None):
        """获取最近的交易日"""
        if date is None:
            date = datetime.now().date()
        elif isinstance(date, (str, pd.Timestamp, datetime)):
            date = pd.to_datetime(date).date()
        
        # 从给定日期开始往前找交易日
        current_date = date
        for _ in range(10):  # 最多往前找10天
            if self.is_trading_day(current_date):
                return current_date
            current_date = current_date - timedelta(days=1)
        
        return date  # 如果找不到，返回原日期
    
    def get_next_trading_day(self, date=None):
        """获取下一个交易日"""
        if date is None:
            date = datetime.now().date()
        elif isinstance(date, (str, pd.Timestamp, datetime)):
            date = pd.to_datetime(date).date()
        
        # 从给定日期的下一天开始找交易日
        current_date = date + timedelta(days=1)
        for _ in range(10):  # 最多往后找10天
            if self.is_trading_day(current_date):
                return current_date
            current_date = current_date + timedelta(days=1)
        
        return date  # 如果找不到，返回原日期

# 全局实例
trading_calendar = TradingCalendar()

# 便捷函数
def is_trading_day(date):
    """判断是否为交易日"""
    return trading_calendar.is_trading_day(date)

def filter_trading_days(df):
    """过滤DataFrame，只保留交易日的数据"""
    return trading_calendar.filter_trading_days(df)

def get_latest_trading_day(date=None):
    """获取最近的交易日"""
    return trading_calendar.get_latest_trading_day(date)

def get_next_trading_day(date=None):
    """获取下一个交易日"""
    return trading_calendar.get_next_trading_day(date)

def get_trading_days_in_range(start_date, end_date):
    """获取指定日期范围内的所有交易日"""
    return trading_calendar.get_trading_days_in_range(start_date, end_date)
"""
数据模块 - 负责获取和处理股票数据
修复版本，确保交易日过滤功能正常工作
"""
import streamlit as st
import akshare as ak
import pandas as pd
import datetime
from .utils import format_stock_code
from .smart_data_manager import cached_stock_data, cached_realtime_data, smart_data_manager

# 检查数据源可用性
try:
    from .Ashare import *
    has_ashare = True
    print("✅ Ashare模块加载成功")
except ImportError:
    has_ashare = False
    print("❌ Ashare模块未找到，将使用AKShare作为备用数据源")

def get_stock_data_ashare(symbol, start, end, period_type):
    """使用Ashare获取股票数据"""
    try:
        # 格式化股票代码
        formatted_symbol = format_stock_code(symbol)
        
        # 转换日期格式
        # 转换日期格式 - Ashare只支持end_date和count参数
        end_str = end.strftime('%Y-%m-%d') if hasattr(end, 'strftime') else str(end)
        
        # 计算需要获取的数据量
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        days_diff = (end_date - start_date).days
        
        # 根据周期类型计算count
        if period_type == 'daily':
            count = min(max(days_diff + 50, 100), 1000)  # 多获取一些数据确保覆盖范围
            frequency = '1d'
        elif period_type == 'weekly':
            count = min(max(days_diff // 7 + 20, 52), 200)
            frequency = '1w'
        elif period_type == 'monthly':
            count = min(max(days_diff // 30 + 12, 24), 100)
            frequency = '1M'
        else:
            st.error(f"不支持的数据周期: {period_type}")
            return pd.DataFrame()
        
        print(f"🔄 正在使用Ashare获取 {formatted_symbol} 的数据...")
        print(f"   📅 结束日期: {end_str}")
        print(f"   📊 数据类型: {period_type}")
        print(f"   📈 获取数量: {count} 条")
        
        # 使用Ashare获取数据
        df = get_price(formatted_symbol, end_date=end_str, count=count, frequency=frequency)
        
        if df.empty:
            print(f"❌ Ashare获取 {formatted_symbol} 数据为空")
            return pd.DataFrame()
        
        # 标准化列名
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # 确保索引是日期时间类型
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # 按日期排序
        df = df.sort_index()
        
        # 过滤日期范围
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        
        if end_date < df.index[0]:
            st.warning(f"请求的结束时间 {end_date.date()} 早于数据的最早时间 {df.index[0].date()}，返回最早数据")
            return df.head(min(500, len(df)))
        elif start_date > df.index[-1]:
            st.warning(f"请求的开始时间 {start_date.date()} 晚于数据的最新时间 {df.index[-1].date()}，返回最新数据")
            return df.tail(min(500, len(df)))
        else:
            mask = (df.index >= start_date) & (df.index <= end_date)
            df_filtered = df.loc[mask]
            
            if df_filtered.empty:
                return df.head(min(500, len(df)))
        
        print(f"✅ Ashare数据获取成功!")
        print(f"   📊 数据条数: {len(df_filtered)}")
        print(f"   📅 时间范围: {df_filtered.index[0]} 到 {df_filtered.index[-1]}")
        print(f"   💰 最新收盘价: {df_filtered['Close'].iloc[-1]:.2f}")
        
        return df_filtered
        
    except Exception as e:
        st.error(f"Ashare数据获取失败: {str(e)}")
        return pd.DataFrame()

def get_stock_data_ak(symbol, start, end, period_type):
    """使用AKShare获取股票数据"""
    try:
        # 格式化股票代码
        formatted_symbol = format_stock_code(symbol)
        
        print(f"🔄 正在使用AKShare获取 {formatted_symbol} 的数据...")
        
        # 根据周期类型获取数据
        if period_type in ['daily', 'weekly', 'monthly']:
            # 转换周期参数
            period_map = {
                'daily': 'daily',
                'weekly': 'weekly', 
                'monthly': 'monthly'
            }
            period = period_map[period_type]
            
            # 格式化日期
            start_date = start.strftime('%Y%m%d') if hasattr(start, 'strftime') else str(start).replace('-', '')
            end_date = end.strftime('%Y%m%d') if hasattr(end, 'strftime') else str(end).replace('-', '')
            
            # 获取股票历史数据
            df = ak.stock_zh_a_hist(
                symbol=formatted_symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df.empty:
                return pd.DataFrame()
                
            # 处理日期和索引
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期').set_index('日期')
            
            # 标准化列名
            if '开盘' in df.columns:
                df = df.rename(columns={
                    '开盘': 'Open',
                    '收盘': 'Close',
                    '最高': 'High',
                    '最低': 'Low',
                    '成交量': 'Volume'
                })
            
            print(f"✅ AKShare数据获取成功!")
            print(f"   📊 数据条数: {len(df)}")
            if not df.empty:
                print(f"   📅 时间范围: {df.index[0]} 到 {df.index[-1]}")
                print(f"   💰 最新收盘价: {df['Close'].iloc[-1]:.2f}")
            
            return df
            
    except Exception as e:
        st.error(f"AKShare数据获取失败: {str(e)}")
        return pd.DataFrame()

def get_stock_data(symbol, start, end, period_type, data_source="Ashare"):
    """获取股票数据的主函数，根据数据源选择不同的获取方法"""
    try:
        # 确保日期格式正确
        if not isinstance(start, (str, pd.Timestamp, datetime.datetime)):
            start = pd.to_datetime(start, format='%Y%m%d')
        if not isinstance(end, (str, pd.Timestamp, datetime.datetime)):
            end = pd.to_datetime(end, format='%Y%m%d')
        
        # 根据用户选择的数据源获取数据
        if data_source == "Ashare" and has_ashare:
            df = get_stock_data_ashare(symbol, start, end, period_type)
        elif data_source == "Ashare" and not has_ashare:
            st.warning("💡 未检测到Ashare模块，使用AKShare数据源")
            df = get_stock_data_ak(symbol, start, end, period_type)
        else:
            # 使用AKShare数据源
            df = get_stock_data_ak(symbol, start, end, period_type)
        
        # 🔧 统一应用交易日过滤，确保K线连续显示
        if not df.empty and period_type in ['daily', 'weekly', 'monthly']:
            from .trading_calendar import filter_trading_days
            original_count = len(df)
            df = filter_trading_days(df)
            filtered_count = len(df)
            
            if filtered_count < original_count:
                st.info(f"📅 交易日过滤: {original_count} → {filtered_count} 条数据")
                st.success(f"✅ 已过滤掉 {original_count - filtered_count} 个非交易日（周末和节假日）")
        
        return df
        
    except Exception as e:
        st.error(f"获取股票数据失败: {str(e)}")
        return pd.DataFrame()

# 其他辅助函数保持不变
def get_realtime_price(symbol):
    """获取实时股价"""
    try:
        # 使用缓存的实时数据
        return cached_realtime_data(symbol)
    except Exception as e:
        st.error(f"获取实时价格失败: {str(e)}")
        return None

def get_stock_info(symbol):
    """获取股票基本信息"""
    try:
        formatted_symbol = format_stock_code(symbol)
        
        if has_ashare:
            # 使用Ashare获取股票信息
            info = get_security_info(formatted_symbol)
            return info
        else:
            # 使用AKShare获取股票信息
            info = ak.stock_individual_info_em(symbol=formatted_symbol)
            return info
            
    except Exception as e:
        st.error(f"获取股票信息失败: {str(e)}")
        return None
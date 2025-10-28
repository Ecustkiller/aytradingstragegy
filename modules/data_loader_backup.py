"""
数据模块 - 负责获取和处理股票数据
"""
import streamlit as st
import akshare as ak
import pandas as pd
import datetime
from .utils import format_stock_code
from .smart_data_manager import cached_stock_data, cached_realtime_data, smart_data_manager

# 检查是否可以导入Ashare模块
try:
    # 从当前模块导入
    from .Ashare import get_price
    has_ashare = True
    print("✅ Ashare模块检测成功")
except ImportError as e:
    has_ashare = False
    print(f"Ashare模块未找到: {e}，将只能使用AKShare数据源")

# MiniQMT 模块已移除
has_miniqmt = False

# 导入交易日历模块
try:
    from .trading_calendar import is_trading_day, get_latest_trading_day
except ImportError:
    # 如果导入失败，定义简单的替代函数
    def is_trading_day(date=None):
        if date is None:
            date = datetime.datetime.now().date()
        return date.weekday() < 5  # 简单判断：周一至周五为交易日
    
    def get_latest_trading_day(date=None):
        if date is None:
            date = datetime.datetime.now().date()
        if date.weekday() >= 5:  # 如果是周末
            days_to_friday = (date.weekday() - 4) % 7
            return date - datetime.timedelta(days=days_to_friday)
        return date

@cached_stock_data(cache_type='daily_data')
def get_stock_data_ashare(symbol, start, end, period_type):
    """使用Ashare库获取股票数据"""
    if not has_ashare:
        st.error("未安装Ashare模块，请使用AKShare数据源")
        return pd.DataFrame()
        
    try:
        # 格式化股票代码
        formatted_code = format_stock_code(symbol)
        
        # 转换周期类型为Ashare参数格式
        frequency = '1d'  # 默认日线
        if period_type == 'daily':
            frequency = '1d'
        elif period_type == 'weekly':
            frequency = '1w'
        elif period_type == 'monthly':
            frequency = '1M'
        elif period_type == '60min':
            frequency = '60m'
        elif period_type == '30min':
            frequency = '30m'
        elif period_type == '15min':
            frequency = '15m'
        elif period_type == '5min':
            frequency = '5m'
        elif period_type == '1min':
            frequency = '1m'
        
        # 计算需要获取的数据数量 - 充分利用Ashare的历史数据获取能力
        days_requested = (pd.to_datetime(end) - pd.to_datetime(start)).days
        
        if period_type in ['daily', 'weekly', 'monthly']:
            count = max(500, days_requested + 100)  # 日线数据至少500条，或根据请求天数调整
        elif period_type in ['60min']:
            # 60分钟线：每天约4条数据，获取足够的历史数据
            count = max(3000, days_requested * 6)  # 至少3000条，或按天数*6计算
        elif period_type in ['30min']:
            # 30分钟线：每天约8条数据
            count = max(5000, days_requested * 10)  # 至少5000条，或按天数*10计算
        elif period_type in ['15min']:
            # 15分钟线：每天约16条数据
            count = max(8000, days_requested * 20)  # 至少8000条，或按天数*20计算
        elif period_type in ['5min']:
            # 5分钟线：每天约48条数据
            count = max(10000, days_requested * 60)  # 至少10000条，或按天数*60计算
        elif period_type in ['1min']:
            # 1分钟线：每天约240条数据
            count = max(5000, min(days_requested * 300, 20000))  # 最多20000条，避免过大
        else:
            count = 2000
        
        print(f"正在获取 {formatted_code} 的 {frequency} 数据，数量: {count}")
        
        # 获取数据 - 对于日线数据，强制设置end_date为空，确保获取最新数据
        if period_type in ['daily', 'weekly', 'monthly']:
            # 强制获取最新数据，不设置end_date
            df = get_price(formatted_code, count=count, frequency=frequency)
            
            # 检查是否包含最新交易日的数据
            today = datetime.datetime.now().date()
            latest_trading_day = get_latest_trading_day(today)
            latest_trading_date = pd.to_datetime(latest_trading_day)
            
            # 如果数据中没有最新交易日的数据，尝试获取实时行情
            if not df.empty and latest_trading_date not in df.index:
                print(f"数据中缺少最新交易日 {latest_trading_date.date()} 的数据，尝试获取实时行情...")
                
                try:
                    # 暂时跳过实时行情获取，因为函数不存在
                    print("跳过实时行情获取，使用历史数据")
                    pass
                except Exception as e:
                    print(f"获取实时行情失败: {e}")
            
            # 检查当前是否为交易时间，如果是，更新最新价格
            now = datetime.datetime.now()
            is_trading_time = (
                (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 15
            ) and is_trading_day(now)
            
            if is_trading_time:
                try:
                    # 获取实时行情数据
                    # 跳过实时行情获取，因为函数不存在
                    real_time_data = pd.DataFrame()
                    
                    if not real_time_data.empty:
                        # 获取实时价格
                        latest_price = real_time_data['price'].iloc[0]
                        today_date = pd.to_datetime(now.strftime('%Y-%m-%d'))
                        
                        # 如果今天的数据已存在，更新价格
                        if today_date in df.index:
                            # 更新收盘价
                            df.loc[today_date, 'Close'] = latest_price
                            
                            # 更新最高价和最低价
                            if latest_price > df.loc[today_date, 'High']:
                                df.loc[today_date, 'High'] = latest_price
                            if latest_price < df.loc[today_date, 'Low']:
                                df.loc[today_date, 'Low'] = latest_price
                                
                            print(f"已更新今日 {today_date.date()} 的实时价格: {latest_price}")
                except Exception as e:
                    print(f"更新实时价格失败: {e}")
        else:
            # 分钟线数据正常获取
            df = get_price(formatted_code, count=count, frequency=frequency)
        
        if df.empty:
            print(f"Ashare获取数据为空: {formatted_code}")
            return pd.DataFrame()
            
        # 标准化列名
        column_mapping = {
            'Open': 'Open',
            'Close': 'Close', 
            'High': 'High',
            'Low': 'Low',
            'Volume': 'Volume',
            'open': 'Open',
            'close': 'Close',
            'high': 'High', 
            'low': 'Low',
            'volume': 'Volume'
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        print(f"✅ Ashare数据获取成功!")
        print(f"   📊 数据列名: {df.columns.tolist()}")
        print(f"   📈 数据形状: {df.shape}")
        print(f"   📅 原始数据时间范围: {df.index[0]} 到 {df.index[-1]}")
        print(f"   💰 最新价格: {df['Close'].iloc[-1]:.2f}")
        
        # 过滤日期范围
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        
        print(f"请求时间范围: {start_date} 到 {end_date}")
        print(f"原始数据时间范围: {df.index[0]} 到 {df.index[-1]}")
        
        # 🔧 修复日期过滤bug：end_date应该包含当天的所有时间
        # 将结束日期设置为当天的23:59:59，确保包含当天的所有数据
        if hasattr(end_date, 'date'):
            end_date_inclusive = pd.to_datetime(end_date.date()) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        else:
            end_date_inclusive = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        print(f"修正后的结束时间: {end_date_inclusive}")
        
        # 使用修正后的结束时间进行过滤
        df_filtered = df[(df.index >= start_date) & (df.index <= end_date_inclusive)]
        
        if df_filtered.empty:
            print(f"按请求时间范围过滤后数据为空")
            # 如果按请求时间范围过滤后为空，检查是否是因为请求的时间范围超出了数据范围
            if start_date > df.index[-1]:
                st.warning(f"请求的开始时间 {start_date.date()} 晚于数据的最新时间 {df.index[-1].date()}，返回最新数据")
                return df.tail(min(500, len(df)))
            elif end_date < df.index[0]:
                st.warning(f"请求的结束时间 {end_date.date()} 早于数据的最早时间 {df.index[0].date()}，返回最早数据")
                return df.head(min(500, len(df)))
            else:
                # 如果时间范围有重叠但过滤后为空，可能是非交易时间，返回时间范围内最接近的数据
                st.info("请求的时间范围内可能没有交易数据，返回相近时间的数据")
                # 找到最接近请求时间范围的数据
                closest_data = df[(df.index <= end_date)]
                if not closest_data.empty:
                    return closest_data.tail(min(500, len(closest_data)))
                else:
                    return df.head(min(500, len(df)))
        
        print(f"✅ 数据过滤完成!")
        print(f"   📊 过滤后数据条数: {len(df_filtered)}")
        print(f"   📅 过滤后时间范围: {df_filtered.index[0]} 到 {df_filtered.index[-1]}")
        print(f"   💰 最新收盘价: {df_filtered['Close'].iloc[-1]:.2f}")
        
        # 🔧 过滤非交易日，确保K线连续显示
        if period_type in ['daily', 'weekly', 'monthly']:
            from .trading_calendar import filter_trading_days
            df_filtered = filter_trading_days(df_filtered)
            
            if not df_filtered.empty:
                print(f"📅 交易日过滤后: {len(df_filtered)} 条数据")
                print(f"   📅 最终时间范围: {df_filtered.index[0]} 到 {df_filtered.index[-1]}")
        
        return df_filtered
        
    except Exception as e:
        st.error(f"Ashare数据获取失败: {str(e)}")
        print(f"详细错误: {str(e)}")
        return pd.DataFrame()

@cached_stock_data(cache_type='daily_data')
def get_stock_data_ak(symbol, start_date, end_date, period):
    """使用AKShare获取股票数据"""
    try:
        # 检查股票代码是否为ETF或指数
        # ETF代码规则: 上交所(51开头)，深交所(15开头)
        is_etf = symbol.startswith(('51', '15', '16', '56', '58', '50', '159', '512', '513', '510', '511', '515', '516', '518', '588', '501'))
        
        # 检查是否为特殊板块指数
        is_index = symbol.startswith(('88', '000', '399'))
        
        # 处理特殊板块指数
        if is_index and symbol.startswith('88'):
            try:
                # 尝试获取板块指数数据
                st.info(f"正在获取板块指数 {symbol} 的数据...")
                # 使用股票板块指数数据接口
                df = ak.stock_board_industry_index_ths(symbol=symbol)
                
                # 确保日期在指定范围内
                df['日期'] = pd.to_datetime(df['日期'])
                mask = (df['日期'] >= pd.to_datetime(start_date)) & (df['日期'] <= pd.to_datetime(end_date))
                df = df.loc[mask]
                
                # 重命名列以匹配标准格式
                df = df.rename(columns={
                    '开盘': 'Open',
                    '收盘': 'Close',
                    '最高': 'High',
                    '最低': 'Low',
                    '成交量': 'Volume'
                })
                
                # 设置日期为索引
                df.set_index('日期', inplace=True)
                
                # 根据周期重采样
                if period == "weekly":
                    df = df.resample('W').agg({
                        'Open': 'first', 
                        'High': 'max', 
                        'Low': 'min', 
                        'Close': 'last',
                        'Volume': 'sum'
                    })
                elif period == "monthly":
                    df = df.resample('M').agg({
                        'Open': 'first', 
                        'High': 'max', 
                        'Low': 'min', 
                        'Close': 'last',
                        'Volume': 'sum'
                    })
                
                return df
            except Exception as e:
                st.warning(f"获取板块指数数据失败: {e}，尝试使用其他方法...")
        
        if period == "daily":
            # 日线数据
            if is_etf:
                # 使用新浪ETF接口获取ETF数据
                if symbol.startswith(('5', '588')):
                    sina_symbol = f"sh{symbol}"  # 上海ETF
                else:
                    sina_symbol = f"sz{symbol}"  # 深圳ETF
                
                df = ak.fund_etf_hist_sina(symbol=sina_symbol)
                # 确保日期在指定范围内
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
                df = df.loc[mask]
            elif is_index and symbol.startswith(('000', '399')):
                # 获取指数数据
                if symbol.startswith('000'):
                    index_symbol = f"sh{symbol}"
                else:
                    index_symbol = f"sz{symbol}"
                
                df = ak.stock_zh_index_daily(symbol=index_symbol)
                # 确保日期在指定范围内
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
                df = df.loc[mask]
            else:
                # 普通股票数据
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                       start_date=start_date.strftime('%Y%m%d'), 
                                       end_date=end_date.strftime('%Y%m%d'),
                                       adjust="qfq")
        elif period == "weekly":
            # 周线数据
            if is_etf:
                # 直接使用日线数据然后重采样为周线数据
                if symbol.startswith(('5', '588')):
                    sina_symbol = f"sh{symbol}"  # 上海ETF
                else:
                    sina_symbol = f"sz{symbol}"  # 深圳ETF
                
                df_daily = ak.fund_etf_hist_sina(symbol=sina_symbol)
                # 确保日期在指定范围内
                df_daily['date'] = pd.to_datetime(df_daily['date'])
                mask = (df_daily['date'] >= pd.to_datetime(start_date)) & (df_daily['date'] <= pd.to_datetime(end_date))
                df_daily = df_daily.loc[mask]
                
                # 设置日期为索引进行重采样
                df_daily.set_index('date', inplace=True)
                # 重采样为周线数据
                df = df_daily.resample('W').agg({
                    'open': 'first', 
                    'high': 'max', 
                    'low': 'min', 
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()
                df.rename(columns={'index': 'date'}, inplace=True)
            elif is_index and symbol.startswith(('000', '399')):
                # 获取指数日线数据然后重采样
                if symbol.startswith('000'):
                    index_symbol = f"sh{symbol}"
                else:
                    index_symbol = f"sz{symbol}"
                
                df_daily = ak.stock_zh_index_daily(symbol=index_symbol)
                # 确保日期在指定范围内
                df_daily['date'] = pd.to_datetime(df_daily['date'])
                mask = (df_daily['date'] >= pd.to_datetime(start_date)) & (df_daily['date'] <= pd.to_datetime(end_date))
                df_daily = df_daily.loc[mask]
                
                # 设置日期为索引进行重采样
                df_daily.set_index('date', inplace=True)
                # 重采样为周线数据
                df = df_daily.resample('W').agg({
                    'open': 'first', 
                    'high': 'max', 
                    'low': 'min', 
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()
                df.rename(columns={'index': 'date'}, inplace=True)
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="weekly", 
                                       start_date=start_date.strftime('%Y%m%d'), 
                                       end_date=end_date.strftime('%Y%m%d'),
                                       adjust="qfq")
        elif period == "monthly":
            # 月线数据
            if is_etf:
                # 直接使用日线数据然后重采样为月线数据
                if symbol.startswith(('5', '588')):
                    sina_symbol = f"sh{symbol}"  # 上海ETF
                else:
                    sina_symbol = f"sz{symbol}"  # 深圳ETF
                
                df_daily = ak.fund_etf_hist_sina(symbol=sina_symbol)
                # 确保日期在指定范围内
                df_daily['date'] = pd.to_datetime(df_daily['date'])
                mask = (df_daily['date'] >= pd.to_datetime(start_date)) & (df_daily['date'] <= pd.to_datetime(end_date))
                df_daily = df_daily.loc[mask]
                
                # 设置日期为索引进行重采样
                df_daily.set_index('date', inplace=True)
                # 重采样为月线数据
                df = df_daily.resample('M').agg({
                    'open': 'first', 
                    'high': 'max', 
                    'low': 'min', 
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()
                df.rename(columns={'index': 'date'}, inplace=True)
            elif is_index and symbol.startswith(('000', '399')):
                # 获取指数日线数据然后重采样
                if symbol.startswith('000'):
                    index_symbol = f"sh{symbol}"
                else:
                    index_symbol = f"sz{symbol}"
                
                df_daily = ak.stock_zh_index_daily(symbol=index_symbol)
                # 确保日期在指定范围内
                df_daily['date'] = pd.to_datetime(df_daily['date'])
                mask = (df_daily['date'] >= pd.to_datetime(start_date)) & (df_daily['date'] <= pd.to_datetime(end_date))
                df_daily = df_daily.loc[mask]
                
                # 设置日期为索引进行重采样
                df_daily.set_index('date', inplace=True)
                # 重采样为月线数据
                df = df_daily.resample('M').agg({
                    'open': 'first', 
                    'high': 'max', 
                    'low': 'min', 
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()
                df.rename(columns={'index': 'date'}, inplace=True)
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="monthly", 
                                       start_date=start_date.strftime('%Y%m%d'), 
                                       end_date=end_date.strftime('%Y%m%d'),
                                       adjust="qfq")
        elif period in ["5min", "15min", "30min", "60min"]:
            # 提取数字部分作为period参数
            period_num = period.replace("min", "")
            
            # 处理时间格式 - 使用正确的时间格式
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # 格式化股票代码
            if symbol.startswith('6'):
                formatted_symbol = f"sh{symbol}"
            elif symbol.startswith('0') or symbol.startswith('3'):
                formatted_symbol = f"sz{symbol}"
            else:
                formatted_symbol = symbol
                
            try:
                # 尝试使用stock_zh_a_minute获取数据 (新浪API)
                st.info(f"正在尝试获取 {symbol} 的 {period} 数据 - 方法1 (新浪API)...")
                df = ak.stock_zh_a_minute(symbol=formatted_symbol, period=period_num, adjust="qfq")
                
                if df is not None and not df.empty:
                    # 确保索引是日期格式
                    if 'day' in df.columns:
                        df = df.rename(columns={'day': 'Date'})
                    
                    # 保持列名一致性并设置索引
                    df = df.rename(columns={
                        'open': 'Open',
                        'high': 'High',
                        'low': 'Low',
                        'close': 'Close',
                        'volume': 'Volume'
                    })
                    
                    # 设置索引
                    if 'Date' in df.columns:
                        df['Date'] = pd.to_datetime(df['Date'])
                        df.set_index('Date', inplace=True)
                    else:
                        st.error(f"无法获取 {symbol} 的 {period} 分钟级数据。分钟级别数据通常只能获取最近几天的交易数据，请尝试选择其他周期或其他股票。")
                        return pd.DataFrame()
                else:
                    st.error(f"无法获取 {symbol} 的 {period} 分钟级数据。分钟级别数据通常只能获取最近几天的交易数据，请尝试选择其他周期或其他股票。")
                    return pd.DataFrame()
                    
            except Exception as e3:
                st.error(f"所有获取分钟数据的方法都失败: {e3}。分钟级数据通常受到数据源API的限制，只能获取最近的交易数据。")
                return pd.DataFrame()
                    
        else:
            raise ValueError(f"不支持的周期: {period}")
        
        # 最终检查和处理返回的数据
        if df is not None and not df.empty:
            # 检查并标准化列名
            # 首先检查是否有中文列名
            if '开盘' in df.columns:
                df = df.rename(columns={
                    '开盘': 'Open',
                    '收盘': 'Close',
                    '最高': 'High',
                    '最低': 'Low',
                    '成交量': 'Volume'
                })
            # 检查是否有小写列名
            elif 'open' in df.columns:
                df = df.rename(columns={
                    'open': 'Open',
                    'close': 'Close',
                    'high': 'High',
                    'low': 'Low',
                    'volume': 'Volume'
                })
            
            # 确保所有必要的列都存在
            required_cols = ['Open', 'Close', 'High', 'Low', 'Volume']
            for col in required_cols:
                if col not in df.columns:
                    st.warning(f"获取的数据缺少 {col} 列，尝试从其他列补充")
                    # 尝试从其他可能的列名补充
                    alt_col_maps = {
                        'Open': ['open', '开盘', '开盘价'],
                        'Close': ['close', '收盘', '收盘价'],
                        'High': ['high', '最高', '最高价'],
                        'Low': ['low', '最低', '最低价'],
                        'Volume': ['volume', '成交量']
                    }
                    
                    for alt_col in alt_col_maps[col]:
                        if alt_col in df.columns:
                            df[col] = df[alt_col]
                            break
                    
                    # 如果仍然缺少该列，创建一个默认值
                    if col not in df.columns:
                        if col == 'Volume':
                            df[col] = 0
                        else:
                            # 使用收盘价填充其他缺失价格
                            if 'Close' in df.columns:
                                df[col] = df['Close']
                            elif '收盘' in df.columns:
                                df[col] = df['收盘']
                            else:
                                # 最后的备选方案：使用常数值
                                df[col] = 0.0
            
            # 确保所有数值列是浮点型
            for col in required_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        else:
            st.error(f"未能获取到代码 {symbol} 的数据，请检查代码是否正确")
            return pd.DataFrame()
    
    except Exception as e:
        st.error(f"获取AKShare数据时出错: {str(e)}")
        return pd.DataFrame()

def get_stock_data(symbol, start, end, period_type, data_source="Ashare"):
def get_stock_data(symbol, start, end, period_type, data_source="Ashare"):
    """获取股票数据的主函数，根据数据源选择不同的获取方法"""
    try:
        # 确保日期格式正确
        if not isinstance(start, (str, pd.Timestamp, datetime.datetime)):
            start = pd.to_datetime(start, format='%Y%m%d')
        if not isinstance(end, (str, pd.Timestamp, datetime.datetime)):
            end = pd.to_datetime(end, format='%Y%m%d')
        
        # 根据用户选择的数据源
        if data_source == "Ashare" and has_ashare:
            df = get_stock_data_ashare(symbol, start, end, period_type)
        elif data_source == "Ashare" and not has_ashare:
            st.warning("💡 未检测到Ashare模块，使用AKShare数据源")
            df = get_stock_data_ak(symbol, start, end, period_type)
        else:
            # 使用AKShare数据源（用户选择AKShare或其他数据源不可用时的备用）
            df = get_stock_data_ak(symbol, start, end, period_type)
        
        # 🔧 统一应用交易日过滤，确保K线连续显示
        if not df.empty and period_type in ['daily', 'weekly', 'monthly']:
            from .trading_calendar import filter_trading_days
            original_count = len(df)
            df = filter_trading_days(df)
            filtered_count = len(df)
            
            if filtered_count < original_count:
                print(f"📅 交易日过滤: {original_count} → {filtered_count} 条数据")
                print(f"   ✅ 已过滤掉 {original_count - filtered_count} 个非交易日")
        
        return df
                    df = ak.fund_etf_hist_sina(symbol=sina_symbol)
                    # 确保日期在指定范围内
                    df['date'] = pd.to_datetime(df['date'])
                    mask = (df['date'] >= pd.to_datetime(start)) & (df['date'] <= pd.to_datetime(end))
                    df = df.loc[mask]
                    
                    if df.empty:
                        st.warning(f"获取ETF {symbol} 数据为空，请检查代码和日期范围是否正确")
                        return pd.DataFrame()
                    
                    # 如果是周线或月线，需要重采样
                    if period_type == "weekly":
                        df.set_index('date', inplace=True)
                        df = df.resample('W').agg({
                            'open': 'first', 
                            'high': 'max', 
                            'low': 'min', 
                            'close': 'last',
                            'volume': 'sum'
                        })
                    elif period_type == "monthly":
                        df.set_index('date', inplace=True)
                        df = df.resample('M').agg({
                            'open': 'first', 
                            'high': 'max', 
                            'low': 'min', 
                            'close': 'last',
                            'volume': 'sum'
                        })
                    else:
                        df.set_index('date', inplace=True)
                    
                    # 重命名列以匹配A股数据格式
                    df.rename(columns={
                        'open': '开盘',
                        'high': '最高',
                        'low': '最低',
                        'close': '收盘',
                        'volume': '成交量'
                    }, inplace=True)
                    
                    # 计算涨跌幅等指标
                    df['涨跌额'] = df['收盘'].diff()
                    df['涨跌幅'] = df['收盘'].pct_change() * 100
                    
                    return df
                except Exception as e:
                    st.error(f"获取ETF数据失败: {e}，尝试使用股票接口获取...")
                    # 如果ETF接口失败，尝试使用普通股票接口
                    try:
                        # 确保是字符串格式
                        start_date = start.strftime("%Y%m%d") if hasattr(start, 'strftime') else pd.to_datetime(start).strftime("%Y%m%d")
                        end_date = end.strftime("%Y%m%d") if hasattr(end, 'strftime') else pd.to_datetime(end).strftime("%Y%m%d")
                        
                        df = ak.stock_zh_a_hist(
                            symbol=symbol,
                            period=period_type,
                            start_date=start_date,
                            end_date=end_date,
                            adjust="qfq"
                        )
                        if df.empty:
                            return pd.DataFrame()
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
                        
                        return df
                    except Exception as inner_e:
                        st.error(f"备用方法也失败: {inner_e}")
                        return pd.DataFrame()
            else:
                # 确保是字符串格式
                start_date = start.strftime("%Y%m%d") if hasattr(start, 'strftime') else pd.to_datetime(start).strftime("%Y%m%d")
                end_date = end.strftime("%Y%m%d") if hasattr(end, 'strftime') else pd.to_datetime(end).strftime("%Y%m%d")
                
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period_type,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                if df.empty:
                    return pd.DataFrame()
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.sort_values('日期').set_index('日期')
                
                # 标准化列名
                # 标准化列名
                if '开盘' in df.columns:
                    df = df.rename(columns={
                        '开盘': 'Open',
                        '收盘': 'Close',
                        '最高': 'High',
                        '最低': 'Low',
                        '成交量': 'Volume'
                    })
                
                # 🔧 过滤非交易日，确保K线连续显示
                if period in ['daily', 'weekly', 'monthly']:
                    from .trading_calendar import filter_trading_days
                    df = filter_trading_days(df)
                    
                    if not df.empty:
                        print(f"📅 AKShare交易日过滤后: {len(df)} 条数据")
                
                return df
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return pd.DataFrame()


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

# 尝试导入Tushare相关模块
try:
    import sys
    import os
    # 添加aitrader_core到路径
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'aitrader_core'))
    from datafeed.tushare_loader import get_stock_data as tushare_get_stock_data
    has_tushare = True
except ImportError:
    has_tushare = False
    print("⚠️ Tushare模块未找到")

# 尝试导入CSV数据加载器
try:
    from datafeed.csv_dataloader import CsvDataLoader
    has_csv = True
except ImportError:
    has_csv = False
    print("⚠️ CSV数据加载器未找到")

def get_stock_data_tushare(symbol, start, end, period_type):
    """使用Tushare获取股票数据"""
    if not has_tushare:
        st.warning("Tushare模块不可用，请检查aitrader_core/datafeed/tushare_loader.py")
        return pd.DataFrame()
    
    try:
        # 格式化股票代码为Tushare格式 (如: 600519.SH)
        if '.' not in symbol:
            if symbol.startswith('6'):
                symbol = f"{symbol}.SH"
            elif symbol.startswith(('0', '3')):
                symbol = f"{symbol}.SZ"
        
        print(f"🔄 正在使用Tushare获取 {symbol} 的数据...")
        
        # 调用tushare_loader (注意：tushare_loader没有freq参数，只支持日线)
        df = tushare_get_stock_data(
            symbol=symbol,
            start_date=start.strftime('%Y%m%d') if hasattr(start, 'strftime') else str(start).replace('-', ''),
            end_date=end.strftime('%Y%m%d') if hasattr(end, 'strftime') else str(end).replace('-', '')
        )
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 标准化列名 (tushare返回小写列名)
        column_mapping = {
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 确保Date列是datetime类型
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
        
        # 只保留需要的列
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_columns = [col for col in required_columns if col in df.columns]
        df = df[available_columns]
        
        # 按日期排序
        df = df.sort_index()
        
        print(f"✅ Tushare数据获取成功! 数据条数: {len(df)}")
        return df
        
    except Exception as e:
        st.error(f"Tushare数据获取失败: {str(e)}")
        import traceback
        print(f"Tushare错误详情: {traceback.format_exc()}")
        return pd.DataFrame()

def get_stock_data_csv(symbol, start, end, period_type):
    """从本地CSV文件获取股票数据"""
    if not has_csv:
        st.warning("CSV数据加载器不可用")
        return pd.DataFrame()
    
    try:
        # 格式化股票代码
        if '.' not in symbol:
            if symbol.startswith('6'):
                symbol = f"{symbol}.SH"
            elif symbol.startswith(('0', '3')):
                symbol = f"{symbol}.SZ"
        
        print(f"🔄 正在从本地CSV获取 {symbol} 的数据...")
        
        # 首先尝试用户目录下的stock_data文件夹
        user_stock_data_dir = os.path.expanduser('~/stock_data')
        
        # 创建CSV加载器实例 (CsvDataLoader不接受data_dir参数)
        csv_loader = CsvDataLoader()
        
        # 根据路径决定使用哪个目录
        if os.path.exists(user_stock_data_dir):
            csv_path = user_stock_data_dir
            print(f"📁 使用用户数据目录: {user_stock_data_dir}")
        else:
            # 回退到默认路径 (使用'quotes'会自动使用DATA_DIR/quotes)
            csv_path = 'quotes'
            print(f"📁 使用默认数据目录")
        
        # 读取CSV数据 (传入path参数)
        df = csv_loader._read_csv(symbol, path=csv_path)
        
        if df is None or df.empty:
            st.warning(f"本地CSV未找到 {symbol} 的数据文件")
            st.info("💡 请先在「AI数据管理」中更新股票数据")
            return pd.DataFrame()
        
        # 标准化列名 (CSV通常返回小写列名)
        column_mapping = {
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 确保Date列是datetime类型并设置为索引
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
        
        # 只保留需要的列
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_columns = [col for col in required_columns if col in df.columns]
        df = df[available_columns]
        
        # 按日期过滤
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        if df.empty:
            st.warning(f"⚠️ 在指定日期范围内({start} 至 {end})未找到数据")
            return pd.DataFrame()
        
        print(f"✅ CSV数据加载成功! 数据条数: {len(df)}")
        return df
        
    except Exception as e:
        st.error(f"CSV数据加载失败: {str(e)}")
        import traceback
        print(f"CSV错误详情: {traceback.format_exc()}")
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
        elif data_source == "Tushare":
            if has_tushare:
                df = get_stock_data_tushare(symbol, start, end, period_type)
            else:
                st.warning("💡 Tushare模块不可用，回退到AKShare")
                df = get_stock_data_ak(symbol, start, end, period_type)
        elif data_source == "本地CSV":
            if has_csv:
                df = get_stock_data_csv(symbol, start, end, period_type)
            else:
                st.warning("💡 CSV数据源不可用，回退到AKShare")
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
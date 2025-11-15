"""
数据模块 - 负责获取和处理股票数据
修复版本，确保交易日过滤功能正常工作

支持同步和异步两种模式：
- 同步模式：get_stock_data() - 单只股票
- 异步模式：get_multiple_stocks_data_async() - 批量股票（性能提升3-5倍）
"""
import asyncio
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Union

import akshare as ak
import pandas as pd
import streamlit as st

from .constants import (
    ASYNC_BATCH_FETCH_WORKERS,
    CACHE_TTL_LOCAL_DATA,
    CACHE_TTL_ONLINE_DATA,
    DATA_BUFFER_DAYS,
    MAX_DATA_COUNT_DAILY,
    MAX_DATA_COUNT_MONTHLY,
    MAX_DATA_COUNT_WEEKLY,
    MAX_RETURN_ROWS,
    MIN_DATA_COUNT_DAILY,
    MIN_DATA_COUNT_MONTHLY,
    MIN_DATA_COUNT_WEEKLY,
)
from .error_handler import handle_data_error
from .logger_config import get_logger
from .smart_data_manager import cached_realtime_data, cached_stock_data, smart_data_manager
from .utils import format_stock_code

# 导入重试机制
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        RetryError
    )
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False
    logger.warning("tenacity 未安装，重试功能将不可用")

logger = get_logger(__name__)


# ========== 数据验证函数 ==========

def validate_stock_code(symbol: str) -> tuple[bool, str]:
    """
    验证股票代码格式
    
    Args:
        symbol: 股票代码
        
    Returns:
        (is_valid, error_message): 验证结果和错误信息
    """
    if not symbol:
        return False, "股票代码不能为空"
    
    # 移除空格和特殊字符
    symbol = str(symbol).strip()
    
    # 提取纯数字部分
    if '.' in symbol:
        code_part = symbol.split('.')[0]
    elif symbol.startswith(('sh', 'sz', 'bj', 'nq')):
        code_part = symbol[2:]
    else:
        code_part = symbol
    
    # 检查是否为6位数字
    if not code_part.isdigit():
        return False, f"股票代码格式错误：'{symbol}' 应包含6位数字"
    
    if len(code_part) != 6:
        return False, f"股票代码长度错误：'{symbol}' 应为6位数字"
    
    # 检查是否在有效范围内（A股、创业板、科创板等）
    code_int = int(code_part)
    valid_ranges = [
        (600000, 605999),  # 上海A股
        (0, 2999),  # 深圳A股 (000000-002999)
        (300000, 301999),  # 创业板
        (688000, 688999),  # 科创板
        (430000, 439999),  # 新三板
        (830000, 839999),  # 新三板
    ]
    
    # 检查深圳A股（000000-002999）需要特殊处理
    is_valid = any(start <= code_int <= end for start, end in valid_ranges)
    # 深圳A股特殊检查：000000-002999
    if not is_valid and 0 <= code_int <= 2999:
        is_valid = True
    
    if not is_valid:
        return False, f"股票代码 '{symbol}' 不在有效的A股代码范围内"
    
    return True, ""


def validate_date_range(
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp]
) -> tuple[bool, str]:
    """
    验证日期范围
    
    Args:
        start: 开始日期
        end: 结束日期
        
    Returns:
        (is_valid, error_message): 验证结果和错误信息
    """
    try:
        # 转换为datetime
        if isinstance(start, str):
            start = pd.to_datetime(start)
        if isinstance(end, str):
            end = pd.to_datetime(end)
        
        # 检查日期顺序
        if end < start:
            return False, f"结束日期（{end.strftime('%Y-%m-%d')}）不能早于开始日期（{start.strftime('%Y-%m-%d')}）"
        
        # 检查未来日期
        now = datetime.datetime.now()
        if end > now:
            return False, f"结束日期（{end.strftime('%Y-%m-%d')}）不能是未来日期"
        
        # 检查日期范围（不能超过5年）
        days_diff = (end - start).days
        if days_diff > 365 * 5:
            return False, f"日期范围不能超过5年（当前：{days_diff}天）"
        
        # 检查开始日期不能太早（A股数据通常从1990年开始）
        if start < pd.to_datetime('1990-01-01'):
            return False, f"开始日期（{start.strftime('%Y-%m-%d')}）不能早于1990年（A股市场起始时间）"
        
        return True, ""
        
    except Exception as e:
        return False, f"日期格式错误：{str(e)}"


def format_user_friendly_error(
    error: Exception,
    symbol: str,
    data_source: str,
    context: str = ""
) -> str:
    """
    格式化用户友好的错误信息
    
    Args:
        error: 异常对象
        data_source: 数据源名称
        context: 上下文信息
        
    Returns:
        格式化的错误信息
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # 根据错误类型提供不同的提示
    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        return f"⏱️ 数据获取超时\n\n**原因：** 网络连接较慢或数据源响应超时\n**股票：** {symbol}\n**数据源：** {data_source}\n\n💡 **建议：**\n- 检查网络连接\n- 稍后重试\n- 尝试切换数据源"
    
    elif "connection" in error_msg.lower() or "网络" in error_msg:
        return f"🌐 网络连接失败\n\n**原因：** 无法连接到数据源服务器\n**股票：** {symbol}\n**数据源：** {data_source}\n\n💡 **建议：**\n- 检查网络连接\n- 检查防火墙设置\n- 尝试切换数据源"
    
    elif "not found" in error_msg.lower() or "不存在" in error_msg or "404" in error_msg:
        return f"❌ 股票代码不存在\n\n**原因：** 未找到股票 '{symbol}' 的数据\n**数据源：** {data_source}\n\n💡 **建议：**\n- 检查股票代码是否正确\n- 确认股票是否已退市\n- 尝试其他股票代码"
    
    elif "rate limit" in error_msg.lower() or "频率" in error_msg or "限制" in error_msg:
        return f"⏸️ 请求过于频繁\n\n**原因：** 数据源API请求频率限制\n**数据源：** {data_source}\n\n💡 **建议：**\n- 等待30秒后重试\n- 尝试切换数据源\n- 减少请求频率"
    
    elif "permission" in error_msg.lower() or "权限" in error_msg or "401" in error_msg or "403" in error_msg:
        return f"🔒 权限不足\n\n**原因：** 数据源访问权限受限\n**数据源：** {data_source}\n\n💡 **建议：**\n- 检查API密钥配置\n- 确认账户权限\n- 联系数据源提供商"
    
    else:
        # 通用错误信息
        return f"❌ 数据获取失败\n\n**错误类型：** {error_type}\n**错误信息：** {error_msg}\n**股票：** {symbol}\n**数据源：** {data_source}\n\n💡 **建议：**\n- 检查股票代码和日期范围\n- 尝试切换数据源\n- 稍后重试\n- 如问题持续，请联系技术支持"


def check_data_quality(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    检查数据质量
    
    Args:
        df: 股票数据DataFrame
        symbol: 股票代码
        
    Returns:
        dict: 数据质量信息
    """
    quality = {
        'is_latest': False,
        'is_complete': False,
        'has_delay': False,
        'missing_days': 0,
        'warnings': []
    }
    
    if df.empty:
        quality['warnings'].append("数据为空")
        return quality
    
    try:
        from .trading_calendar import get_latest_trading_day
        
        # 检查是否包含最新交易日
        latest_trading_day = get_latest_trading_day()
        latest_trading_date = pd.to_datetime(latest_trading_day)
        
        if latest_trading_date in df.index:
            quality['is_latest'] = True
        else:
            quality['has_delay'] = True
            days_delay = (pd.to_datetime('today') - df.index[-1]).days
            if days_delay > 3:
                quality['warnings'].append(f"数据可能不是最新的，最新数据日期：{df.index[-1].strftime('%Y-%m-%d')}，延迟约 {days_delay} 天")
        
        # 检查数据完整性（检查是否有缺失的交易日）
        if len(df) > 1:
            # 计算预期交易日数（粗略估计）
            date_range = (df.index[-1] - df.index[0]).days
            # 假设交易日占比约65%（排除周末和节假日）
            expected_trading_days = int(date_range * 0.65)
            actual_days = len(df)
            
            if actual_days < expected_trading_days * 0.9:
                quality['is_complete'] = False
                quality['missing_days'] = expected_trading_days - actual_days
                if quality['missing_days'] > 10:
                    quality['warnings'].append(f"数据可能不完整，预期约 {expected_trading_days} 个交易日，实际 {actual_days} 个，缺失约 {quality['missing_days']} 天")
        
        # 检查数据异常值
        if 'Close' in df.columns:
            # 检查是否有异常的价格波动（单日涨跌幅超过20%）
            if len(df) > 1:
                pct_change = df['Close'].pct_change().abs()
                extreme_changes = pct_change[pct_change > 0.2]
                if len(extreme_changes) > 0:
                    quality['warnings'].append(f"发现 {len(extreme_changes)} 个异常价格波动（单日涨跌幅>20%），请检查数据准确性")
        
        quality['is_complete'] = True if not quality['warnings'] else False
        
    except Exception as e:
        logger.warning(f"数据质量检查失败: {e}")
        quality['warnings'].append("数据质量检查失败")
    
    return quality


def _get_stock_data_with_retry(
    symbol: str,
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str,
    data_source: str,
) -> pd.DataFrame:
    """
    带重试机制的数据获取函数
    
    Args:
        symbol: 股票代码
        start: 开始日期
        end: 结束日期
        period_type: 数据周期类型
        data_source: 数据源
        
    Returns:
        pd.DataFrame: 股票数据
    """
    # 定义重试装饰器（仅对网络错误重试）
    if HAS_TENACITY:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError))
        )
        def _fetch_with_retry():
            if data_source == "Ashare" and has_ashare:
                return get_stock_data_ashare(symbol, start, end, period_type)
            elif data_source == "Ashare" and not has_ashare:
                st.warning("💡 未检测到Ashare模块，使用AKShare数据源")
                return get_stock_data_ak(symbol, start, end, period_type)
            elif data_source == "Tushare":
                if has_tushare:
                    return get_stock_data_tushare(symbol, start, end, period_type)
                else:
                    st.warning("💡 Tushare模块不可用，回退到AKShare")
                    return get_stock_data_ak(symbol, start, end, period_type)
            elif data_source == "本地CSV":
                if has_csv:
                    return get_stock_data_csv(symbol, start, end, period_type)
                else:
                    st.warning("💡 CSV数据源不可用，回退到AKShare")
                    return get_stock_data_ak(symbol, start, end, period_type)
            else:
                # 使用AKShare数据源
                return get_stock_data_ak(symbol, start, end, period_type)
        
        try:
            return _fetch_with_retry()
        except RetryError as e:
            # 重试失败后，尝试切换到备用数据源
            logger.warning(f"数据源 {data_source} 重试失败，尝试备用数据源: {e}")
            if data_source != "AKShare":
                st.warning(f"💡 {data_source} 数据源失败，切换到AKShare")
                return get_stock_data_ak(symbol, start, end, period_type)
            else:
                raise
    else:
        # 如果没有tenacity，直接调用（无重试）
        if data_source == "Ashare" and has_ashare:
            return get_stock_data_ashare(symbol, start, end, period_type)
        elif data_source == "Ashare" and not has_ashare:
            st.warning("💡 未检测到Ashare模块，使用AKShare数据源")
            return get_stock_data_ak(symbol, start, end, period_type)
        elif data_source == "Tushare":
            if has_tushare:
                return get_stock_data_tushare(symbol, start, end, period_type)
            else:
                st.warning("💡 Tushare模块不可用，回退到AKShare")
                return get_stock_data_ak(symbol, start, end, period_type)
        elif data_source == "本地CSV":
            if has_csv:
                return get_stock_data_csv(symbol, start, end, period_type)
            else:
                st.warning("💡 CSV数据源不可用，回退到AKShare")
                return get_stock_data_ak(symbol, start, end, period_type)
        else:
            # 使用AKShare数据源
            return get_stock_data_ak(symbol, start, end, period_type)


# 检查数据源可用性
try:
    # 显式导入，避免命名冲突
    # 注意：Ashare模块可能导出多个函数，这里只导入常用的
    from .Ashare import (
        get_price,  # Ashare的主要数据获取函数
        get_realtime_quotes_sina,
        get_stock_name,
    )
    has_ashare = True
    logger.info("✅ Ashare模块加载成功")
except ImportError:
    has_ashare = False
    logger.warning("❌ Ashare模块未找到，将使用AKShare作为备用数据源")
    # 定义占位函数，避免后续调用错误
    get_price = None
    get_realtime_quotes_sina = None
    get_stock_name = None


@st.cache_data(ttl=CACHE_TTL_ONLINE_DATA, show_spinner=False)
def get_stock_data_ashare(
    symbol: str,
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str,
) -> pd.DataFrame:
    """
    使用Ashare获取股票数据
    
    Args:
        symbol: 股票代码（如 '600519' 或 '000001'）
        start: 开始日期（字符串、datetime或Timestamp）
        end: 结束日期（字符串、datetime或Timestamp）
        period_type: 数据周期类型（'daily'/'weekly'/'monthly'）
    
    Returns:
        pd.DataFrame: 包含OHLCV数据的DataFrame，索引为日期
    
    Raises:
        Exception: 数据获取失败时抛出异常
    
    Example:
        >>> df = get_stock_data_ashare('600519', '2023-01-01', '2023-12-31', 'daily')
        >>> print(df.head())
    """
    try:
        # 格式化股票代码
        formatted_symbol = format_stock_code(symbol)

        # 转换日期格式
        # 转换日期格式 - Ashare只支持end_date和count参数
        end_str = end.strftime("%Y-%m-%d") if hasattr(end, "strftime") else str(end)

        # 计算需要获取的数据量
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        days_diff = (end_date - start_date).days

        # 根据周期类型计算count
        if period_type == "daily":
            count = min(
                max(days_diff + DATA_BUFFER_DAYS, MIN_DATA_COUNT_DAILY), MAX_DATA_COUNT_DAILY
            )
            frequency = "1d"
        elif period_type == "weekly":
            count = min(max(days_diff // 7 + 20, MIN_DATA_COUNT_WEEKLY), MAX_DATA_COUNT_WEEKLY)
            frequency = "1w"
        elif period_type == "monthly":
            count = min(max(days_diff // 30 + 12, MIN_DATA_COUNT_MONTHLY), MAX_DATA_COUNT_MONTHLY)
            frequency = "1M"
        else:
            st.error(f"不支持的数据周期: {period_type}")
            return pd.DataFrame()

        logger.info(f"🔄 正在使用Ashare获取 {formatted_symbol} 的数据...")
        logger.debug(f"   📅 结束日期: {end_str}")
        logger.debug(f"   📊 数据类型: {period_type}")
        logger.debug(f"   📈 获取数量: {count} 条")

        # 使用Ashare获取数据
        df = get_price(formatted_symbol, end_date=end_str, count=count, frequency=frequency)

        if df.empty:
            logger.warning(f"❌ Ashare获取 {formatted_symbol} 数据为空")
            return pd.DataFrame()

        # 标准化列名 - 先检查实际列数，避免列数不匹配错误
        logger.debug(f"📊 Ashare返回的列: {list(df.columns)}, 列数: {len(df.columns)}")
        
        # 根据实际列名映射到标准列名
        column_mapping = {}
        # 可能的列名变体
        possible_names = {
            'open': 'Open',
            'Open': 'Open',
            'high': 'High',
            'High': 'High',
            'low': 'Low',
            'Low': 'Low',
            'close': 'Close',
            'Close': 'Close',
            'volume': 'Volume',
            'Volume': 'Volume',
        }
        
        # 只选择需要的列
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = []
        
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in possible_names:
                target_col = possible_names[col_lower]
                if target_col not in column_mapping.values():
                    column_mapping[col] = target_col
                    available_cols.append(col)
        
        # 如果找到了所有需要的列，重命名
        if len(column_mapping) >= 5:
            df = df[available_cols].rename(columns=column_mapping)
        elif len(column_mapping) >= 4:
            # 如果缺少某些列，尝试使用默认值
            logger.warning(f"⚠️ Ashare返回的列不完整: {list(df.columns)}")
            df = df[available_cols].rename(columns=column_mapping)
            # 补充缺失的列
            for req_col in required_cols:
                if req_col not in df.columns:
                    if req_col == 'Volume':
                        df[req_col] = 0
                    else:
                        df[req_col] = df.get('Close', 0)
        else:
            # 如果列名完全不匹配，尝试按位置映射（假设顺序是 open, high, low, close, volume）
            logger.warning(f"⚠️ 列名不匹配，尝试按位置映射。实际列: {list(df.columns)}")
            if len(df.columns) >= 5:
                # 假设前5列是 OHLCV
                df = df.iloc[:, :5]
                df.columns = required_cols
            else:
                raise ValueError(f"Ashare返回的列数不足: {len(df.columns)}列，需要5列")

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
            return df.head(min(MAX_RETURN_ROWS, len(df)))
        elif start_date > df.index[-1]:
            st.warning(f"请求的开始时间 {start_date.date()} 晚于数据的最新时间 {df.index[-1].date()}，返回最新数据")
            return df.tail(min(MAX_RETURN_ROWS, len(df)))
        else:
            mask = (df.index >= start_date) & (df.index <= end_date)
            df_filtered = df.loc[mask]

            if df_filtered.empty:
                return df.head(min(MAX_RETURN_ROWS, len(df)))

        logger.info(f"✅ Ashare数据获取成功!")
        logger.debug(f"   📊 数据条数: {len(df_filtered)}")
        logger.debug(f"   📅 时间范围: {df_filtered.index[0]} 到 {df_filtered.index[-1]}")
        logger.debug(f"   💰 最新收盘价: {df_filtered['Close'].iloc[-1]:.2f}")

        return df_filtered

    except Exception as e:
        logger.error(f"Ashare数据获取失败: {str(e)}", exc_info=True)
        st.error(f"Ashare数据获取失败: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_ONLINE_DATA, show_spinner=False)
def get_stock_data_ak(
    symbol: str,
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str,
) -> pd.DataFrame:
    """使用AKShare获取股票数据"""
    try:
        # 清理股票代码，移除前缀和后缀
        # AKShare需要纯数字代码，如 "600519"
        formatted_symbol = symbol.strip()

        # 移除 "sh" 或 "sz" 前缀
        if formatted_symbol.lower().startswith(("sh", "sz")):
            formatted_symbol = formatted_symbol[2:]

        # 移除 ".SH" 或 ".SZ" 后缀
        if "." in formatted_symbol:
            formatted_symbol = formatted_symbol.split(".")[0]

        # 确保是纯数字
        formatted_symbol = "".join(filter(str.isdigit, formatted_symbol))

        if not formatted_symbol:
            st.error("❌ 无效的股票代码")
            return pd.DataFrame()

        logger.info(f"🔄 正在使用AKShare获取 {formatted_symbol} 的数据...")

        # 根据周期类型获取数据
        if period_type in ["daily", "weekly", "monthly"]:
            # 转换周期参数
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
            period = period_map[period_type]

            # 格式化日期
            start_date = (
                start.strftime("%Y%m%d")
                if hasattr(start, "strftime")
                else str(start).replace("-", "")
            )
            end_date = (
                end.strftime("%Y%m%d") if hasattr(end, "strftime") else str(end).replace("-", "")
            )

            # 获取股票历史数据
            df = ak.stock_zh_a_hist(
                symbol=formatted_symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )

            if df.empty:
                return pd.DataFrame()

            # 处理日期和索引
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values("日期").set_index("日期")

            # 标准化列名
            if "开盘" in df.columns:
                df = df.rename(
                    columns={
                        "开盘": "Open",
                        "收盘": "Close",
                        "最高": "High",
                        "最低": "Low",
                        "成交量": "Volume",
                    }
                )

            logger.info(f"✅ AKShare数据获取成功!")
            logger.debug(f"   📊 数据条数: {len(df)}")
            if not df.empty:
                logger.debug(f"   📅 时间范围: {df.index[0]} 到 {df.index[-1]}")
                logger.debug(f"   💰 最新收盘价: {df['Close'].iloc[-1]:.2f}")

            return df

    except Exception as e:
        logger.error(f"AKShare数据获取失败: {str(e)}", exc_info=True)
        st.error(f"AKShare数据获取失败: {str(e)}")
        return pd.DataFrame()


# 尝试导入Tushare相关模块
try:
    import os
    import sys

    # 添加aitrader_core到路径
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "aitrader_core"))
    from datafeed.tushare_loader import get_stock_data as tushare_get_stock_data

    has_tushare = True
except ImportError:
    has_tushare = False
    logger.warning("⚠️ Tushare模块未找到")

# 尝试导入CSV数据加载器
try:
    from datafeed.csv_dataloader import CsvDataLoader

    has_csv = True
except ImportError:
    has_csv = False
    logger.warning("⚠️ CSV数据加载器未找到")


@st.cache_data(ttl=CACHE_TTL_ONLINE_DATA, show_spinner=False)
def get_stock_data_tushare(
    symbol: str,
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str,
) -> pd.DataFrame:
    """使用Tushare获取股票数据"""
    if not has_tushare:
        st.warning("Tushare模块不可用，请检查aitrader_core/datafeed/tushare_loader.py")
        return pd.DataFrame()

    try:
        # 格式化股票代码为Tushare格式 (如: 600519.SH)
        if "." not in symbol:
            if symbol.startswith("6"):
                symbol = f"{symbol}.SH"
            elif symbol.startswith(("0", "3")):
                symbol = f"{symbol}.SZ"

        logger.info(f"🔄 正在使用Tushare获取 {symbol} 的数据...")

        # 调用tushare_loader (注意：tushare_loader没有freq参数，只支持日线)
        df = tushare_get_stock_data(
            symbol=symbol,
            start_date=start.strftime("%Y%m%d")
            if hasattr(start, "strftime")
            else str(start).replace("-", ""),
            end_date=end.strftime("%Y%m%d")
            if hasattr(end, "strftime")
            else str(end).replace("-", ""),
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # 标准化列名 (tushare返回小写列名)
        column_mapping = {
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }

        df = df.rename(columns=column_mapping)

        # 确保Date列是datetime类型
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")

        # 只保留需要的列
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        available_columns = [col for col in required_columns if col in df.columns]
        df = df[available_columns]

        # 按日期排序
        df = df.sort_index()

        logger.info(f"✅ Tushare数据获取成功! 数据条数: {len(df)}")
        return df

    except Exception as e:
        logger.error(f"Tushare数据获取失败: {str(e)}", exc_info=True)
        st.error(f"Tushare数据获取失败: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_LOCAL_DATA, show_spinner=False)
def get_stock_data_csv(
    symbol: str,
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str,
) -> pd.DataFrame:
    """从本地CSV文件获取股票数据"""
    if not has_csv:
        st.warning("CSV数据加载器不可用")
        return pd.DataFrame()

    try:
        # 格式化股票代码
        if "." not in symbol:
            if symbol.startswith("6"):
                symbol = f"{symbol}.SH"
            elif symbol.startswith(("0", "3")):
                symbol = f"{symbol}.SZ"

        logger.info(f"🔄 正在从本地CSV获取 {symbol} 的数据...")

        # 首先尝试用户目录下的stock_data文件夹
        user_stock_data_dir = os.path.expanduser("~/stock_data")

        # 创建CSV加载器实例 (CsvDataLoader不接受data_dir参数)
        csv_loader = CsvDataLoader()

        # 根据路径决定使用哪个目录
        if os.path.exists(user_stock_data_dir):
            csv_path = user_stock_data_dir
            logger.debug(f"📁 使用用户数据目录: {user_stock_data_dir}")
        else:
            # 回退到默认路径 (使用'quotes'会自动使用DATA_DIR/quotes)
            csv_path = "quotes"
            logger.debug(f"📁 使用默认数据目录")

        # 读取CSV数据 (传入path参数)
        df = csv_loader._read_csv(symbol, path=csv_path)

        if df is None or df.empty:
            st.warning(f"本地CSV未找到 {symbol} 的数据文件")
            st.info("💡 请先在「AI数据管理」中更新股票数据")
            return pd.DataFrame()

        # 标准化列名 (CSV通常返回小写列名)
        column_mapping = {
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }

        df = df.rename(columns=column_mapping)

        # 确保Date列是datetime类型并设置为索引
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")

        # 只保留需要的列
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        available_columns = [col for col in required_columns if col in df.columns]
        df = df[available_columns]

        # 按日期过滤
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)
        df = df[(df.index >= start_date) & (df.index <= end_date)]

        if df.empty:
            st.warning(f"⚠️ 在指定日期范围内({start} 至 {end})未找到数据")
            return pd.DataFrame()

        logger.info(f"✅ CSV数据加载成功! 数据条数: {len(df)}")
        return df

    except Exception as e:
        logger.error(f"CSV数据加载失败: {str(e)}", exc_info=True)
        st.error(f"CSV数据加载失败: {str(e)}")
        return pd.DataFrame()


def get_stock_data(
    symbol: str,
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str,
    data_source: str = "Ashare",
) -> pd.DataFrame:
    """
    获取股票数据的主函数，根据数据源选择不同的获取方法
    
    Args:
        symbol: 股票代码（如 '600519' 或 '000001'）
        start: 开始日期（字符串、datetime或Timestamp）
        end: 结束日期（字符串、datetime或Timestamp）
        period_type: 数据周期类型（'daily'/'weekly'/'monthly'）
        data_source: 数据源选择（'Ashare'/'AKShare'/'Tushare'/'本地CSV'）
    
    Returns:
        pd.DataFrame: 包含OHLCV数据的DataFrame，索引为日期，已过滤非交易日
    
    Note:
        - 自动应用交易日过滤（排除周末和节假日）
        - 支持多种数据源自动回退
        - 数据自动缓存（在线数据1小时，本地数据2小时）
    
    Example:
        >>> df = get_stock_data('600519', '2023-01-01', '2023-12-31', 'daily', 'Ashare')
        >>> print(f"获取到 {len(df)} 条交易日数据")
    """
    try:
        # ========== 数据验证 ==========
        # 验证股票代码
        is_valid_code, code_error = validate_stock_code(symbol)
        if not is_valid_code:
            st.error(f"❌ {code_error}")
            st.info("💡 **提示：** 请输入6位数字的A股代码，如：600519（贵州茅台）、000001（平安银行）")
            return pd.DataFrame()
        
        # 确保日期格式正确
        if not isinstance(start, (str, pd.Timestamp, datetime.datetime)):
            start = pd.to_datetime(start, format="%Y%m%d")
        if not isinstance(end, (str, pd.Timestamp, datetime.datetime)):
            end = pd.to_datetime(end, format="%Y%m%d")
        
        # 验证日期范围
        is_valid_date, date_error = validate_date_range(start, end)
        if not is_valid_date:
            st.error(f"❌ {date_error}")
            return pd.DataFrame()

        # 根据用户选择的数据源获取数据（带重试机制）
        df = _get_stock_data_with_retry(symbol, start, end, period_type, data_source)

        # 🔧 统一应用交易日过滤，确保K线连续显示
        if not df.empty and period_type in ["daily", "weekly", "monthly"]:
            from .trading_calendar import filter_trading_days

            original_count = len(df)
            df = filter_trading_days(df)
            filtered_count = len(df)

            if filtered_count < original_count:
                st.info(f"📅 交易日过滤: {original_count} → {filtered_count} 条数据")
                st.success(f"✅ 已过滤掉 {original_count - filtered_count} 个非交易日（周末和节假日）")
        
        # 数据质量检查
        if not df.empty:
            quality_info = check_data_quality(df, symbol)
            if quality_info.get('warnings'):
                for warning in quality_info['warnings']:
                    st.warning(f"⚠️ {warning}")

        return df

    except Exception as e:
        # 格式化用户友好的错误信息
        error_message = format_user_friendly_error(e, symbol, data_source)
        st.error(error_message)
        
        # 记录详细错误日志
        logger.error(
            f"获取股票数据失败: symbol={symbol}, data_source={data_source}, "
            f"start={start}, end={end}, period_type={period_type}, "
            f"error={type(e).__name__}: {str(e)}",
            exc_info=True
        )
        
        return pd.DataFrame()


# 其他辅助函数保持不变
def get_realtime_price(symbol: str) -> Optional[float]:
    """获取实时股价"""
    try:
        # 使用缓存的实时数据
        return cached_realtime_data(symbol)
    except Exception as e:
        st.error(f"获取实时价格失败: {str(e)}")
        return None


def get_stock_info(symbol: str) -> Optional[pd.DataFrame]:
    """获取股票基本信息"""
    try:
        formatted_symbol = format_stock_code(symbol)

        if has_ashare:
            # 使用Ashare获取股票信息
            try:
                from .Ashare import get_security_info

                info = get_security_info(formatted_symbol)
                return info
            except (ImportError, AttributeError):
                logger.warning("Ashare的get_security_info函数不可用")
                # 回退到AKShare
                info = ak.stock_individual_info_em(symbol=formatted_symbol)
                return info
        else:
            # 使用AKShare获取股票信息
            info = ak.stock_individual_info_em(symbol=formatted_symbol)
            return info

    except Exception as e:
        logger.error(f"获取股票信息失败: {str(e)}", exc_info=True)
        st.error(f"获取股票信息失败: {str(e)}")
        return None


# ========== 异步批量数据获取（性能优化） ==========


def _fetch_single_stock_sync(
    symbol: str,
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str,
    data_source: str,
) -> Dict[str, Any]:
    """
    同步获取单只股票数据（用于异步并发）

    Returns:
        dict: {'symbol': str, 'status': 'success'|'error', 'data': pd.DataFrame|None, 'error': str|None}
    """
    try:
        df = get_stock_data(symbol, start, end, period_type, data_source)
        if df is not None and not df.empty:
            return {"symbol": symbol, "status": "success", "data": df, "error": None}
        else:
            return {"symbol": symbol, "status": "error", "data": None, "error": "数据为空"}
    except Exception as e:
        logger.error(f"获取 {symbol} 数据失败: {str(e)}", exc_info=True)
        return {"symbol": symbol, "status": "error", "data": None, "error": str(e)}


async def get_multiple_stocks_data_async(
    symbols: List[str],
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str = "daily",
    data_source: str = "Ashare",
    max_workers: int = ASYNC_BATCH_FETCH_WORKERS,
    progress_callback: Optional[Callable] = None,
) -> Dict[str, pd.DataFrame]:
    """
    异步批量获取多只股票数据（性能优化版本）

    Args:
        symbols: 股票代码列表
        start: 开始日期
        end: 结束日期
        period_type: 数据周期类型
        data_source: 数据源
        max_workers: 最大并发数（默认5，避免API限流）
        progress_callback: 进度回调函数 callback(current, total, symbol)

    Returns:
        dict: {symbol: DataFrame} 成功获取的数据字典

    Example:
        symbols = ['600519', '000001', '000002']
        data_dict = await get_multiple_stocks_data_async(
            symbols, '2023-01-01', '2023-12-31'
        )
        # 返回: {'600519': DataFrame, '000001': DataFrame, ...}
    """
    logger.info(f"🚀 开始异步批量获取 {len(symbols)} 只股票数据（并发数: {max_workers}）")

    loop = asyncio.get_event_loop()
    results = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        async def fetch_single(symbol: str):
            return await loop.run_in_executor(
                executor, _fetch_single_stock_sync, symbol, start, end, period_type, data_source
            )

        # 并发执行所有任务
        tasks = [fetch_single(symbol) for symbol in symbols]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(task_results):
            symbol = symbols[i]
            completed += 1

            if isinstance(result, Exception):
                logger.error(f"获取 {symbol} 数据异常: {result}", exc_info=True)
                if progress_callback:
                    progress_callback(completed, len(symbols), symbol)
                continue

            if isinstance(result, dict):
                if result["status"] == "success" and result["data"] is not None:
                    results[symbol] = result["data"]
                    logger.debug(f"✅ {symbol} 数据获取成功: {len(result['data'])} 条")
                else:
                    logger.warning(f"⚠️ {symbol} 数据获取失败: {result.get('error', '未知错误')}")

                if progress_callback:
                    progress_callback(completed, len(symbols), symbol)

    logger.info(f"✅ 异步批量获取完成: 成功 {len(results)}/{len(symbols)} 只")
    return results


def get_multiple_stocks_data(
    symbols: List[str],
    start: Union[str, datetime.datetime, pd.Timestamp],
    end: Union[str, datetime.datetime, pd.Timestamp],
    period_type: str = "daily",
    data_source: str = "Ashare",
    use_async: bool = True,
    max_workers: int = 5,
) -> Dict[str, pd.DataFrame]:
    """
    批量获取多只股票数据（同步接口，内部可选择异步）

    Args:
        symbols: 股票代码列表
        start: 开始日期
        end: 结束日期
        period_type: 数据周期类型
        data_source: 数据源
        use_async: 是否使用异步模式（默认True，性能提升3-5倍）
        max_workers: 异步模式的最大并发数

    Returns:
        dict: {symbol: DataFrame} 成功获取的数据字典
    """
    if use_async:
        # 异步模式
        try:
            return asyncio.run(
                get_multiple_stocks_data_async(
                    symbols, start, end, period_type, data_source, max_workers
                )
            )
        except Exception as e:
            logger.error(f"异步批量获取失败，回退到同步模式: {e}")
            # 回退到同步模式
            use_async = False

    if not use_async:
        # 同步模式
        results = {}
        for i, symbol in enumerate(symbols):
            try:
                df = get_stock_data(symbol, start, end, period_type, data_source)
                if df is not None and not df.empty:
                    results[symbol] = df
                    logger.debug(f"✅ {symbol} 数据获取成功: {len(df)} 条")
            except Exception as e:
                logger.warning(f"⚠️ {symbol} 数据获取失败: {str(e)}")

        return results

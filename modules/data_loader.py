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

logger = get_logger(__name__)

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

        # 标准化列名
        df.columns = ["Open", "High", "Low", "Close", "Volume"]

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


@handle_data_error
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


@handle_data_error
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
        # 确保日期格式正确
        if not isinstance(start, (str, pd.Timestamp, datetime.datetime)):
            start = pd.to_datetime(start, format="%Y%m%d")
        if not isinstance(end, (str, pd.Timestamp, datetime.datetime)):
            end = pd.to_datetime(end, format="%Y%m%d")

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
        if not df.empty and period_type in ["daily", "weekly", "monthly"]:
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

#!/usr/bin/env python3
"""
A股全量数据更新脚本 - Tushare Direct版本（适用于Streamlit Cloud）
直接调用Tushare API，无需subprocess，适合在Streamlit界面中直接调用

支持同步和异步两种模式：
- 同步模式：update_data_direct() - 向后兼容
- 异步模式：update_data_direct_async() - 性能提升4-6倍
"""
import os
import sys
import pandas as pd
import tushare as ts
from pathlib import Path
from datetime import datetime, timedelta
import time
import asyncio
from typing import Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# 尝试导入常量
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from modules.constants import (
        TUSHARE_RATE_LIMIT_CALLS,
        TUSHARE_RATE_LIMIT_PERIOD,
        TUSHARE_SLEEP_INTERVAL,
        ASYNC_MAX_WORKERS_DEFAULT,
        RETRY_MAX_ATTEMPTS,
        RETRY_WAIT_MIN,
        RETRY_WAIT_MAX,
        LOG_BATCH_SIZE,
        LOG_SKIP_INTERVAL,
        LOG_ERROR_DISPLAY_LIMIT
    )
    USE_CONSTANTS = True
except ImportError:
    # 回退到硬编码值
    USE_CONSTANTS = False
    TUSHARE_RATE_LIMIT_CALLS = 1500
    TUSHARE_RATE_LIMIT_PERIOD = 60
    TUSHARE_SLEEP_INTERVAL = 0.04
    ASYNC_MAX_WORKERS_DEFAULT = 10
    RETRY_MAX_ATTEMPTS = 3
    RETRY_WAIT_MIN = 2
    RETRY_WAIT_MAX = 10
    LOG_BATCH_SIZE = 50
    LOG_SKIP_INTERVAL = 100
    LOG_ERROR_DISPLAY_LIMIT = 5

# 尝试导入异步和限流相关库
try:
    from tenacity import retry, stop_after_attempt, wait_exponential
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False

try:
    from ratelimit import limits, sleep_and_retry
    HAS_RATELIMIT = True
except ImportError:
    HAS_RATELIMIT = False

# 尝试导入logger，如果失败则使用print作为fallback
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from modules.logger_config import get_logger
    logger = get_logger(__name__)
    USE_LOGGER = True
except ImportError:
    # 如果logger不可用，使用print
    USE_LOGGER = False
    logger = None

# Tushare Token - 从环境变量读取
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN')
if not TUSHARE_TOKEN:
    msg = "❌ 错误：TUSHARE_TOKEN 环境变量未设置\n请在 .env 文件中配置 TUSHARE_TOKEN\n参考 .env.example 文件"
    if USE_LOGGER:
        logger.error(msg)
    else:
        print(msg)

def get_stock_data_dir():
    """获取数据目录"""
    # 1. 优先使用环境变量
    if 'STOCK_DATA_DIR' in os.environ:
        data_dir = Path(os.environ['STOCK_DATA_DIR'])
    # 2. 检测 Streamlit Cloud 环境 (通过检查项目路径特征)
    elif '/mount/src/' in str(Path(__file__).absolute()):
        # Streamlit Cloud 环境：使用项目内的 data 目录
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data" / "stock_data"
    # 3. 本地环境：使用用户主目录
    else:
        data_dir = Path.home() / "stock_data"
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def update_data_direct(progress_callback=None, log_callback=None):
    """
    直接更新数据（适用于Streamlit界面直接调用）
    
    Args:
        progress_callback: 进度回调函数 callback(progress, current, total, message)
        log_callback: 日志回调函数 callback(message)
    
    Returns:
        dict: 更新结果统计
    """
    def log(msg, level='info'):
        """日志输出"""
        if USE_LOGGER:
            if level == 'error':
                logger.error(msg)
            elif level == 'warning':
                logger.warning(msg)
            elif level == 'debug':
                logger.debug(msg)
            else:
                logger.info(msg)
        else:
            print(msg)
            sys.stdout.flush()
        if log_callback:
            log_callback(msg)
    
    def update_progress(progress, current, total, msg=""):
        """更新进度"""
        if progress_callback:
            progress_callback(progress, current, total, msg)
    
    try:
        # 初始化Tushare API
        log("✅ 正在初始化Tushare API...")
        pro = ts.pro_api(TUSHARE_TOKEN)
        
        # 获取数据目录
        data_dir = get_stock_data_dir()
        log(f"✅ 数据目录: {data_dir}")
        
        # 获取股票列表
        log("🔍 正在获取A股股票列表...")
        stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
        total_stocks = len(stock_list)
        log(f"✅ 获取到 {total_stocks} 只A股股票")
        
        # 确定时间范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        log(f"📅 更新时间范围: {start_date} ~ {end_date}")
        
        # 统计变量
        success_count = 0
        skip_count = 0
        error_count = 0
        
        # 遍历更新每只股票
        for idx, row in stock_list.iterrows():
            ts_code = row['ts_code']
            name = row['name']
            
            # 更新进度
            progress = int((idx + 1) / total_stocks * 100)
            update_progress(progress, idx + 1, total_stocks, f"正在更新: {name}")
            
            csv_file = data_dir / f"{ts_code}_{name}.csv"
            
            # 检查是否需要更新
            start_date_incremental = start_date
            if csv_file.exists():
                try:
                    existing_df = pd.read_csv(csv_file)
                    if not existing_df.empty and 'trade_date' in existing_df.columns:
                        # 获取最后日期并统一转换为 YYYYMMDD 格式字符串
                        last_date_raw = existing_df['trade_date'].max()
                        
                        # 统一转换为 YYYYMMDD 字符串格式
                        try:
                            if pd.isna(last_date_raw):
                                # 如果是 NaN，跳过此文件
                                pass
                            elif isinstance(last_date_raw, (int, float)):
                                # 如果是数字，转为字符串
                                last_date = str(int(last_date_raw))
                            elif isinstance(last_date_raw, str):
                                # 如果是字符串，清理横杠和空格
                                last_date = last_date_raw.replace('-', '').replace(' ', '').strip()[:8]
                            else:
                                # 其他类型（如datetime），转为字符串后清理
                                last_date = str(last_date_raw).replace('-', '').replace(' ', '').strip()[:8]
                            
                            # 确保 end_date 也是纯字符串格式
                            end_date_str = str(end_date).replace('-', '').strip()
                            
                            # 验证格式是否正确（8位数字）
                            if len(last_date) == 8 and last_date.isdigit():
                                # 如果已是最新，跳过
                                if last_date >= end_date_str:
                                    skip_count += 1
                                    if skip_count % 100 == 0:
                                        log(f"⏩ 已跳过 {skip_count} 只最新股票")
                                    continue
                                start_date_incremental = last_date
                        except Exception:
                            # 日期解析失败，重新下载全部数据
                            pass
                except Exception:
                    # 文件读取失败，重新下载全部数据
                    pass
            
            # 下载数据
            try:
                df = pro.daily(
                    ts_code=ts_code,
                    start_date=start_date_incremental,
                    end_date=end_date,
                    adj='qfq'
                )
                
                if df is not None and not df.empty:
                    # 合并数据
                    if csv_file.exists():
                        existing_df = pd.read_csv(csv_file)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        
                        # 确保 trade_date 列为统一格式（字符串）再去重和排序
                        df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '').str.strip()
                        df = df.drop_duplicates(subset=['trade_date'], keep='last')
                        df = df.sort_values('trade_date')
                    else:
                        # 新文件也需要格式化日期
                        df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '').str.strip()
                    
                    # 保存
                    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                    success_count += 1
                    
                    if success_count % LOG_BATCH_SIZE == 0:
                        log(f"✅ 已更新 {success_count} 只股票")
                else:
                    skip_count += 1
                
                # API限流优化 (2000积分用户: 2000次/分钟)
                # 2000积分 = 2000次/分钟 = 60秒/2000次 = 0.03秒/次
                # 为了安全起见，设置为 0.04秒/次 (约1500次/分钟)
                time.sleep(0.04)  # 约1500次
            except Exception as e:
                error_count += 1
                error_msg = f"❌ {name} 更新失败: {str(e)[:50]}"
                if error_count <= LOG_ERROR_DISPLAY_LIMIT:
                    log(error_msg, level='error')
                elif USE_LOGGER:
                    # 超过5个错误后，只记录到日志，不显示给用户
                    logger.error(f"{name} 更新失败: {str(e)}", exc_info=True)
        
        # 完成
        update_progress(100, total_stocks, total_stocks, "更新完成")
        log("=" * 60)
        log(f"✅ 更新完成")
        log(f"   成功: {success_count} 只")
        log(f"   跳过: {skip_count} 只")
        log(f"   失败: {error_count} 只")
        log("=" * 60)
        
        return {
            'success': success_count,
            'skip': skip_count,
            'error': error_count,
            'total': total_stocks
        }
        
    except Exception as e:
        error_msg = f"❌ 更新失败: {e}"
        log(error_msg, level='error')
        import traceback
        if USE_LOGGER:
            logger.exception("数据更新过程中发生异常")
        else:
            log(traceback.format_exc(), level='error')
        return None


# ========== 异步版本（性能优化） ==========

def _update_single_stock_sync(
    pro: Any,
    ts_code: str,
    name: str,
    csv_file: Path,
    start_date: str,
    end_date: str,
    start_date_incremental: str
) -> Dict[str, Any]:
    """
    同步更新单只股票数据（用于异步并发）
    
    Returns:
        dict: {'status': 'success'|'skip'|'error', 'name': str}
    """
    def _call_api_with_retry():
        """带重试的API调用"""
        if HAS_TENACITY:
            @retry(
                stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
                wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX)
            )
            def _call():
                return pro.daily(
                    ts_code=ts_code,
                    start_date=start_date_incremental,
                    end_date=end_date,
                    adj='qfq'
                )
            return _call()
        else:
            # 简单重试逻辑
            for attempt in range(RETRY_MAX_ATTEMPTS):
                try:
                    return pro.daily(
                        ts_code=ts_code,
                        start_date=start_date_incremental,
                        end_date=end_date,
                        adj='qfq'
                    )
                except Exception as e:
                    if attempt == RETRY_MAX_ATTEMPTS - 1:
                        raise
                    time.sleep(RETRY_WAIT_MIN ** attempt)  # 指数退避
            return None
    
    try:
        # 使用限流装饰器（如果可用）
        if HAS_RATELIMIT:
            @sleep_and_retry
            @limits(calls=TUSHARE_RATE_LIMIT_CALLS, period=TUSHARE_RATE_LIMIT_PERIOD)
            def _call_with_limit():
                return _call_api_with_retry()
            df = _call_with_limit()
        else:
            # 回退到简单限流
            df = _call_api_with_retry()
            time.sleep(TUSHARE_SLEEP_INTERVAL)
        
        if df is not None and not df.empty:
            # 合并数据
            if csv_file.exists():
                existing_df = pd.read_csv(csv_file)
                df = pd.concat([existing_df, df], ignore_index=True)
                
                # 确保 trade_date 列为统一格式（字符串）再去重和排序
                df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '').str.strip()
                df = df.drop_duplicates(subset=['trade_date'], keep='last')
                df = df.sort_values('trade_date')
            else:
                # 新文件也需要格式化日期
                df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '').str.strip()
            
            # 保存
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            return {'status': 'success', 'name': name, 'ts_code': ts_code}
        else:
            return {'status': 'skip', 'name': name, 'ts_code': ts_code}
            
    except Exception as e:
        return {'status': 'error', 'name': name, 'ts_code': ts_code, 'error': str(e)}


async def update_data_direct_async(
    progress_callback: Optional[Callable] = None,
    log_callback: Optional[Callable] = None,
    max_workers: int = ASYNC_MAX_WORKERS_DEFAULT
) -> Optional[Dict[str, int]]:
    """
    异步并发更新数据（性能优化版本）
    
    Args:
        progress_callback: 进度回调函数 callback(progress, current, total, message)
        log_callback: 日志回调函数 callback(message)
        max_workers: 最大并发数（默认10，可根据API限制调整）
    
    Returns:
        dict: 更新结果统计
    """
    def log(msg: str, level: str = 'info'):
        """日志输出"""
        if USE_LOGGER:
            if level == 'error':
                logger.error(msg)
            elif level == 'warning':
                logger.warning(msg)
            elif level == 'debug':
                logger.debug(msg)
            else:
                logger.info(msg)
        else:
            print(msg)
            sys.stdout.flush()
        if log_callback:
            log_callback(msg)
    
    def update_progress(progress: int, current: int, total: int, msg: str = ""):
        """更新进度"""
        if progress_callback:
            progress_callback(progress, current, total, msg)
    
    try:
        # 初始化Tushare API
        log("✅ 正在初始化Tushare API（异步模式）...")
        pro = ts.pro_api(TUSHARE_TOKEN)
        
        # 获取数据目录
        data_dir = get_stock_data_dir()
        log(f"✅ 数据目录: {data_dir}")
        
        # 获取股票列表
        log("🔍 正在获取A股股票列表...")
        stock_list = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
        total_stocks = len(stock_list)
        log(f"✅ 获取到 {total_stocks} 只A股股票")
        log(f"🚀 使用异步并发模式，最大并发数: {max_workers}")
        
        # 确定时间范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        log(f"📅 更新时间范围: {start_date} ~ {end_date}")
        
        # 统计变量
        success_count = 0
        skip_count_pre = 0  # 预先跳过的（已是最新）
        skip_count = 0      # 执行中跳过的（数据为空）
        error_count = 0
        
        # 准备任务列表
        tasks = []
        for idx, row in stock_list.iterrows():
            ts_code = row['ts_code']
            name = row['name']
            csv_file = data_dir / f"{ts_code}_{name}.csv"
            
            # 检查是否需要更新
            start_date_incremental = start_date
            if csv_file.exists():
                try:
                    existing_df = pd.read_csv(csv_file)
                    if not existing_df.empty and 'trade_date' in existing_df.columns:
                        last_date_raw = existing_df['trade_date'].max()
                        try:
                            if pd.isna(last_date_raw):
                                pass
                            elif isinstance(last_date_raw, (int, float)):
                                last_date = str(int(last_date_raw))
                            elif isinstance(last_date_raw, str):
                                last_date = last_date_raw.replace('-', '').replace(' ', '').strip()[:8]
                            else:
                                last_date = str(last_date_raw).replace('-', '').replace(' ', '').strip()[:8]
                            
                            end_date_str = str(end_date).replace('-', '').strip()
                            if len(last_date) == 8 and last_date.isdigit():
                                if last_date >= end_date_str:
                                    skip_count_pre += 1
                                    if skip_count_pre % LOG_SKIP_INTERVAL == 0:
                                        log(f"⏩ 已跳过 {skip_count_pre} 只最新股票")
                                    continue
                                start_date_incremental = last_date
                        except Exception:
                            pass
                except Exception:
                    pass
            
            # 创建任务
            tasks.append({
                'ts_code': ts_code,
                'name': name,
                'csv_file': csv_file,
                'start_date': start_date,
                'end_date': end_date,
                'start_date_incremental': start_date_incremental
            })
        
        # 使用线程池并发执行
        log(f"🔄 开始并发更新 {len(tasks)} 只股票...")
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建异步任务
            async def process_task(task_data):
                return await loop.run_in_executor(
                    executor,
                    _update_single_stock_sync,
                    pro,
                    task_data['ts_code'],
                    task_data['name'],
                    task_data['csv_file'],
                    task_data['start_date'],
                    task_data['end_date'],
                    task_data['start_date_incremental']
                )
            
            # 并发执行所有任务
            completed = 0
            async def process_all_tasks():
                nonlocal success_count, skip_count, error_count, completed
                results = await asyncio.gather(*[process_task(task) for task in tasks], return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        error_count += 1
                        if USE_LOGGER:
                            logger.error(f"任务执行异常: {result}", exc_info=True)
                    elif isinstance(result, dict):
                        completed += 1
                        if result['status'] == 'success':
                            success_count += 1
                            if success_count % LOG_BATCH_SIZE == 0:
                                log(f"✅ 已更新 {success_count} 只股票")
                        elif result['status'] == 'skip':
                            skip_count += 1
                        elif result['status'] == 'error':
                            error_count += 1
                            if error_count <= LOG_ERROR_DISPLAY_LIMIT:
                                log(f"❌ {result['name']} 更新失败: {result.get('error', '未知错误')[:50]}", level='error')
                        
                        # 更新进度
                        progress = int(completed / len(tasks) * 100)
                        update_progress(progress, completed, len(tasks), f"已处理: {completed}/{len(tasks)}")
            
            await process_all_tasks()
        
        # 完成
        update_progress(100, len(tasks), len(tasks), "更新完成")
        total_skip = skip_count_pre + skip_count
        log("=" * 60)
        log(f"✅ 异步更新完成")
        log(f"   成功: {success_count} 只")
        log(f"   跳过: {total_skip} 只（已最新: {skip_count_pre}, 数据为空: {skip_count}）")
        log(f"   失败: {error_count} 只")
        log("=" * 60)
        
        return {
            'success': success_count,
            'skip': total_skip,
            'error': error_count,
            'total': total_stocks
        }
        
    except Exception as e:
        error_msg = f"❌ 异步更新失败: {e}"
        log(error_msg, level='error')
        if USE_LOGGER:
            logger.exception("异步数据更新过程中发生异常")
        return None


if __name__ == "__main__":
    # 命令行模式
    import argparse
    
    parser = argparse.ArgumentParser(description='A股数据更新脚本')
    parser.add_argument('--async-mode', '--async', dest='use_async', action='store_true', 
                       help='使用异步模式（性能提升4-6倍）')
    parser.add_argument('--workers', type=int, default=10, help='异步模式的最大并发数（默认10）')
    args = parser.parse_args()
    
    if args.use_async:
        # 异步模式
        result = asyncio.run(update_data_direct_async(max_workers=args.workers))
    else:
        # 同步模式（默认）
        result = update_data_direct()
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


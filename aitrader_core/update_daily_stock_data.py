#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日股票数据增量更新脚本
功能：
1. 自动获取最新交易日
2. 增量更新所有股票的最新数据（A股全量）
3. 支持企业微信推送通知

数据来源：Tushare
适用于：aitrader_v3.3项目
"""

import tushare as ts
import pandas as pd
import os
import sys
import io
import time
import requests
import json
from datetime import datetime, timedelta
import logging
import re

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 配置日志
log_dir = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'daily_update.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置参数
# 优先级：环境变量 > 项目目录 > 用户目录
if 'STOCK_DATA_DIR' in os.environ:
    STOCK_DATA_DIR = os.environ['STOCK_DATA_DIR']
    logger.info(f"✅ 使用环境变量指定的数据目录: {STOCK_DATA_DIR}")
else:
    # 优先使用项目目录（统一云端和本地）
    PROJECT_STOCK_DATA_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), "data", "stock_data")
    USER_STOCK_DATA_DIR = os.path.expanduser("~/stock_data")
    
    if os.path.exists(PROJECT_STOCK_DATA_DIR):
        STOCK_DATA_DIR = PROJECT_STOCK_DATA_DIR
        logger.info(f"✅ 使用项目目录数据: {STOCK_DATA_DIR}")
    elif os.path.exists(USER_STOCK_DATA_DIR):
        STOCK_DATA_DIR = USER_STOCK_DATA_DIR
        logger.info(f"✅ 使用用户目录数据: {STOCK_DATA_DIR}")
    else:
        # 默认创建项目目录
        STOCK_DATA_DIR = PROJECT_STOCK_DATA_DIR
        os.makedirs(STOCK_DATA_DIR, exist_ok=True)
        logger.info(f"✅ 创建并使用项目目录: {STOCK_DATA_DIR}")

ADJUST_FLAG = "qfq"  # 前复权 (Tushare)
WEBHOOK_URL = ""  # 企业微信Webhook地址（可选）

# 初始化 Tushare API
try:
    # 从环境变量读取 Token
    tushare_token = os.environ.get('TUSHARE_TOKEN')
    if not tushare_token:
        logger.error("❌ TUSHARE_TOKEN 环境变量未设置，请在 .env 文件中配置")
        print("❌ 错误：TUSHARE_TOKEN 环境变量未设置")
        print("请参考 .env.example 文件配置环境变量")
        sys.exit(1)
    
    pro = ts.pro_api(tushare_token)
    logger.info("✅ Tushare API 初始化成功")
except Exception as e:
    logger.error(f"❌ Tushare API 初始化失败: {e}")
    sys.exit(1)

def get_latest_trading_date():
    """获取最近一个交易日 (使用Tushare)"""
    try:
        # 使用 Tushare 获取交易日历（直接调用，不设置超时）
        today = datetime.now().strftime('%Y%m%d')
        logger.info(f"🔍 正在获取交易日历（截止{today}）...")
        print(f"🔍 正在获取交易日历（截止{today}）...")
        sys.stdout.flush()
        
        df = pro.trade_cal(exchange='SSE', end_date=today, is_open='1')
        
        if not df.empty:
            latest_date = df.iloc[0]['cal_date']
            formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:]}"
            logger.info(f"✅ 获取到最新交易日: {formatted_date}")
            print(f"✅ 获取到最新交易日: {formatted_date}")
            sys.stdout.flush()
            return formatted_date
    except Exception as e:
        logger.warning(f"⚠️ 使用Tushare获取交易日失败: {e}，使用备用方法")
        print(f"⚠️ Tushare获取失败: {e}")
        sys.stdout.flush()
    
    # 备用方法：简单推算
    today = datetime.now()
    for i in range(7):
        check_date = today - timedelta(days=i)
        if check_date.weekday() < 5:  # 0-4 for Monday-Friday
            formatted_date = check_date.strftime('%Y-%m-%d')
            logger.info(f"📅 使用备用方法推算交易日: {formatted_date}")
            print(f"📅 使用备用方法推算交易日: {formatted_date}")
            sys.stdout.flush()
            return formatted_date
    return None

def send_wecom_notification(message):
    """发送企业微信通知"""
    if not WEBHOOK_URL:
        return False
        
    data = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        logger.info(f"企业微信通知结果: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"企业微信通知失败: {e}")
        return False

def update_stock_data_incremental(ts_code, stock_name, latest_trading_date):
    """增量更新单只股票数据 (使用Tushare)"""
    # 清理文件名中的非法字符
    file_name_sanitized = re.sub(r'[\\/:*?\"<>|]', '', stock_name)
    stock_id = ts_code.split('.')[0]
    file_path = os.path.join(STOCK_DATA_DIR, f"{stock_id}_{file_name_sanitized}.csv")

    if not os.path.exists(file_path):
        logger.warning(f"文件 {file_path} 不存在，跳过更新。")
        return 0

    try:
        # 读取现有数据
        existing_df = pd.read_csv(file_path)
        if 'date' not in existing_df.columns and 'trade_date' not in existing_df.columns:
            logger.warning(f"文件 {file_path} 缺少日期列，跳过更新。")
            return 0

        # 统一日期列名
        date_col = 'trade_date' if 'trade_date' in existing_df.columns else 'date'
        existing_df[date_col] = pd.to_datetime(existing_df[date_col], format='%Y%m%d', errors='coerce')
        last_local_date = existing_df[date_col].max()

        # 如果本地数据已是最新，跳过
        latest_date_dt = datetime.strptime(latest_trading_date, '%Y-%m-%d')
        if pd.notna(last_local_date) and last_local_date >= latest_date_dt:
            return 0

        # 查询起始日期为本地最后日期的下一天
        start_date_to_query = (last_local_date + timedelta(days=1)).strftime('%Y%m%d')
        end_date_query = latest_trading_date.replace('-', '')
        
        # 使用Tushare查询新数据
        new_df = pro.daily(
            ts_code=ts_code,
            start_date=start_date_to_query,
            end_date=end_date_query,
            adj=ADJUST_FLAG
        )

        if new_df is not None and not new_df.empty:
            # 合并并去重
            updated_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['trade_date']).sort_values(by='trade_date')
            updated_df.to_csv(file_path, index=False)
            
            logger.info(f"{ts_code} {stock_name} 新增 {len(new_df)} 条记录")
            return len(new_df)
        else:
            return 0
            
    except Exception as e:
        logger.error(f"更新股票 {ts_code} 失败: {e}")
        return 0

def main():
    """主函数"""
    start_time = time.time()
    
    # 立即输出启动信息（确保用户能看到）
    print("=" * 60)
    print("🚀 A股数据更新程序启动中...")
    print(f"📂 数据目录: {STOCK_DATA_DIR}")
    print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    sys.stdout.flush()  # 强制刷新输出
    
    logger.info("=" * 60)
    logger.info("开始执行每日股票数据增量更新任务 (使用Tushare)")
    logger.info("=" * 60)
    
    # 确保数据目录存在
    if not os.path.exists(STOCK_DATA_DIR):
        logger.error(f"股票数据目录 {STOCK_DATA_DIR} 不存在！")
        send_wecom_notification(f"❌ 股票数据更新失败：数据目录不存在\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return

    latest_trading_date = get_latest_trading_date()
    
    if not latest_trading_date:
        logger.error("无法获取最新交易日，退出数据更新。")
        send_wecom_notification(f"❌ 股票数据更新失败：无法获取最新交易日\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return

    logger.info(f"最新交易日: {latest_trading_date}")
    
    # 获取所有CSV文件
    stock_files = [f for f in os.listdir(STOCK_DATA_DIR) if f.endswith('.csv')]
    total_files = len(stock_files)
    updated_count = 0
    processed_count = 0
    error_count = 0
    
    logger.info(f"开始处理 {total_files} 个股票文件")
    
    for file_name in stock_files:
        processed_count += 1
        try:
            # 从文件名解析股票代码
            stock_id = file_name.split('_')[0]
            
            # 根据股票代码确定市场（Tushare格式：代码.市场）
            if stock_id.startswith('6'):
                ts_code = f'{stock_id}.SH'
            elif stock_id.startswith(('0', '3')):
                ts_code = f'{stock_id}.SZ'
            elif stock_id.startswith(('8', '4')):  # 北交所
                ts_code = f'{stock_id}.BJ'
            else:
                logger.warning(f"未知市场代码: {stock_id}")
                continue

            stock_name = file_name.split('_', 1)[1].replace('.csv', '') if '_' in file_name else stock_id
            
            # 显示进度（每50只显示一次）
            if processed_count % 50 == 0:
                progress = processed_count / total_files * 100
                elapsed = time.time() - start_time
                eta = (elapsed / processed_count) * (total_files - processed_count)
                logger.info(f"[{progress:.1f}%] 进度: {processed_count}/{total_files}, 已更新: {updated_count}, 预计剩余: {eta/60:.1f}分钟")
            
            # 更新数据
            added_rows = update_stock_data_incremental(ts_code, stock_name, latest_trading_date)
            if added_rows > 0:
                updated_count += 1
            
            # Tushare API限流：每分钟200次
            if processed_count % 200 == 0:
                logger.info("达到API调用限制，休息60秒...")
                time.sleep(60)
            else:
                time.sleep(0.3)  # 每次请求间隔0.3秒
                
        except Exception as e:
            error_count += 1
            logger.error(f"处理文件 {file_name} 时发生错误: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info("-" * 60)
    logger.info("每日数据更新完成!")
    logger.info(f"最新交易日: {latest_trading_date}")
    logger.info(f"总文件数: {total_files}")
    logger.info(f"成功检查: {processed_count}")
    logger.info(f"实际更新: {updated_count}")
    logger.info(f"错误数量: {error_count}")
    logger.info(f"总耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)")
    logger.info("=" * 60)
    
    # 发送企业微信通知
    if updated_count > 0 or error_count > 0:
        status_icon = "✅" if error_count == 0 else "⚠️"
        message = f"""{status_icon} 股票数据更新完成

📅 更新日期: {latest_trading_date}
📊 总股票数: {total_files}
🔄 实际更新: {updated_count}
❌ 错误数量: {error_count}
⏱️ 耗时: {duration:.1f}秒

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        send_wecom_notification(message)
    else:
        logger.info("无新数据需要更新，跳过通知")

if __name__ == '__main__':
    main()


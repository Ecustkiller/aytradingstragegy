#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日股票数据增量更新脚本
功能：
1. 自动获取最新交易日
2. 增量更新所有股票的最新数据（A股全量）
3. 支持企业微信推送通知

数据来源：baostock
适用于：aitrader_v3.3项目
"""

import baostock as bs
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
# 优先使用用户目录的stock_data，如果不存在则使用项目目录
USER_STOCK_DATA_DIR = os.path.expanduser("~/stock_data")
PROJECT_STOCK_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "quotes")

if os.path.exists(USER_STOCK_DATA_DIR):
    STOCK_DATA_DIR = USER_STOCK_DATA_DIR
    logger.info(f"使用用户目录数据: {STOCK_DATA_DIR}")
else:
    STOCK_DATA_DIR = PROJECT_STOCK_DATA_DIR
    logger.info(f"使用项目目录数据: {STOCK_DATA_DIR}")
ADJUST_FLAG = "2"  # 前复权
WEBHOOK_URL = ""  # 企业微信Webhook地址（可选）

def login_baostock():
    """登录baostock"""
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"登录失败: {lg.error_msg}")
        sys.exit(1)
    else:
        logger.info("登录baostock成功")
        return lg

def logout_baostock():
    """登出baostock"""
    bs.logout()
    logger.info("登出baostock成功")

def get_latest_trading_date():
    """获取最近一个交易日"""
    today = datetime.now()
    for i in range(7):  # 往前推7天，找到最近的交易日
        check_date = today - timedelta(days=i)
        if check_date.weekday() < 5:  # 0-4 for Monday-Friday
            return check_date.strftime('%Y-%m-%d')
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

def update_stock_data_incremental(lg, stock_code_full, stock_name, latest_trading_date):
    """增量更新单只股票数据"""
    # 清理文件名中的非法字符
    file_name_sanitized = re.sub(r'[\\/:*?\"<>|]', '', stock_name)
    file_path = os.path.join(STOCK_DATA_DIR, f"{stock_code_full.split('.')[-1]}_{file_name_sanitized}.csv")

    if not os.path.exists(file_path):
        logger.warning(f"文件 {file_path} 不存在，跳过更新。")
        return 0

    try:
        # 读取现有数据
        existing_df = pd.read_csv(file_path)
        if 'date' not in existing_df.columns:
            logger.warning(f"文件 {file_path} 缺少 'date' 列，跳过更新。")
            return 0

        existing_df['date'] = pd.to_datetime(existing_df['date'])
        last_local_date = existing_df['date'].max().strftime('%Y-%m-%d')

        # 如果本地数据已是最新，跳过
        if last_local_date >= latest_trading_date:
            return 0

        # 查询起始日期为本地最后日期的下一天
        start_date_to_query = (datetime.strptime(last_local_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 查询新数据
        rs = bs.query_history_k_data_plus(
            stock_code_full,
            "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
            start_date=start_date_to_query,
            end_date=latest_trading_date,
            frequency="d",
            adjustflag=ADJUST_FLAG
        )

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        if data_list:
            new_df = pd.DataFrame(data_list, columns=rs.fields)
            new_df['date'] = pd.to_datetime(new_df['date'])
            
            # 合并并去重
            updated_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['date']).sort_values(by='date')
            updated_df.to_csv(file_path, index=False)
            
            logger.info(f"{stock_code_full} {stock_name} 新增 {len(new_df)} 条记录")
            return len(new_df)
        else:
            return 0
            
    except Exception as e:
        logger.error(f"更新股票 {stock_code_full} 失败: {e}")
        return 0

def main():
    """主函数"""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("开始执行每日股票数据增量更新任务")
    logger.info("=" * 60)
    
    # 确保数据目录存在
    if not os.path.exists(STOCK_DATA_DIR):
        logger.error(f"股票数据目录 {STOCK_DATA_DIR} 不存在！")
        send_wecom_notification(f"❌ 股票数据更新失败：数据目录不存在\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return

    lg = login_baostock()
    latest_trading_date = get_latest_trading_date()
    
    if not latest_trading_date:
        logger.error("无法获取最新交易日，退出数据更新。")
        logout_baostock()
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
            
            # 根据股票代码确定市场
            if stock_id.startswith('6'):
                stock_code_full = f'sh.{stock_id}'
            elif stock_id.startswith(('0', '3')):
                stock_code_full = f'sz.{stock_id}'
            elif stock_id.startswith(('8', '4')):  # 北交所
                stock_code_full = f'bj.{stock_id}'
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
            added_rows = update_stock_data_incremental(lg, stock_code_full, stock_name, latest_trading_date)
            if added_rows > 0:
                updated_count += 1
            
            # 每更新200只股票休息一下
            if processed_count % 200 == 0:
                time.sleep(1)
                
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
    
    logout_baostock()
    
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


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股全量数据下载脚本
功能：
1. 从Tushare下载所有A股股票的历史数据
2. 适用于首次部署或数据丢失后的全量下载
3. 支持断点续传

数据来源：Tushare
适用于：aitrader_v3.3项目
"""

import tushare as ts
import pandas as pd
import os
import sys
import io
import time
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
        logging.FileHandler(os.path.join(log_dir, 'download_all.log')),
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
    
    if os.path.exists(USER_STOCK_DATA_DIR) and len(os.listdir(USER_STOCK_DATA_DIR)) > 0:
        STOCK_DATA_DIR = USER_STOCK_DATA_DIR
        logger.info(f"✅ 使用用户目录数据: {STOCK_DATA_DIR}")
    else:
        # 默认创建项目目录
        STOCK_DATA_DIR = PROJECT_STOCK_DATA_DIR
        os.makedirs(STOCK_DATA_DIR, exist_ok=True)
        logger.info(f"✅ 创建并使用项目目录: {STOCK_DATA_DIR}")

# 初始化 Tushare API
try:
    # 从环境变量或配置文件读取 Token
    tushare_token = os.environ.get('TUSHARE_TOKEN', 'ad56243b601d82fd5c4aaf04b72d4d9d567401898d46c20f4d905d59')
    pro = ts.pro_api(tushare_token)
    logger.info("✅ Tushare API 初始化成功")
except Exception as e:
    logger.error(f"❌ Tushare API 初始化失败: {e}")
    sys.exit(1)


def get_all_stock_list():
    """获取所有A股股票列表"""
    try:
        logger.info("🔍 正在获取A股股票列表...")
        
        # 获取所有股票基本信息
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
        
        # 过滤掉北交所（8开头和4开头）
        df = df[~df['symbol'].str.startswith(('8', '4'))]
        
        logger.info(f"✅ 获取到 {len(df)} 只A股股票")
        return df
    
    except Exception as e:
        logger.error(f"❌ 获取股票列表失败: {e}")
        return pd.DataFrame()


def download_stock_data(ts_code, stock_name, start_date='20150101'):
    """下载单只股票的历史数据
    
    Args:
        ts_code: Tushare股票代码 (如 '600519.SH')
        stock_name: 股票名称
        start_date: 开始日期 (默认从2015年开始)
    
    Returns:
        下载的数据行数
    """
    # 清理文件名中的非法字符
    stock_id = ts_code.split('.')[0]  # 提取纯数字代码
    file_name_sanitized = re.sub(r'[\\/:*?"<>|]', '', stock_name)
    file_path = os.path.join(STOCK_DATA_DIR, f"{stock_id}_{file_name_sanitized}.csv")
    
    # 如果文件已存在，跳过
    if os.path.exists(file_path):
        logger.info(f"✅ {ts_code} {stock_name} 已存在，跳过下载")
        return 0
    
    try:
        # 获取历史数据
        today = datetime.now().strftime('%Y%m%d')
        
        # Tushare日线数据（前复权）
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=today)
        
        if df is None or df.empty:
            logger.warning(f"⚠️ {ts_code} {stock_name} 无数据")
            return 0
        
        # 按日期排序（从旧到新）
        df = df.sort_values('trade_date')
        
        # 重命名列以匹配原baostock格式
        df = df.rename(columns={
            'trade_date': 'date',
            'ts_code': 'code',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'vol': 'volume',
            'amount': 'amount',
            'pct_chg': 'pctChg'
        })
        
        # 格式化日期 (YYYYMMDD -> YYYY-MM-DD)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # 选择需要的列
        columns_to_save = ['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pctChg']
        available_columns = [col for col in columns_to_save if col in df.columns]
        df = df[available_columns]
        
        # 保存为CSV
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"✅ {ts_code} {stock_name} 下载成功，共 {len(df)} 条数据")
        return len(df)
        
    except Exception as e:
        logger.error(f"❌ {ts_code} {stock_name} 下载失败: {e}")
        return 0


def main():
    """主函数"""
    start_time = time.time()
    
    # 立即输出启动信息
    print("=" * 60)
    print("🚀 A股全量数据下载程序启动中...")
    print(f"📂 数据目录: {STOCK_DATA_DIR}")
    print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    sys.stdout.flush()
    
    logger.info("=" * 60)
    logger.info("开始执行A股全量数据下载任务 (使用Tushare)")
    logger.info("=" * 60)
    
    # 确保数据目录存在
    if not os.path.exists(STOCK_DATA_DIR):
        os.makedirs(STOCK_DATA_DIR, exist_ok=True)
        logger.info(f"✅ 创建数据目录: {STOCK_DATA_DIR}")
    
    # 获取股票列表
    stock_list = get_all_stock_list()
    
    if stock_list.empty:
        logger.error("❌ 无法获取股票列表，退出下载任务")
        return
    
    total_stocks = len(stock_list)
    downloaded_count = 0
    skipped_count = 0
    error_count = 0
    
    logger.info(f"📊 共需下载 {total_stocks} 只股票数据")
    print(f"📊 共需下载 {total_stocks} 只股票数据")
    sys.stdout.flush()
    
    for idx, row in stock_list.iterrows():
        ts_code = row['ts_code']
        stock_name = row['name']
        
        try:
            # 显示进度
            progress = (idx + 1) / total_stocks * 100
            if (idx + 1) % 10 == 0:
                elapsed = time.time() - start_time
                eta = (elapsed / (idx + 1)) * (total_stocks - idx - 1)
                print(f"[{progress:.1f}%] 进度: {idx + 1}/{total_stocks}, 已下载: {downloaded_count}, 预计剩余: {eta/60:.1f}分钟")
                sys.stdout.flush()
            
            # 下载数据
            rows = download_stock_data(ts_code, stock_name)
            
            if rows > 0:
                downloaded_count += 1
            else:
                skipped_count += 1
            
            # Tushare API限流：每分钟200次（积分不足用户更严格）
            if (idx + 1) % 200 == 0:
                logger.info("⏸️ 达到API调用限制，休息60秒...")
                print("⏸️ 达到API调用限制，休息60秒...")
                sys.stdout.flush()
                time.sleep(60)
            else:
                time.sleep(0.3)  # 每次请求间隔0.3秒
        
        except Exception as e:
            error_count += 1
            logger.error(f"❌ 处理 {ts_code} {stock_name} 时发生错误: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 输出统计信息
    print("=" * 60)
    print("✅ A股全量数据下载完成!")
    print(f"📊 总股票数: {total_stocks}")
    print(f"✅ 下载成功: {downloaded_count}")
    print(f"⏭️ 跳过已有: {skipped_count}")
    print(f"❌ 错误数量: {error_count}")
    print(f"⏱️ 总耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)")
    print("=" * 60)
    sys.stdout.flush()
    
    logger.info("-" * 60)
    logger.info("A股全量数据下载完成!")
    logger.info(f"总股票数: {total_stocks}")
    logger.info(f"下载成功: {downloaded_count}")
    logger.info(f"跳过已有: {skipped_count}")
    logger.info(f"错误数量: {error_count}")
    logger.info(f"总耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()


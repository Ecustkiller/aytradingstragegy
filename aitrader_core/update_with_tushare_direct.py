#!/usr/bin/env python3
"""
A股全量数据更新脚本 - Tushare Direct版本（适用于Streamlit Cloud）
直接调用Tushare API，无需subprocess，适合在Streamlit界面中直接调用
"""
import os
import sys
import pandas as pd
import tushare as ts
from pathlib import Path
from datetime import datetime, timedelta
import time

# Tushare Token
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', 'ad56243b601d82fd5c4aaf04b72d4d9d567401898d46c20f4d905d59')

def get_stock_data_dir():
    """获取数据目录"""
    # 优先使用环境变量
    if 'STOCK_DATA_DIR' in os.environ:
        data_dir = Path(os.environ['STOCK_DATA_DIR'])
    # 本地环境
    elif Path.home().exists():
        data_dir = Path.home() / "stock_data"
    # Streamlit Cloud环境
    else:
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data" / "stock_data"
    
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
    def log(msg):
        """日志输出"""
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
                        last_date = str(existing_df['trade_date'].max())
                        # 如果已是最新，跳过
                        if last_date >= end_date:
                            skip_count += 1
                            if skip_count % 100 == 0:
                                log(f"⏩ 已跳过 {skip_count} 只最新股票")
                            continue
                        start_date_incremental = last_date
                except Exception:
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
                        df = df.drop_duplicates(subset=['trade_date'], keep='last')
                        df = df.sort_values('trade_date')
                    
                    # 保存
                    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                    success_count += 1
                    
                    if success_count % 50 == 0:
                        log(f"✅ 已更新 {success_count} 只股票")
                else:
                    skip_count += 1
                
                # API限流 (免费用户: 200次/分钟)
                time.sleep(0.32)
                
            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    log(f"❌ {name} 更新失败: {str(e)[:50]}")
        
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
        log(f"❌ 更新失败: {e}")
        import traceback
        log(traceback.format_exc())
        return None


if __name__ == "__main__":
    # 命令行模式
    result = update_data_direct()
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


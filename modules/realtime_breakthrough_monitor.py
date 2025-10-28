"""
实时突破监测系统
基于预筛选机制的高效实时股价突破监测
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import requests
import logging
from typing import List, Dict, Optional
import threading
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealtimeBreakthroughMonitor:
    def __init__(self, webhook_url: str, monitor_interval: int = 30):
        """
        实时突破监测器
        :param webhook_url: 企业微信webhook地址
        :param monitor_interval: 监测间隔（秒）
        """
        self.webhook_url = webhook_url
        self.monitor_interval = monitor_interval
        self.monitoring = False
        self.monitor_pool = []  # 当日监控股票池
        self.breakthrough_cache = set()  # 已推送的突破股票缓存
        self.last_update_time = None
        
    def send_message(self, content: str, msg_type: str = "text") -> bool:
        """发送消息到企业微信"""
        try:
            headers = {'Content-Type': 'application/json'}
            
            if msg_type == "markdown":
                data = {
                    "msgtype": "markdown",
                    "markdown": {"content": content}
                }
            else:
                data = {
                    "msgtype": "text",
                    "text": {"content": content}
                }
            
            response = requests.post(
                self.webhook_url,
                headers=headers,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8')
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('errcode') == 0
            return False
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def get_main_board_stocks(self) -> pd.DataFrame:
        """获取沪深主板股票列表"""
        try:
            logger.info("获取沪深主板股票列表...")
            stock_list = ak.stock_zh_a_spot_em()
            
            if stock_list.empty:
                return pd.DataFrame()
            
            # 筛选沪深主板股票
            main_board = stock_list[
                (stock_list['代码'].str.startswith('000')) |  # 深圳主板
                (stock_list['代码'].str.startswith('001')) |  # 深圳主板
                (stock_list['代码'].str.startswith('002')) |  # 深圳主板（部分）
                (stock_list['代码'].str.startswith('600')) |  # 上海主板
                (stock_list['代码'].str.startswith('601')) |  # 上海主板
                (stock_list['代码'].str.startswith('603')) |  # 上海主板
                (stock_list['代码'].str.startswith('605'))    # 上海主板
            ].copy()
            
            # 排除创业板、科创板、北交所
            main_board = main_board[
                ~main_board['代码'].str.startswith('300') &  # 排除创业板
                ~main_board['代码'].str.startswith('688') &  # 排除科创板
                ~main_board['代码'].str.startswith('8')      # 排除北交所
            ]
            
            logger.info(f"获取到 {len(main_board)} 只主板股票")
            return main_board
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_data(self, code: str, days: int = 80) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                  start_date=start_date, end_date=end_date, adjust="")
            
            if df.empty:
                return None
            
            # 标准化列名
            column_mapping = {
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume',
                '涨跌幅': 'change_pct'
            }
            
            df = df.rename(columns=column_mapping)
            required_columns = ['date', 'open', 'close', 'high', 'low', 'volume']
            
            if not all(col in df.columns for col in required_columns):
                return None
            
            # 数据类型转换
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'close', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if 'change_pct' not in df.columns:
                df['change_pct'] = df['close'].pct_change() * 100
            else:
                df['change_pct'] = pd.to_numeric(df['change_pct'], errors='coerce')
            
            df['change_pct'] = df['change_pct'].fillna(0)
            df = df.dropna(subset=['open', 'close', 'high', 'low'])
            df = df.sort_values('date').reset_index(drop=True)
            
            return df.tail(days) if len(df) > days else df
            
        except Exception as e:
            logger.debug(f"获取股票 {code} 数据失败: {e}")
            return None
    
    def find_previous_high(self, df: pd.DataFrame) -> Optional[Dict]:
        """寻找前高点（左三右三确认）"""
        if len(df) < 10:
            return None
        
        search_end = len(df) - 3  # 排除最近3天
        
        for i in range(search_end - 1, 2, -1):
            current_high = df.iloc[i]['high']
            current_date = df.iloc[i]['date']
            
            # 检查左三右三条件
            left_highs = df.iloc[i-3:i]['high'].values
            right_highs = df.iloc[i+1:i+4]['high'].values
            
            left_condition = all(current_high > h for h in left_highs)
            right_condition = all(current_high > h for h in right_highs)
            
            if left_condition and right_condition:
                confirm_date = df.iloc[i+3]['date']
                return {
                    'price': current_high,
                    'date': current_date,
                    'confirm_date': confirm_date,
                    'index': i
                }
        
        return None
    
    def build_monitor_pool(self) -> List[Dict]:
        """构建当日监控股票池"""
        logger.info("🔍 开始构建监控股票池...")
        
        # 获取主板股票
        main_board_stocks = self.get_main_board_stocks()
        if main_board_stocks.empty:
            return []
        
        # 第一层筛选：价格和成交量
        filtered_stocks = main_board_stocks[
            (main_board_stocks['最新价'] >= 5) &
            (main_board_stocks['最新价'] <= 100) &
            (main_board_stocks['成交额'] >= 10000000) &  # 成交额大于1000万
            (main_board_stocks['涨跌幅'] < 9.8)  # 排除接近涨停的股票
        ].copy()
        
        logger.info(f"📊 第一层筛选后剩余 {len(filtered_stocks)} 只股票")
        
        monitor_pool = []
        
        # 第二层筛选：技术指标预筛选
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for _, stock in filtered_stocks.head(300).iterrows():  # 限制处理数量
                future = executor.submit(self._analyze_stock_for_pool, stock)
                futures.append(future)
            
            for i, future in enumerate(futures):
                try:
                    result = future.result(timeout=10)
                    if result:
                        monitor_pool.append(result)
                    
                    if (i + 1) % 50 == 0:
                        logger.info(f"已处理 {i + 1} 只股票，当前监控池大小: {len(monitor_pool)}")
                        
                except Exception as e:
                    logger.debug(f"分析股票失败: {e}")
                    continue
        
        # 按接近突破程度排序
        monitor_pool.sort(key=lambda x: x['breakthrough_proximity'], reverse=True)
        
        logger.info(f"🎯 监控股票池构建完成，共 {len(monitor_pool)} 只股票")
        return monitor_pool
    
    def _analyze_stock_for_pool(self, stock) -> Optional[Dict]:
        """分析单只股票是否加入监控池"""
        try:
            code = stock['代码']
            name = stock['名称']
            current_price = stock['最新价']
            
            # 获取历史数据
            df = self.get_stock_data(code, days=80)
            if df is None or len(df) < 60:
                return None
            
            # 计算55日均线
            df['ma55'] = df['close'].rolling(55).mean()
            df = df.dropna(subset=['ma55'])
            
            if len(df) < 10:
                return None
            
            latest = df.iloc[-1]
            prev_5 = df.iloc[-6:-1] if len(df) >= 6 else df.iloc[:-1]
            
            # 检查55日均线方向
            if len(prev_5) >= 3:
                ma55_trend_up = (latest['ma55'] > prev_5.iloc[-1]['ma55'] and 
                               prev_5.iloc[-1]['ma55'] > prev_5.iloc[-3]['ma55'])
            else:
                ma55_trend_up = False
            
            # 检查股价位置（在55日均线上方且不超过105%）
            price_ratio = latest['close'] / latest['ma55']
            price_position_good = 1.0 <= price_ratio <= 1.05
            
            # 寻找前高点
            previous_high_info = self.find_previous_high(df)
            if previous_high_info is None:
                return None
            
            prev_high = previous_high_info['price']
            
            # 检查是否接近前高点（95%-100%）
            high_ratio = latest['close'] / prev_high
            near_previous_high = 0.95 <= high_ratio <= 1.0
            
            # 综合判断是否加入监控池
            if ma55_trend_up and price_position_good and near_previous_high:
                breakthrough_proximity = high_ratio * 100  # 接近突破的程度
                
                return {
                    'code': code,
                    'name': name,
                    'current_price': current_price,
                    'ma55': latest['ma55'],
                    'previous_high': prev_high,
                    'previous_high_date': previous_high_info['date'].strftime('%Y-%m-%d'),
                    'breakthrough_proximity': breakthrough_proximity,
                    'price_ratio': price_ratio,
                    'high_ratio': high_ratio
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"分析股票 {code if 'code' in locals() else 'unknown'} 失败: {e}")
            return None
    
    def check_realtime_breakthrough(self, stock_info: Dict) -> Optional[Dict]:
        """检查实时突破情况"""
        try:
            code = stock_info['code']
            
            # 获取实时价格数据
            realtime_data = ak.stock_zh_a_spot_em()
            stock_realtime = realtime_data[realtime_data['代码'] == code]
            
            if stock_realtime.empty:
                return None
            
            current_high = stock_realtime.iloc[0]['最高']
            current_price = stock_realtime.iloc[0]['最新价']
            change_pct = stock_realtime.iloc[0]['涨跌幅']
            
            previous_high = stock_info['previous_high']
            
            # 检查是否突破前高点
            if current_high > previous_high:
                breakthrough_amount = current_high - previous_high
                breakthrough_pct = (breakthrough_amount / previous_high) * 100
                
                return {
                    'code': code,
                    'name': stock_info['name'],
                    'current_price': current_price,
                    'current_high': current_high,
                    'previous_high': previous_high,
                    'previous_high_date': stock_info['previous_high_date'],
                    'breakthrough_amount': breakthrough_amount,
                    'breakthrough_pct': breakthrough_pct,
                    'change_pct': change_pct,
                    'breakthrough_time': datetime.now().strftime('%H:%M:%S')
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"检查股票 {code} 实时突破失败: {e}")
            return None
    
    def format_breakthrough_message(self, breakthrough: Dict) -> str:
        """格式化突破消息"""
        breakthrough_pct = breakthrough['breakthrough_pct']
        
        # 根据突破幅度设置紧急程度
        if breakthrough_pct > 5:
            urgency = "🚨🚨🚨 重大突破"
            stars = "🚀🚀🚀"
        elif breakthrough_pct > 3:
            urgency = "🚨🚨 重要突破"
            stars = "🚀🚀"
        elif breakthrough_pct > 1:
            urgency = "🚨 一般突破"
            stars = "🚀"
        else:
            urgency = "📈 微小突破"
            stars = "⭐"
        
        message = f"""## {urgency} {stars}

**股票**: {breakthrough['name']} ({breakthrough['code']})
**突破时间**: {breakthrough['breakthrough_time']}
**现价**: {breakthrough['current_price']:.2f}元
**今日最高**: {breakthrough['current_high']:.2f}元
**前高价格**: {breakthrough['previous_high']:.2f}元 ({breakthrough['previous_high_date']})
**突破幅度**: {breakthrough_pct:.2f}%
**今日涨跌**: {breakthrough['change_pct']:.2f}%

---
*实时突破监测系统*"""
        
        return message
    
    def start_monitoring(self):
        """启动实时监测"""
        logger.info("🚀 启动实时突破监测系统...")
        
        # 构建监控池
        self.monitor_pool = self.build_monitor_pool()
        
        if not self.monitor_pool:
            logger.warning("监控股票池为空，无法启动监测")
            return
        
        # 发送启动通知
        start_msg = f"""🤖 实时突破监测系统已启动

📊 **监控股票池**: {len(self.monitor_pool)} 只股票
⏰ **监测频率**: 每 {self.monitor_interval} 秒
🎯 **监测条件**: 突破前高点（左三右三确认）

🔍 系统正在实时监测中..."""
        
        self.send_message(start_msg, "markdown")
        
        self.monitoring = True
        self.last_update_time = datetime.now()
        
        # 启动监测循环
        self._monitoring_loop()
    
    def _monitoring_loop(self):
        """监测主循环"""
        breakthrough_batch = []  # 批量推送缓存
        last_batch_time = time.time()
        
        while self.monitoring:
            try:
                current_time = datetime.now()
                
                # 检查是否在交易时间内
                if not self._is_trading_time(current_time):
                    logger.info("非交易时间，暂停监测")
                    time.sleep(300)  # 非交易时间休息5分钟
                    continue
                
                logger.info(f"🔍 开始检查 {len(self.monitor_pool)} 只股票的突破情况...")
                
                # 并发检查突破情况
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = [executor.submit(self.check_realtime_breakthrough, stock) 
                             for stock in self.monitor_pool]
                    
                    for future in futures:
                        try:
                            breakthrough = future.result(timeout=5)
                            if breakthrough:
                                stock_key = f"{breakthrough['code']}_{breakthrough['breakthrough_time'][:5]}"  # 精确到分钟
                                
                                if stock_key not in self.breakthrough_cache:
                                    self.breakthrough_cache.add(stock_key)
                                    
                                    # 根据突破幅度决定推送策略
                                    if breakthrough['breakthrough_pct'] > 3:
                                        # 重要突破立即推送
                                        message = self.format_breakthrough_message(breakthrough)
                                        self.send_message(message, "markdown")
                                        logger.info(f"✅ 立即推送重要突破: {breakthrough['code']} {breakthrough['name']}")
                                    else:
                                        # 一般突破加入批量推送
                                        breakthrough_batch.append(breakthrough)
                                        
                        except Exception as e:
                            logger.debug(f"检查突破失败: {e}")
                            continue
                
                # 批量推送一般突破（每5分钟或累积5只股票）
                current_batch_time = time.time()
                if (breakthrough_batch and 
                    (len(breakthrough_batch) >= 5 or 
                     current_batch_time - last_batch_time > 300)):
                    
                    self._send_batch_breakthroughs(breakthrough_batch)
                    breakthrough_batch.clear()
                    last_batch_time = current_batch_time
                
                # 每小时重新构建监控池
                if (current_time - self.last_update_time).seconds > 3600:
                    logger.info("🔄 重新构建监控股票池...")
                    self.monitor_pool = self.build_monitor_pool()
                    self.last_update_time = current_time
                
                # 等待下次检查，增加随机延迟避免请求过于规律
                import random
                delay = self.monitor_interval + random.uniform(5, 15)  # 增加5-15秒随机延迟
                time.sleep(delay)
                
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在关闭监测系统...")
                break
            except Exception as e:
                logger.error(f"监测循环异常: {e}")
                time.sleep(60)
        
        self.monitoring = False
        self.send_message("🛑 实时突破监测系统已停止")
    
    def _send_batch_breakthroughs(self, breakthroughs: List[Dict]):
        """批量发送一般突破"""
        if not breakthroughs:
            return
        
        message = f"## 📊 批量突破提醒 ({len(breakthroughs)}只)\n\n"
        
        for i, bt in enumerate(breakthroughs, 1):
            message += f"{i}. **{bt['name']}** ({bt['code']}) - {bt['current_price']:.2f}元 突破{bt['breakthrough_pct']:.2f}%\n"
        
        message += f"\n*{datetime.now().strftime('%H:%M:%S')} 批量推送*"
        
        self.send_message(message, "markdown")
        logger.info(f"✅ 批量推送 {len(breakthroughs)} 只突破股票")
    
    def _is_trading_time(self, current_time: datetime) -> bool:
        """检查是否在交易时间内"""
        # 周末不交易
        if current_time.weekday() >= 5:
            return False
        
        # 交易时间：9:30-11:30, 13:00-15:00
        time_str = current_time.strftime('%H:%M')
        morning_session = '09:30' <= time_str <= '11:30'
        afternoon_session = '13:00' <= time_str <= '15:00'
        
        return morning_session or afternoon_session
    
    def stop_monitoring(self):
        """停止监测"""
        self.monitoring = False
        logger.info("监测系统已停止")

# 测试功能
if __name__ == "__main__":
    # 测试配置
    webhook_url = "your_webhook_url_here"
    
    monitor = RealtimeBreakthroughMonitor(webhook_url, monitor_interval=30)
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()
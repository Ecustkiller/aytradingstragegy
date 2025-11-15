#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业轮动监控机器人
监控28个申万一级行业的轮动情况，识别热点行业
"""

import requests
import json
import logging
import time
from datetime import datetime, timedelta
import schedule
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import threading
try:
    from .optimized_data_loader import OptimizedDataLoader as AshareDataLoader
except ImportError:
    from optimized_data_loader import OptimizedDataLoader as AshareDataLoader

class RateLimiter:
    """请求频率限制器"""
    def __init__(self, max_requests_per_minute=10):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """如果需要，等待以满足频率限制"""
        with self.lock:
            now = time.time()
            # 清理1分钟前的记录
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            if len(self.requests) >= self.max_requests:
                sleep_time = 60 - (now - self.requests[0]) + 1
                print(f"⏳ 请求过于频繁，等待 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)
                self.requests = []
            
            self.requests.append(now)

class IndustryRotationBot:
    """行业轮动监控机器人"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.data_loader = AshareDataLoader()
        self.rate_limiter = RateLimiter(max_requests_per_minute=10)  # 降低到每分钟10次请求
        self.setup_logging()
        
        # 申万一级行业列表
        self.sw_industries = [
            "银行", "非银金融", "房地产", "建筑装饰", "建筑材料", "钢铁",
            "有色金属", "化工", "石油石化", "煤炭", "电力设备", "公用事业",
            "交通运输", "汽车", "家用电器", "纺织服装", "轻工制造", "商业贸易",
            "消费者服务", "农林牧渔", "食品饮料", "医药生物", "电子", "计算机",
            "通信", "传媒", "综合", "机械设备"
        ]
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s%(msecs)03d - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler('industry_rotation.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_sw_industry_data(self) -> Optional[pd.DataFrame]:
        """获取申万行业指数数据"""
        try:
            # 首先尝试web爬虫方式
            df = self.crawl_eastmoney_industry_data()
            if df is not None and not df.empty:
                return df
            
            # 备用方案：尝试同花顺
            df = self.crawl_tonghuashun_industry_data()
            if df is not None and not df.empty:
                return df
            
            # 最后尝试akshare (如果可用)
            try:
                import akshare as ak
                # 尝试仍然可用的API
                df = ak.stock_board_industry_name_em()
                if df is not None and not df.empty:
                    return df
            except:
                pass
                
            self.logger.warning("所有行业数据源都无法获取数据")
            return None
            
        except Exception as e:
            self.logger.error(f"获取申万行业数据失败: {e}")
            return None
    
    def crawl_eastmoney_industry_data(self) -> Optional[pd.DataFrame]:
        """爬取东方财富行业数据"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # 东方财富行业板块API
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '50',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'm:90 t:2',
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'http://quote.eastmoney.com/'
            }
            
            # 频率控制
            self.rate_limiter.wait_if_needed()
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and 'diff' in data['data']:
                    items = data['data']['diff']
                    
                    # 解析数据
                    industry_data = []
                    for item in items:
                        industry_info = {
                            '行业名称': item.get('f14', ''),  # 名称
                            '最新价': item.get('f2', 0),      # 最新价
                            '涨跌幅': item.get('f3', 0),      # 涨跌幅
                            '涨跌额': item.get('f4', 0),      # 涨跌额
                            '成交量': item.get('f5', 0),      # 成交量
                            '成交额': item.get('f6', 0),      # 成交额
                            '换手率': item.get('f8', 0),      # 换手率
                        }
                        industry_data.append(industry_info)
                    
                    if industry_data:
                        df = pd.DataFrame(industry_data)
                        self.logger.info(f"东方财富爬取到 {len(df)} 个行业数据")
                        return df
                        
        except Exception as e:
            self.logger.warning(f"东方财富行业数据爬取失败: {e}")
        
        return None
    
    def crawl_tonghuashun_industry_data(self) -> Optional[pd.DataFrame]:
        """爬取同花顺行业数据"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            url = "http://q.10jqka.com.cn/thshy/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # 频率控制
            self.rate_limiter.wait_if_needed()
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找行业数据表格
                table = soup.find('table', {'class': 'm-table'})
                if table:
                    rows = table.find_all('tr')[1:]  # 跳过表头
                    
                    industry_data = []
                    for row in rows[:20]:  # 取前20个行业
                        cols = row.find_all('td')
                        if len(cols) >= 6:
                            industry_info = {
                                '行业名称': cols[1].text.strip(),
                                '涨跌幅': float(cols[2].text.strip().replace('%', '')),
                                '平均价格': float(cols[3].text.strip()) if cols[3].text.strip() != '-' else 0,
                                '领涨股': cols[4].text.strip(),
                                '涨跌幅_领涨': float(cols[5].text.strip().replace('%', '')) if cols[5].text.strip() != '-' else 0,
                            }
                            industry_data.append(industry_info)
                    
                    if industry_data:
                        df = pd.DataFrame(industry_data)
                        self.logger.info(f"同花顺爬取到 {len(df)} 个行业数据")
                        return df
                        
        except Exception as e:
            self.logger.warning(f"同花顺行业数据爬取失败: {e}")
        
        return None
    
    
    def get_concept_board_data(self) -> Optional[pd.DataFrame]:
        """获取概念板块数据"""
        try:
            import akshare as ak
            # 获取概念板块行情
            df = ak.stock_board_concept_name_em()
            return df
        except Exception as e:
            self.logger.error(f"获取概念板块数据失败: {e}")
            return None
    
    def calculate_rotation_strength(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算行业轮动强度"""
        if df is None or df.empty:
            return pd.DataFrame()
        
        try:
            # 先按涨跌幅排序
            df = df.sort_values('涨跌幅', ascending=False).reset_index(drop=True)
            
            # 计算轮动强度指标
            df['rotation_score'] = 0.0
            
            # 1. 涨跌幅权重 (40%)
            if '涨跌幅' in df.columns:
                df['change_score'] = df['涨跌幅'].rank(pct=True) * 40
                df['rotation_score'] += df['change_score']
            
            # 2. 成交量权重 (30%) 
            if '成交量' in df.columns:
                df['volume_score'] = df['成交量'].rank(pct=True) * 30
                df['rotation_score'] += df['volume_score']
            
            # 3. 成交额权重 (20%)
            if '成交额' in df.columns:
                df['amount_score'] = df['成交额'].rank(pct=True) * 20
                df['rotation_score'] += df['amount_score']
            
            # 4. 换手率权重 (10%)
            if '换手率' in df.columns:
                df['turnover_score'] = df['换手率'].rank(pct=True) * 10
                df['rotation_score'] += df['turnover_score']
            
            return df.sort_values('rotation_score', ascending=False)
            
        except Exception as e:
            self.logger.error(f"计算轮动强度失败: {e}")
            return df
    
    def identify_hot_sectors(self, industry_df: pd.DataFrame, fund_df: Optional[pd.DataFrame] = None) -> List[Dict]:
        """识别热点行业"""
        hot_sectors = []
        
        try:
            # 仅基于行业涨跌数据分析
            if industry_df is not None and not industry_df.empty:
                # 计算轮动强度
                industry_df = self.calculate_rotation_strength(industry_df)
                
                # 筛选热点行业 (轮动强度前10)
                top_industries = industry_df.head(10)
                
                for _, row in top_industries.iterrows():
                    # 根据实际API字段名进行映射
                    sector_info = {
                        'name': row.get('行业名称', row.get('板块名称', row.get('名称', ''))),
                        'code': row.get('板块代码', row.get('代码', '')),
                        'change_pct': float(row.get('涨跌幅', 0)),
                        'volume': float(row.get('成交量', 0)),
                        'amount': float(row.get('总市值', row.get('成交额', 0))),
                        'turnover': float(row.get('换手率', 0)),
                        'rotation_score': float(row.get('rotation_score', 0)),
                        'leading_stock': row.get('领涨股', ''),
                        'leading_change': float(row.get('涨跌幅_领涨', 0))
                    }
                    
                    hot_sectors.append(sector_info)
            
            return hot_sectors
            
        except Exception as e:
            self.logger.error(f"识别热点行业失败: {e}")
            return []
    
    def analyze_rotation_trend(self, hot_sectors: List[Dict]) -> Dict:
        """分析轮动趋势"""
        if not hot_sectors:
            return {}
        
        try:
            analysis = {
                'total_sectors': len(hot_sectors),
                'rising_sectors': len([s for s in hot_sectors if s['change_pct'] > 0]),
                'falling_sectors': len([s for s in hot_sectors if s['change_pct'] < 0]),
                'strong_sectors': len([s for s in hot_sectors if s['change_pct'] > 2]),
                'weak_sectors': len([s for s in hot_sectors if s['change_pct'] < -2]),
                'avg_change': np.mean([s['change_pct'] for s in hot_sectors]),
                'top_sector': hot_sectors[0] if hot_sectors else None,
                'bottom_sector': hot_sectors[-1] if hot_sectors else None
            }
            
            # 判断市场轮动状态
            if analysis['strong_sectors'] >= 3:
                analysis['market_status'] = '强势轮动'
            elif analysis['rising_sectors'] > analysis['falling_sectors']:
                analysis['market_status'] = '温和轮动'
            elif analysis['weak_sectors'] >= 3:
                analysis['market_status'] = '弱势调整'
            else:
                analysis['market_status'] = '震荡整理'
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"分析轮动趋势失败: {e}")
            return {}
    
    def format_rotation_report(self, hot_sectors: List[Dict], analysis: Dict) -> str:
        """格式化轮动报告"""
        if not hot_sectors or not analysis:
            return "📊 行业轮动数据获取失败"
        
        # 市场状态emoji
        status_emoji = {
            '强势轮动': '🚀',
            '温和轮动': '📈', 
            '弱势调整': '📉',
            '震荡整理': '🔄'
        }
        
        emoji = status_emoji.get(analysis['market_status'], '📊')
        
        report = f"""## {emoji} 行业轮动监控报告

**📊 市场状态**: {analysis['market_status']}
**📈 上涨行业**: {analysis['rising_sectors']}个
**📉 下跌行业**: {analysis['falling_sectors']}个
**🔥 强势行业**: {analysis['strong_sectors']}个 (涨幅>2%)
**❄️ 弱势行业**: {analysis['weak_sectors']}个 (跌幅>2%)
**📊 平均涨跌**: {analysis['avg_change']:.2f}%

### 🏆 热点行业排行 (TOP10)

"""
        
        for i, sector in enumerate(hot_sectors[:10], 1):
            change_emoji = "📈" if sector['change_pct'] > 0 else "📉"
            
            report += f"""**{i}. {sector['name']}**
{change_emoji} 涨跌幅: {sector['change_pct']:.2f}%
💰 成交额: {sector['amount']/100000000:.1f}亿元
🔄 换手率: {sector['turnover']:.2f}%
🎯 轮动得分: {sector['rotation_score']:.1f}
"""
            
            # 添加领涨股信息
            if sector.get('leading_stock'):
                report += f"🏆 领涨股: {sector['leading_stock']} ({sector['leading_change']:.2f}%)\n"
            
            report += "\n"
        
        return report
    
    def send_message(self, content: str) -> bool:
        """发送消息到企业微信"""
        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    self.logger.info("行业轮动报告发送成功")
                    return True
                else:
                    self.logger.error(f"发送失败: {result}")
                    return False
            else:
                self.logger.error(f"HTTP错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送消息异常: {e}")
            return False
    
    def run_rotation_analysis(self):
        """执行行业轮动分析"""
        try:
            self.logger.info("开始行业轮动分析...")
            
            # 获取行业数据
            industry_df = self.get_sw_industry_data()
            
            # 识别热点行业（仅基于行业涨跌数据）
            hot_sectors = self.identify_hot_sectors(industry_df, None)
            
            # 分析轮动趋势
            analysis = self.analyze_rotation_trend(hot_sectors)
            
            # 生成并发送报告
            if hot_sectors and analysis:
                report = self.format_rotation_report(hot_sectors, analysis)
                report += f"\n\n---\n*📊 数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
                self.send_message(report)
            else:
                self.send_message("📊 行业轮动数据获取失败，请稍后重试")
                
        except Exception as e:
            error_msg = f"❌ 行业轮动分析失败: {str(e)}"
            self.logger.error(error_msg)
            self.send_message(error_msg)
    
    def start_scheduler(self):
        """启动定时任务"""
        self.logger.info("启动行业轮动监控定时任务...")
        
        # 设置定时任务
        schedule.every().day.at("09:35").do(self.run_rotation_analysis)  # 开盘后
        schedule.every().day.at("15:35").do(self.run_rotation_analysis)  # 收盘后
        schedule.every().day.at("21:00").do(self.run_rotation_analysis)  # 晚间总结
        
        self.logger.info("定时任务已设置:")
        self.logger.info("- 09:35 开盘行业轮动")
        self.logger.info("- 15:35 收盘行业总结")
        self.logger.info("- 21:00 晚间轮动分析")
        
        # 发送启动通知
        start_msg = """🤖 行业轮动监控机器人已启动

⏰ **监控时间**:
- 09:35 开盘行业轮动
- 15:35 收盘行业总结
- 21:00 晚间轮动分析

📊 **监控内容**:
- 申万28个一级行业
- 行业轮动强度计算
- 热点行业识别
- 轮动趋势判断
- 领涨股分析

🚀 系统已就绪，开始监控..."""
        
        self.send_message(start_msg)
        
        # 持续运行
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.logger.error(f"定时任务执行异常: {e}")
                time.sleep(60)

if __name__ == "__main__":
    # 测试运行
    webhook_url = "your_webhook_url_here"
    bot = IndustryRotationBot(webhook_url)
    bot.run_rotation_analysis()

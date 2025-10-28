#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import logging
import time
from datetime import datetime, timedelta
import schedule
from bs4 import BeautifulSoup
import feedparser
import re
from typing import List, Dict, Optional
import threading
import hashlib
import random
from urllib.parse import urljoin, urlparse

# 导入增强版爬虫
try:
    from .enhanced_news_crawler import EnhancedNewsCrawler
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False
    print("⚠️ 增强版爬虫不可用，将使用基础版本")

class NewsCrawlerBot:
    """财经新闻爬虫机器人"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.setup_logging()
        self.news_sources = self.init_news_sources()
        self.seen_news = set()  # 用于去重，避免重复发送
        self.session = requests.Session()  # 使用session提高性能
        self.setup_session_headers()
        
        # 初始化增强版爬虫
        if ENHANCED_AVAILABLE:
            self.enhanced_crawler = EnhancedNewsCrawler(webhook_url)
            self.logger.info("✅ 增强版爬虫已启用")
        else:
            self.enhanced_crawler = None
            self.logger.warning("⚠️ 增强版爬虫不可用，使用基础版本")
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s%(msecs)03d - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler('news_crawler_bot.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_session_headers(self):
        """设置session的通用headers"""
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def init_news_sources(self) -> Dict:
        """初始化新闻源配置"""
        return {
            'sina_finance': {
                'name': '新浪财经',
                'url': 'https://finance.sina.com.cn/roll/',
                'rss': 'https://feed.sina.com.cn/api/roll/get?pageid=153&lid=1686&k=&num=20&page=1',
                'type': 'rss'
            },
            'eastmoney': {
                'name': '东方财富',
                'url': 'https://finance.eastmoney.com/news/',
                'api': 'https://np-anotice-stock.eastmoney.com/api/security/ann',
                'type': 'api'
            },
            'wallstreetcn': {
                'name': '华尔街见闻',
                'url': 'https://wallstreetcn.com/news',
                'rss': 'https://api-prod.wallstreetcn.com/apiv1/content/articles',
                'type': 'api'
            },
            'cailianshe': {
                'name': '财联社',
                'url': 'https://www.cls.cn/telegraph',
                'type': 'web'
            },
            'yicai': {
                'name': '第一财经',
                'url': 'https://www.yicai.com/news/',
                'rss': 'https://www.yicai.com/api/ajax/getlatest',
                'type': 'api'
            }
        }
    
    def crawl_sina_finance(self) -> List[Dict]:
        """爬取新浪财经新闻"""
        news_list = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 直接爬取新浪财经首页
            url = 'https://finance.sina.com.cn/'
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找新闻链接
                news_links = soup.find_all('a', href=True)
                
                for link in news_links[:50]:  # 检查前50个链接
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    # 过滤有效的财经新闻
                    if (len(title) > 10 and 
                        self.is_finance_related(title) and
                        ('finance.sina.com.cn' in href or href.startswith('//'))):
                        
                        # 处理相对链接
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = 'https://finance.sina.com.cn' + href
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '新浪财经'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 10:  # 限制数量
                            break
            
            # 如果首页爬取失败，尝试RSS
            if not news_list:
                rss_url = 'http://rss.sina.com.cn/finance/roll.xml'
                try:
                    feed = feedparser.parse(rss_url)
                    for entry in feed.entries[:10]:
                        if hasattr(entry, 'title') and self.is_finance_related(entry.title):
                            news_item = {
                                'title': entry.title,
                                'url': entry.link if hasattr(entry, 'link') else '',
                                'time': entry.published if hasattr(entry, 'published') else '',
                                'source': '新浪财经'
                            }
                            news_list.append(news_item)
                except:
                    pass
                            
        except Exception as e:
            self.logger.error(f"爬取新浪财经新闻失败: {e}")
            
        return news_list
    
    def crawl_eastmoney_news(self) -> List[Dict]:
        """爬取东方财富新闻"""
        news_list = []
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://finance.eastmoney.com/'
            }
            
            # 直接爬取东方财富财经首页
            url = 'https://finance.eastmoney.com/'
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找新闻标题和链接
                news_elements = soup.find_all(['a', 'span'], class_=re.compile(r'.*title.*|.*news.*|.*article.*'))
                
                for element in news_elements[:50]:
                    title = element.get_text().strip()
                    
                    # 获取链接
                    if element.name == 'a':
                        href = element.get('href', '')
                    else:
                        # 如果是span，查找父级或兄弟元素的链接
                        parent_a = element.find_parent('a')
                        href = parent_a.get('href', '') if parent_a else ''
                    
                    if (len(title) > 10 and 
                        self.is_finance_related(title) and
                        href):
                        
                        # 处理相对链接
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = 'https://finance.eastmoney.com' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '东方财富'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
            
            # 如果没有获取到足够新闻，尝试移动端接口
            if len(news_list) < 3:
                try:
                    mobile_url = 'https://wap.eastmoney.com/news/'
                    mobile_response = self.session.get(mobile_url, timeout=10)
                    
                    if mobile_response.status_code == 200:
                        mobile_soup = BeautifulSoup(mobile_response.content, 'html.parser')
                        mobile_links = mobile_soup.find_all('a', href=True)
                        
                        for link in mobile_links[:20]:
                            title = link.get_text().strip()
                            href = link.get('href', '')
                            
                            if (len(title) > 10 and self.is_finance_related(title) and
                                ('eastmoney.com' in href or href.startswith('/'))):
                                
                                if href.startswith('/'):
                                    href = 'https://wap.eastmoney.com' + href
                                elif href.startswith('//'):
                                    href = 'https:' + href
                                
                                news_item = {
                                    'title': title,
                                    'url': href,
                                    'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    'source': '东方财富'
                                }
                                news_list.append(news_item)
                                
                                if len(news_list) >= 8:
                                    break
                except Exception as e:
                    self.logger.warning(f"东方财富移动端爬取失败: {e}")
                            
        except Exception as e:
            self.logger.error(f"爬取东方财富新闻失败: {e}")
            
        return news_list
    
    def crawl_cailianshe_news(self) -> List[Dict]:
        """爬取财联社快讯 - 使用真实API和多种方法"""
        news_list = []
        
        # 方法1: 尝试财联社API接口
        try:
            api_news = self.crawl_cailianshe_api()
            news_list.extend(api_news)
            self.logger.info(f"财联社API获取到 {len(api_news)} 条新闻")
        except Exception as e:
            self.logger.warning(f"财联社API爬取失败: {e}")
        
        # 方法2: 爬取财联社快讯页面
        if len(news_list) < 5:
            try:
                web_news = self.crawl_cailianshe_web()
                news_list.extend(web_news)
                self.logger.info(f"财联社网页爬取获取到 {len(web_news)} 条新闻")
            except Exception as e:
                self.logger.warning(f"财联社网页爬取失败: {e}")
        
        # 方法3: 爬取财联社RSS
        if len(news_list) < 3:
            try:
                rss_news = self.crawl_cailianshe_rss()
                news_list.extend(rss_news)
                self.logger.info(f"财联社RSS获取到 {len(rss_news)} 条新闻")
            except Exception as e:
                self.logger.warning(f"财联社RSS爬取失败: {e}")
        
        # 去重处理
        unique_news = self.deduplicate_news(news_list)
        
        # 如果仍然没有获取到新闻，记录错误但不使用模拟数据
        if not unique_news:
            self.logger.error("财联社所有数据源都无法获取真实数据，跳过此次推送")
            return []
        
        return unique_news[:8]  # 返回最多8条新闻
    
    def crawl_cailianshe_api(self) -> List[Dict]:
        """使用财联社API接口获取新闻"""
        news_list = []
        try:
            # 财联社快讯API
            api_url = 'https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=7.7.5'
            
            params = {
                'channel': 'telegraph',
                'limit': 20,
                'sign': self.generate_cls_sign()
            }
            
            response = self.session.get(api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 200 and 'data' in data:
                    items = data['data'].get('list', [])
                    
                    for item in items:
                        title = item.get('title', '').strip()
                        content = item.get('content', '').strip()
                        pub_time = item.get('publish_time', '')
                        news_id = item.get('id', '')
                        
                        # 使用标题或内容
                        final_title = title if title else content[:100]
                        
                        if (final_title and len(final_title) > 10 and 
                            self.is_finance_related(final_title)):
                            
                            news_item = {
                                'title': final_title,
                                'url': f'https://www.cls.cn/telegraph/{news_id}' if news_id else 'https://www.cls.cn/telegraph',
                                'time': self.format_time(pub_time),
                                'source': '财联社',
                                'id': news_id
                            }
                            news_list.append(news_item)
                            
        except Exception as e:
            self.logger.error(f"财联社API爬取失败: {e}")
            
        return news_list
    
    def crawl_cailianshe_web(self) -> List[Dict]:
        """爬取财联社网页版快讯"""
        news_list = []
        try:
            # 更新headers
            self.session.headers.update({
                'Referer': 'https://www.cls.cn/',
                'Host': 'www.cls.cn'
            })
            
            url = 'https://www.cls.cn/telegraph'
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找快讯内容的多种选择器
                selectors = [
                    '.telegraph-content-box .telegraph-content',
                    '.telegraph-item',
                    '[class*="telegraph"]',
                    '.news-item',
                    '.telegraph-content-box p',
                    '.telegraph-list .item'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        self.logger.info(f"使用选择器 {selector} 找到 {len(elements)} 个元素")
                        
                        for element in elements[:20]:
                            title = element.get_text().strip()
                            
                            # 清理标题
                            title = re.sub(r'\s+', ' ', title)
                            title = re.sub(r'^[0-9:\-\s]+', '', title)  # 移除开头的时间
                            
                            if (len(title) > 15 and len(title) < 200 and 
                                self.is_finance_related(title) and
                                not self.is_duplicate_news(title)):
                                
                                # 尝试获取链接
                                link_element = element.find('a') or element.find_parent('a')
                                news_url = 'https://www.cls.cn/telegraph'
                                if link_element and link_element.get('href'):
                                    href = link_element.get('href')
                                    if href.startswith('/'):
                                        news_url = 'https://www.cls.cn' + href
                                    elif href.startswith('http'):
                                        news_url = href
                                
                                news_item = {
                                    'title': title,
                                    'url': news_url,
                                    'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    'source': '财联社',
                                    'id': hashlib.md5(title.encode()).hexdigest()[:8]
                                }
                                news_list.append(news_item)
                                
                                if len(news_list) >= 10:
                                    break
                        
                        if news_list:
                            break
                            
        except Exception as e:
            self.logger.error(f"财联社网页爬取失败: {e}")
            
        return news_list
    
    def crawl_cailianshe_rss(self) -> List[Dict]:
        """尝试爬取财联社RSS或其他格式的数据源"""
        news_list = []
        try:
            # 尝试移动端API
            mobile_api = 'https://m.cls.cn/api/telegraph'
            params = {
                'limit': 20,
                'channel': 'all'
            }
            
            response = self.session.get(mobile_api, params=params, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    items = data.get('data', {}).get('list', [])
                    
                    for item in items:
                        title = item.get('title', '').strip()
                        if not title:
                            title = item.get('content', '').strip()[:100]
                        
                        if (title and len(title) > 10 and 
                            self.is_finance_related(title)):
                            
                            news_item = {
                                'title': title,
                                'url': f"https://www.cls.cn/telegraph/{item.get('id', '')}",
                                'time': self.format_time(item.get('publish_time', '')),
                                'source': '财联社',
                                'id': item.get('id', '')
                            }
                            news_list.append(news_item)
                            
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"财联社RSS爬取失败: {e}")
            
        return news_list
    
    def generate_cls_sign(self) -> str:
        """生成财联社API签名（如果需要）"""
        timestamp = str(int(time.time()))
        # 简单的签名生成，实际可能需要更复杂的算法
        return hashlib.md5(f"cls{timestamp}".encode()).hexdigest()
    
    def format_time(self, time_str: str) -> str:
        """格式化时间字符串"""
        if not time_str:
            return datetime.now().strftime('%Y-%m-%d %H:%M')
        
        try:
            # 尝试解析不同格式的时间
            if isinstance(time_str, (int, float)):
                return datetime.fromtimestamp(time_str).strftime('%Y-%m-%d %H:%M')
            elif 'T' in time_str:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M')
            else:
                return time_str
        except:
            return datetime.now().strftime('%Y-%m-%d %H:%M')
    
    def is_duplicate_news(self, title: str) -> bool:
        """检查新闻是否重复"""
        title_hash = hashlib.md5(title.encode()).hexdigest()
        if title_hash in self.seen_news:
            return True
        self.seen_news.add(title_hash)
        return False
    
    def deduplicate_news(self, news_list: List[Dict]) -> List[Dict]:
        """去重新闻列表"""
        unique_news = []
        seen_titles = set()
        
        for news in news_list:
            title = news['title'].strip()
            title_normalized = re.sub(r'\s+', ' ', title).lower()
            
            if title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_news.append(news)
        
        return unique_news
    
    def add_real_time_news_sources(self) -> List[Dict]:
        """添加更多真实的新闻源"""
        news_list = []
        
        # 尝试新华财经API
        try:
            xinhua_news = self.crawl_xinhua_finance()
            news_list.extend(xinhua_news)
            self.logger.info(f"新华财经获取到 {len(xinhua_news)} 条新闻")
        except Exception as e:
            self.logger.warning(f"新华财经爬取失败: {e}")
        
        # 尝试证券时报API
        try:
            stcn_news = self.crawl_stcn_news()
            news_list.extend(stcn_news)
            self.logger.info(f"证券时报获取到 {len(stcn_news)} 条新闻")
        except Exception as e:
            self.logger.warning(f"证券时报爬取失败: {e}")
            
        return news_list
    
    def crawl_xinhua_finance(self) -> List[Dict]:
        """爬取新华财经新闻"""
        news_list = []
        try:
            url = 'http://www.xinhuanet.com/money/index.htm'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找新闻链接
                news_links = soup.find_all('a', href=True)
                
                for link in news_links[:30]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('xinhuanet.com' in href or href.startswith('/'))):
                        
                        if href.startswith('/'):
                            href = 'http://www.xinhuanet.com' + href
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '新华财经'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 5:
                            break
        except Exception as e:
            self.logger.error(f"新华财经爬取失败: {e}")
            
        return news_list
    
    def crawl_stcn_news(self) -> List[Dict]:
        """爬取证券时报新闻"""
        news_list = []
        try:
            url = 'https://www.stcn.com/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找新闻
                news_elements = soup.find_all(['a', 'h3', 'h4'], href=True)
                
                for element in news_elements[:30]:
                    title = element.get_text().strip()
                    href = element.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('stcn.com' in href or href.startswith('/'))):
                        
                        if href.startswith('/'):
                            href = 'https://www.stcn.com' + href
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '证券时报'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 5:
                            break
        except Exception as e:
            self.logger.error(f"证券时报爬取失败: {e}")
            
        return news_list
    
    def is_finance_related(self, title: str) -> bool:
        """判断是否为财经相关新闻"""
        finance_keywords = [
            '股市', '股票', '基金', '债券', '期货', '外汇', '黄金',
            '银行', '保险', '证券', '投资', '融资', 'IPO', '并购',
            '央行', '货币政策', '利率', '汇率', '通胀', 'CPI', 'GDP',
            '上市', '退市', '停牌', '复牌', '涨停', '跌停',
            '财报', '业绩', '营收', '利润', '亏损',
            '监管', '证监会', '银保监会', '交易所',
            '科技股', '新能源', '芯片', '医药', '地产', '金融'
        ]
        
        return any(keyword in title for keyword in finance_keywords)
    
    def format_news_report(self, news_list: List[Dict], report_type: str) -> List[str]:
        """格式化新闻报告，返回多条消息列表"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if report_type == 'morning':
            title = f"📰 早间财经新闻汇总 ({current_time})"
            intro = "🌅 隔夜重要财经新闻，助您把握市场脉搏"
        else:
            title = f"📰 晚间财经新闻汇总 ({current_time})"
            intro = "🌙 今日重要市场动态，为您梳理投资要点"
        
        if not news_list:
            report = f"{title}\n\n{intro}\n\n"
            report += "📭 所有新闻源暂时无法获取真实数据\n"
            report += "🔄 系统将在下次推送时重新尝试\n"
            report += "⚠️ 绝不使用模拟数据，确保信息真实性\n"
            return [report]
        
        # 按来源分组
        sources = {}
        for news in news_list:
            source = news['source']
            if source not in sources:
                sources[source] = []
            sources[source].append(news)
        
        # 将新闻分成多条消息，每条消息包含部分来源
        messages = []
        
        # 第一条消息包含标题和介绍
        first_message = f"{title}\n\n{intro}\n\n"
        messages.append(first_message)
        
        # 将来源分成多组，每组3-4个来源
        source_groups = []
        current_group = []
        for source, news_items in sources.items():
            current_group.append((source, news_items))
            if len(current_group) >= 3:  # 每3个来源为一组
                source_groups.append(current_group)
                current_group = []
        
        # 添加剩余的来源
        if current_group:
            source_groups.append(current_group)
        
        # 为每组来源生成一条消息
        for i, group in enumerate(source_groups):
            group_message = f"📰 财经新闻汇总 (第{i+1}部分)\n\n"
            
            for source, source_news in group:
                group_message += f"## 📊 {source}\n"
                for j, news in enumerate(source_news[:5], 1):  # 每个来源最多5条
                    title = news['title'][:50] + '...' if len(news['title']) > 50 else news['title']
                    url = news.get('url', '')
                    
                    # 添加链接
                    if url:
                        group_message += f"{j}. [{title}]({url})\n"
                    else:
                        group_message += f"{j}. {title}\n"
                group_message += "\n"
            
            messages.append(group_message)
        
        return messages
    
    def collect_all_news(self) -> List[Dict]:
        """收集所有新闻源的新闻 - 优先使用增强版"""
        
        # 优先使用增强版爬虫
        if self.enhanced_crawler:
            self.logger.info("🚀 使用增强版爬虫收集新闻...")
            try:
                enhanced_news = self.enhanced_crawler.collect_all_news_enhanced()
                if enhanced_news:
                    self.logger.info(f"✅ 增强版爬虫获取到 {len(enhanced_news)} 条新闻")
                    return enhanced_news
                else:
                    self.logger.warning("⚠️ 增强版爬虫未获取到新闻，尝试基础版本")
            except Exception as e:
                self.logger.error(f"❌ 增强版爬虫失败: {e}，尝试基础版本")
        
        # 基础版本爬虫作为备用
        self.logger.info("📰 使用基础版爬虫收集新闻...")
        all_news = []
        
        # 主要新闻源爬虫
        main_crawlers = [
            self.crawl_sina_finance,
            self.crawl_eastmoney_news,
            self.crawl_cailianshe_news
        ]
        
        for crawler in main_crawlers:
            try:
                news = crawler()
                all_news.extend(news)
                self.logger.info(f"{crawler.__name__} 获取到 {len(news)} 条新闻")
                time.sleep(random.uniform(1, 3))  # 随机延迟避免被封
            except Exception as e:
                self.logger.error(f"爬取新闻失败 {crawler.__name__}: {e}")
        
        # 如果主要源新闻不足，尝试额外的新闻源
        if len(all_news) < 5:
            self.logger.info("主要新闻源数据不足，尝试额外新闻源...")
            try:
                additional_news = self.add_real_time_news_sources()
                all_news.extend(additional_news)
                self.logger.info(f"额外新闻源获取到 {len(additional_news)} 条新闻")
            except Exception as e:
                self.logger.error(f"额外新闻源爬取失败: {e}")
        
        # 去重和过滤
        unique_news = self.deduplicate_news(all_news)
        
        # 按时间排序
        try:
            unique_news.sort(key=lambda x: x.get('time', ''), reverse=True)
        except Exception as e:
            self.logger.warning(f"新闻排序失败: {e}")
        
        if not unique_news:
            self.logger.error("❌ 所有新闻源都无法获取真实数据，本次推送取消")
            return []
        
        self.logger.info(f"✅ 基础版成功收集到 {len(unique_news)} 条真实财经新闻")
        return unique_news[:15]  # 返回最新的15条
    
    def send_markdown(self, content: str) -> bool:
        """发送单条Markdown消息到企业微信"""
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
                    self.logger.info("新闻报告发送成功")
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
    
    def send_messages(self, messages: List[str]) -> bool:
        """发送多条消息到企业微信"""
        if not messages:
            self.logger.error("没有消息可发送")
            return False
            
        success_count = 0
        for i, message in enumerate(messages):
            try:
                if i > 0:
                    # 消息之间添加短暂延迟，避免频率限制
                    time.sleep(1)
                    
                success = self.send_markdown(message)
                if success:
                    success_count += 1
                else:
                    self.logger.error(f"第{i+1}条消息发送失败")
            except Exception as e:
                self.logger.error(f"发送第{i+1}条消息异常: {e}")
                
        self.logger.info(f"成功发送 {success_count}/{len(messages)} 条消息")
        return success_count == len(messages)
    
    def send_morning_news(self):
        """发送早间新闻 - 只发送真实数据"""
        self.logger.info("开始发送早间财经新闻...")
        news_list = self.collect_all_news()
        
        if not news_list:
            error_msg = f"""❌ **早间新闻推送失败**

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
🚫 原因: 所有新闻源都无法获取真实数据
🔄 下次推送: {datetime.now().strftime('%Y-%m-%d')} 20:00
⚠️ 系统绝不使用模拟数据，确保信息真实性"""
            
            self.send_markdown(error_msg)
            self.logger.error("早间新闻: 无真实数据可发送")
            return
        
        messages = self.format_news_report(news_list, 'morning')
        success = self.send_messages(messages)
        
        if success:
            self.logger.info(f"✅ 早间财经新闻发送成功 ({len(news_list)} 条真实新闻)")
        else:
            self.logger.error("早间财经新闻发送失败")
    
    def send_midday_news(self):
        """发送午间新闻"""
        self.logger.info("开始发送午间财经新闻...")
        news_list = self.collect_all_news()
        messages = self.format_news_report(news_list, 'midday')
        success = self.send_messages(messages)
        
        if success:
            self.logger.info("午间财经新闻发送成功")
        else:
            self.logger.error("午间财经新闻发送失败")
    
    def send_afternoon_news(self):
        """发送下午新闻"""
        self.logger.info("开始发送下午财经新闻...")
        news_list = self.collect_all_news()
        messages = self.format_news_report(news_list, 'afternoon')
        success = self.send_messages(messages)
        
        if success:
            self.logger.info("下午财经新闻发送成功")
        else:
            self.logger.error("下午财经新闻发送失败")
    
    def send_evening_news(self):
        """发送晚间新闻 - 只发送真实数据"""
        self.logger.info("开始发送晚间财经新闻...")
        news_list = self.collect_all_news()
        
        if not news_list:
            error_msg = f"""❌ **晚间新闻推送失败**

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
🚫 原因: 所有新闻源都无法获取真实数据
🔄 下次推送: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')} 08:00
⚠️ 系统绝不使用模拟数据，确保信息真实性"""
            
            self.send_markdown(error_msg)
            self.logger.error("晚间新闻: 无真实数据可发送")
            return
        
        messages = self.format_news_report(news_list, 'evening')
        success = self.send_messages(messages)
        
        if success:
            self.logger.info(f"✅ 晚间财经新闻发送成功 ({len(news_list)} 条真实新闻)")
        else:
            self.logger.error("晚间财经新闻发送失败")
    
    def send_night_news(self):
        """发送夜间新闻"""
        self.logger.info("开始发送夜间财经新闻...")
        news_list = self.collect_all_news()
        messages = self.format_news_report(news_list, 'night')
        success = self.send_messages(messages)
        
        if success:
            self.logger.info("夜间财经新闻发送成功")
        else:
            self.logger.error("夜间财经新闻发送失败")
    
    def start_scheduler(self):
        """启动定时任务"""
        self.logger.info("启动新闻爬虫定时任务...")
        
        # 设置定时任务 - 增加推送频率
        schedule.every().day.at("08:00").do(self.send_morning_news)
        schedule.every().day.at("12:30").do(self.send_midday_news)  # 新增午间新闻
        schedule.every().day.at("15:30").do(self.send_afternoon_news)  # 新增下午新闻
        schedule.every().day.at("20:00").do(self.send_evening_news)
        schedule.every().day.at("22:00").do(self.send_night_news)  # 新增夜间新闻
        
        self.logger.info("定时任务已设置:")
        self.logger.info("- 早间新闻: 每日 08:00")
        self.logger.info("- 午间新闻: 每日 12:30")
        self.logger.info("- 下午新闻: 每日 15:30")
        self.logger.info("- 晚间新闻: 每日 20:00")
        self.logger.info("- 夜间新闻: 每日 22:00")
        
        # 发送启动通知
        startup_msg = f"""🤖 **新闻爬虫机器人已启动**

📅 **推送时间表**
• 08:00 - 早间财经新闻汇总
• 20:00 - 晚间财经新闻汇总

📰 **新闻源覆盖**
• 新浪财经、东方财富、财联社
• 重点关注股市、政策、行业动态

🚀 机器人已开始工作，为您提供及时的财经资讯！

⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        self.send_markdown(startup_msg)
        
        # 运行定时任务
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                self.logger.info("收到停止信号，正在关闭新闻爬虫机器人...")
                break
            except Exception as e:
                self.logger.error(f"定时任务执行异常: {e}")
                time.sleep(60)

if __name__ == "__main__":
    # 测试用配置
    webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=6d5ddff9-8787-4863-922a-6b2c1ab9f450"
    
    bot = NewsCrawlerBot(webhook_url)
    
    # 测试新闻收集
    print("测试新闻收集...")
    news = bot.collect_all_news()
    print(f"收集到 {len(news)} 条新闻")
    
    # 测试报告生成
    report = bot.format_news_report(news, 'morning')
    print("生成的报告:")
    print(report)
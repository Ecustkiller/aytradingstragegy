#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版新闻爬虫 - 支持更多数据源和模拟浏览器
"""

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
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

class EnhancedNewsCrawler:
    """增强版财经新闻爬虫 - 支持更多数据源"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.setup_logging()
        self.seen_news = set()
        self.session = requests.Session()
        self.setup_session_headers()
        self.chrome_options = self.setup_chrome_options()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s%(msecs)03d - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler('enhanced_news_crawler.log', encoding='utf-8'),
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
    
    def setup_chrome_options(self):
        """设置Chrome选项"""
        options = Options()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        return options
    
    def create_driver(self):
        """创建WebDriver实例"""
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            self.logger.error(f"创建WebDriver失败: {e}")
            return None
    
    # ==================== 财联社新闻源 ====================
    def crawl_cailianshe_selenium(self) -> List[Dict]:
        """使用Selenium爬取财联社快讯"""
        news_list = []
        driver = None
        
        try:
            driver = self.create_driver()
            if not driver:
                return news_list
            
            self.logger.info("使用Selenium访问财联社...")
            driver.get('https://www.cls.cn/telegraph')
            
            # 等待页面加载
            time.sleep(3)
            
            # 尝试点击加载更多按钮
            try:
                load_more_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "load-more"))
                )
                ActionChains(driver).move_to_element(load_more_btn).click().perform()
                time.sleep(2)
            except:
                pass
            
            # 获取快讯内容
            selectors = [
                '.telegraph-item',
                '.telegraph-content',
                '[class*="telegraph"]',
                '.news-item',
                '.item-content'
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"财联社Selenium找到 {len(elements)} 个元素 (选择器: {selector})")
                        
                        for element in elements[:30]:
                            try:
                                title = element.text.strip()
                                
                                # 清理标题
                                title = re.sub(r'\s+', ' ', title)
                                title = re.sub(r'^[0-9:\-\s]+', '', title)
                                
                                if (len(title) > 15 and len(title) < 300 and 
                                    self.is_finance_related(title) and
                                    not self.is_duplicate_news(title)):
                                    
                                    # 尝试获取链接
                                    try:
                                        link_element = element.find_element(By.TAG_NAME, 'a')
                                        news_url = link_element.get_attribute('href')
                                    except:
                                        news_url = 'https://www.cls.cn/telegraph'
                                    
                                    news_item = {
                                        'title': title,
                                        'url': news_url,
                                        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                        'source': '财联社',
                                        'method': 'selenium'
                                    }
                                    news_list.append(news_item)
                                    
                                    if len(news_list) >= 15:
                                        break
                            except Exception as e:
                                continue
                        
                        if news_list:
                            break
                except Exception as e:
                    continue
                    
        except Exception as e:
            self.logger.error(f"财联社Selenium爬取失败: {e}")
        finally:
            if driver:
                driver.quit()
        
        return news_list
    
    def crawl_cailianshe_api_enhanced(self) -> List[Dict]:
        """增强版财联社API爬取"""
        news_list = []
        
        # 多个API端点
        api_endpoints = [
            {
                'url': 'https://www.cls.cn/api/sw',
                'params': {
                    'app': 'CailianpressWeb',
                    'os': 'web',
                    'sv': '7.7.5',
                    'channel': 'telegraph',
                    'limit': 30
                }
            },
            {
                'url': 'https://m.cls.cn/api/telegraph',
                'params': {
                    'limit': 30,
                    'channel': 'all'
                }
            },
            {
                'url': 'https://www.cls.cn/nodeapi/telegraphList',
                'params': {
                    'app': 'CailianpressWeb',
                    'limit': 30,
                    'lastTime': int(time.time())
                }
            }
        ]
        
        for endpoint in api_endpoints:
            try:
                response = self.session.get(endpoint['url'], params=endpoint['params'], timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 处理不同API的响应格式
                    items = []
                    if 'data' in data and isinstance(data['data'], dict) and 'list' in data['data']:
                        items = data['data']['list']
                    elif 'data' in data and isinstance(data['data'], list):
                        items = data['data']
                    elif isinstance(data, list):
                        items = data
                    
                    for item in items:
                        title = item.get('title', '').strip() or item.get('content', '').strip()[:100]
                        
                        if (title and len(title) > 10 and 
                            self.is_finance_related(title) and
                            not self.is_duplicate_news(title)):
                            
                            news_item = {
                                'title': title,
                                'url': f"https://www.cls.cn/telegraph/{item.get('id', '')}",
                                'time': self.format_time(item.get('publish_time', item.get('ctime', ''))),
                                'source': '财联社',
                                'method': 'api'
                            }
                            news_list.append(news_item)
                    
                    if news_list:
                        self.logger.info(f"财联社API获取到 {len(news_list)} 条新闻")
                        break
                        
            except Exception as e:
                self.logger.warning(f"财联社API端点失败: {e}")
                continue
        
        return news_list
    
    # ==================== 东方财富新闻源 ====================
    def crawl_eastmoney_enhanced(self) -> List[Dict]:
        """增强版东方财富新闻爬取"""
        news_list = []
        
        # 多个东方财富数据源
        sources = [
            {
                'name': '东方财富快讯',
                'url': 'https://finance.eastmoney.com/news/cjkx.html',
                'selectors': ['.newslist li a', '.news-item a', '.content-list a']
            },
            {
                'name': '东方财富要闻',
                'url': 'https://finance.eastmoney.com/',
                'selectors': ['.news-list a', '.important-news a', '.finance-news a']
            },
            {
                'name': '东方财富移动端',
                'url': 'https://wap.eastmoney.com/news/',
                'selectors': ['.news-item a', '.article-item a', '.list-item a']
            }
        ]
        
        for source in sources:
            try:
                response = self.session.get(source['url'], timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    for selector in source['selectors']:
                        elements = soup.select(selector)
                        if elements:
                            for element in elements[:20]:
                                title = element.get_text().strip()
                                href = element.get('href', '')
                                
                                if (len(title) > 10 and self.is_finance_related(title) and
                                    not self.is_duplicate_news(title)):
                                    
                                    # 处理相对链接
                                    if href.startswith('/'):
                                        href = 'https://finance.eastmoney.com' + href
                                    elif href.startswith('//'):
                                        href = 'https:' + href
                                    elif not href.startswith('http'):
                                        continue
                                    
                                    news_item = {
                                        'title': title,
                                        'url': href,
                                        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                        'source': source['name'],
                                        'method': 'web'
                                    }
                                    news_list.append(news_item)
                                    
                                    if len(news_list) >= 15:
                                        break
                            
                            if len(news_list) >= 10:
                                break
                    
                    if len(news_list) >= 8:
                        break
                        
            except Exception as e:
                self.logger.warning(f"东方财富源 {source['name']} 失败: {e}")
                continue
        
        return news_list
    
    # ==================== 新浪财经新闻源 ====================
    def crawl_sina_finance_enhanced(self) -> List[Dict]:
        """增强版新浪财经新闻爬取"""
        news_list = []
        
        sources = [
            {
                'name': '新浪财经',
                'url': 'https://finance.sina.com.cn/',
                'selectors': ['.news-list a', '.important-news a', '.finance-list a']
            },
            {
                'name': '新浪财经滚动',
                'url': 'https://finance.sina.com.cn/roll/',
                'selectors': ['.d_list_txt a', '.news-item a', '.list-item a']
            },
            {
                'name': '新浪财经要闻',
                'url': 'https://finance.sina.com.cn/china/',
                'selectors': ['.blk_03 a', '.news-list a', '.content-list a']
            }
        ]
        
        for source in sources:
            try:
                response = self.session.get(source['url'], timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # 获取所有链接
                    all_links = soup.find_all('a', href=True)
                    
                    for link in all_links[:50]:
                        title = link.get_text().strip()
                        href = link.get('href', '')
                        
                        if (len(title) > 10 and self.is_finance_related(title) and
                            ('finance.sina.com.cn' in href or href.startswith('/')) and
                            not self.is_duplicate_news(title)):
                            
                            # 处理相对链接
                            if href.startswith('//'):
                                href = 'https:' + href
                            elif href.startswith('/'):
                                href = 'https://finance.sina.com.cn' + href
                            
                            news_item = {
                                'title': title,
                                'url': href,
                                'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                'source': source['name'],
                                'method': 'web'
                            }
                            news_list.append(news_item)
                            
                            if len(news_list) >= 10:
                                break
                    
                    if len(news_list) >= 5:
                        break
                        
            except Exception as e:
                self.logger.warning(f"新浪财经源 {source['name']} 失败: {e}")
                continue
        
        return news_list
    
    # ==================== 更多新闻源 ====================
    def crawl_wallstreetcn_news(self) -> List[Dict]:
        """爬取华尔街见闻"""
        news_list = []
        
        try:
            # 华尔街见闻API
            api_url = 'https://api-prod.wallstreetcn.com/apiv1/content/articles'
            params = {
                'limit': 20,
                'platform': 'web',
                'fields': 'title,summary,display_time,uri'
            }
            
            response = self.session.get(api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('data', {}).get('items', [])
                
                for item in items:
                    title = item.get('title', '').strip()
                    
                    if (title and len(title) > 10 and 
                        self.is_finance_related(title) and
                        not self.is_duplicate_news(title)):
                        
                        news_item = {
                            'title': title,
                            'url': f"https://wallstreetcn.com/articles/{item.get('id', '')}",
                            'time': self.format_time(item.get('display_time', '')),
                            'source': '华尔街见闻',
                            'method': 'api'
                        }
                        news_list.append(news_item)
                        
        except Exception as e:
            self.logger.error(f"华尔街见闻爬取失败: {e}")
        
        return news_list
    
    def crawl_yicai_news(self) -> List[Dict]:
        """爬取第一财经"""
        news_list = []
        
        try:
            url = 'https://www.yicai.com/api/ajax/getlatest'
            params = {
                'page': 1,
                'pagesize': 20
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('data', [])
                
                # 确保items是列表
                if not isinstance(items, list):
                    items = []
                
                for item in items:
                    title = item.get('NewsTitle', '').strip()
                    
                    if (title and len(title) > 10 and 
                        self.is_finance_related(title) and
                        not self.is_duplicate_news(title)):
                        
                        news_item = {
                            'title': title,
                            'url': f"https://www.yicai.com/news/{item.get('NewsID', '')}",
                            'time': self.format_time(item.get('CreateTime', '')),
                            'source': '第一财经',
                            'method': 'api'
                        }
                        news_list.append(news_item)
                        
        except Exception as e:
            self.logger.error(f"第一财经爬取失败: {e}")
        
        return news_list
    
    def crawl_jrj_news(self) -> List[Dict]:
        """爬取金融界"""
        news_list = []
        
        try:
            url = 'https://finance.jrj.com.cn/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找新闻链接
                links = soup.find_all('a', href=True)
                
                for link in links[:40]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('jrj.com.cn' in href or href.startswith('/')) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://finance.jrj.com.cn' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '金融界',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"金融界爬取失败: {e}")
        
        return news_list
    
    def crawl_cnstock_news(self) -> List[Dict]:
        """爬取中国证券网"""
        news_list = []
        
        try:
            url = 'https://www.cnstock.com/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                
                for link in links[:40]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('cnstock.com' in href or href.startswith('/')) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://www.cnstock.com' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '中国证券网',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"中国证券网爬取失败: {e}")
        
        return news_list
    
    def crawl_stcn_enhanced(self) -> List[Dict]:
        """增强版证券时报爬取"""
        news_list = []
        
        sources = [
            'https://www.stcn.com/',
            'https://kuaixun.stcn.com/',
            'https://news.stcn.com/'
        ]
        
        for url in sources:
            try:
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    links = soup.find_all('a', href=True)
                    
                    for link in links[:30]:
                        title = link.get_text().strip()
                        href = link.get('href', '')
                        
                        if (len(title) > 10 and self.is_finance_related(title) and
                            ('stcn.com' in href or href.startswith('/')) and
                            not self.is_duplicate_news(title)):
                            
                            if href.startswith('/'):
                                href = 'https://www.stcn.com' + href
                            elif not href.startswith('http'):
                                continue
                            
                            news_item = {
                                'title': title,
                                'url': href,
                                'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                'source': '证券时报',
                                'method': 'web'
                            }
                            news_list.append(news_item)
                            
                            if len(news_list) >= 5:
                                break
                
                if len(news_list) >= 3:
                    break
                    
            except Exception as e:
                self.logger.warning(f"证券时报源失败: {e}")
                continue
        
        return news_list
    
    # ==================== 更多中国国内新闻源 ====================
    def crawl_people_finance(self) -> List[Dict]:
        """爬取人民网财经"""
        news_list = []
        
        try:
            url = 'http://finance.people.com.cn/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找财经新闻链接
                selectors = [
                    '.news_list a',
                    '.list_14 a', 
                    '.w1000_320_left a',
                    '.clearfix a'
                ]
                
                for selector in selectors:
                    links = soup.select(selector)
                    if links:
                        for link in links[:20]:
                            title = link.get_text().strip()
                            href = link.get('href', '')
                            
                            if (len(title) > 10 and self.is_finance_related(title) and
                                not self.is_duplicate_news(title)):
                                
                                if href.startswith('/'):
                                    href = 'http://finance.people.com.cn' + href
                                elif not href.startswith('http'):
                                    continue
                                
                                news_item = {
                                    'title': title,
                                    'url': href,
                                    'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    'source': '人民网财经',
                                    'method': 'web'
                                }
                                news_list.append(news_item)
                                
                                if len(news_list) >= 8:
                                    break
                        
                        if news_list:
                            break
                            
        except Exception as e:
            self.logger.error(f"人民网财经爬取失败: {e}")
        
        return news_list
    
    def crawl_xinhua_finance_enhanced(self) -> List[Dict]:
        """增强版新华网财经"""
        news_list = []
        
        sources = [
            'http://www.xinhuanet.com/fortune/',
            'http://www.xinhuanet.com/money/',
            'http://www.xinhuanet.com/stock/'
        ]
        
        for url in sources:
            try:
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    links = soup.find_all('a', href=True)
                    
                    for link in links[:30]:
                        title = link.get_text().strip()
                        href = link.get('href', '')
                        
                        if (len(title) > 10 and self.is_finance_related(title) and
                            ('xinhuanet.com' in href or href.startswith('/')) and
                            not self.is_duplicate_news(title)):
                            
                            if href.startswith('/'):
                                href = 'http://www.xinhuanet.com' + href
                            elif not href.startswith('http'):
                                continue
                            
                            news_item = {
                                'title': title,
                                'url': href,
                                'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                'source': '新华网财经',
                                'method': 'web'
                            }
                            news_list.append(news_item)
                            
                            if len(news_list) >= 5:
                                break
                
                if len(news_list) >= 3:
                    break
                    
            except Exception as e:
                self.logger.warning(f"新华网财经源失败: {e}")
                continue
        
        return news_list
    
    def crawl_cctv_finance(self) -> List[Dict]:
        """爬取央视财经"""
        news_list = []
        
        try:
            # 央视财经频道
            url = 'https://tv.cctv.com/lm/jjxx/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找新闻链接
                links = soup.find_all('a', href=True)
                
                for link in links[:30]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://tv.cctv.com' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '央视财经',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"央视财经爬取失败: {e}")
        
        return news_list
    
    def crawl_caixin_news(self) -> List[Dict]:
        """爬取财新网"""
        news_list = []
        
        try:
            url = 'https://www.caixin.com/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找新闻链接
                selectors = [
                    '.news-list a',
                    '.article-list a',
                    '.content-list a'
                ]
                
                for selector in selectors:
                    links = soup.select(selector)
                    if links:
                        for link in links[:20]:
                            title = link.get_text().strip()
                            href = link.get('href', '')
                            
                            if (len(title) > 10 and self.is_finance_related(title) and
                                not self.is_duplicate_news(title)):
                                
                                if href.startswith('/'):
                                    href = 'https://www.caixin.com' + href
                                elif not href.startswith('http'):
                                    continue
                                
                                news_item = {
                                    'title': title,
                                    'url': href,
                                    'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    'source': '财新网',
                                    'method': 'web'
                                }
                                news_list.append(news_item)
                                
                                if len(news_list) >= 8:
                                    break
                        
                        if news_list:
                            break
                            
        except Exception as e:
            self.logger.error(f"财新网爬取失败: {e}")
        
        return news_list
    
    def crawl_21jingji_news(self) -> List[Dict]:
        """爬取21世纪经济报道"""
        news_list = []
        
        try:
            url = 'https://www.21jingji.com/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                
                for link in links[:40]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('21jingji.com' in href or href.startswith('/')) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://www.21jingji.com' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '21世纪经济报道',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"21世纪经济报道爬取失败: {e}")
        
        return news_list
    
    def crawl_jiemian_finance(self) -> List[Dict]:
        """爬取界面新闻财经"""
        news_list = []
        
        try:
            url = 'https://www.jiemian.com/lists/2.html'  # 财经频道
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                
                for link in links[:40]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('jiemian.com' in href or href.startswith('/')) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://www.jiemian.com' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '界面新闻',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"界面新闻爬取失败: {e}")
        
        return news_list
    
    def crawl_thepaper_finance(self) -> List[Dict]:
        """爬取澎湃新闻财经"""
        news_list = []
        
        try:
            url = 'https://www.thepaper.cn/channel_25950'  # 财经频道
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                
                for link in links[:40]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('thepaper.cn' in href or href.startswith('/')) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://www.thepaper.cn' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '澎湃新闻',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"澎湃新闻爬取失败: {e}")
        
        return news_list
    
    def crawl_nbd_news(self) -> List[Dict]:
        """爬取每日经济新闻"""
        news_list = []
        
        try:
            url = 'https://www.nbd.com.cn/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                
                for link in links[:40]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('nbd.com.cn' in href or href.startswith('/')) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://www.nbd.com.cn' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '每日经济新闻',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"每日经济新闻爬取失败: {e}")
        
        return news_list
    
    def crawl_cs_com_cn(self) -> List[Dict]:
        """爬取中证网"""
        news_list = []
        
        try:
            url = 'https://www.cs.com.cn/'
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                links = soup.find_all('a', href=True)
                
                for link in links[:40]:
                    title = link.get_text().strip()
                    href = link.get('href', '')
                    
                    if (len(title) > 10 and self.is_finance_related(title) and
                        ('cs.com.cn' in href or href.startswith('/')) and
                        not self.is_duplicate_news(title)):
                        
                        if href.startswith('/'):
                            href = 'https://www.cs.com.cn' + href
                        elif not href.startswith('http'):
                            continue
                        
                        news_item = {
                            'title': title,
                            'url': href,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'source': '中证网',
                            'method': 'web'
                        }
                        news_list.append(news_item)
                        
                        if len(news_list) >= 8:
                            break
                            
        except Exception as e:
            self.logger.error(f"中证网爬取失败: {e}")
        
        return news_list
    
    # ==================== 工具函数 ====================
    def is_finance_related(self, title: str) -> bool:
        """判断是否为财经相关新闻"""
        finance_keywords = [
            '股市', '股票', '基金', '债券', '期货', '外汇', '黄金', '银行', '保险', '证券',
            '投资', '融资', 'IPO', '并购', '央行', '货币政策', '利率', '汇率', '通胀',
            'CPI', 'GDP', '上市', '退市', '停牌', '复牌', '涨停', '跌停', '财报', '业绩',
            '营收', '利润', '亏损', '监管', '证监会', '银保监会', '交易所', '科技股',
            '新能源', '芯片', '医药', '地产', '金融', '消费', '制造业', '服务业',
            '宏观经济', '微观经济', '市场', '行业', '板块', '概念股', '题材股',
            '机构', '基金公司', '券商', '信托', '私募', '公募', '资管', '理财'
        ]
        
        return any(keyword in title for keyword in finance_keywords)
    
    def is_duplicate_news(self, title: str) -> bool:
        """检查新闻是否重复"""
        title_hash = hashlib.md5(title.encode()).hexdigest()
        if title_hash in self.seen_news:
            return True
        self.seen_news.add(title_hash)
        return False
    
    def format_time(self, time_str: str) -> str:
        """格式化时间字符串"""
        if not time_str:
            return datetime.now().strftime('%Y-%m-%d %H:%M')
        
        try:
            if isinstance(time_str, (int, float)):
                return datetime.fromtimestamp(time_str).strftime('%Y-%m-%d %H:%M')
            elif 'T' in time_str:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M')
            else:
                return time_str
        except:
            return datetime.now().strftime('%Y-%m-%d %H:%M')
    
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
    
    # ==================== 主要收集函数 ====================
    def collect_all_news_enhanced(self) -> List[Dict]:
        """收集所有新闻源的新闻 - 增强版"""
        all_news = []
        
        self.logger.info("🚀 开始增强版新闻收集...")
        
        # 所有爬虫函数 - 重点加强中国国内数据源
        crawlers = [
            # 财联社 (多种方法)
            self.crawl_cailianshe_selenium,
            self.crawl_cailianshe_api_enhanced,
            
            # 主流财经网站
            self.crawl_eastmoney_enhanced,
            self.crawl_sina_finance_enhanced,
            
            # 官方权威媒体
            self.crawl_people_finance,        # 人民网财经
            self.crawl_xinhua_finance_enhanced,  # 新华网财经
            self.crawl_cctv_finance,          # 央视财经
            
            # 专业财经媒体
            self.crawl_caixin_news,           # 财新网
            self.crawl_21jingji_news,         # 21世纪经济报道
            self.crawl_jiemian_finance,       # 界面新闻
            self.crawl_thepaper_finance,      # 澎湃新闻
            self.crawl_nbd_news,              # 每日经济新闻
            self.crawl_cs_com_cn,             # 中证网
            
            # 证券专业媒体
            self.crawl_cnstock_news,          # 中国证券网
            self.crawl_stcn_enhanced,         # 证券时报
            
            # 国际财经媒体
            self.crawl_wallstreetcn_news,     # 华尔街见闻
            self.crawl_yicai_news,            # 第一财经
            self.crawl_jrj_news,              # 金融界
        ]
        
        for crawler in crawlers:
            try:
                start_time = time.time()
                news = crawler()
                end_time = time.time()
                
                if news:
                    all_news.extend(news)
                    self.logger.info(f"✅ {crawler.__name__} 获取到 {len(news)} 条新闻 (耗时: {end_time-start_time:.2f}s)")
                else:
                    self.logger.warning(f"❌ {crawler.__name__} 未获取到新闻")
                
                # 随机延迟避免被封
                time.sleep(random.uniform(0.5, 2.0))
                
            except Exception as e:
                self.logger.error(f"❌ {crawler.__name__} 执行失败: {e}")
        
        # 去重和过滤
        unique_news = self.deduplicate_news(all_news)
        
        # 按时间排序
        try:
            unique_news.sort(key=lambda x: x.get('time', ''), reverse=True)
        except Exception as e:
            self.logger.warning(f"新闻排序失败: {e}")
        
        if not unique_news:
            self.logger.error("❌ 所有新闻源都无法获取真实数据")
            return []
        
        self.logger.info(f"🎉 增强版收集完成，获取到 {len(unique_news)} 条真实财经新闻")
        
        # 显示来源统计
        sources = {}
        for news in unique_news:
            source = news['source']
            method = news.get('method', 'unknown')
            key = f"{source}({method})"
            sources[key] = sources.get(key, 0) + 1
        
        self.logger.info("📊 新闻来源分布:")
        for source, count in sources.items():
            self.logger.info(f"   • {source}: {count} 条")
        
        return unique_news[:50]  # 返回最新的50条
    
    def send_markdown(self, content: str) -> bool:
        """发送Markdown消息到企业微信"""
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
    
    def format_news_report(self, news_list: List[Dict], report_type: str) -> str:
        """格式化新闻报告"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if report_type == 'morning':
            title = f"📰 早间财经新闻汇总 ({current_time})"
            intro = "🌅 隔夜重要财经新闻，助您把握市场脉搏"
        else:
            title = f"📰 晚间财经新闻汇总 ({current_time})"
            intro = "🌙 今日重要市场动态，为您梳理投资要点"
        
        report = f"{title}\n\n{intro}\n\n"
        
        if not news_list:
            report += "📭 所有新闻源暂时无法获取真实数据\n"
            report += "🔄 系统将在下次推送时重新尝试\n"
            report += "⚠️ 绝不使用模拟数据，确保信息真实性\n"
            return report
        
        # 按来源分组
        sources = {}
        for news in news_list:
            source = news['source']
            if source not in sources:
                sources[source] = []
            sources[source].append(news)
        
        # 严格限制总数，避免超出企业微信4096字符限制
        max_sources = min(5, len(sources))  # 最多5个来源
        top_sources = list(sources.items())[:max_sources]
        
        # 生成报告
        for source, source_news in top_sources:
            report += f"## 📊 {source}\n"
            for i, news in enumerate(source_news[:3], 1):  # 每个来源最多3条
                title = news['title'][:30] + '...' if len(news['title']) > 30 else news['title']
                url = news.get('url', '')
                method_icon = "🤖" if news.get('method') == 'selenium' else "🌐" if news.get('method') == 'api' else "📄"
                
                # 添加链接 - 使用短URL格式
                if url:
                    # 提取URL的主要部分，缩短显示
                    domain = urlparse(url).netloc
                    report += f"{i}. {method_icon} [{title}]({url}) [{domain}]\n"
                else:
                    report += f"{i}. {method_icon} {title}\n"
            report += "\n"
        
        # 添加统计信息
        total_sources = len(sources)
        total_news = len(news_list)
        report += f"📈 **数据统计**\n"
        report += f"• 新闻源数量: {total_sources} 个\n"
        report += f"• 新闻总数: {total_news} 条\n"
        report += f"• 数据获取: 100% 真实数据"
        
        return report

if __name__ == "__main__":
    # 测试用配置
    test_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
    
    crawler = EnhancedNewsCrawler(test_webhook)
    
    print("🧪 测试增强版新闻爬虫...")
    news = crawler.collect_all_news_enhanced()
    print(f"📊 收集到 {len(news)} 条新闻")
    
    # 生成报告
    report = crawler.format_news_report(news, 'morning')
    print("📋 生成的报告:")
    print(report)

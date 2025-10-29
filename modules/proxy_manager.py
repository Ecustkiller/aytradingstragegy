"""
轻量级代理管理器
支持免费代理池和自定义代理
"""
import requests
import random
from datetime import datetime, timedelta

class ProxyManager:
    """简单的代理管理器"""
    
    def __init__(self):
        self.proxies_list = []
        self.last_update = None
        self.update_interval = timedelta(minutes=30)  # 30分钟更新一次
        
    def get_free_proxies(self):
        """从免费代理源获取代理列表"""
        proxies = []
        
        # 来源1: 免费代理API (示例，需要替换为实际可用的)
        try:
            # 这里可以添加多个免费代理源
            # 例如: http://www.66ip.cn/mo.php?tqsl=100
            #      https://www.kuaidaili.com/free/
            #      https://ip.jiangxianli.com/
            
            # 示例：从GitHub上的免费代理列表获取
            url = "https://raw.githubusercontent.com/fate0/proxylist/master/proxy.list"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                for line in lines[:50]:  # 只取前50个
                    try:
                        import json
                        proxy_data = json.loads(line)
                        if proxy_data.get('type') in ['http', 'https']:
                            proxy = f"{proxy_data['host']}:{proxy_data['port']}"
                            proxies.append(proxy)
                    except:
                        continue
        except Exception as e:
            print(f"获取免费代理失败: {e}")
        
        return proxies
    
    def add_custom_proxy(self, proxy):
        """添加自定义代理
        
        Args:
            proxy: 代理地址，格式如 "127.0.0.1:7890" 或 "http://127.0.0.1:7890"
        """
        if not proxy.startswith('http'):
            proxy = f"http://{proxy}"
        
        if proxy not in self.proxies_list:
            self.proxies_list.append(proxy)
            print(f"✅ 添加代理: {proxy}")
    
    def update_proxies(self, force=False):
        """更新代理列表"""
        now = datetime.now()
        
        # 检查是否需要更新
        if not force and self.last_update:
            if now - self.last_update < self.update_interval:
                return False
        
        # 获取免费代理
        free_proxies = self.get_free_proxies()
        if free_proxies:
            self.proxies_list.extend(free_proxies)
            self.proxies_list = list(set(self.proxies_list))  # 去重
            self.last_update = now
            print(f"✅ 更新代理列表，当前共 {len(self.proxies_list)} 个代理")
            return True
        
        return False
    
    def get_random_proxy(self):
        """随机获取一个代理"""
        if not self.proxies_list:
            self.update_proxies()
        
        if self.proxies_list:
            proxy = random.choice(self.proxies_list)
            return {
                'http': proxy,
                'https': proxy
            }
        return None
    
    def test_proxy(self, proxy, test_url='https://www.baidu.com'):
        """测试代理是否可用
        
        Args:
            proxy: 代理地址
            test_url: 测试URL
            
        Returns:
            bool: 代理是否可用
        """
        try:
            proxies = {
                'http': proxy if proxy.startswith('http') else f'http://{proxy}',
                'https': proxy if proxy.startswith('http') else f'http://{proxy}'
            }
            response = requests.get(test_url, proxies=proxies, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def remove_invalid_proxy(self, proxy):
        """移除无效代理"""
        if proxy in self.proxies_list:
            self.proxies_list.remove(proxy)
            print(f"❌ 移除无效代理: {proxy}")

# 全局代理管理器实例
proxy_manager = ProxyManager()


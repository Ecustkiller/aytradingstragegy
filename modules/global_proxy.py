"""
全局代理设置
通过 Monkey Patch 的方式让所有 requests 请求都走代理
"""
import os
import requests
from .proxy_manager import proxy_manager

# 保存原始的 requests.Session
_original_session_init = requests.Session.__init__
_original_request = requests.Session.request

# 全局代理开关
_global_proxy_enabled = False
_current_proxy = None

def enable_global_proxy(custom_proxy=None):
    """
    启用全局代理
    
    Args:
        custom_proxy: 自定义代理地址（如：http://127.0.0.1:7890）
    """
    global _global_proxy_enabled, _current_proxy
    
    _global_proxy_enabled = True
    
    if custom_proxy:
        _current_proxy = custom_proxy
        print(f"✅ 启用全局代理: {custom_proxy}")
    else:
        # 使用代理池
        proxy_dict = proxy_manager.get_random_proxy()
        if proxy_dict:
            _current_proxy = proxy_dict.get('http')
            print(f"✅ 启用全局代理池: {_current_proxy}")
        else:
            print("⚠️ 无可用代理，将使用直连")
            _current_proxy = None
    
    # 设置环境变量（某些库会读取这些变量）
    if _current_proxy:
        os.environ['HTTP_PROXY'] = _current_proxy
        os.environ['HTTPS_PROXY'] = _current_proxy
        os.environ['http_proxy'] = _current_proxy  # 小写版本
        os.environ['https_proxy'] = _current_proxy

def disable_global_proxy():
    """禁用全局代理"""
    global _global_proxy_enabled, _current_proxy
    
    _global_proxy_enabled = False
    _current_proxy = None
    
    # 清除环境变量
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(key, None)
    
    print("❌ 已禁用全局代理")

def patched_session_init(self, *args, **kwargs):
    """Monkey Patch: 替换 requests.Session.__init__"""
    _original_session_init(self, *args, **kwargs)
    
    # 如果全局代理已启用，自动设置代理
    if _global_proxy_enabled and _current_proxy:
        self.proxies = {
            'http': _current_proxy,
            'https': _current_proxy
        }

def patched_request(self, method, url, *args, **kwargs):
    """Monkey Patch: 替换 requests.Session.request"""
    # 如果全局代理已启用且没有显式设置代理，则使用全局代理
    if _global_proxy_enabled and _current_proxy:
        if 'proxies' not in kwargs or kwargs['proxies'] is None:
            kwargs['proxies'] = {
                'http': _current_proxy,
                'https': _current_proxy
            }
    
    return _original_request(self, method, url, *args, **kwargs)

def apply_monkey_patch():
    """应用 Monkey Patch"""
    requests.Session.__init__ = patched_session_init
    requests.Session.request = patched_request
    print("🔧 已应用全局代理 Monkey Patch")

def is_proxy_enabled():
    """检查全局代理是否已启用"""
    return _global_proxy_enabled

def get_current_proxy():
    """获取当前使用的代理"""
    return _current_proxy

# 自动应用 Monkey Patch
apply_monkey_patch()


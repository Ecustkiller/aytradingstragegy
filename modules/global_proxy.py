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
_available_proxies = []  # 存储所有可用代理列表
_current_proxy_index = 0  # 当前使用的代理索引

def test_proxy_connection(proxy, timeout=10):
    """
    测试代理是否可用
    
    Args:
        proxy: 代理地址
        timeout: 超时时间（秒）
    
    Returns:
        bool: 代理是否可用
    """
    try:
        proxies = {
            'http': proxy,
            'https': proxy
        }
        # 使用 Google 测试（因为需要代理才能访问）
        print(f"🔍 正在测试代理连接到 Google...")
        response = requests.get('https://www.google.com', proxies=proxies, timeout=timeout)
        success = response.status_code == 200
        if success:
            print(f"✅ 代理测试成功！")
        return success
    except Exception as e:
        print(f"⚠️ 代理测试失败: {type(e).__name__}: {str(e)[:100]}")
        return False

def detect_local_proxy(find_all=False):
    """
    自动检测本地常见代理端口
    
    Args:
        find_all: 是否查找所有可用代理（True）还是只找第一个（False）
    
    Returns:
        str 或 list: 如果find_all=False，返回第一个可用代理地址；如果find_all=True，返回所有可用代理列表
    """
    global _available_proxies
    
    # 常见代理工具及其默认端口
    common_ports = [
        12334,  # Hiddify
        12335,  # Hiddify 备用
        7890,   # Clash
        7891,   # Clash 备用
        10808,  # V2Ray
        10809,  # V2Ray 备用
        1080,   # SOCKS5 常用端口（但我们用HTTP）
        8080,   # 通用代理端口
    ]
    
    print("🔍 正在自动检测本地代理...")
    
    found_proxies = []
    
    for port in common_ports:
        proxy = f"http://127.0.0.1:{port}"
        print(f"   尝试端口 {port}...", end=" ")
        
        if test_proxy_connection(proxy):
            print(f"✅")
            found_proxies.append(proxy)
            if not find_all:
                # 只找第一个就返回
                print(f"✅ 找到可用代理: {proxy}")
                _available_proxies = [proxy]  # 保存单个代理
                return proxy
        else:
            print("❌")
    
    if find_all:
        _available_proxies = found_proxies
        if found_proxies:
            print(f"✅ 共找到 {len(found_proxies)} 个可用代理: {found_proxies}")
            return found_proxies
        else:
            print("⚠️ 未检测到任何可用代理")
            return []
    else:
        print("⚠️ 未检测到本地代理")
        return None

def enable_global_proxy(custom_proxy=None, test_connection=True):
    """
    启用全局代理
    
    Args:
        custom_proxy: 自定义代理地址（如：http://127.0.0.1:7890），如果为None则自动检测
        test_connection: 是否测试代理连接
    
    Returns:
        bool: 是否成功启用代理
    """
    global _global_proxy_enabled, _current_proxy
    
    # 优先使用自定义代理，否则自动检测
    if custom_proxy:
        proxy = custom_proxy
        print(f"🔍 使用指定代理: {proxy}")
    else:
        # 自动检测本地代理
        proxy = detect_local_proxy()
        if not proxy:
            print("❌ 未找到可用代理")
            return False
    
    # 最终测试（detect_local_proxy已经测试过了，但如果是custom_proxy则需要测试）
    if custom_proxy and test_connection:
        if not test_proxy_connection(proxy):
            print(f"❌ 代理不可用: {proxy}")
            return False
    
    # 启用代理
    _global_proxy_enabled = True
    _current_proxy = proxy
    
    # 设置环境变量（某些库会读取这些变量）
    os.environ['HTTP_PROXY'] = _current_proxy
    os.environ['HTTPS_PROXY'] = _current_proxy
    os.environ['http_proxy'] = _current_proxy  # 小写版本
    os.environ['https_proxy'] = _current_proxy
    
    print(f"✅ 全局代理已启用: {proxy}")
    return True

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

def switch_to_next_proxy():
    """
    切换到下一个可用代理
    
    Returns:
        bool: 是否成功切换
    """
    global _current_proxy, _current_proxy_index, _available_proxies
    
    if not _available_proxies:
        print("⚠️ 没有可用的备用代理")
        return False
    
    # 如果只有一个代理，重新扫描所有代理
    if len(_available_proxies) == 1:
        print("🔄 只有一个代理，重新扫描所有端口...")
        proxies = detect_local_proxy(find_all=True)
        if not proxies or len(proxies) <= 1:
            print("❌ 没有找到其他可用代理")
            return False
    
    # 切换到下一个代理
    _current_proxy_index = (_current_proxy_index + 1) % len(_available_proxies)
    new_proxy = _available_proxies[_current_proxy_index]
    
    # 测试新代理
    if test_proxy_connection(new_proxy):
        _current_proxy = new_proxy
        
        # 更新环境变量
        os.environ['HTTP_PROXY'] = _current_proxy
        os.environ['HTTPS_PROXY'] = _current_proxy
        os.environ['http_proxy'] = _current_proxy
        os.environ['https_proxy'] = _current_proxy
        
        print(f"✅ 已切换到新代理: {new_proxy}")
        return True
    else:
        print(f"❌ 备用代理不可用: {new_proxy}")
        # 从列表中移除这个代理
        _available_proxies.remove(new_proxy)
        if _available_proxies:
            return switch_to_next_proxy()  # 递归尝试下一个
        else:
            print("❌ 所有代理都不可用")
            return False

def get_available_proxies():
    """获取所有可用代理列表"""
    return _available_proxies.copy()

# 自动应用 Monkey Patch
apply_monkey_patch()


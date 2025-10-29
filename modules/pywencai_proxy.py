"""
支持代理的 pywencai 包装器
"""
import pywencai
from .proxy_manager import proxy_manager

# 保存原始的 get 方法
_original_get = pywencai.get

def get_with_proxy(query, use_proxy=False, custom_proxy=None, **kwargs):
    """
    支持代理的 pywencai.get 包装函数
    
    Args:
        query: 查询条件
        use_proxy: 是否使用代理
        custom_proxy: 自定义代理地址（格式：http://127.0.0.1:7890）
        **kwargs: 其他参数传递给 pywencai.get
    
    Returns:
        DataFrame 或 None
    """
    # 如果不使用代理，直接调用原始方法
    if not use_proxy:
        return _original_get(query=query, **kwargs)
    
    # 获取代理
    if custom_proxy:
        proxies = {
            'http': custom_proxy,
            'https': custom_proxy
        }
    else:
        proxies = proxy_manager.get_random_proxy()
    
    if not proxies:
        print("⚠️ 无可用代理，使用直连")
        return _original_get(query=query, **kwargs)
    
    # 尝试使用代理
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 注意：pywencai 内部使用 requests
            # 我们需要通过环境变量或者 monkeypatch 来设置代理
            import os
            
            # 保存原始代理设置
            original_http_proxy = os.environ.get('HTTP_PROXY')
            original_https_proxy = os.environ.get('HTTPS_PROXY')
            
            # 设置代理环境变量
            os.environ['HTTP_PROXY'] = proxies['http']
            os.environ['HTTPS_PROXY'] = proxies['https']
            
            try:
                result = _original_get(query=query, **kwargs)
                return result
            finally:
                # 恢复原始代理设置
                if original_http_proxy:
                    os.environ['HTTP_PROXY'] = original_http_proxy
                else:
                    os.environ.pop('HTTP_PROXY', None)
                
                if original_https_proxy:
                    os.environ['HTTPS_PROXY'] = original_https_proxy
                else:
                    os.environ.pop('HTTPS_PROXY', None)
        
        except Exception as e:
            print(f"代理尝试 {attempt + 1}/{max_retries} 失败: {e}")
            if attempt < max_retries - 1:
                # 尝试下一个代理
                proxies = proxy_manager.get_random_proxy()
                if not proxies:
                    break
            else:
                # 所有代理都失败，尝试直连
                print("⚠️ 所有代理都失败，尝试直连")
                return _original_get(query=query, **kwargs)
    
    return None


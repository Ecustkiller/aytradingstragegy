"""
异步操作集成测试
测试异步数据获取和更新的完整流程
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.asyncio
class TestAsyncOperations:
    """异步操作集成测试"""
    
    async def test_get_multiple_stocks_data_async_import(self):
        """测试异步批量获取函数导入"""
        from modules.data_loader import get_multiple_stocks_data_async
        
        assert callable(get_multiple_stocks_data_async)
        
        # 检查是否为异步函数
        import inspect
        assert inspect.iscoroutinefunction(get_multiple_stocks_data_async)
    
    def test_async_function_signature(self):
        """测试异步函数签名"""
        from modules.data_loader import get_multiple_stocks_data_async
        import inspect
        
        sig = inspect.signature(get_multiple_stocks_data_async)
        
        assert 'symbols' in sig.parameters
        assert 'max_workers' in sig.parameters
        assert 'progress_callback' in sig.parameters
    
    def test_sync_wrapper_exists(self):
        """测试同步包装函数存在"""
        from modules.data_loader import get_multiple_stocks_data
        
        assert callable(get_multiple_stocks_data)
        
        import inspect
        sig = inspect.signature(get_multiple_stocks_data)
        assert 'use_async' in sig.parameters


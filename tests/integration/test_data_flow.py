"""
数据流集成测试
测试从数据获取到处理的完整流程
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDataFlow:
    """测试数据流集成"""
    
    def test_data_loader_import(self):
        """测试数据加载器模块导入"""
        from modules.data_loader import (
            get_stock_data,
            get_multiple_stocks_data,
            get_realtime_price,
            get_stock_info
        )
        
        assert callable(get_stock_data)
        assert callable(get_multiple_stocks_data)
        assert callable(get_realtime_price)
        assert callable(get_stock_info)
    
    def test_error_handler_import(self):
        """测试错误处理模块导入"""
        from modules.error_handler import (
            safe_execute,
            handle_errors,
            validate_required,
            ErrorContext
        )
        
        assert callable(safe_execute)
        assert callable(handle_errors)
        assert callable(validate_required)
    
    def test_config_manager_import(self):
        """测试配置管理模块导入"""
        from modules.config_manager import Config
        
        assert Config is not None
        assert hasattr(Config, 'PROJECT_ROOT')
        assert hasattr(Config, 'ensure_dirs')
    
    def test_constants_import(self):
        """测试常量模块导入"""
        from modules.constants import (
            CACHE_TTL_ONLINE_DATA,
            CACHE_TTL_LOCAL_DATA,
            ASYNC_MAX_WORKERS_DEFAULT
        )
        
        assert isinstance(CACHE_TTL_ONLINE_DATA, int)
        assert isinstance(CACHE_TTL_LOCAL_DATA, int)
        assert isinstance(ASYNC_MAX_WORKERS_DEFAULT, int)
        assert CACHE_TTL_ONLINE_DATA > 0
        assert CACHE_TTL_LOCAL_DATA > CACHE_TTL_ONLINE_DATA
    
    def test_performance_monitor_import(self):
        """测试性能监控模块导入"""
        from modules.performance_monitor import (
            monitor_performance,
            get_performance_stats,
            PerformanceMonitor
        )
        
        assert callable(monitor_performance)
        assert callable(get_performance_stats)
        assert PerformanceMonitor is not None


class TestDataLoaderIntegration:
    """数据加载器集成测试"""
    
    @pytest.mark.slow
    def test_get_stock_data_with_fallback(self):
        """测试数据获取的回退机制"""
        from modules.data_loader import get_stock_data
        
        # 测试无效数据源时的回退
        end = datetime.now()
        start = end - timedelta(days=30)
        
        # 应该能正常处理，即使数据源不可用也会回退
        result = get_stock_data(
            '600519',
            start.strftime('%Y-%m-%d'),
            end.strftime('%Y-%m-%d'),
            'daily',
            'InvalidSource'  # 无效数据源，应该回退到AKShare
        )
        
        # 结果应该是DataFrame（可能为空，但不应该报错）
        import pandas as pd
        assert isinstance(result, pd.DataFrame)
    
    def test_get_multiple_stocks_data_signature(self):
        """测试批量获取函数签名"""
        from modules.data_loader import get_multiple_stocks_data
        
        # 检查函数签名
        import inspect
        sig = inspect.signature(get_multiple_stocks_data)
        
        assert 'symbols' in sig.parameters
        assert 'use_async' in sig.parameters
        assert 'max_workers' in sig.parameters


class TestErrorHandlingIntegration:
    """错误处理集成测试"""
    
    def test_safe_execute_with_error(self):
        """测试safe_execute的错误处理"""
        from modules.error_handler import safe_execute
        
        def failing_func():
            raise ValueError("测试错误")
        
        result = safe_execute(failing_func, default_value="默认值")
        assert result == "默认值"
    
    def test_error_context_usage(self):
        """测试ErrorContext的使用"""
        from modules.error_handler import ErrorContext
        
        with ErrorContext("测试操作") as ctx:
            ctx.execute(lambda: None, "操作1")
            ctx.execute(lambda: 1 / 0, "操作2")
            ctx.execute(lambda: None, "操作3")
        
        assert ctx.success_count == 2
        assert ctx.error_count == 1
        assert len(ctx.errors) == 1


class TestConstantsIntegration:
    """常量模块集成测试"""
    
    def test_constants_consistency(self):
        """测试常量的一致性"""
        from modules.constants import (
            ASYNC_MAX_WORKERS_MIN,
            ASYNC_MAX_WORKERS_MAX,
            ASYNC_MAX_WORKERS_DEFAULT
        )
        
        assert ASYNC_MAX_WORKERS_MIN <= ASYNC_MAX_WORKERS_DEFAULT <= ASYNC_MAX_WORKERS_MAX
    
    def test_cache_ttl_consistency(self):
        """测试缓存TTL的一致性"""
        from modules.constants import (
            CACHE_TTL_ONLINE_DATA,
            CACHE_TTL_LOCAL_DATA
        )
        
        # 本地数据应该缓存更久
        assert CACHE_TTL_LOCAL_DATA >= CACHE_TTL_ONLINE_DATA


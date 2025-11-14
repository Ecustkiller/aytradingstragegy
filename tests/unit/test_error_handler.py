"""
错误处理模块单元测试
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.error_handler import (
    handle_errors,
    safe_execute,
    validate_required,
    validate_type,
    ErrorContext
)


class TestSafeExecute:
    """测试 safe_execute 函数"""
    
    def test_success(self):
        """测试成功执行"""
        result = safe_execute(lambda: 1 + 1, default_value=0)
        assert result == 2
    
    def test_error_with_default(self):
        """测试错误时返回默认值"""
        result = safe_execute(lambda: 1 / 0, default_value=-1)
        assert result == -1
    
    def test_error_without_logging(self):
        """测试不记录日志的错误处理"""
        result = safe_execute(
            lambda: 1 / 0,
            default_value=None,
            log_error=False
        )
        assert result is None


class TestHandleErrors:
    """测试 handle_errors 装饰器"""
    
    def test_success(self):
        """测试成功执行"""
        @handle_errors("测试错误", return_value=None)
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
    
    def test_error_with_return_value(self):
        """测试错误时返回指定值"""
        @handle_errors("测试错误", return_value="default")
        def test_func():
            raise ValueError("测试异常")
        
        result = test_func()
        assert result == "default"
    
    def test_error_with_raise(self):
        """测试错误时重新抛出异常"""
        @handle_errors("测试错误", raise_exception=True)
        def test_func():
            raise ValueError("测试异常")
        
        with pytest.raises(ValueError):
            test_func()


class TestValidateRequired:
    """测试 validate_required 函数"""
    
    def test_valid_value(self):
        """测试有效值"""
        validate_required("test", "参数名")
        # 不应该抛出异常
    
    def test_none_value(self):
        """测试None值"""
        with pytest.raises(ValueError):
            validate_required(None, "参数名")
    
    def test_empty_string(self):
        """测试空字符串"""
        with pytest.raises(ValueError):
            validate_required("", "参数名")
    
    def test_custom_error_message(self):
        """测试自定义错误信息"""
        with pytest.raises(ValueError, match="自定义错误"):
            validate_required(None, "参数名", "自定义错误")


class TestValidateType:
    """测试 validate_type 函数"""
    
    def test_valid_type(self):
        """测试有效类型"""
        validate_type(123, int, "参数名")
        # 不应该抛出异常
    
    def test_invalid_type(self):
        """测试无效类型"""
        with pytest.raises(TypeError):
            validate_type("123", int, "参数名")


class TestErrorContext:
    """测试 ErrorContext 上下文管理器"""
    
    def test_success_operations(self):
        """测试成功操作"""
        with ErrorContext("测试操作") as ctx:
            ctx.execute(lambda: None, "操作1")
            ctx.execute(lambda: None, "操作2")
        
        assert ctx.success_count == 2
        assert ctx.error_count == 0
        assert not ctx.has_errors()
    
    def test_mixed_operations(self):
        """测试混合操作（成功+失败）"""
        with ErrorContext("测试操作") as ctx:
            ctx.execute(lambda: None, "操作1")
            ctx.execute(lambda: 1 / 0, "操作2")
            ctx.execute(lambda: None, "操作3")
        
        assert ctx.success_count == 2
        assert ctx.error_count == 1
        assert ctx.has_errors()
        assert len(ctx.errors) == 1


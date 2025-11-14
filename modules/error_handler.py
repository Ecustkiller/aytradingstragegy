"""
统一错误处理模块
提供装饰器和工具函数用于统一的错误处理
"""
import functools
import traceback
from typing import Callable, Optional, Any
import streamlit as st
from loguru import logger


def handle_errors(
    error_message: str = "操作失败",
    show_user_message: bool = True,
    show_traceback: bool = False,
    return_value: Any = None,
    raise_exception: bool = False
):
    """
    统一错误处理装饰器
    
    Args:
        error_message: 错误提示信息
        show_user_message: 是否在UI显示错误信息
        show_traceback: 是否显示详细堆栈信息
        return_value: 发生错误时的返回值
        raise_exception: 是否重新抛出异常
    
    Example:
        @handle_errors("数据加载失败", return_value=pd.DataFrame())
        def load_data():
            # your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录日志
                logger.error(f"{error_message}: {str(e)}")
                if show_traceback:
                    logger.exception(e)
                
                # 显示用户提示
                if show_user_message:
                    error_text = f"❌ {error_message}: {str(e)}"
                    st.error(error_text)
                    
                    if show_traceback:
                        with st.expander("查看详细错误信息"):
                            st.code(traceback.format_exc())
                
                # 是否重新抛出异常
                if raise_exception:
                    raise
                
                return return_value
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    error_message: str = "执行失败",
    default_value: Any = None,
    log_error: bool = True
) -> Any:
    """
    安全执行函数，捕获异常并返回默认值
    
    Args:
        func: 要执行的函数
        error_message: 错误提示信息
        default_value: 发生错误时的返回值
        log_error: 是否记录错误日志
    
    Returns:
        函数执行结果或默认值
    
    Example:
        result = safe_execute(
            lambda: risky_operation(),
            error_message="操作失败",
            default_value=[]
        )
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"{error_message}: {str(e)}")
        return default_value


def validate_required(value: Any, name: str, error_message: Optional[str] = None):
    """
    验证必填参数
    
    Args:
        value: 要验证的值
        name: 参数名称
        error_message: 自定义错误信息
    
    Raises:
        ValueError: 如果值为空
    
    Example:
        validate_required(symbol, "股票代码")
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        msg = error_message or f"参数 {name} 不能为空"
        logger.error(msg)
        raise ValueError(msg)


def validate_type(value: Any, expected_type: type, name: str):
    """
    验证参数类型
    
    Args:
        value: 要验证的值
        expected_type: 期望的类型
        name: 参数名称
    
    Raises:
        TypeError: 如果类型不匹配
    
    Example:
        validate_type(count, int, "数量")
    """
    if not isinstance(value, expected_type):
        msg = f"参数 {name} 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
        logger.error(msg)
        raise TypeError(msg)


class ErrorContext:
    """
    错误上下文管理器，用于批量操作的错误收集
    
    Example:
        with ErrorContext("批量处理股票") as ctx:
            for symbol in symbols:
                ctx.execute(lambda: process_stock(symbol), f"处理{symbol}")
        
        if ctx.has_errors():
            print(f"失败: {ctx.error_count}, 成功: {ctx.success_count}")
    """
    
    def __init__(self, operation_name: str = "操作"):
        self.operation_name = operation_name
        self.errors = []
        self.success_count = 0
        self.error_count = 0
    
    def __enter__(self):
        logger.info(f"开始{self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            logger.info(
                f"{self.operation_name}完成: "
                f"成功 {self.success_count}, 失败 {self.error_count}"
            )
        else:
            logger.error(f"{self.operation_name}异常终止: {exc_val}")
        return False
    
    def execute(self, func: Callable, item_name: str = "项目") -> bool:
        """
        执行单个操作并记录结果
        
        Args:
            func: 要执行的函数
            item_name: 项目名称（用于日志）
        
        Returns:
            是否执行成功
        """
        try:
            func()
            self.success_count += 1
            return True
        except Exception as e:
            self.error_count += 1
            error_info = {
                'item': item_name,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            self.errors.append(error_info)
            logger.error(f"{item_name}失败: {str(e)}")
            return False
    
    def has_errors(self) -> bool:
        """是否有错误发生"""
        return self.error_count > 0
    
    def get_summary(self) -> str:
        """获取执行摘要"""
        return (
            f"{self.operation_name}完成\n"
            f"成功: {self.success_count}\n"
            f"失败: {self.error_count}"
        )
    
    def show_errors(self, max_display: int = 5):
        """在UI显示错误信息"""
        if not self.has_errors():
            st.success(f"✅ {self.get_summary()}")
            return
        
        st.warning(f"⚠️ {self.get_summary()}")
        
        with st.expander(f"查看错误详情 ({len(self.errors)}个错误)"):
            for i, error in enumerate(self.errors[:max_display], 1):
                st.error(f"{i}. {error['item']}: {error['error']}")
            
            if len(self.errors) > max_display:
                st.info(f"还有 {len(self.errors) - max_display} 个错误未显示")


# 预定义的常用错误处理装饰器
handle_data_error = functools.partial(
    handle_errors,
    error_message="数据处理失败",
    show_traceback=False,
    return_value=None
)

handle_api_error = functools.partial(
    handle_errors,
    error_message="API调用失败",
    show_traceback=False,
    return_value=None
)

handle_file_error = functools.partial(
    handle_errors,
    error_message="文件操作失败",
    show_traceback=True,
    return_value=None
)

"""
增强错误恢复模块
提供更完善的错误恢复和重试机制
"""
import time
from typing import Callable, Optional, Any, Dict, List
from functools import wraps
from enum import Enum
from .logger_config import get_logger
from .error_handler import safe_execute

logger = get_logger(__name__)


class RecoveryStrategy(Enum):
    """错误恢复策略"""
    RETRY = "retry"  # 重试
    FALLBACK = "fallback"  # 回退到备用方案
    SKIP = "skip"  # 跳过
    ABORT = "abort"  # 中止


class ErrorRecovery:
    """错误恢复管理器"""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    ):
        """
        初始化错误恢复管理器
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            exponential_backoff: 是否使用指数退避
            recovery_strategy: 恢复策略
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.recovery_strategy = recovery_strategy
    
    def execute_with_recovery(
        self,
        func: Callable,
        fallback_func: Optional[Callable] = None,
        error_handler: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        执行函数并自动恢复错误
        
        Args:
            func: 要执行的函数
            fallback_func: 备用函数（当主函数失败时调用）
            error_handler: 错误处理函数
            *args, **kwargs: 函数参数
        
        Returns:
            函数返回值或None
        """
        last_error = None
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"✅ 重试成功（第{attempt+1}次尝试）")
                return result
            except Exception as e:
                last_error = e
                if error_handler:
                    error_handler(e, attempt)
                
                if attempt < self.max_retries - 1:
                    # 计算延迟时间
                    delay = self.retry_delay
                    if self.exponential_backoff:
                        delay = self.retry_delay * (2 ** attempt)
                    
                    logger.warning(
                        f"⚠️ 执行失败（第{attempt+1}次），{delay:.1f}秒后重试: {str(e)[:50]}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"❌ 执行失败（已重试{self.max_retries}次）: {str(e)}", exc_info=True)
        
        # 所有重试都失败，尝试备用方案
        if self.recovery_strategy == RecoveryStrategy.FALLBACK and fallback_func:
            logger.info("🔄 尝试备用方案...")
            try:
                return fallback_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ 备用方案也失败: {str(e)}", exc_info=True)
        
        # 返回默认值或None
        if self.recovery_strategy == RecoveryStrategy.SKIP:
            logger.warning("⏩ 跳过当前操作")
            return None
        
        raise last_error


def with_recovery(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    exponential_backoff: bool = True,
    fallback_func: Optional[Callable] = None,
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
):
    """
    错误恢复装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        exponential_backoff: 是否使用指数退避
        fallback_func: 备用函数
        recovery_strategy: 恢复策略
    
    Example:
        @with_recovery(max_retries=3, retry_delay=1.0)
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            recovery = ErrorRecovery(
                max_retries=max_retries,
                retry_delay=retry_delay,
                exponential_backoff=exponential_backoff,
                recovery_strategy=recovery_strategy
            )
            return recovery.execute_with_recovery(func, fallback_func, None, *args, **kwargs)
        return wrapper
    return decorator


class CircuitBreaker:
    """熔断器模式 - 防止连续失败导致系统崩溃"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值（超过后打开熔断器）
            recovery_timeout: 恢复超时（秒）
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args, **kwargs: 函数参数
        
        Returns:
            函数返回值
        """
        # 检查熔断器状态
        if self.state == "open":
            # 检查是否可以尝试恢复
            if self.last_failure_time and \
               time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                logger.info("🔄 熔断器进入半开状态，尝试恢复...")
            else:
                raise Exception("熔断器已打开，拒绝请求")
        
        try:
            result = func(*args, **kwargs)
            
            # 成功：重置失败计数
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("✅ 熔断器已关闭，服务恢复正常")
            elif self.failure_count > 0:
                self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(
                    f"🔴 熔断器已打开（失败{self.failure_count}次）: {str(e)[:50]}"
                )
            
            raise


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type = Exception
):
    """
    熔断器装饰器
    
    Args:
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时（秒）
        expected_exception: 预期的异常类型
    
    Example:
        @circuit_breaker(failure_threshold=5, recovery_timeout=60)
        def my_function():
            pass
    """
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


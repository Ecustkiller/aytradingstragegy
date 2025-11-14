"""
性能监控模块
提供性能指标收集和分析功能
"""
import time
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from .logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标数据类"""

    function_name: str
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, max_records: int = 1000):
        """
        初始化性能监控器

        Args:
            max_records: 最大记录数（超过后自动清理旧记录）
        """
        self.metrics: List[PerformanceMetric] = []
        self.max_records = max_records

    def record(
        self,
        function_name: str,
        execution_time: float,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """记录性能指标"""
        metric = PerformanceMetric(
            function_name=function_name,
            execution_time=execution_time,
            success=success,
            error=error,
            metadata=metadata or {},
        )
        self.metrics.append(metric)

        # 自动清理旧记录
        if len(self.metrics) > self.max_records:
            self.metrics = self.metrics[-self.max_records :]

    def get_stats(self, function_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取性能统计

        Args:
            function_name: 函数名（None表示所有函数）

        Returns:
            dict: 统计信息
        """
        if function_name:
            filtered = [m for m in self.metrics if m.function_name == function_name]
        else:
            filtered = self.metrics

        if not filtered:
            return {"count": 0, "avg_time": 0, "min_time": 0, "max_time": 0, "success_rate": 0}

        times = [m.execution_time for m in filtered]
        success_count = sum(1 for m in filtered if m.success)

        return {
            "count": len(filtered),
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "success_rate": success_count / len(filtered) * 100,
        }

    def get_slow_functions(self, threshold: float = 1.0, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取慢函数列表

        Args:
            threshold: 时间阈值（秒）
            limit: 返回数量限制

        Returns:
            list: 慢函数列表
        """
        slow = [
            {"function": m.function_name, "time": m.execution_time, "timestamp": m.timestamp}
            for m in self.metrics
            if m.execution_time > threshold
        ]
        slow.sort(key=lambda x: x["time"], reverse=True)
        return slow[:limit]

    def clear(self):
        """清空所有记录"""
        self.metrics.clear()


# 全局性能监控器实例
_global_monitor = PerformanceMonitor()


def monitor_performance(
    function_name: Optional[str] = None, log_slow: bool = True, slow_threshold: float = 1.0
):
    """
    性能监控装饰器

    Args:
        function_name: 自定义函数名（默认使用函数本身名称）
        log_slow: 是否记录慢函数
        slow_threshold: 慢函数阈值（秒）

    Example:
        @monitor_performance()
        def my_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = function_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            success = True
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                _global_monitor.record(
                    function_name=name, execution_time=execution_time, success=success, error=error
                )

                if log_slow and execution_time > slow_threshold:
                    logger.warning(
                        f"🐌 慢函数检测: {name} 执行时间 {execution_time:.2f}秒 " f"(阈值: {slow_threshold}秒)"
                    )

        return wrapper

    return decorator


def get_performance_stats(function_name: Optional[str] = None) -> Dict[str, Any]:
    """获取性能统计（便捷函数）"""
    return _global_monitor.get_stats(function_name)


def get_slow_functions(threshold: float = 1.0, limit: int = 10) -> List[Dict[str, Any]]:
    """获取慢函数列表（便捷函数）"""
    return _global_monitor.get_slow_functions(threshold, limit)

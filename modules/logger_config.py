"""
统一日志配置模块
使用 loguru 提供统一的日志记录
"""
import sys
from pathlib import Path
from loguru import logger
from .config_manager import Config


def setup_logger():
    """配置日志系统"""
    
    # 移除默认的 handler
    logger.remove()
    
    # 控制台输出（彩色）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=Config.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 文件输出 - 所有日志
    logger.add(
        Config.LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # 每天午夜轮转
        retention=f"{Config.LOG_RETENTION_DAYS} days",  # 保留天数
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    # 文件输出 - 错误日志
    logger.add(
        Config.LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention=f"{Config.LOG_RETENTION_DAYS} days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    # 文件输出 - JSON格式（用于日志分析）
    logger.add(
        Config.LOG_DIR / "app_{time:YYYY-MM-DD}.json",
        format="{message}",
        level="INFO",
        rotation="00:00",
        retention=f"{Config.LOG_RETENTION_DAYS} days",
        compression="zip",
        encoding="utf-8",
        serialize=True  # JSON格式
    )
    
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {Config.LOG_LEVEL}")
    logger.info(f"日志目录: {Config.LOG_DIR}")
    logger.info(f"日志保留: {Config.LOG_RETENTION_DAYS}天")


def get_logger(name: str = None):
    """
    获取logger实例
    
    Args:
        name: logger名称，通常使用 __name__
    
    Returns:
        logger实例
    
    Example:
        from modules.logger_config import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条日志")
    """
    if name:
        return logger.bind(name=name)
    return logger


# 初始化日志系统
setup_logger()

# 导出logger
__all__ = ['logger', 'get_logger', 'setup_logger']

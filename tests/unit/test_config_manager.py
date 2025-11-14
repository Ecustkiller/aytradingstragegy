"""
配置管理模块单元测试
"""
import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.config_manager import Config


class TestConfig:
    """测试 Config 类"""
    
    def test_project_root(self):
        """测试项目根目录"""
        assert Config.PROJECT_ROOT.exists()
        assert Config.PROJECT_ROOT.is_dir()
    
    def test_data_dirs(self):
        """测试数据目录"""
        assert Config.DATA_DIR.exists() or Config.DATA_DIR.parent.exists()
        assert Config.CACHE_DIR is not None
        assert Config.LOG_DIR is not None
    
    def test_ensure_dirs(self):
        """测试目录创建"""
        Config.ensure_dirs()
        # 不应该抛出异常
    
    def test_validate(self):
        """测试配置验证"""
        Config.validate()
        # 不应该抛出异常（只是警告）
    
    def test_get_webhook_url(self):
        """测试获取Webhook URL"""
        url = Config.get_webhook_url()
        # 可能为None，但不应该抛出异常
        assert url is None or isinstance(url, str)
    
    def test_print_config(self):
        """测试打印配置"""
        Config.print_config()
        # 不应该抛出异常


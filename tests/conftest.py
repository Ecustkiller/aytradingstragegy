"""
Pytest 配置文件
提供测试用的 fixtures 和配置
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def sample_stock_symbols():
    """示例股票代码列表"""
    return ['600519', '000001', '000002']

@pytest.fixture
def sample_date_range():
    """示例日期范围"""
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=365)
    return start, end

@pytest.fixture
def mock_dataframe():
    """模拟的DataFrame"""
    import pandas as pd
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'Open': [100 + i * 0.1 for i in range(100)],
        'High': [101 + i * 0.1 for i in range(100)],
        'Low': [99 + i * 0.1 for i in range(100)],
        'Close': [100.5 + i * 0.1 for i in range(100)],
        'Volume': [1000000] * 100
    }, index=dates)


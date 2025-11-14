"""
数据加载器模块单元测试
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Optional, Union
import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDataLoader:
    """测试数据加载器"""
    
    def test_get_stock_data_signature(self):
        """测试函数签名和类型"""
        from modules.data_loader import get_stock_data
        
        # 检查函数存在
        assert callable(get_stock_data)
        
        # 检查参数
        import inspect
        sig = inspect.signature(get_stock_data)
        assert 'symbol' in sig.parameters
        assert 'start' in sig.parameters
        assert 'end' in sig.parameters
        assert 'period_type' in sig.parameters
        assert 'data_source' in sig.parameters
    
    def test_get_multiple_stocks_data_signature(self):
        """测试批量获取函数签名"""
        from modules.data_loader import get_multiple_stocks_data
        
        assert callable(get_multiple_stocks_data)
        
        import inspect
        sig = inspect.signature(get_multiple_stocks_data)
        assert 'symbols' in sig.parameters
        assert 'use_async' in sig.parameters
    
    @patch('modules.data_loader.get_stock_data')
    def test_get_multiple_stocks_data_sync(self, mock_get_stock_data):
        """测试同步批量获取"""
        from modules.data_loader import get_multiple_stocks_data
        
        # Mock返回值
        mock_df = pd.DataFrame({'Close': [100, 101, 102]})
        mock_get_stock_data.return_value = mock_df
        
        symbols = ['600519', '000001']
        result = get_multiple_stocks_data(
            symbols,
            '2023-01-01',
            '2023-12-31',
            use_async=False
        )
        
        assert isinstance(result, dict)
        assert len(result) == 2
        assert '600519' in result
        assert '000001' in result
        assert mock_get_stock_data.call_count == 2
    
    def test_get_realtime_price_signature(self):
        """测试实时价格函数"""
        from modules.data_loader import get_realtime_price
        from typing import Union
        
        assert callable(get_realtime_price)
        
        import inspect
        sig = inspect.signature(get_realtime_price)
        # Python 3.9兼容：使用Union而不是|
        assert sig.return_annotation in (float, type(None), Union[float, None], Optional[float])
    
    def test_get_stock_info_signature(self):
        """测试股票信息函数"""
        from modules.data_loader import get_stock_info
        
        assert callable(get_stock_info)
        
        import inspect
        sig = inspect.signature(get_stock_info)
        assert 'symbol' in sig.parameters


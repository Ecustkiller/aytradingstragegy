"""
股票搜索模块 - 支持通过名称、简称、拼音等方式搜索股票
"""
import akshare as ak
import pandas as pd
import re
from typing import List, Dict, Optional, Any
import streamlit as st

# 尝试导入pypinyin库进行拼音转换
try:
    from pypinyin import lazy_pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False
    print("未安装pypinyin库，将使用简化的拼音匹配功能")

class StockSearcher:
    """股票搜索器"""
    
    def __init__(self):
        self._stock_info_cache: Optional[pd.DataFrame] = None
        self._etf_info_cache: Optional[pd.DataFrame] = None
        self._all_info_cache: Optional[pd.DataFrame] = None
        self._pinyin_cache: Dict[str, str] = {}  # 缓存拼音转换结果
        self._last_update = None
        
    def _get_stock_info(self) -> pd.DataFrame:
        """获取所有A股股票信息"""
        try:
            # 获取A股股票基本信息
            stock_info = ak.stock_zh_a_spot_em()
            if stock_info is not None and not stock_info.empty:
                # 标准化列名
                stock_info = stock_info.rename(columns={
                    '代码': 'code',
                    '名称': 'name', 
                    '最新价': 'price',
                    '涨跌幅': 'change_pct'
                })
                return stock_info
        except Exception as e:
            print(f"获取股票信息失败: {e}")
        
        return pd.DataFrame()
    
    def _get_etf_info(self) -> pd.DataFrame:
        """获取所有ETF基金信息"""
        try:
            # 获取ETF基金信息
            etf_info = ak.fund_etf_spot_em()
            if etf_info is not None and not etf_info.empty:
                # 标准化列名
                etf_info = etf_info.rename(columns={
                    '代码': 'code',
                    '名称': 'name',
                    '最新价': 'price', 
                    '涨跌幅': 'change_pct'
                })
                return etf_info
        except Exception as e:
            print(f"获取ETF信息失败: {e}")
            
        return pd.DataFrame()
    
    def _get_pinyin_initials(self, text: str) -> str:
        """
        获取中文文本的拼音首字母
        
        参数:
            text: 中文文本
            
        返回:
            拼音首字母字符串
        """
        if not text:
            return ""
            
        # 先检查缓存
        if text in self._pinyin_cache:
            return self._pinyin_cache[text]
        
        if HAS_PYPINYIN:
            # 使用pypinyin库获取拼音首字母
            try:
                pinyin_list = lazy_pinyin(text, style=Style.FIRST_LETTER)
                initials = ''.join(pinyin_list).upper()
                self._pinyin_cache[text] = initials
                return initials
            except Exception as e:
                print(f"拼音转换失败: {e}")
        
        # 如果没有pypinyin库，返回空字符串，不进行拼音匹配
        return ""
    
    def _update_cache(self):
        """更新缓存数据"""
        print("正在更新股票信息缓存...")
        self._stock_info_cache = self._get_stock_info()
        self._etf_info_cache = self._get_etf_info()
        
        # 合并股票和ETF信息
        all_info = []
        
        if self._stock_info_cache is not None and not self._stock_info_cache.empty:
            stock_data = self._stock_info_cache[['code', 'name', 'price', 'change_pct']].copy()
            stock_data['type'] = 'A股'
            all_info.append(stock_data)
            
        if self._etf_info_cache is not None and not self._etf_info_cache.empty:
            etf_data = self._etf_info_cache[['code', 'name', 'price', 'change_pct']].copy()
            etf_data['type'] = 'ETF'
            all_info.append(etf_data)
        
        if all_info:
            self._all_info_cache = pd.concat(all_info, ignore_index=True)
            
            # 如果有pypinyin库，为所有股票名称生成拼音首字母
            if HAS_PYPINYIN:
                print("正在生成拼音索引...")
                self._all_info_cache['pinyin'] = self._all_info_cache['name'].apply(self._get_pinyin_initials)
            
            print(f"缓存更新完成: 共{len(self._all_info_cache)}只股票/ETF")
        else:
            self._all_info_cache = pd.DataFrame()
            print("缓存更新失败: 未获取到数据")
    
    def search_stock(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索股票
        
        参数:
            query: 搜索关键词 (股票代码、名称、简称等)
            limit: 返回结果数量限制
            
        返回:
            匹配的股票信息列表
        """
        if not query or len(query.strip()) == 0:
            return []
            
        query = query.strip()
        
        # 如果缓存为空或过期，更新缓存
        if (self._all_info_cache is None or 
            self._all_info_cache.empty):
            self._update_cache()
            
        if self._all_info_cache is None or self._all_info_cache.empty:
            return []
        
        results = []
        
        # 1. 精确匹配股票代码（优先级最高）
        exact_code_match = self._all_info_cache[
            self._all_info_cache['code'] == query
        ]
        if not exact_code_match.empty:
            for _, row in exact_code_match.iterrows():
                results.append({
                    'code': row['code'],
                    'name': row['name'],
                    'type': row['type'],
                    'price': row.get('price', 0),
                    'change_pct': row.get('change_pct', 0),
                    'match_type': '代码精确匹配'
                })
        
        # 2. 精确匹配股票名称
        if len(results) < limit:
            exact_name_match = self._all_info_cache[
                self._all_info_cache['name'] == query
            ]
            if not exact_name_match.empty:
                for _, row in exact_name_match.iterrows():
                    # 避免重复
                    if not any(r['code'] == row['code'] for r in results):
                        results.append({
                            'code': row['code'],
                            'name': row['name'],
                            'type': row['type'],
                            'price': row.get('price', 0),
                            'change_pct': row.get('change_pct', 0),
                            'match_type': '名称精确匹配'
                        })
        
        # 3. 股票代码前缀匹配（如输入"600"匹配所有600开头的股票）
        if len(results) < limit and query.isdigit() and len(query) >= 2:
            prefix_code_match = self._all_info_cache[
                self._all_info_cache['code'].str.startswith(query)
            ]
            for _, row in prefix_code_match.iterrows():
                if len(results) >= limit:
                    break
                # 避免重复
                if not any(r['code'] == row['code'] for r in results):
                    results.append({
                        'code': row['code'],
                        'name': row['name'],
                        'type': row['type'],
                        'price': row.get('price', 0),
                        'change_pct': row.get('change_pct', 0),
                        'match_type': '代码前缀匹配'
                    })
        
        # 4. 股票名称开头匹配（如输入"中国"匹配所有中国开头的股票）
        if len(results) < limit:
            name_prefix_match = self._all_info_cache[
                self._all_info_cache['name'].str.startswith(query)
            ]
            for _, row in name_prefix_match.iterrows():
                if len(results) >= limit:
                    break
                # 避免重复
                if not any(r['code'] == row['code'] for r in results):
                    results.append({
                        'code': row['code'],
                        'name': row['name'],
                        'type': row['type'],
                        'price': row.get('price', 0),
                        'change_pct': row.get('change_pct', 0),
                        'match_type': '名称前缀匹配'
                    })
        
        # 5. 全量拼音首字母匹配（如果有pypinyin库）
        if len(results) < limit and HAS_PYPINYIN and 'pinyin' in self._all_info_cache.columns:
            query_upper = query.upper()
            # 精确匹配拼音首字母
            pinyin_exact_match = self._all_info_cache[
                self._all_info_cache['pinyin'] == query_upper
            ]
            for _, row in pinyin_exact_match.iterrows():
                if len(results) >= limit:
                    break
                # 避免重复
                if not any(r['code'] == row['code'] for r in results):
                    results.append({
                        'code': row['code'],
                        'name': row['name'],
                        'type': row['type'],
                        'price': row.get('price', 0),
                        'change_pct': row.get('change_pct', 0),
                        'match_type': '拼音精确匹配'
                    })
            
            # 拼音前缀匹配
            if len(results) < limit and len(query_upper) >= 2:
                pinyin_prefix_match = self._all_info_cache[
                    self._all_info_cache['pinyin'].str.startswith(query_upper)
                ]
                for _, row in pinyin_prefix_match.iterrows():
                    if len(results) >= limit:
                        break
                    # 避免重复
                    if not any(r['code'] == row['code'] for r in results):
                        results.append({
                            'code': row['code'],
                            'name': row['name'],
                            'type': row['type'],
                            'price': row.get('price', 0),
                            'change_pct': row.get('change_pct', 0),
                            'match_type': '拼音前缀匹配'
                        })
        
        # 6. 模糊匹配股票名称 (包含查询字符串)
        if len(results) < limit:
            fuzzy_name_match = self._all_info_cache[
                self._all_info_cache['name'].str.contains(query, case=False, na=False)
            ]
            for _, row in fuzzy_name_match.iterrows():
                if len(results) >= limit:
                    break
                # 避免重复
                if not any(r['code'] == row['code'] for r in results):
                    results.append({
                        'code': row['code'],
                        'name': row['name'],
                        'type': row['type'],
                        'price': row.get('price', 0),
                        'change_pct': row.get('change_pct', 0),
                        'match_type': '名称模糊匹配'
                    })
        
        # 7. 模糊匹配股票代码 (包含查询字符串)
        if len(results) < limit:
            fuzzy_code_match = self._all_info_cache[
                self._all_info_cache['code'].str.contains(query, case=False, na=False)
            ]
            for _, row in fuzzy_code_match.iterrows():
                if len(results) >= limit:
                    break
                # 避免重复
                if not any(r['code'] == row['code'] for r in results):
                    results.append({
                        'code': row['code'],
                        'name': row['name'],
                        'type': row['type'],
                        'price': row.get('price', 0),
                        'change_pct': row.get('change_pct', 0),
                        'match_type': '代码模糊匹配'
                    })
        
        # 8. 拼音模糊匹配（如果有pypinyin库）
        if len(results) < limit and HAS_PYPINYIN and 'pinyin' in self._all_info_cache.columns:
            query_upper = query.upper()
            pinyin_fuzzy_match = self._all_info_cache[
                self._all_info_cache['pinyin'].str.contains(query_upper, case=False, na=False)
            ]
            for _, row in pinyin_fuzzy_match.iterrows():
                if len(results) >= limit:
                    break
                # 避免重复
                if not any(r['code'] == row['code'] for r in results):
                    results.append({
                        'code': row['code'],
                        'name': row['name'],
                        'type': row['type'],
                        'price': row.get('price', 0),
                        'change_pct': row.get('change_pct', 0),
                        'match_type': '拼音模糊匹配'
                    })
        
        return results[:limit]
    
    def get_stock_suggestions(self, query: str) -> List[str]:
        """
        获取股票搜索建议
        
        参数:
            query: 搜索关键词
            
        返回:
            建议的搜索词列表
        """
        results = self.search_stock(query, limit=5)
        suggestions = []
        
        for result in results:
            suggestion = f"{result['code']} {result['name']} ({result['type']})"
            suggestions.append(suggestion)
            
        return suggestions

# 全局搜索器实例
_stock_searcher = None

def get_stock_searcher() -> StockSearcher:
    """获取股票搜索器实例"""
    global _stock_searcher
    if _stock_searcher is None:
        _stock_searcher = StockSearcher()
    # 确保实例有所有必要的属性
    if not hasattr(_stock_searcher, '_all_info_cache'):
        _stock_searcher._all_info_cache = None
    return _stock_searcher

def search_stock_by_name(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    通过名称搜索股票的便捷函数
    
    参数:
        query: 搜索关键词
        limit: 返回结果数量限制
        
    返回:
        匹配的股票信息列表
    """
    try:
        searcher = get_stock_searcher()
        # 确保搜索器有所有必要的属性
        if not hasattr(searcher, '_all_info_cache'):
            searcher._all_info_cache = None
        if not hasattr(searcher, '_stock_info_cache'):
            searcher._stock_info_cache = None
        if not hasattr(searcher, '_etf_info_cache'):
            searcher._etf_info_cache = None
        if not hasattr(searcher, '_last_update'):
            searcher._last_update = None
        if not hasattr(searcher, '_pinyin_cache'):
            searcher._pinyin_cache = {}
        
        return searcher.search_stock(query, limit)
    except Exception as e:
        print(f"搜索股票时出错: {e}")
        return []

def extract_stock_code(query: str) -> Optional[str]:
    """
    从查询中提取股票代码
    
    参数:
        query: 用户输入的查询字符串
        
    返回:
        提取的股票代码，如果没找到则返回None
    """
    if not query:
        return None
        
    query = query.strip()
    
    # 如果输入的就是6位数字代码，直接返回
    if re.match(r'^\d{6}$', query):
        return query
    
    # 如果输入包含代码格式 (如 "600519 贵州茅台")
    code_match = re.search(r'\b(\d{6})\b', query)
    if code_match:
        return code_match.group(1)
    
    # 尝试通过名称搜索获取代码
    try:
        results = search_stock_by_name(query, limit=1)
        if results:
            return results[0]['code']
    except Exception as e:
        print(f"通过名称搜索股票代码时出错: {e}")
    
    return None

def install_pypinyin_hint():
    """
    提示用户安装pypinyin库以获得更好的拼音搜索体验
    """
    if not HAS_PYPINYIN:
        print("💡 提示：安装pypinyin库可以获得更好的拼音搜索体验")
        print("   安装命令：pip install pypinyin")
        return False
    return True
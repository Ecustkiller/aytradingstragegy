"""
AY Trading App - Streamlit 主入口文件
股票技术分析与智能选股系统
"""

import sys
import os
import warnings

# 屏蔽所有警告
warnings.filterwarnings('ignore')

# 过滤stderr输出，屏蔽py_mini_racer和Node.js的错误信息
class FilteredStderr:
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.filter_keywords = [
            'MiniRacer.__del__',
            'mr_free_context',
            'AttributeError',
            'Exception ignored',
            'DeprecationWarning',
            'punycode',
            'node:',
            'Use `node --trace-deprecation',
            'keyword arguments have been deprecated',
            'Use config instead'
        ]

    def write(self, text):
        # 只输出不包含过滤关键词的内容
        if not any(keyword in text for keyword in self.filter_keywords):
            self.original_stderr.write(text)

    def flush(self):
        self.original_stderr.flush()

    def fileno(self):
        return self.original_stderr.fileno()

# 替换stderr
sys.stderr = FilteredStderr(sys.stderr)

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入主应用
from modules.app import main

# 配置Streamlit使用固定端口8501
if __name__ == "__main__":
    main()

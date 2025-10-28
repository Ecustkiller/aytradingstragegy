"""
AY Trading App - Streamlit 主入口文件
股票技术分析与智能选股系统
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入主应用
from modules.app import main

# 配置Streamlit使用固定端口8501
if __name__ == "__main__":
    main()

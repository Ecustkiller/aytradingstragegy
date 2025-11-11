#!/usr/bin/env python3
"""
简单测试数据源功能
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_import():
    """测试导入功能"""
    print("🧪 测试模块导入...")
    
    try:
        from modules.custom_strategy_editor import run_backtest_with_task, run_backtest_with_akshare
        print("✅ 自定义策略编辑器导入成功")
        
        from aitrader_core.bt_engine import Task
        print("✅ Task类导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_task():
    """测试简单的Task创建"""
    print("\n🧪 测试Task创建...")
    
    try:
        from aitrader_core.bt_engine import Task
        
        task = Task()
        task.name = '测试策略'
        task.symbols = ['600519.SH']
        task.start_date = '20240101'
        task.end_date = '20240131'
        task.benchmark = '000300.SH'
        
        print(f"✅ Task创建成功: {task.name}")
        return task
        
    except Exception as e:
        print(f"❌ Task创建失败: {e}")
        return None

def main():
    """主测试函数"""
    print("🧪 数据源功能测试")
    print("=" * 40)
    
    if not test_import():
        return
        
    task = test_simple_task()
    if task is None:
        return
        
    print("\n🎉 基础功能测试完成!")

if __name__ == "__main__":
    main()
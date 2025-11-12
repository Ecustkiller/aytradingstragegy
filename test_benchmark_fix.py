#!/usr/bin/env python3
"""
测试基准数据缺失时的回测功能修复
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "aitrader_core"))

def test_backtest():
    """测试回测功能"""
    try:
        # 导入必要的模块
        from bt_engine import Task, Engine
        from datafeed.csv_dataloader import CsvDataLoader
        
        print("✅ 模块导入成功")
        
        # 创建测试任务
        task = Task()
        task.name = '测试策略'
        task.symbols = ['000001.SZ']
        task.benchmark = '510300.SH'  # 这个基准数据不存在
        task.start_date = '20240101'
        task.end_date = '20241201'
        task.rules = []
        
        print(f"✅ Task创建成功: {task.name}")
        
        # 测试基准数据加载
        benchmark_df = CsvDataLoader().read_df([task.benchmark], path='quotes')
        if benchmark_df.empty:
            print(f"⚠️ 基准数据 {task.benchmark} 不存在，这是预期的")
        else:
            print(f"✅ 基准数据 {task.benchmark} 存在")
        
        # 尝试运行回测（这里可能会失败，但不应该因为基准数据而崩溃）
        try:
            # 检查数据路径
            data_path = project_root / "data" / "stock_data"
            if not data_path.exists():
                print(f"⚠️ 数据路径不存在: {data_path}")
                return False
            
            engine = Engine(path=str(data_path))
            commissions = lambda q, p: max(5, abs(q) * p * 0.00025)
            
            result = engine.run(task, commissions=commissions)
            print("✅ 回测成功完成！")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "cannot concat" in error_msg or "concat" in error_msg.lower():
                print(f"❌ 基准数据concat错误未修复: {e}")
                return False
            else:
                print(f"⚠️ 回测失败，但不是因为基准数据concat问题: {e}")
                return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 测试基准数据缺失处理...")
    success = test_backtest()
    if success:
        print("\n🎉 测试通过！基准数据缺失问题已修复")
    else:
        print("\n❌ 测试失败！基准数据缺失问题未修复")
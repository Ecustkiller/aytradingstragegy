"""
测试峰级线趋势分析功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.peak_valley_analyzer import peak_valley_analyzer
from modules.data_loader import get_stock_data
from datetime import datetime, timedelta
import pandas as pd

def test_peak_valley_analysis():
    """测试峰谷分析功能"""
    print("=" * 60)
    print("峰级线趋势分析测试")
    print("=" * 60)

    # 测试股票：000001.SZ 平安银行
    symbol = "000001"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 最近180天数据

    print(f"\n📊 获取股票数据: {symbol}")
    print(f"   时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    try:
        # 获取数据
        df = get_stock_data(symbol, start_date, end_date, "daily", "csv")

        if df is None or df.empty:
            print("❌ 无法获取股票数据")
            return

        print(f"✅ 成功获取 {len(df)} 条数据")
        print(f"   数据列: {df.columns.tolist()}")
        print(f"   价格范围: {df['Low'].min():.2f} - {df['High'].max():.2f}")

        # 1. 测试峰谷识别
        print("\n" + "=" * 60)
        print("1. 峰谷点识别测试")
        print("=" * 60)

        df_marked = peak_valley_analyzer.identify_peaks_valleys(df)
        peaks = df_marked[df_marked['is_peak']]
        valleys = df_marked[df_marked['is_valley']]

        print(f"✅ 识别到 {len(peaks)} 个峰点")
        if len(peaks) > 0:
            print("   最近的峰点:")
            for idx, row in peaks.tail(5).iterrows():
                print(f"   - {idx.strftime('%Y-%m-%d')}: {row['peak_price']:.2f}")

        print(f"\n✅ 识别到 {len(valleys)} 个谷点")
        if len(valleys) > 0:
            print("   最近的谷点:")
            for idx, row in valleys.tail(5).iterrows():
                print(f"   - {idx.strftime('%Y-%m-%d')}: {row['valley_price']:.2f}")

        # 2. 测试支撑压力位计算
        print("\n" + "=" * 60)
        print("2. 支撑压力位计算测试")
        print("=" * 60)

        sr_levels = peak_valley_analyzer.calculate_support_resistance(df)
        current_price = sr_levels['current_price']
        support_levels = sr_levels['support_levels']
        resistance_levels = sr_levels['resistance_levels']

        print(f"当前价格: {current_price:.2f}")
        print(f"\n压力位 ({len(resistance_levels)} 个):")
        for i, level in enumerate(resistance_levels[:5], 1):
            distance = ((level - current_price) / current_price) * 100
            print(f"   {i}. {level:.2f} (距离 +{distance:.2f}%)")

        print(f"\n支撑位 ({len(support_levels)} 个):")
        for i, level in enumerate(support_levels[:5], 1):
            distance = ((current_price - level) / current_price) * 100
            print(f"   {i}. {level:.2f} (距离 -{distance:.2f}%)")

        # 3. 测试趋势分析
        print("\n" + "=" * 60)
        print("3. 趋势分析测试")
        print("=" * 60)

        trend_info = peak_valley_analyzer.analyze_trend(df)
        print(f"趋势方向: {trend_info.get('trend', 'unknown')}")
        print(f"置信度: {trend_info.get('confidence', 0):.2%}")
        print(f"描述: {trend_info.get('description', '无')}")

        # 4. 测试交易形态识别
        print("\n" + "=" * 60)
        print("4. 交易形态识别测试")
        print("=" * 60)

        patterns = peak_valley_analyzer.identify_trading_patterns(df)
        print(f"识别到 {len(patterns)} 个交易形态:")

        for i, pattern in enumerate(patterns, 1):
            print(f"\n   {i}. {pattern['pattern']}")
            print(f"      类型: {pattern['type']}")
            print(f"      置信度: {pattern['confidence']:.2%}")
            print(f"      描述: {pattern['description']}")
            if 'entry_price' in pattern:
                print(f"      入场价: {pattern['entry_price']:.2f}")
            if 'stop_loss' in pattern:
                print(f"      止损价: {pattern['stop_loss']:.2f}")

        # 5. 测试综合交易建议
        print("\n" + "=" * 60)
        print("5. 综合交易建议测试")
        print("=" * 60)

        advice = peak_valley_analyzer.generate_trade_advice(df)
        print(f"建议操作: {advice['action']}")
        print(f"置信度: {advice['confidence']:.2%}")
        print(f"描述: {advice['description']}")

        if 'entry_price' in advice and advice['entry_price']:
            print(f"建议入场价: {advice['entry_price']:.2f}")
        if 'stop_loss' in advice and advice['stop_loss']:
            print(f"建议止损价: {advice['stop_loss']:.2f}")
        if 'take_profit' in advice and advice['take_profit']:
            print(f"建议止盈价: {advice['take_profit']:.2f}")

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_peak_valley_analysis()

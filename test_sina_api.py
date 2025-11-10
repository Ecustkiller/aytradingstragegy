#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新浪实时行情接口
"""
import requests
import time

def test_sina_realtime():
    """测试新浪实时行情接口"""
    timestamp = int(time.time() * 1000)
    stock_codes = 'sz000001,sh600519'
    url = f'https://hq.sinajs.cn/rn={timestamp}&list={stock_codes}'
    
    print(f"请求URL: {url}")
    print("=" * 60)
    
    # 添加请求头避免403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://finance.sina.com.cn'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应内容:\n{response.text}")
        
        # 解析数据
        lines = response.text.strip().split('\n')
        for line in lines:
            if 'hq_str_' in line:
                # 提取股票代码和数据
                parts = line.split('="')
                if len(parts) >= 2:
                    code = parts[0].split('hq_str_')[1]
                    data = parts[1].rstrip('";')
                    fields = data.split(',')
                    
                    if len(fields) >= 32:
                        print(f"\n股票代码: {code}")
                        print(f"股票名称: {fields[0]}")
                        print(f"今日开盘价: {fields[1]}")
                        print(f"昨日收盘价: {fields[2]}")
                        print(f"当前价格: {fields[3]}")
                        print(f"今日最高价: {fields[4]}")
                        print(f"今日最低价: {fields[5]}")
                        print(f"成交量(手): {fields[8]}")
                        print(f"成交额(元): {fields[9]}")
                        print(f"时间: {fields[30]} {fields[31]}")
                        
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == '__main__':
    test_sina_realtime()

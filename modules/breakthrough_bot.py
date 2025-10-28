import requests
import json
import schedule
import time
from datetime import datetime
import pandas as pd
from .breakthrough_selector_fixed import BreakthroughSelector
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BreakthroughBot:
    def __init__(self, webhook_url):
        """
        突破选股机器人
        :param webhook_url: 企业微信机器人的webhook地址
        """
        self.webhook_url = webhook_url
        self.selector = BreakthroughSelector()
    
    def send_message(self, content):
        """发送消息到企业微信群"""
        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            response = requests.post(
                self.webhook_url, 
                headers=headers, 
                data=json.dumps(data, ensure_ascii=False).encode('utf-8')
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info("消息发送成功")
                    return True
                else:
                    logger.error(f"消息发送失败: {result}")
                    return False
            else:
                logger.error(f"HTTP请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False
    
    def send_markdown(self, content):
        """发送markdown格式消息，如果内容过长则分段发送"""
        try:
            # 企业微信markdown消息限制4096字符
            max_length = 4000  # 留一些余量
            
            if len(content) <= max_length:
                # 内容不长，直接发送
                return self._send_single_markdown(content)
            else:
                # 内容过长，分段发送
                return self._send_long_content(content, max_length)
                
        except Exception as e:
            logger.error(f"发送markdown消息异常: {e}")
            return False
    
    def _send_single_markdown(self, content):
        """发送单条markdown消息"""
        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
            
            response = requests.post(
                self.webhook_url, 
                headers=headers, 
                data=json.dumps(data, ensure_ascii=False).encode('utf-8')
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info("Markdown消息发送成功")
                    return True
                else:
                    logger.error(f"Markdown消息发送失败: {result}")
                    return False
            else:
                logger.error(f"HTTP请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"发送markdown消息异常: {e}")
            return False
    
    def _send_long_content(self, content, max_length):
        """分段发送长内容"""
        try:
            # 按段落分割内容
            lines = content.split('\n')
            current_chunk = ""
            chunk_count = 1
            success_count = 0
            
            for line in lines:
                # 检查添加这一行后是否会超长
                if len(current_chunk + line + '\n') > max_length and current_chunk:
                    # 发送当前块
                    chunk_header = f"📄 第{chunk_count}部分:\n\n"
                    chunk_content = chunk_header + current_chunk
                    
                    if self._send_single_markdown(chunk_content):
                        success_count += 1
                        time.sleep(2)  # 避免发送过快，增加延迟
                    
                    # 开始新的块
                    current_chunk = line + '\n'
                    chunk_count += 1
                else:
                    current_chunk += line + '\n'
            
            # 发送最后一块
            if current_chunk:
                chunk_header = f"📄 第{chunk_count}部分:\n\n"
                chunk_content = chunk_header + current_chunk
                
                if self._send_single_markdown(chunk_content):
                    success_count += 1
            
            logger.info(f"长内容分{chunk_count}段发送，成功{success_count}段")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"分段发送异常: {e}")
            return False
    
    def format_stock_results(self, df, time_period):
        """智能格式化股票选股结果，自动分段"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if df.empty:
            return [f"🎯 突破选股结果 ({time_period})\n时间: {current_time}\n结果: 暂无符合条件的突破股票"]
        
        # 按突破幅度排序
        df_sorted = df.sort_values('breakthrough_pct', ascending=False)
        total_count = len(df)
        
        # 计算每条消息的最大字符数（企业微信限制4096字符）
        max_chars = 3800  # 留一些余量
        
        # 估算每只股票的字符数（约60-80字符）
        chars_per_stock = 80
        stocks_per_message = max_chars // chars_per_stock
        
        messages = []
        current_message = f"🎯 突破选股结果 ({time_period}) - 共{total_count}只\n时间: {current_time}\n\n"
        current_length = len(current_message)
        current_stock_count = 0
        message_num = 1
        
        for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
            stock_code = str(row['code']).zfill(6)
            breakthrough_pct = row['breakthrough_pct']
            
            # 突破等级标识
            if breakthrough_pct > 50:
                stars = "🚀🚀🚀"
            elif breakthrough_pct > 20:
                stars = "🚀🚀"
            else:
                stars = "🚀"
            
            stock_line = f"{idx:2d}. {stock_code} {row['name']} {row['current_price']:.2f}元 {breakthrough_pct:.2f}% {stars}\n"
            
            # 检查是否需要开始新消息
            if current_length + len(stock_line) > max_chars and current_stock_count > 0:
                # 当前消息已满，保存并开始新消息
                messages.append(current_message.rstrip())
                message_num += 1
                current_message = f"📋 第{message_num}部分 ({idx}-{min(idx + stocks_per_message - 1, total_count)}):\n\n"
                current_length = len(current_message)
                current_stock_count = 0
            
            current_message += stock_line
            current_length += len(stock_line)
            current_stock_count += 1
        
        # 添加最后一条消息
        if current_message.strip():
            messages.append(current_message.rstrip())
        
        return messages
        
        # 构建markdown格式的结果
        content = f"""## 🎯 突破选股结果 ({time_period})
**时间**: {current_time}
**找到**: {len(df)} 只突破股票

"""
        
        # 添加股票列表
        for i, (_, stock) in enumerate(df.iterrows(), 1):  # 显示所有股票
            content += f"""### {i}. {stock['name']} ({stock['code']})
- **现价**: {stock['current_price']:.2f}元
- **今日最高**: {stock['current_high']:.2f}元  
- **前高价格**: {stock['previous_high']:.2f}元
- **突破幅度**: {stock['breakthrough_pct']:.2f}%
- **涨跌幅**: {stock['change_pct']:.2f}%

"""
        
        content += f"\n*共找到 {len(df)} 只突破股票，详细结果已保存到文件*"
        
        content += "\n---\n*数据来源: 突破选股系统*"
        
        return content
    
    def run_stock_selection(self, time_period):
        """运行选股程序并发送结果"""
        try:
            logger.info(f"开始执行{time_period}选股...")
            
            # 发送开始通知
            start_msg = f"🚀 开始执行{time_period}突破选股分析..."
            self.send_message(start_msg)
            
            # 执行选股
            results = self.selector.select_breakthrough_stocks()
            
            # 转换为DataFrame格式
            if results:
                df_results = pd.DataFrame(results)
                filename = f"breakthrough_stocks_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                df_results.to_csv(filename, index=False, encoding='utf-8-sig')
                logger.info(f"选股结果已保存到: {filename}")
            else:
                df_results = pd.DataFrame()
            
            # 智能格式化并分段发送结果
            message_list = self.format_stock_results(df_results, time_period)
            
            success_count = 0
            for i, message in enumerate(message_list):
                if i > 0:
                    time.sleep(3)  # 消息间隔3秒，避免发送过快
                
                if self.send_markdown(message):
                    success_count += 1
                    logger.info(f"第{i+1}部分消息发送成功")
                else:
                    logger.error(f"第{i+1}部分消息发送失败")
            
            if success_count > 0:
                logger.info(f"{time_period}选股结果发送成功，共{success_count}/{len(message_list)}部分")
            else:
                # 如果所有markdown发送都失败，尝试发送简单文本
                simple_msg = f"{time_period}选股完成，找到 {len(results)} 只突破股票"
                self.send_message(simple_msg)
            
        except Exception as e:
            error_msg = f"❌ {time_period}选股执行失败: {str(e)}"
            logger.error(error_msg)
            self.send_message(error_msg)
    
    def noon_selection(self):
        """中午12点选股"""
        self.run_stock_selection("午间")
    
    def afternoon_selection(self):
        """下午14:50选股"""
        self.run_stock_selection("尾盘")
    
    def get_breakthrough_stocks(self):
        """获取突破股票（用于测试）"""
        try:
            logger.info("获取突破股票...")
            stocks = self.selector.get_breakthrough_stocks()
            return stocks if stocks is not None else []
        except Exception as e:
            logger.error(f"获取突破股票失败: {e}")
            return []
    
    def start_scheduler(self):
        """启动定时任务"""
        logger.info("启动突破选股定时任务...")
        
        # 设置定时任务
        schedule.every().day.at("12:00").do(self.noon_selection)
        schedule.every().day.at("14:50").do(self.afternoon_selection)
        
        logger.info("定时任务已设置:")
        logger.info("- 每日 12:00 执行午间选股")
        logger.info("- 每日 14:50 执行尾盘选股")
        
        # 发送启动通知
        start_msg = """🤖 突破选股机器人已启动

⏰ **定时任务**:
- 每日 12:00 午间选股
- 每日 14:50 尾盘选股

📊 **选股条件**:
- 股价在55日均线上方
- 55日均线拐头向上  
- 突破前高点
- 沪深主板股票

🚀 系统已就绪，等待定时执行..."""
        
        self.send_markdown(start_msg)
        
        # 持续运行
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在关闭...")
                self.send_message("🛑 突破选股机器人已停止运行")
                break
            except Exception as e:
                logger.error(f"调度器异常: {e}")
                time.sleep(60)

def main():
    """主函数"""
    # 从配置文件加载webhook地址
    try:
        import json
        with open('wechat_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        webhook_url = config['webhook_url']
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return
    
    # 创建机器人实例
    bot = BreakthroughBot(webhook_url)
    
    # 启动定时任务
    bot.start_scheduler()

if __name__ == "__main__":
    main()
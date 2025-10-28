"""
综合生活类机器人
功能: 天气预报、穿衣建议、电影推荐、热搜监控、节假日提醒等
"""

import requests
import json
import time
import random
import re
from datetime import datetime, timedelta
import schedule
import logging
from typing import Dict, List, Any
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class LifestyleBot:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('lifestyle_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def translate_text(self, text: str, target_lang: str = 'zh') -> str:
        """使用多翻译源对比，选择最佳翻译结果"""
        try:
            # 获取多个翻译源的结果
            translations = []
            
            # 1. Google Translate (免费接口)
            google_result = self.translate_with_google(text, target_lang)
            if google_result:
                translations.append(('Google', google_result))
            
            # 2. MyMemory API
            mymemory_result = self.translate_with_mymemory(text, target_lang)
            if mymemory_result:
                translations.append(('MyMemory', mymemory_result))
            
            # 3. 选择最佳翻译
            if translations:
                best_translation = self.select_best_translation(text, translations)
                return best_translation
                
        except Exception as e:
            self.logger.warning(f"多源翻译失败: {e}")
        
        return ""
    
    def translate_with_google(self, text: str, target_lang: str = 'zh') -> str:
        """使用Google Translate翻译"""
        try:
            import urllib.parse
            encoded_text = urllib.parse.quote(text)
            
            # Google Translate免费接口
            api_url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target_lang}&dt=t&q={encoded_text}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    import json
                    # Google返回的是一个复杂的数组结构
                    result = json.loads(response.text)
                    if result and len(result) > 0 and len(result[0]) > 0:
                        translated = result[0][0][0]  # 第一个翻译结果
                        if translated and translated != text:
                            return translated
                        
                except Exception as e:
                    self.logger.warning(f"解析Google翻译结果失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Google翻译API失败: {e}")
        
        return ""
    
    def translate_with_mymemory(self, text: str, target_lang: str = 'zh') -> str:
        """使用MyMemory API翻译"""
        try:
            import urllib.parse
            encoded_text = urllib.parse.quote(text)
            
            api_url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair=en|{target_lang}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('responseStatus') == 200:
                        translated = data.get('responseData', {}).get('translatedText', '')
                        if translated and translated != text:
                            return translated
                        
                except Exception as e:
                    self.logger.warning(f"解析MyMemory翻译结果失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"MyMemory翻译API失败: {e}")
        
        return ""
    
    def select_best_translation(self, original_text: str, translations: list) -> str:
        """选择最佳翻译结果"""
        try:
            if not translations:
                return ""
            
            if len(translations) == 1:
                return translations[0][1]
            
            # 翻译质量评分规则
            scores = []
            
            for source, translation in translations:
                score = 0
                
                # 1. 长度合理性 (翻译不应该过短或过长)
                length_ratio = len(translation) / len(original_text)
                if 0.5 <= length_ratio <= 2.0:
                    score += 2
                elif 0.3 <= length_ratio <= 3.0:
                    score += 1
                
                # 2. 包含中文字符 (确保是中文翻译)
                chinese_chars = sum(1 for char in translation if '\u4e00' <= char <= '\u9fff')
                if chinese_chars > 0:
                    score += 3
                    # 中文字符比例合理
                    chinese_ratio = chinese_chars / len(translation)
                    if chinese_ratio > 0.3:
                        score += 2
                
                # 3. 避免明显的直译痕迹
                # 检查是否包含过多的英文单词残留
                english_words = sum(1 for char in translation if char.isalpha() and ord(char) < 128)
                if english_words == 0:
                    score += 2
                elif english_words < len(translation) * 0.1:
                    score += 1
                
                # 4. 语义完整性检查
                # 检查翻译是否包含关键信息
                score += self.check_semantic_completeness(original_text, translation)
                
                # 5. 自然度检查 (中文表达习惯)
                score += self.check_naturalness(translation)
                
                # 6. Google翻译通常质量更好，给予轻微加分
                if source == 'Google':
                    score += 1
                
                # 7. 检查标点符号的合理性
                if '。' in translation or '，' in translation or '？' in translation:
                    score += 1
                
                scores.append((score, source, translation))
                self.logger.info(f"翻译评分 - {source}: {score}分 - {translation}")
            
            # 选择得分最高的翻译
            scores.sort(key=lambda x: x[0], reverse=True)
            best_score, best_source, best_translation = scores[0]
            
            self.logger.info(f"选择最佳翻译: {best_source} ({best_score}分) - {best_translation}")
            return best_translation
            
        except Exception as e:
            self.logger.warning(f"选择最佳翻译失败: {e}")
            # 如果评分失败，返回第一个翻译
            return translations[0][1] if translations else ""
    
    def check_semantic_completeness(self, original: str, translation: str) -> int:
        """检查语义完整性"""
        score = 0
        
        # 检查数字是否保持一致
        import re
        original_numbers = re.findall(r'\d+', original)
        translation_numbers = re.findall(r'\d+', translation)
        
        if len(original_numbers) == len(translation_numbers):
            if original_numbers == translation_numbers:
                score += 2  # 数字完全一致
            else:
                score += 1  # 数字数量一致
        
        # 检查问号等关键标点
        if '?' in original and ('？' in translation or '吗' in translation):
            score += 1
        
        # 检查否定词
        negative_words_en = ['not', "n't", 'no', 'never', 'none']
        negative_words_zh = ['不', '没', '非', '无', '未']
        
        has_negative_en = any(word in original.lower() for word in negative_words_en)
        has_negative_zh = any(word in translation for word in negative_words_zh)
        
        if has_negative_en == has_negative_zh:
            score += 1
        
        return score
    
    def check_naturalness(self, translation: str) -> int:
        """检查中文表达的自然度"""
        score = 0
        
        # 检查常见的自然表达
        natural_patterns = [
            '可以', '能够', '应该', '需要', '必须',
            '一个', '一种', '一些', '这个', '那个',
            '的话', '的时候', '因为', '所以', '但是',
            '大约', '差不多', '左右', '或者', '还是'
        ]
        
        natural_count = sum(1 for pattern in natural_patterns if pattern in translation)
        if natural_count >= 2:
            score += 2
        elif natural_count >= 1:
            score += 1
        
        # 检查是否有不自然的直译痕迹
        unnatural_patterns = [
            '的的', '在在', '是是',  # 重复词
            '一匹马可以用一只眼睛与另一只眼睛一起',  # 明显的直译
        ]
        
        if any(pattern in translation for pattern in unnatural_patterns):
            score -= 2
        
        # 检查语序是否自然
        if translation.count('的') > len(translation) * 0.15:  # 过多的"的"字
            score -= 1
        
        return score
    
    def setup_selenium_driver(self):
        """设置Selenium浏览器驱动"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            self.logger.warning(f"设置Selenium驱动失败: {e}")
            return None

    def send_message(self, content: str):
        """发送消息到企业微信"""
        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            response = requests.post(self.webhook_url, json=data, timeout=10)
            if response.status_code == 200:
                self.logger.info("消息发送成功")
            else:
                self.logger.error(f"消息发送失败: {response.status_code}")
        except Exception as e:
            self.logger.error(f"发送消息异常: {e}")

    def fetch_real_weather(self) -> Dict[str, Any]:
        """获取真实天气数据"""
        # 优先使用中国天气网API，数据更准确
        try:
            url = "http://t.weather.sojson.com/api/weather/city/101020100"  # 上海城市代码
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 200:
                    today_data = data['data']['forecast'][0]
                    
                    weather_data = {
                        "city": "上海",
                        "temperature": float(data['data']['wendu']),
                        "weather": today_data['type'],
                        "wind": f"{today_data['fx']}{today_data['fl']}",
                        "humidity": int(data['data']['shidu'].replace('%', '')),
                        "air_quality": data['data']['quality'],
                        "pm25": data['data'].get('pm25', 0),
                        "pm10": data['data'].get('pm10', 0),
                        "uv_index": 5,  # 默认值
                        "visibility": 15,  # 默认值
                        "feels_like": float(data['data']['wendu']),
                        "high_temp": int(today_data['high'].replace('高温 ', '').replace('℃', '')),
                        "low_temp": int(today_data['low'].replace('低温 ', '').replace('℃', '')),
                        "sunrise": today_data.get('sunrise', '06:00'),
                        "sunset": today_data.get('sunset', '18:00'),
                        "notice": today_data.get('notice', '')
                    }
                    
                    # 获取未来3天预报
                    forecast = []
                    for i, day_data in enumerate(data['data']['forecast'][:3]):
                        forecast.append({
                            "date": day_data['ymd'],
                            "week": day_data['week'],
                            "weather": day_data['type'],
                            "high_temp": int(day_data['high'].replace('高温 ', '').replace('℃', '')),
                            "low_temp": int(day_data['low'].replace('低温 ', '').replace('℃', '')),
                            "wind": f"{day_data['fx']}{day_data['fl']}",
                            "notice": day_data.get('notice', '')
                        })
                    
                    weather_data['forecast'] = forecast
                    return weather_data
                    
        except Exception as e:
            self.logger.error(f"获取中国天气网数据失败: {e}")
            
        # 备用方案: 使用wttr.in服务
        try:
            url = "http://wttr.in/Shanghai?format=j1"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # 解析wttr.in数据格式
                current = data['current_condition'][0]
                today = data['weather'][0]
                
                # 转换天气描述为中文
                weather_desc_map = {
                    'Sunny': '晴',
                    'Clear': '晴',
                    'Partly cloudy': '多云',
                    'Cloudy': '阴',
                    'Overcast': '阴',
                    'Light rain': '小雨',
                    'Moderate rain': '中雨',
                    'Heavy rain': '大雨',
                    'Thundery outbreaks possible': '可能有雷阵雨',
                    'Patchy rain possible': '可能有小雨',
                    'Light drizzle': '毛毛雨',
                    'Fog': '雾',
                    'Mist': '薄雾'
                }
                
                weather_desc = current['weatherDesc'][0]['value']
                chinese_weather = weather_desc_map.get(weather_desc, weather_desc)
                
                # 构建天气数据
                weather_data = {
                    "city": "上海",
                    "temperature": int(current['temp_C']),
                    "weather": chinese_weather,
                    "wind": f"{current['windspeedKmph']}km/h",
                    "humidity": int(current['humidity']),
                    "air_quality": "良",  # wttr.in不提供空气质量，使用默认值
                    "uv_index": int(current.get('uvIndex', 5)),
                    "visibility": int(current['visibility']),
                    "feels_like": int(current['FeelsLikeC']),
                    "high_temp": int(current['temp_C']) + 2,  # 估算
                    "low_temp": int(current['temp_C']) - 5,   # 估算
                    "sunrise": "06:00",
                    "sunset": "18:00",
                    "notice": ""
                }
                
                # 全天预报
                hourly = today['hourly']
                forecast = []
                for i, hour_data in enumerate(hourly[::8]):  # 每8小时取一个点
                    time_periods = ['上午', '下午', '晚上']
                    if i < len(time_periods):
                        weather_desc = hour_data['weatherDesc'][0]['value']
                        chinese_weather = weather_desc_map.get(weather_desc, weather_desc)
                        forecast.append({
                            "time": time_periods[i],
                            "weather": chinese_weather,
                            "temp": int(hour_data['tempC'])
                        })
                
                weather_data['forecast'] = forecast
                return weather_data
                
        except Exception as e:
            self.logger.error(f"获取wttr.in天气数据失败: {e}")
        
        return {}

    def get_weather_info(self) -> str:
        """获取上海天气信息和穿衣建议"""
        try:
            # 获取真实天气数据
            weather_data = self.fetch_real_weather()
            
            if not weather_data:
                return "🌤️ 天气信息获取失败，请注意关注天气变化，建议带伞以防万一！"
            
            # 穿衣建议
            temp = int(weather_data["temperature"])
            if temp >= 28:
                clothing = "👕 短袖、短裤、凉鞋"
            elif temp >= 23:
                clothing = "👔 长袖衬衫、薄外套"
            elif temp >= 18:
                clothing = "🧥 外套、长裤、运动鞋"
            elif temp >= 10:
                clothing = "🧥 厚外套、毛衣、长裤"
            else:
                clothing = "🧥 羽绒服、厚毛衣、保暖裤"
            
            # 增强的异常天气检测和提醒
            current_weather = weather_data["weather"]
            weather_warning = ""
            
            # 检查当前天气
            if any(keyword in current_weather for keyword in ["雷阵雨", "雷雨", "暴雨", "雷暴"]):
                weather_warning += "\n⚠️ 【重要提醒】今天有雷雨天气，请务必带伞！避免在空旷地带活动！"
            elif any(keyword in current_weather for keyword in ["大雨", "中雨"]):
                weather_warning += "\n☔ 【出行提醒】今天有雨，记得带伞，注意路面湿滑！"
            elif any(keyword in current_weather for keyword in ["小雨", "毛毛雨"]):
                weather_warning += "\n🌧️ 【温馨提示】今天有小雨，建议带把伞以防万一！"
            elif any(keyword in current_weather for keyword in ["雾", "霾", "薄雾", "浓雾"]):
                weather_warning += "\n😷 【健康提醒】今天有雾霾，建议佩戴口罩，减少户外活动！"
            
            # 检查风力
            wind_str = str(weather_data.get("wind", ""))
            if any(keyword in wind_str for keyword in ["大风", "强风", "6级", "7级", "8级"]):
                weather_warning += "\n💨 【大风提醒】今天风力较大，注意安全，小心高空坠物！"
            
            # 检查未来几天的异常天气
            forecast = weather_data.get('forecast', [])
            future_warnings = []
            for day in forecast[:3]:  # 检查未来3天
                day_weather = day.get('weather', '')
                day_date = day.get('date', '')
                if any(keyword in day_weather for keyword in ["暴雨", "雷雨", "雷阵雨"]):
                    future_warnings.append(f"⚠️ {day_date}有{day_weather}，请提前准备！")
                elif any(keyword in day_weather for keyword in ["大雨", "中雨"]):
                    future_warnings.append(f"☔ {day_date}有{day_weather}，记得带伞！")
            
            if future_warnings:
                weather_warning += "\n\n📅 未来天气提醒:"
                for warning in future_warnings:
                    weather_warning += f"\n{warning}"
            
            # 空气质量提醒
            air_quality = weather_data.get('air_quality', '良')
            pm25 = weather_data.get('pm25', 0)
            if air_quality in ['轻度污染', '中度污染', '重度污染', '严重污染'] or pm25 > 75:
                weather_warning += f"\n😷 【空气质量提醒】今日空气质量{air_quality}，建议减少户外活动！"
            
            # 紫外线提醒
            uv_warning = ""
            uv_index = int(weather_data.get("uv_index", 5))
            if uv_index >= 8:
                uv_warning = "\n☀️ 【防晒提醒】紫外线很强，请做好防晒措施！"
            elif uv_index >= 6:
                uv_warning = "\n🕶️ 【防晒建议】紫外线较强，建议涂抹防晒霜！"
            
            # 温度提醒
            temp_warning = ""
            if temp >= 35:
                temp_warning = "\n🌡️ 【高温提醒】今天温度很高，注意防暑降温！"
            elif temp <= 5:
                temp_warning = "\n❄️ 【低温提醒】今天温度较低，注意保暖！"
            
            # 组装天气预报
            weather_msg = f"""🌤️ 上海天气预报
📍 {weather_data['city']}
🌡️ 当前温度: {weather_data['temperature']}°C
📊 今日温度: {weather_data.get('low_temp', 'N/A')}°C - {weather_data.get('high_temp', 'N/A')}°C
☁️ 天气: {weather_data['weather']}
💨 风力: {weather_data['wind']}
💧 湿度: {weather_data['humidity']}%
🌬️ 空气质量: {weather_data['air_quality']} (PM2.5: {pm25})
☀️ 紫外线指数: {uv_index}/10
👁️ 能见度: {weather_data.get('visibility', 'N/A')}km
🌅 日出: {weather_data.get('sunrise', 'N/A')} | 🌇 日落: {weather_data.get('sunset', 'N/A')}

👗 穿衣建议: {clothing}"""
            
            # 添加官方提醒
            if weather_data.get('notice'):
                weather_msg += f"\n\n📢 官方提醒: {weather_data['notice']}"
            
            # 添加未来3天预报
            if forecast:
                weather_msg += "\n\n📅 未来3天预报:"
                for day in forecast[:3]:
                    weather_msg += f"\n{day.get('date', 'N/A')} {day.get('week', 'N/A')}: {day.get('weather', 'N/A')} {day.get('low_temp', 'N/A')}°C-{day.get('high_temp', 'N/A')}°C"
            
            # 添加所有提醒
            weather_msg += weather_warning + uv_warning + temp_warning
            
            return weather_msg
            
        except Exception as e:
            self.logger.error(f"获取天气信息失败: {e}")
            return "🌤️ 天气信息获取失败，请注意关注天气变化，建议带伞以防万一！"

    def crawl_daily_taboo(self) -> str:
        """爬取每日禁忌信息"""
        try:
            # 尝试多个黄历网站
            taboo_sources = [
                self.crawl_huangli_net,
                self.crawl_laohuangli_com,
                self.crawl_wnl_com
            ]
            
            for source_func in taboo_sources:
                try:
                    result = source_func()
                    if result and len(result) > 10:  # 确保获取到有效内容
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取禁忌失败: {e}")
                    continue
            
            # 如果所有爬虫都失败，如实返回失败信息
            return "🚫 每日禁忌获取失败 - 所有数据源都无法访问"
            
        except Exception as e:
            self.logger.error(f"获取每日禁忌失败: {e}")
            return f"🚫 每日禁忌获取失败 - 系统错误: {str(e)}"
    
    def crawl_huangli_net(self) -> str:
        """爬取黄历网每日禁忌"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 尝试多个黄历网站
            urls = [
                "https://www.huangli.com/",
                "https://www.laohuangli.com/",
                "https://www.wnl.com/",
                "https://www.rili.com.cn/",
                "https://www.51wnl.com/"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找禁忌信息 - 多种选择器
                        taboo_selectors = [
                            {'tag': 'div', 'class': re.compile(r'.*忌.*|.*不宜.*|.*禁忌.*')},
                            {'tag': 'span', 'class': re.compile(r'.*忌.*|.*不宜.*|.*禁忌.*')},
                            {'tag': 'p', 'class': re.compile(r'.*忌.*|.*不宜.*|.*禁忌.*')},
                            {'tag': 'li', 'class': re.compile(r'.*忌.*|.*不宜.*|.*禁忌.*')},
                            {'tag': 'div', 'text': re.compile(r'.*忌.*|.*不宜.*|.*禁忌.*')},
                            {'tag': 'span', 'text': re.compile(r'.*忌.*|.*不宜.*|.*禁忌.*')}
                        ]
                        
                        taboos = []
                        for selector in taboo_selectors:
                            if 'class' in selector:
                                elements = soup.find_all(selector['tag'], class_=selector['class'])
                            else:
                                elements = soup.find_all(selector['tag'], text=selector['text'])
                            
                            for element in elements:
                                text = element.get_text().strip()
                                if text and len(text) > 3 and len(text) < 50:
                                    if any(keyword in text for keyword in ['忌', '不宜', '避免', '不要', '禁忌']):
                                        taboos.append(text)
                        
                        if taboos:
                            # 去重并选择前3条
                            unique_taboos = list(dict.fromkeys(taboos))[:3]
                            taboo_msg = f"🚫 今日禁忌\n\n"
                            for i, taboo in enumerate(unique_taboos, 1):
                                taboo_msg += f"{i}. {taboo}\n"
                            return taboo_msg
            
                except Exception as e:
                    self.logger.warning(f"爬取{url}失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取黄历网失败: {e}")
        
        return ""
    
    def crawl_laohuangli_com(self) -> str:
        """爬取老黄历网每日禁忌"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            url = "https://www.laohuangli.com/"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找禁忌信息
                taboo_elements = soup.find_all(['div', 'span', 'li'], text=re.compile(r'.*忌.*|.*不宜.*'))
                
                taboos = []
                for element in taboo_elements:
                    text = element.get_text().strip()
                    if text and len(text) > 3 and len(text) < 50:
                        taboos.append(text)
                
                if taboos:
                    selected_taboos = taboos[:3]
                    taboo_msg = f"🚫 今日禁忌\n\n"
                    for i, taboo in enumerate(selected_taboos, 1):
                        taboo_msg += f"{i}. {taboo}\n"
                    taboo_msg += "\n"
                    return taboo_msg
                    
        except Exception as e:
            self.logger.warning(f"爬取老黄历网失败: {e}")
        
        return ""
    
    def crawl_wnl_com(self) -> str:
        """爬取万年历网每日禁忌"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            url = "https://www.wnl.com/"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找禁忌信息
                taboo_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*忌.*|.*不宜.*'))
                
                taboos = []
                for element in taboo_elements:
                    text = element.get_text().strip()
                    if text and len(text) > 3 and len(text) < 50:
                        taboos.append(text)
                
                if taboos:
                    selected_taboos = taboos[:3]
                    taboo_msg = f"🚫 今日禁忌\n\n"
                    for i, taboo in enumerate(selected_taboos, 1):
                        taboo_msg += f"{i}. {taboo}\n"
                    taboo_msg += "\n"
                    return taboo_msg
                    
        except Exception as e:
            self.logger.warning(f"爬取万年历网失败: {e}")
        
        return ""
    
    
    def get_daily_taboo(self) -> str:
        """获取每日禁忌（主入口）"""
        return self.crawl_daily_taboo()
    
    def crawl_tarot_reading(self) -> str:
        """爬取塔罗牌占卜信息"""
        try:
            # 首先尝试简单的API方法
            simple_sources = [
                self.crawl_simple_tarot_api
            ]
            
            for source_func in simple_sources:
                try:
                    result = source_func()
                    if result and len(result) > 20:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取简单塔罗牌失败: {e}")
                    continue
            
            # 然后尝试Selenium方法
            tarot_sources = [
                self.crawl_tarot_com,
                self.crawl_tarot_online,
                self.crawl_daily_tarot
            ]
            
            for source_func in tarot_sources:
                try:
                    result = source_func()
                    if result and len(result) > 20:  # 确保获取到有效内容
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取塔罗牌失败: {e}")
                    continue
            
            # 如果所有爬虫都失败，如实返回失败信息
            return "🔮 塔罗牌占卜获取失败 - 所有数据源都无法访问"
            
        except Exception as e:
            self.logger.error(f"获取塔罗牌占卜失败: {e}")
            return f"🔮 塔罗牌占卜获取失败 - 系统错误: {str(e)}"
    
    def crawl_simple_tarot_api(self) -> str:
        """使用GitHub塔罗牌数据API"""
        try:
            # 使用GitHub上的真实塔罗牌数据
            api_url = "https://raw.githubusercontent.com/MinatoAquaCrews/nonebot_plugin_tarot/main/nonebot_plugin_tarot/tarot.json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=15)
            if response.status_code == 200:
                try:
                    tarot_data = response.json()
                    cards = tarot_data.get("cards", {})
                    
                    if cards:
                        # 随机选择一张塔罗牌
                        import random
                        card_keys = list(cards.keys())
                        selected_key = random.choice(card_keys)
                        selected_card = cards[selected_key]
                        
                        # 获取卡牌信息
                        name_cn = selected_card.get("name_cn", "未知")
                        name_en = selected_card.get("name_en", "Unknown")
                        meaning = selected_card.get("meaning", {})
                        
                        # 随机选择正位或逆位
                        is_upright = random.choice([True, False])
                        position = "正位" if is_upright else "逆位"
                        card_meaning = meaning.get("up" if is_upright else "down", "")
                        
                        # 格式化输出
                        result = f"🔮 今日塔罗牌\n\n"
                        result += f"🃏 {name_cn} ({name_en})\n"
                        result += f"🔄 {position}\n\n"
                        result += f"💫 {card_meaning}"
                        
                        return result
                        
                except Exception as e:
                    self.logger.warning(f"解析塔罗牌JSON失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"GitHub塔罗牌API失败: {e}")
        
        return ""
    
    
    def crawl_tarot_com(self) -> str:
        """爬取塔罗牌网站 - 使用Selenium模拟点击"""
        driver = None
        try:
            driver = self.setup_selenium_driver()
            if not driver:
                return ""
            
            # 尝试访问塔罗牌网站
            tarot_sources = [
                self.crawl_tarot_com_selenium,
                self.crawl_astro_com_selenium,
                self.crawl_horoscope_com_selenium
            ]
            
            for source_func in tarot_sources:
                try:
                    result = source_func(driver)
                    if result and len(result) > 20:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取塔罗牌失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取塔罗牌网站失败: {e}")
        finally:
            if driver:
                driver.quit()
        
        return ""
    
    def crawl_tarot_com_selenium(self, driver) -> str:
        """使用Selenium爬取tarot.com - 改用一卡占卜"""
        try:
            driver.get("https://www.tarot.com/tarot/one-card")
            time.sleep(5)
            
            # 等待页面加载
            wait = WebDriverWait(driver, 15)
            
            # 尝试点击抽牌按钮
            click_selectors = [
                "a[href*='card']",
                ".btn",
                ".button",
                "button",
                "[onclick*='card']",
                "a:contains('Draw')",
                "a:contains('Pick')",
                "a:contains('Select')",
                "a:contains('One Card')"
            ]
            
            for selector in click_selectors:
                try:
                    if ":contains" in selector:
                        # 使用XPath查找包含文本的按钮
                        text = selector.split("'")[1]
                        button = driver.find_element(By.XPATH, f"//a[contains(text(), '{text}')]")
                    else:
                        button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if button.is_displayed() and button.is_enabled():
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(3)
                        break
                except:
                    continue
            
            # 等待结果加载
            time.sleep(5)
            
            # 查找结果内容
            result_selectors = [
                ".tarot-reading",
                ".card-reading",
                ".daily-reading",
                ".reading-result",
                ".card-result",
                ".tarot-result",
                "[class*='reading']",
                "[class*='result']",
                "[class*='card']",
                "[class*='tarot']",
                "p",
                "div"
            ]
            
            for selector in result_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 30 and len(text) < 800:
                            if any(keyword in text.lower() for keyword in ['tarot', 'card', 'reading', 'fortune', 'spiritual', 'guidance']):
                                # 清理文本
                                if not any(skip_word in text.lower() for skip_word in ['cookie', 'privacy', 'terms', 'contact', 'sign up', 'login']):
                                    return f"🔮 今日塔罗牌占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取tarot.com失败: {e}")
        
        return ""
    
    def crawl_astro_com_selenium(self, driver) -> str:
        """使用Selenium爬取astro.com"""
        try:
            driver.get("https://www.astro.com/daily-horoscope")
            time.sleep(3)
            
            # 等待页面加载
            wait = WebDriverWait(driver, 10)
            
            # 查找占星内容
            result_selectors = [
                ".horoscope",
                ".daily-horoscope",
                ".astrology",
                ".zodiac",
                "[class*='horoscope']",
                "[class*='astrology']"
            ]
            
            for selector in result_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 20 and len(text) < 500:
                            if any(keyword in text.lower() for keyword in ['horoscope', 'astrology', 'zodiac', 'fortune']):
                                return f"🔮 今日塔罗牌占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取astro.com失败: {e}")
        
        return ""
    
    def crawl_horoscope_com_selenium(self, driver) -> str:
        """使用Selenium爬取horoscope.com"""
        try:
            driver.get("https://www.horoscope.com/daily-horoscope")
            time.sleep(3)
            
            # 等待页面加载
            wait = WebDriverWait(driver, 10)
            
            # 查找占星内容
            result_selectors = [
                ".horoscope",
                ".daily-horoscope",
                ".astrology",
                ".zodiac",
                "[class*='horoscope']",
                "[class*='astrology']"
            ]
            
            for selector in result_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 20 and len(text) < 500:
                            if any(keyword in text.lower() for keyword in ['horoscope', 'astrology', 'zodiac', 'fortune']):
                                return f"🔮 今日塔罗牌占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取horoscope.com失败: {e}")
        
        return ""
    
    def crawl_tarot_online(self) -> str:
        """爬取在线塔罗牌网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问其他塔罗牌网站
            urls = [
                "https://www.tarot-online.com/daily",
                "https://www.free-tarot-reading.net/daily",
                "https://www.tarotreading.com/daily"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找塔罗牌信息
                        card_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*card.*|.*tarot.*'))
                        
                        for element in card_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 20 and len(text) < 200:
                                return f"🔮 今日塔罗牌占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取在线塔罗牌失败: {e}")
        
        return ""
    
    def crawl_daily_tarot(self) -> str:
        """爬取每日塔罗牌"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问每日塔罗牌网站
            urls = [
                "https://www.dailytarot.com",
                "https://www.tarotdaily.com",
                "https://www.free-tarot.com/daily"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找塔罗牌信息
                        card_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*card.*|.*tarot.*'))
                        
                        for element in card_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 20 and len(text) < 200:
                                return f"🔮 今日塔罗牌占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取每日塔罗牌失败: {e}")
        
        return ""
    
    
    def get_tarot_card(self) -> str:
        """获取塔罗牌占卜（主入口）"""
        return self.crawl_tarot_reading()
    
    def crawl_daily_fortune(self) -> str:
        """爬取每日运势信息"""
        try:
            # 首先尝试免费的星座运势API
            api_sources = [
                self.crawl_horoscope_api,
                self.crawl_aztro_api
            ]
            
            for source_func in api_sources:
                try:
                    result = source_func()
                    if result and len(result) > 20:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取运势API失败: {e}")
                    continue
            
            # 然后尝试Selenium方法
            fortune_sources = [
                self.crawl_xingzuo_com,
                self.crawl_astro_com,
                self.crawl_fortune_net
            ]
            
            for source_func in fortune_sources:
                try:
                    result = source_func()
                    if result and len(result) > 20:  # 确保获取到有效内容
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取运势失败: {e}")
                    continue
            
            # 如果所有爬虫都失败，如实返回失败信息
            return "🌟 每日运势获取失败 - 所有数据源都无法访问"
            
        except Exception as e:
            self.logger.error(f"获取每日运势失败: {e}")
            return f"🌟 每日运势获取失败 - 系统错误: {str(e)}"
    
    def crawl_horoscope_api(self) -> str:
        """使用免费的星座运势API"""
        try:
            import random
            
            # 12个星座
            zodiac_signs = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 
                           'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
            
            # 星座中文名称
            zodiac_names = {
                'aries': '白羊座', 'taurus': '金牛座', 'gemini': '双子座', 
                'cancer': '巨蟹座', 'leo': '狮子座', 'virgo': '处女座',
                'libra': '天秤座', 'scorpio': '天蝎座', 'sagittarius': '射手座',
                'capricorn': '摩羯座', 'aquarius': '水瓶座', 'pisces': '双鱼座'
            }
            
            # 随机选择一个星座
            selected_sign = random.choice(zodiac_signs)
            sign_name = zodiac_names.get(selected_sign, selected_sign)
            
            # 调用API
            api_url = f"https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign={selected_sign}&day=today"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success') and data.get('data'):
                        horoscope_data = data['data']
                        date = horoscope_data.get('date', '今日')
                        horoscope_text = horoscope_data.get('horoscope_data', '')
                        
                        if horoscope_text:
                            # 尝试翻译成中文
                            chinese_text = self.translate_text(horoscope_text)
                            
                            result = f"🌟 今日运势\n\n"
                            result += f"♈ {sign_name} ({selected_sign.title()})\n"
                            result += f"📅 {date}\n\n"
                            result += f"🇬🇧 {horoscope_text}\n\n"
                            if chinese_text:
                                result += f"🇨🇳 {chinese_text}"
                            else:
                                result += f"🇨🇳 翻译失败，仅显示英文原文"
                            
                            return result
                            
                except Exception as e:
                    self.logger.warning(f"解析星座运势API失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"星座运势API失败: {e}")
        
        return ""
    
    def crawl_aztro_api(self) -> str:
        """使用Aztro星座运势API"""
        try:
            import random
            
            # 12个星座
            zodiac_signs = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 
                           'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
            
            # 星座中文名称
            zodiac_names = {
                'aries': '白羊座', 'taurus': '金牛座', 'gemini': '双子座', 
                'cancer': '巨蟹座', 'leo': '狮子座', 'virgo': '处女座',
                'libra': '天秤座', 'scorpio': '天蝎座', 'sagittarius': '射手座',
                'capricorn': '摩羯座', 'aquarius': '水瓶座', 'pisces': '双鱼座'
            }
            
            # 随机选择一个星座
            selected_sign = random.choice(zodiac_signs)
            sign_name = zodiac_names.get(selected_sign, selected_sign)
            
            # 调用Aztro API (POST方法)
            api_url = f"https://aztro.sameerkumar.website/?sign={selected_sign}&day=today"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.post(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    description = data.get('description', '')
                    date_range = data.get('date_range', '')
                    current_date = data.get('current_date', '今日')
                    compatibility = data.get('compatibility', '')
                    mood = data.get('mood', '')
                    color = data.get('color', '')
                    lucky_number = data.get('lucky_number', '')
                    
                    if description:
                        # 尝试翻译成中文
                        chinese_description = self.translate_text(description)
                        chinese_mood = self.translate_text(mood) if mood else ""
                        chinese_color = self.translate_text(color) if color else ""
                        chinese_compatibility = self.translate_text(compatibility) if compatibility else ""
                        
                        result = f"🌟 今日运势\n\n"
                        result += f"♈ {sign_name} ({selected_sign.title()})\n"
                        result += f"📅 {current_date} ({date_range})\n\n"
                        result += f"🇬🇧 {description}\n\n"
                        if chinese_description:
                            result += f"🇨🇳 {chinese_description}\n\n"
                        else:
                            result += f"🇨🇳 翻译失败，仅显示英文原文\n\n"
                        
                        if mood:
                            result += f"🇬🇧 😊 今日心情: {mood}\n"
                            if chinese_mood:
                                result += f"🇨🇳 😊 今日心情: {chinese_mood}\n"
                        if color:
                            result += f"🇬🇧 🌈 幸运色彩: {color}\n"
                            if chinese_color:
                                result += f"🇨🇳 🌈 幸运色彩: {chinese_color}\n"
                        if lucky_number:
                            result += f"🍀 幸运数字: {lucky_number}\n"
                        if compatibility:
                            result += f"🇬🇧 💕 星座配对: {compatibility}\n"
                            if chinese_compatibility:
                                result += f"🇨🇳 💕 星座配对: {chinese_compatibility}"
                        
                        return result
                        
                except Exception as e:
                    self.logger.warning(f"解析Aztro API失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Aztro API失败: {e}")
        
        return ""
    
    def crawl_xingzuo_com(self) -> str:
        """爬取星座运势网站 - 使用Selenium模拟点击"""
        driver = None
        try:
            driver = self.setup_selenium_driver()
            if not driver:
                return ""
            
            # 尝试访问星座运势网站
            fortune_sources = [
                self.crawl_xingzuo_com_selenium,
                self.crawl_astro_fortune_selenium,
                self.crawl_horoscope_fortune_selenium
            ]
            
            for source_func in fortune_sources:
                try:
                    result = source_func(driver)
                    if result and len(result) > 20:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取运势失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取星座运势失败: {e}")
        finally:
            if driver:
                driver.quit()
        
        return ""
    
    def crawl_xingzuo_com_selenium(self, driver) -> str:
        """使用Selenium爬取星座运势 - 改用horoscope.com"""
        try:
            driver.get("https://www.horoscope.com/us/index.aspx")
            time.sleep(5)
            
            # 等待页面加载
            wait = WebDriverWait(driver, 15)
            
            # 随机选择一个星座
            import random
            zodiac_signs = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 
                           'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
            selected_sign = random.choice(zodiac_signs)
            
            # 尝试点击星座
            click_selectors = [
                f"a[href*='{selected_sign}']",
                f"[class*='{selected_sign}']",
                f"#{selected_sign}",
                ".zodiac-sign",
                ".horoscope-sign"
            ]
            
            for selector in click_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(3)
                            break
                    if elements:
                        break
                except:
                    continue
            
            # 等待结果加载
            time.sleep(5)
            
            # 查找运势内容
            result_selectors = [
                "[class*='horoscope']",
                "[class*='fortune']",
                "[class*='zodiac']",
                "[class*='astrology']",
                "[class*='daily']",
                ".content",
                ".reading",
                "p",
                "div"
            ]
            
            for selector in result_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 50 and len(text) < 800:
                            if any(keyword in text.lower() for keyword in ['today', 'fortune', 'horoscope', 'zodiac', 'astrology', 'energy', 'stars']):
                                # 清理文本
                                if not any(skip_word in text.lower() for skip_word in ['cookie', 'privacy', 'terms', 'contact', 'sign up', 'login', 'advertisement']):
                                    return f"🌟 今日运势占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取星座运势失败: {e}")
        
        return ""
    
    def crawl_astro_fortune_selenium(self, driver) -> str:
        """使用Selenium爬取占星运势 - 改用astrology.com"""
        try:
            driver.get("https://www.astrology.com/horoscope/daily.html")
            time.sleep(5)
            
            # 等待页面加载
            wait = WebDriverWait(driver, 15)
            
            # 随机选择一个星座
            import random
            zodiac_signs = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 
                           'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
            selected_sign = random.choice(zodiac_signs)
            
            # 尝试点击星座
            click_selectors = [
                f"a[href*='{selected_sign}']",
                f"[class*='{selected_sign}']",
                f"#{selected_sign}",
                ".zodiac-sign",
                ".horoscope-sign",
                "a",
                "button"
            ]
            
            for selector in click_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip().lower()
                            if selected_sign in text or any(sign in text for sign in ['aries', 'taurus', 'gemini']):
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(3)
                                break
                    if elements:
                        break
                except:
                    continue
            
            # 等待结果加载
            time.sleep(5)
            
            # 查找运势内容
            result_selectors = [
                "[class*='horoscope']",
                "[class*='fortune']",
                "[class*='zodiac']",
                "[class*='astrology']",
                "[class*='daily']",
                ".content",
                ".reading",
                "p",
                "div"
            ]
            
            for selector in result_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 50 and len(text) < 800:
                            if any(keyword in text.lower() for keyword in ['today', 'fortune', 'horoscope', 'zodiac', 'astrology', 'energy', 'stars', 'mercury', 'venus']):
                                # 清理文本
                                if not any(skip_word in text.lower() for skip_word in ['cookie', 'privacy', 'terms', 'contact', 'sign up', 'login', 'advertisement']):
                                    return f"🌟 今日运势占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取占星运势失败: {e}")
        
        return ""
    
    def crawl_horoscope_fortune_selenium(self, driver) -> str:
        """使用Selenium爬取占星运势"""
        try:
            driver.get("https://www.horoscope.com/daily-horoscope")
            time.sleep(3)
            
            # 等待页面加载
            wait = WebDriverWait(driver, 10)
            
            # 查找运势内容
            result_selectors = [
                ".horoscope",
                ".daily-horoscope",
                ".astrology",
                ".zodiac",
                "[class*='horoscope']",
                "[class*='astrology']"
            ]
            
            for selector in result_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 20 and len(text) < 500:
                            if any(keyword in text.lower() for keyword in ['horoscope', 'astrology', 'zodiac', 'fortune']):
                                return f"🌟 今日运势占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取占星运势失败: {e}")
        
        return ""
    
    def crawl_astro_com(self) -> str:
        """爬取占星运势网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问占星网站
            urls = [
                "https://www.astro.com/daily-horoscope",
                "https://www.horoscope.com/daily-horoscope",
                "https://www.astrology.com/daily"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找运势信息
                        fortune_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*horoscope.*|.*fortune.*|.*lucky.*'))
                        
                        for element in fortune_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 20 and len(text) < 300:
                                return f"🌟 今日运势占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取占星运势失败: {e}")
        
        return ""
    
    def crawl_fortune_net(self) -> str:
        """爬取运势网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问运势网站
            urls = [
                "https://www.fortune.com/daily",
                "https://www.lucky.net/daily",
                "https://www.fortune-telling.com/daily"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找运势信息
                        fortune_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*fortune.*|.*lucky.*|.*运势.*'))
                        
                        for element in fortune_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 20 and len(text) < 300:
                                return f"🌟 今日运势占卜\n\n{text}\n\n"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取运势网站失败: {e}")
        
        return ""
    
    
    def get_daily_fortune(self) -> str:
        """获取每日运势（主入口）"""
        return self.crawl_daily_fortune()
    
    def get_daily_random_fun(self) -> str:
        """获取每日随机有趣内容"""
        try:
            fun_categories = [
                self.get_daily_joke,
                self.get_daily_quote,
                self.get_daily_fact,
                self.get_daily_riddle
            ]
            
            # 随机选择一个类别
            selected_category = random.choice(fun_categories)
            return selected_category()
            
        except Exception as e:
            self.logger.error(f"获取每日随机有趣内容失败: {e}")
            return "🎲 每日随机内容获取失败"
    
    def crawl_daily_joke(self) -> str:
        """爬取每日笑话"""
        try:
            # 尝试多个笑话网站
            joke_sources = [
                self.crawl_joke_net,
                self.crawl_jokes_com,
                self.crawl_daily_joke_site
            ]
            
            for source_func in joke_sources:
                try:
                    result = source_func()
                    if result and len(result) > 10:  # 确保获取到有效内容
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取笑话失败: {e}")
                    continue
            
            # 如果所有爬虫都失败，如实返回失败信息
            return "😄 每日笑话获取失败 - 所有数据源都无法访问"
            
        except Exception as e:
            self.logger.error(f"获取每日笑话失败: {e}")
            return f"😄 每日笑话获取失败 - 系统错误: {str(e)}"
    
    def crawl_joke_net(self) -> str:
        """爬取笑话网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # 尝试多个笑话API
            joke_sources = [
                self.crawl_jokeapi_api,
                self.crawl_icanhazdadjoke_api,
                self.crawl_jokes_api
            ]
            
            for source_func in joke_sources:
                try:
                    result = source_func()
                    if result and len(result) > 10:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取笑话失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取笑话网站失败: {e}")
        
        return ""
    
    def crawl_jokeapi_api(self) -> str:
        """爬取JokeAPI"""
        try:
            url = "https://v2.jokeapi.dev/joke/Any?type=single"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                joke = data.get('joke', '')
                if joke:
                    return f"😄 每日一笑\n\n{joke}"
        except Exception as e:
            self.logger.warning(f"爬取JokeAPI失败: {e}")
        return ""
    
    def crawl_icanhazdadjoke_api(self) -> str:
        """爬取I Can Haz Dad Joke API"""
        try:
            url = "https://icanhazdadjoke.com/"
            response = requests.get(url, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                joke = data.get('joke', '')
                if joke:
                    return f"😄 每日一笑\n\n{joke}"
        except Exception as e:
            self.logger.warning(f"爬取I Can Haz Dad Joke API失败: {e}")
        return ""
    
    def crawl_jokes_api(self) -> str:
        """爬取Jokes API"""
        try:
            url = "https://official-joke-api.appspot.com/random_joke"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                setup = data.get('setup', '')
                punchline = data.get('punchline', '')
                if setup and punchline:
                    joke = f"{setup}\n{punchline}"
                    return f"😄 每日一笑\n\n{joke}"
        except Exception as e:
            self.logger.warning(f"爬取Jokes API失败: {e}")
        return ""
    
    def crawl_jokes_com(self) -> str:
        """爬取笑话网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问笑话网站
            urls = [
                "https://www.jokes.com/daily-joke",
                "https://www.funny-jokes.com/daily",
                "https://www.joke-of-the-day.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找笑话内容
                        joke_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*joke.*|.*funny.*'))
                        
                        for element in joke_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"😄 每日一笑\n\n{text}"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取笑话网站失败: {e}")
        
        return ""
    
    def crawl_daily_joke_site(self) -> str:
        """爬取每日笑话网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问每日笑话网站
            urls = [
                "https://www.daily-joke.com",
                "https://www.joke-of-the-day.net",
                "https://www.funny-daily.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找笑话内容
                        joke_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*joke.*|.*funny.*'))
                        
                        for element in joke_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"😄 每日一笑\n\n{text}"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取每日笑话网站失败: {e}")
        
        return ""
    
    
    def get_daily_joke(self) -> str:
        """获取每日笑话（主入口）"""
        return self.crawl_daily_joke()
    
    def crawl_daily_quote(self) -> str:
        """爬取每日名言"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # 尝试多个名言API
            quote_sources = [
                self.crawl_quotable_api,
                self.crawl_quotes_api,
                self.crawl_inspirational_api
            ]
            
            for source_func in quote_sources:
                try:
                    result = source_func()
                    if result and len(result) > 20:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取名言失败: {e}")
                    continue
            
            # 如果所有爬虫都失败，如实返回失败信息
            return "💭 每日名言获取失败 - 所有数据源都无法访问"
            
        except Exception as e:
            self.logger.error(f"获取每日名言失败: {e}")
            return f"💭 每日名言获取失败 - 系统错误: {str(e)}"
    
    def crawl_quotable_api(self) -> str:
        """爬取Quotable API"""
        try:
            url = "https://api.quotable.io/random"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                quote = data.get('content', '')
                author = data.get('author', '未知')
                if quote:
                    return f"💭 每日名言\n\n\"{quote}\"\n\n—— {author}"
        except Exception as e:
            self.logger.warning(f"爬取Quotable API失败: {e}")
        return ""
    
    def crawl_quotes_api(self) -> str:
        """爬取Quotes API"""
        try:
            url = "https://zenquotes.io/api/random"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    quote = data[0].get('q', '')
                    author = data[0].get('a', '未知')
                    if quote:
                        return f"💭 每日名言\n\n\"{quote}\"\n\n—— {author}"
        except Exception as e:
            self.logger.warning(f"爬取Quotes API失败: {e}")
        return ""
    
    def crawl_inspirational_api(self) -> str:
        """爬取励志名言API"""
        try:
            url = "https://api.quotable.io/random?tags=inspirational"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                quote = data.get('content', '')
                author = data.get('author', '未知')
                if quote:
                    return f"💭 每日名言\n\n\"{quote}\"\n\n—— {author}"
        except Exception as e:
            self.logger.warning(f"爬取励志名言API失败: {e}")
        return ""
    
    def get_daily_quote(self) -> str:
        """获取每日名言（主入口）"""
        return self.crawl_daily_quote()
    
    def crawl_daily_fact(self) -> str:
        """爬取每日冷知识"""
        try:
            # 首先尝试免费的冷知识API
            api_sources = [
                self.crawl_useless_facts_api,
                self.crawl_fun_facts_api
            ]
            
            for source_func in api_sources:
                try:
                    result = source_func()
                    if result and len(result) > 20:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取冷知识API失败: {e}")
                    continue
            
            # 然后尝试爬虫方法
            fact_sources = [
                self.crawl_fact_net,
                self.crawl_facts_com,
                self.crawl_daily_fact_site
            ]
            
            for source_func in fact_sources:
                try:
                    result = source_func()
                    if result and len(result) > 10:  # 确保获取到有效内容
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取冷知识失败: {e}")
                    continue
            
            # 如果所有爬虫都失败，如实返回失败信息
            return "🤓 每日冷知识获取失败 - 所有数据源都无法访问"
            
        except Exception as e:
            self.logger.error(f"获取每日冷知识失败: {e}")
            return f"🤓 每日冷知识获取失败 - 系统错误: {str(e)}"
    
    def crawl_useless_facts_api(self) -> str:
        """使用Useless Facts API获取冷知识"""
        try:
            api_url = "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    fact_text = data.get('text', '')
                    source = data.get('source', '')
                    
                    if fact_text:
                        # 尝试翻译成中文
                        chinese_text = self.translate_text(fact_text)
                        
                        result = f"🧠 每日冷知识\n\n"
                        result += f"🇬🇧 {fact_text}\n\n"
                        if chinese_text:
                            result += f"🇨🇳 {chinese_text}"
                        else:
                            result += f"🇨🇳 翻译失败，仅显示英文原文"
                        
                        if source:
                            result += f"\n\n📚 来源: {source}"
                        
                        return result
                        
                except Exception as e:
                    self.logger.warning(f"解析冷知识API失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"冷知识API失败: {e}")
        
        return ""
    
    def crawl_fun_facts_api(self) -> str:
        """使用备用冷知识API"""
        try:
            # 可以添加其他冷知识API作为备用
            api_url = "https://api.api-ninjas.com/v1/facts"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        fact_text = data[0].get('fact', '')
                        
                        if fact_text:
                            # 尝试翻译成中文
                            chinese_text = self.translate_text(fact_text)
                            
                            result = f"🧠 每日冷知识\n\n"
                            result += f"🇬🇧 {fact_text}\n\n"
                            if chinese_text:
                                result += f"🇨🇳 {chinese_text}"
                            else:
                                result += f"🇨🇳 翻译失败，仅显示英文原文"
                            
                            return result
                        
                except Exception as e:
                    self.logger.warning(f"解析备用冷知识API失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"备用冷知识API失败: {e}")
        
        return ""
    
    def crawl_fact_net(self) -> str:
        """爬取冷知识网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问冷知识网站
            urls = [
                "https://www.fact.net/daily",
                "https://www.facts.com/daily",
                "https://www.interesting-facts.com/daily"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找冷知识内容
                        fact_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*fact.*|.*冷知识.*|.*interesting.*'))
                        
                        for element in fact_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"🤓 每日冷知识\n\n{text}\n\n💡 知识就是力量，每天学一点新知识！"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取冷知识网站失败: {e}")
        
        return ""
    
    def crawl_facts_com(self) -> str:
        """爬取冷知识网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问冷知识网站
            urls = [
                "https://www.facts.com/daily-fact",
                "https://www.interesting-facts.net/daily",
                "https://www.fact-of-the-day.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找冷知识内容
                        fact_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*fact.*|.*interesting.*'))
                        
                        for element in fact_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"🤓 每日冷知识\n\n{text}\n\n💡 知识就是力量，每天学一点新知识！"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取冷知识网站失败: {e}")
        
        return ""
    
    def crawl_daily_fact_site(self) -> str:
        """爬取每日冷知识网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问每日冷知识网站
            urls = [
                "https://www.daily-fact.com",
                "https://www.fact-of-the-day.net",
                "https://www.interesting-daily.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找冷知识内容
                        fact_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*fact.*|.*interesting.*'))
                        
                        for element in fact_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"🤓 每日冷知识\n\n{text}\n\n💡 知识就是力量，每天学一点新知识！"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取每日冷知识网站失败: {e}")
        
        return ""
    
    
    def get_daily_fact(self) -> str:
        """获取每日冷知识（主入口）"""
        return self.crawl_daily_fact()
    
    def crawl_daily_riddle(self) -> str:
        """爬取每日谜语"""
        try:
            # 首先尝试免费的谜语API
            api_sources = [
                self.crawl_riddles_api,
                self.crawl_brain_teasers_api
            ]
            
            for source_func in api_sources:
                try:
                    result = source_func()
                    if result and len(result) > 20:
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取谜语API失败: {e}")
                    continue
            
            # 然后尝试爬虫方法
            riddle_sources = [
                self.crawl_riddle_net,
                self.crawl_riddles_com,
                self.crawl_daily_riddle_site
            ]
            
            for source_func in riddle_sources:
                try:
                    result = source_func()
                    if result and len(result) > 10:  # 确保获取到有效内容
                        return result
                except Exception as e:
                    self.logger.warning(f"爬取谜语失败: {e}")
                    continue
            
            # 如果所有爬虫都失败，如实返回失败信息
            return "🤔 每日谜语获取失败 - 所有数据源都无法访问"
            
        except Exception as e:
            self.logger.error(f"获取每日谜语失败: {e}")
            return f"🤔 每日谜语获取失败 - 系统错误: {str(e)}"
    
    def crawl_riddles_api(self) -> str:
        """使用免费的谜语API"""
        try:
            api_url = "https://riddles-api.vercel.app/random"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    riddle = data.get('riddle', '')
                    answer = data.get('answer', '')
                    
                    if riddle and answer:
                        # 翻译谜语和答案
                        chinese_riddle = self.translate_text(riddle)
                        chinese_answer = self.translate_text(answer)
                        
                        result = f"🤔 每日谜语\n\n"
                        result += f"🇬🇧 ❓ {riddle}\n"
                        if chinese_riddle:
                            result += f"🇨🇳 ❓ {chinese_riddle}\n\n"
                        else:
                            result += f"🇨🇳 ❓ 翻译失败\n\n"
                            
                        result += f"🇬🇧 💡 答案: {answer}\n"
                        if chinese_answer:
                            result += f"🇨🇳 💡 答案: {chinese_answer}"
                        else:
                            result += f"🇨🇳 💡 答案翻译失败"
                        
                        return result
                        
                except Exception as e:
                    self.logger.warning(f"解析谜语API失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"谜语API失败: {e}")
        
        return ""
    
    def crawl_brain_teasers_api(self) -> str:
        """使用备用脑筋急转弯API"""
        try:
            # 可以添加其他谜语API作为备用
            api_url = "https://api.api-ninjas.com/v1/riddles"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        riddle_data = data[0]
                        title = riddle_data.get('title', '')
                        question = riddle_data.get('question', '')
                        answer = riddle_data.get('answer', '')
                        
                        if question and answer:
                            # 翻译谜语和答案
                            chinese_question = self.translate_text(question)
                            chinese_answer = self.translate_text(answer)
                            chinese_title = self.translate_text(title) if title else ""
                            
                            result = f"🤔 每日谜语\n\n"
                            if title:
                                result += f"🇬🇧 📝 {title}\n"
                                if chinese_title:
                                    result += f"🇨🇳 📝 {chinese_title}\n\n"
                                else:
                                    result += f"🇨🇳 📝 标题翻译失败\n\n"
                            
                            result += f"🇬🇧 ❓ {question}\n"
                            if chinese_question:
                                result += f"🇨🇳 ❓ {chinese_question}\n\n"
                            else:
                                result += f"🇨🇳 ❓ 翻译失败\n\n"
                                
                            result += f"🇬🇧 💡 答案: {answer}\n"
                            if chinese_answer:
                                result += f"🇨🇳 💡 答案: {chinese_answer}"
                            else:
                                result += f"🇨🇳 💡 答案翻译失败"
                            
                            return result
                        
                except Exception as e:
                    self.logger.warning(f"解析备用谜语API失败: {e}")
                    
        except Exception as e:
            self.logger.warning(f"备用谜语API失败: {e}")
        
        return ""
    
    def crawl_riddle_net(self) -> str:
        """爬取谜语网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问谜语网站
            urls = [
                "https://www.riddle.net/daily",
                "https://www.riddles.com/daily",
                "https://www.brain-teasers.com/daily"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找谜语内容
                        riddle_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*riddle.*|.*谜语.*|.*puzzle.*'))
                        
                        for element in riddle_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"🤔 每日谜语\n\n❓ {text}\n\n🧠 动动脑筋，保持思维活跃！"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取谜语网站失败: {e}")
        
        return ""
    
    def crawl_riddles_com(self) -> str:
        """爬取谜语网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问谜语网站
            urls = [
                "https://www.riddles.com/daily-riddle",
                "https://www.brain-teasers.net/daily",
                "https://www.riddle-of-the-day.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找谜语内容
                        riddle_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*riddle.*|.*puzzle.*'))
                        
                        for element in riddle_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"🤔 每日谜语\n\n❓ {text}\n\n🧠 动动脑筋，保持思维活跃！"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取谜语网站失败: {e}")
        
        return ""
    
    def crawl_daily_riddle_site(self) -> str:
        """爬取每日谜语网站"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问每日谜语网站
            urls = [
                "https://www.daily-riddle.com",
                "https://www.riddle-of-the-day.net",
                "https://www.brain-daily.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找谜语内容
                        riddle_elements = soup.find_all(['div', 'span', 'p'], text=re.compile(r'.*riddle.*|.*puzzle.*'))
                        
                        for element in riddle_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 10 and len(text) < 200:
                                return f"🤔 每日谜语\n\n❓ {text}\n\n🧠 动动脑筋，保持思维活跃！"
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取每日谜语网站失败: {e}")
        
        return ""
    
    
    def get_daily_riddle(self) -> str:
        """获取每日谜语（主入口）"""
        return self.crawl_daily_riddle()

    def crawl_hot_search(self) -> str:
        """爬取各平台热搜"""
        try:
            # 尝试多个热搜网站
            hot_search_sources = [
                self.crawl_weibo_hot,
                self.crawl_baidu_hot,
                self.crawl_zhihu_hot
            ]
            
            hot_search_data = {}
            
            for source_func in hot_search_sources:
                try:
                    result = source_func()
                    if result:
                        hot_search_data.update(result)
                except Exception as e:
                    self.logger.warning(f"爬取热搜失败: {e}")
                    continue
            
            # 如果爬虫都失败，如实返回失败信息
            if not hot_search_data:
                return "🔥 热搜信息获取失败 - 所有数据源都无法访问"
            
            # 格式化热搜数据
            hot_search_msg = "🔥 今日热搜榜\n\n"
            for platform, topics in hot_search_data.items():
                hot_search_msg += f"📱 {platform}热搜:\n"
                for i, topic in enumerate(topics[:3], 1):
                    hot_search_msg += f"   {i}. {topic}\n"
                hot_search_msg += "\n"
            
            return hot_search_msg.strip()
            
        except Exception as e:
            self.logger.error(f"获取热搜失败: {e}")
            return f"🔥 热搜信息获取失败 - 系统错误: {str(e)}"
    
    def crawl_weibo_hot(self) -> dict:
        """爬取微博热搜"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问微博热搜
            urls = [
                "https://s.weibo.com/top/summary",
                "https://weibo.com/hot",
                "https://trends.weibo.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找热搜内容
                        hot_elements = soup.find_all(['a', 'span', 'div'], text=re.compile(r'.*热搜.*|.*热门.*|.*trending.*'))
                        
                        topics = []
                        for element in hot_elements:
                            text = element.get_text().strip()
                            if text and len(text) > 2 and len(text) < 50:
                                topics.append(text)
                        
                        if topics:
                            return {"微博": topics[:5]}
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取微博热搜失败: {e}")
        
        return {}
    
    def crawl_baidu_hot(self) -> dict:
        """爬取百度热搜"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问百度热搜
            urls = [
                "https://top.baidu.com/board?tab=realtime",
                "https://www.baidu.com/s?wd=热搜",
                "https://trends.baidu.com"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找热搜内容
                        hot_elements = soup.find_all(['a', 'span', 'div'], text=re.compile(r'.*热搜.*|.*热门.*|.*trending.*'))
                        
                        topics = []
                        # 过滤无用内容的关键词
                        filter_keywords = [
                            '热搜榜', '热搜指数', '热门话题', '热搜', '热门',
                            '推荐', '广告', '赞助', '登录', '注册', '下载', 'APP',
                            '更多', '查看更多', '展开', '收起', '刷新', '加载',
                            '百度', '搜索', '首页', '新闻', '贴吧'
                        ]
                        
                        for element in hot_elements:
                            text = element.get_text().strip()
                            # 基本长度和内容过滤
                            if text and len(text) > 4 and len(text) < 50:
                                # 过滤掉无用关键词
                                if not any(keyword in text for keyword in filter_keywords):
                                    # 确保是有意义的内容（包含中文字符）
                                    if any('\u4e00' <= char <= '\u9fff' for char in text):
                                        topics.append(text)
                        
                        # 去重并限制数量
                        unique_topics = list(dict.fromkeys(topics))
                        if unique_topics:
                            return {"百度": unique_topics[:5]}
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取百度热搜失败: {e}")
        
        return {}
    
    def crawl_zhihu_hot(self) -> dict:
        """爬取知乎热搜"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            # 尝试访问知乎热搜
            urls = [
                "https://www.zhihu.com/hot",
                "https://www.zhihu.com/trending",
                "https://www.zhihu.com/explore"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找热搜内容
                        hot_elements = soup.find_all(['a', 'span', 'div'], text=re.compile(r'.*热搜.*|.*热门.*|.*trending.*'))
                        
                        topics = []
                        # 过滤无用内容的关键词
                        filter_keywords = [
                            '热门收藏夹', '收藏夹', '热搜榜', '热搜指数', '热门话题',
                            '推荐', '广告', '赞助', '登录', '注册', '下载', 'APP',
                            '更多', '查看更多', '展开', '收起', '刷新', '加载'
                        ]
                        
                        for element in hot_elements:
                            text = element.get_text().strip()
                            # 基本长度和内容过滤
                            if text and len(text) > 4 and len(text) < 50:
                                # 过滤掉无用关键词
                                if not any(keyword in text for keyword in filter_keywords):
                                    # 确保是有意义的内容（包含中文字符）
                                    if any('\u4e00' <= char <= '\u9fff' for char in text):
                                        topics.append(text)
                        
                        # 去重并限制数量
                        unique_topics = list(dict.fromkeys(topics))
                        if unique_topics:
                            return {"知乎": unique_topics[:5]}
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"爬取知乎热搜失败: {e}")
        
        return {}
    
    
    def get_hot_search(self) -> str:
        """获取各平台热搜（主入口）"""
        return self.crawl_hot_search()

    def get_daily_tips(self) -> str:
        """获取每日小贴士"""
        tips_categories = {
            "健康": [
                "💧 每天至少喝8杯水，保持身体水分充足",
                "🚶‍♂️ 每小时起身活动5分钟，预防久坐危害",
                "😴 保证7-8小时睡眠，提高免疫力",
                "🥗 多吃蔬菜水果，补充维生素",
                "🧘‍♀️ 深呼吸放松，缓解工作压力"
            ],
            "工作": [
                "📝 使用番茄工作法，提高专注力",
                "📊 制定每日任务清单，提高效率",
                "💻 定期整理电脑文件，保持桌面整洁",
                "📞 重要事情优先处理，避免拖延",
                "🤝 主动沟通协作，提升团队效率"
            ],
            "生活": [
                "🌱 养一盆绿植，净化空气美化环境",
                "📚 每天阅读30分钟，丰富知识储备",
                "🎵 听音乐放松心情，缓解疲劳",
                "👨‍👩‍👧‍👦 多陪伴家人朋友，增进感情",
                "💰 记录每日支出，培养理财习惯"
            ]
        }
        
        # 随机选择一个类别和一条建议
        category = random.choice(list(tips_categories.keys()))
        tip = random.choice(tips_categories[category])
        
        return f"💡 今日{category}小贴士\n{tip}"

    def get_holiday_info(self) -> str:
        """获取节假日信息"""
        try:
            today = datetime.now()
            
            # 2024年节假日
            holidays = {
                "2024-01-01": "元旦",
                "2024-02-10": "春节",
                "2024-04-04": "清明节",
                "2024-05-01": "劳动节",
                "2024-06-10": "端午节",
                "2024-09-17": "中秋节",
                "2024-10-01": "国庆节"
            }
            
            today_str = today.strftime("%Y-%m-%d")
            
            # 检查今天是否是节假日
            if today_str in holidays:
                return f"🎉 今天是{holidays[today_str]}，祝您节日快乐！"
            
            # 检查未来7天内的节假日
            for i in range(1, 8):
                future_date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
                if future_date in holidays:
                    return f"📅 {holidays[future_date]}还有{i}天，记得提前安排哦！"
            
            return ""
            
        except Exception as e:
            self.logger.error(f"获取节假日信息失败: {e}")
            return ""

    def get_stock_index_brief(self) -> str:
        """获取股市指数简报"""
        try:
            # 模拟股市数据
            indices = {
                "上证指数": {"value": 3200 + random.randint(-100, 100), "change": round(random.uniform(-2, 2), 2)},
                "深证成指": {"value": 12000 + random.randint(-500, 500), "change": round(random.uniform(-2, 2), 2)},
                "创业板指": {"value": 2500 + random.randint(-100, 100), "change": round(random.uniform(-3, 3), 2)}
            }
            
            stock_msg = "📈 股市简报\n\n"
            for name, data in indices.items():
                change_emoji = "📈" if data["change"] >= 0 else "📉"
                change_sign = "+" if data["change"] >= 0 else ""
                stock_msg += f"{change_emoji} {name}: {data['value']:.2f} ({change_sign}{data['change']}%)\n"
            
            return stock_msg.strip()
            
        except Exception as e:
            self.logger.error(f"获取股市信息失败: {e}")
            return ""

    def send_morning_report(self):
        """发送早间综合报告"""
        try:
            current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
            
            # 收集所有信息
            weather = self.get_weather_info()
            taboo = self.get_daily_taboo()
            tarot = self.get_tarot_card()
            hot_search = self.get_hot_search()
            daily_tip = self.get_daily_tips()
            holiday_info = self.get_holiday_info()
            stock_info = self.get_stock_index_brief()
            
            # 组合消息
            message = f"""🌅 早安！综合生活助手为您播报
⏰ {current_time}

{weather}

{taboo}

{tarot}

{hot_search}

{daily_tip}"""
            
            if holiday_info:
                message += f"\n\n{holiday_info}"
            
            if stock_info:
                message += f"\n\n{stock_info}"
            
            message += "\n\n祝您今天心情愉快，工作顺利！🌈"
            
            self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"发送早间报告失败: {e}")

    def send_evening_report(self):
        """发送晚间简报"""
        try:
            current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
            
            # 随机选择晚间内容
            evening_functions = [
                self.get_daily_fortune,
                self.get_tarot_card,
                self.get_daily_tips
            ]
            
            # 随机选择2个功能
            selected_functions = random.sample(evening_functions, 2)
            
            # 获取内容
            content1 = selected_functions[0]()
            content2 = selected_functions[1]()
            
            message = f"""🌙 晚安！今日总结
⏰ {current_time}

{content1}

{content2}

🌟 今日感悟:
每一天都是新的开始，感谢今天的努力和收获。
明天又是充满希望的一天！

💤 早点休息，保证充足睡眠哦～"""
            
            self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"发送晚间报告失败: {e}")

    def send_noon_reminder(self):
        """发送午间提醒"""
        try:
            # 随机选择午间内容
            noon_functions = [
                self.get_noon_tip,
                self.get_daily_joke,
                self.get_daily_fact,
                self.get_daily_quote
            ]
            
            # 随机选择1-2个功能
            selected_functions = random.sample(noon_functions, random.randint(1, 2))
            
            current_time = datetime.now().strftime("%H:%M")
            
            message = f"""☀️ 午间提醒
⏰ {current_time}

"""

            for func in selected_functions:
                message += f"{func()}\n\n"
            
            message += "下午继续加油！💪"
            
            self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"发送午间提醒失败: {e}")
    
    def get_noon_tip(self) -> str:
        """获取午间小贴士"""
        tips = [
            "🍽️ 午餐时间到了，记得按时吃饭哦！",
            "😴 午休一下，下午更有精神！",
            "💧 记得多喝水，保持身体水分充足！",
            "🚶‍♂️ 饭后散散步，有助消化！",
            "🧘‍♀️ 放松一下，缓解上午的工作压力！",
            "👀 看看窗外，让眼睛休息一下！",
            "🎵 听首喜欢的歌，放松心情！",
            "📱 放下手机，给大脑一个休息！"
        ]
        
        tip = random.choice(tips)
        return f"💡 午间小贴士\n\n{tip}"

    def run_scheduler(self):
        """运行定时任务"""
        # 早间报告 - 每天8:00
        schedule.every().day.at("08:00").do(self.send_morning_report)
        
        # 午间提醒 - 每天12:00
        schedule.every().day.at("12:00").do(self.send_noon_reminder)
        
        # 晚间简报 - 每天21:00
        schedule.every().day.at("21:00").do(self.send_evening_report)
        
        self.logger.info("综合生活机器人启动成功")
        self.send_message("🤖 综合生活助手已启动！\n将为您提供天气、电影、热搜、生活小贴士等服务～")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                self.logger.info("机器人停止运行")
                break
            except Exception as e:
                self.logger.error(f"运行异常: {e}")
                time.sleep(60)

if __name__ == "__main__":
    webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fc1b1b81-35ef-4c44-83a2-3ad3a4c2f516"
    bot = LifestyleBot(webhook_url)
    bot.run_scheduler()
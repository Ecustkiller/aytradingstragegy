"""
翻译功能模块
提供多源翻译服务
"""
import json
import urllib.parse
import logging
from typing import List, Tuple


class LifestyleTranslator:
    """翻译器类"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
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
            encoded_text = urllib.parse.quote(text)
            
            # Google Translate免费接口
            api_url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target_lang}&dt=t&q={encoded_text}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            import requests
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
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
            encoded_text = urllib.parse.quote(text)
            
            api_url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair=en|{target_lang}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            import requests
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
    
    def select_best_translation(self, original_text: str, translations: List[Tuple[str, str]]) -> str:
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
                english_words = sum(1 for char in translation if char.isalpha() and ord(char) < 128)
                if english_words == 0:
                    score += 2
                elif english_words < len(translation) * 0.1:
                    score += 1
                
                # 4. 语义完整性检查
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


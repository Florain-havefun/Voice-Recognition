"""
文本后处理器

负责对语音识别结果进行后处理，包括标点恢复、中英文混合处理等。
"""

import re
from typing import Optional, List, Dict, Any


class TextPostProcessor:
    """文本后处理器类"""

    def __init__(self, language: str = "cn"):
        """初始化文本后处理器

        Args:
            language: 语言代码 'cn'(中文), 'en'(英文), 'cn-en'(中英文混合)
        """
        self.language = language
        self.punctuation_patterns = self._init_punctuation_patterns()

        print(f"文本后处理器初始化: 语言={language}")

    def _init_punctuation_patterns(self) -> Dict[str, List[str]]:
        """初始化标点符号模式

        Returns:
            Dict[str, List[str]]: 语言到标点符号列表的映射
        """
        patterns = {
            "cn": [
                # 句末标点
                (r"(?<![.。!?！？])$", "。"),  # 句末添加句号
                # 疑问词后加问号
                (r"(吗|呢|吧|啊|呀)(?![.?。!？])$", r"\1？"),
                # 感叹词后加叹号
                (r"(真|太|非常|极其|特别)(.+?)(?![.!。！？])$", r"\1\2！"),
            ],
            "en": [
                # 句末添加句点
                (r"(?<![.!?])$", "."),
                # 疑问句
                (r"^(what|when|where|why|how|who|is|are|do|does|did|can|could|will|would|should)(.+?)(?![.!?])$", r"\1\2?"),
                # 感叹句
                (r"^(wow|oh|ah|hey|great|awesome|amazing)(.+?)(?![.!?])$", r"\1\2!"),
            ],
            "cn-en": [
                # 混合模式的规则
                (r"(?<![.。!?！？])$", "。"),  # 默认中文句号
                # 中英文标点转换
                (r",", "，"),
                (r"\.(?!\d)", "。"),
                (r"\?", "？"),
                (r"!", "！"),
            ]
        }
        return patterns

    def add_punctuation(self, text: str) -> str:
        """为文本添加标点符号

        Args:
            text: 原始文本

        Returns:
            str: 添加标点后的文本
        """
        if not text or not text.strip():
            return text

        text = text.strip()
        patterns = self.punctuation_patterns.get(self.language, [])

        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def fix_spacing(self, text: str) -> str:
        """修复中英文混合文本的间距问题

        Args:
            text: 原始文本

        Returns:
            str: 修复间距后的文本
        """
        if not text:
            return text

        # 在中文字符和英文字符之间添加空格
        # 中文后接英文
        text = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r'\1 \2', text)
        # 英文后接中文
        text = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r'\1 \2', text)

        # 移除多余的空格
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def extract_keywords(self, text: str, keyword_list: Optional[List[str]] = None) -> List[str]:
        """从文本中提取关键词

        Args:
            text: 原始文本
            keyword_list: 关键词列表，如果为None则返回所有单词

        Returns:
            List[str]: 提取的关键词
        """
        if not text:
            return []

        # 根据语言分割单词
        if self.language == "cn":
            # 中文：按字符分割（简单实现）
            words = list(text)
        elif self.language == "en":
            # 英文：按非字母字符分割
            words = re.findall(r'\b\w+\b', text, flags=re.IGNORECASE)
        else:  # cn-en
            # 混合：先提取英文单词，再添加中文字符
            en_words = re.findall(r'\b\w+\b', text, flags=re.IGNORECASE)
            ch_chars = re.findall(r'[\u4e00-\u9fff]', text)
            words = en_words + ch_chars

        if keyword_list is None:
            return words

        # 过滤关键词
        keywords = []
        for word in words:
            if word.lower() in [kw.lower() for kw in keyword_list]:
                keywords.append(word)

        return keywords

    def normalize_text(self, text: str) -> str:
        """标准化文本

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        if not text:
            return ""

        # 移除多余空白
        text = ' '.join(text.split())

        # 根据语言进行标准化
        if self.language == "cn":
            # 中文：全角标点
            text = text.replace(',', '，')
            text = text.replace('.', '。')
            text = text.replace('?', '？')
            text = text.replace('!', '！')
            text = text.replace(':', '：')
            text = text.replace(';', '；')
        elif self.language == "en":
            # 英文：确保句首大写
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.capitalize() for s in sentences if s]
            text = ' '.join(sentences)
        else:  # cn-en
            # 混合：修复间距和标点
            text = self.fix_spacing(text)
            text = self.add_punctuation(text)

        return text

    def detect_language(self, text: str) -> Dict[str, float]:
        """检测文本的语言比例

        Args:
            text: 原始文本

        Returns:
            Dict[str, float]: 语言到比例的映射
        """
        if not text:
            return {"cn": 0.0, "en": 0.0, "other": 0.0}

        total_chars = len(text)

        # 统计中文字符
        ch_chars = re.findall(r'[\u4e00-\u9fff]', text)
        ch_count = len(ch_chars)

        # 统计英文字母
        en_chars = re.findall(r'[a-zA-Z]', text)
        en_count = len(en_chars)

        # 其他字符
        other_count = total_chars - ch_count - en_count

        return {
            "cn": ch_count / total_chars if total_chars > 0 else 0.0,
            "en": en_count / total_chars if total_chars > 0 else 0.0,
            "other": other_count / total_chars if total_chars > 0 else 0.0
        }

    def process(self, text: str, add_punctuation: bool = True,
                normalize: bool = True, fix_spacing: bool = True) -> str:
        """处理文本

        Args:
            text: 原始文本
            add_punctuation: 是否添加标点
            normalize: 是否标准化
            fix_spacing: 是否修复间距

        Returns:
            str: 处理后的文本
        """
        if not text:
            return ""

        result = text

        if fix_spacing and self.language in ["cn-en", "en"]:
            result = self.fix_spacing(result)

        if add_punctuation:
            result = self.add_punctuation(result)

        if normalize:
            result = self.normalize_text(result)

        return result

    def get_language_suggestion(self, text: str) -> str:
        """根据文本内容建议语言

        Args:
            text: 原始文本

        Returns:
            str: 建议的语言代码 'cn', 'en', 或 'cn-en'
        """
        lang_stats = self.detect_language(text)

        if lang_stats["cn"] > 0.7:
            return "cn"
        elif lang_stats["en"] > 0.7:
            return "en"
        else:
            return "cn-en"


# 测试代码
if __name__ == "__main__":
    def test_text_processor():
        print("测试文本后处理器...")

        test_cases = [
            ("你好世界", "cn"),
            ("hello world", "en"),
            ("你好hello世界world", "cn-en"),
        ]

        for text, lang in test_cases:
            print(f"\n测试文本: '{text}' (语言: {lang})")

            processor = TextPostProcessor(language=lang)

            # 语言检测
            lang_stats = processor.detect_language(text)
            print(f"  语言检测: {lang_stats}")

            # 处理文本
            processed = processor.process(text)
            print(f"  处理后: '{processed}'")

            # 提取关键词
            keywords = processor.extract_keywords(text)
            print(f"  关键词: {keywords}")

            # 语言建议
            suggestion = processor.get_language_suggestion(text)
            print(f"  语言建议: {suggestion}")

    test_text_processor()
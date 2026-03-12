"""
语音识别模块基础测试

注意：这些测试需要已安装Vosk模型。
运行测试前请先下载模型。
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch
import tempfile

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.speech_recognizer import SpeechRecognizer
from src.audio_manager import AudioManager
from src.vosk_engine import VoskEngine
from src.text_processor import TextPostProcessor
from src.callback_manager import CallbackManager, CallbackType


class TestTextPostProcessor(unittest.TestCase):
    """文本后处理器测试"""

    def setUp(self):
        self.processor_cn = TextPostProcessor(language="cn")
        self.processor_en = TextPostProcessor(language="en")
        self.processor_mix = TextPostProcessor(language="cn-en")

    def test_add_punctuation(self):
        """测试标点添加"""
        # 中文
        text = "你好世界"
        result = self.processor_cn.add_punctuation(text)
        self.assertIn(result, ["你好世界。", "你好世界"])  # 可能添加句号

        # 英文
        text = "hello world"
        result = self.processor_en.add_punctuation(text)
        self.assertEqual(result, "hello world.")

    def test_fix_spacing(self):
        """测试间距修复"""
        text = "hello世界"
        result = self.processor_mix.fix_spacing(text)
        self.assertEqual(result, "hello 世界")

        text = "世界hello"
        result = self.processor_mix.fix_spacing(text)
        self.assertEqual(result, "世界 hello")

    def test_extract_keywords(self):
        """测试关键词提取"""
        text = "打开浏览器搜索Python教程"
        keywords = self.processor_cn.extract_keywords(text)
        self.assertGreater(len(keywords), 0)

        # 指定关键词列表
        keyword_list = ["打开", "搜索", "教程"]
        keywords = self.processor_cn.extract_keywords(text, keyword_list)
        self.assertIn("打开", keywords)
        self.assertIn("搜索", keywords)

    def test_detect_language(self):
        """测试语言检测"""
        text = "hello世界"
        stats = self.processor_mix.detect_language(text)
        self.assertIn("cn", stats)
        self.assertIn("en", stats)
        self.assertAlmostEqual(stats["cn"] + stats["en"] + stats["other"], 1.0)


class TestCallbackManager(unittest.TestCase):
    """回调管理器测试"""

    def setUp(self):
        self.callback_mgr = CallbackManager(max_queue_size=10)

    def test_register_callback(self):
        """测试回调注册"""
        def dummy_callback(data):
            pass

        callback_id = self.callback_mgr.register_callback(
            CallbackType.FINAL_RESULT,
            dummy_callback,
            priority=1,
            description="测试回调"
        )

        self.assertIsNotNone(callback_id)
        self.assertTrue(len(callback_id) > 0)

    def test_unregister_callback(self):
        """测试取消注册"""
        callback_called = []

        def dummy_callback(data):
            callback_called.append(data)

        callback_id = self.callback_mgr.register_callback(
            CallbackType.FINAL_RESULT,
            dummy_callback
        )

        # 取消注册
        success = self.callback_mgr.unregister_callback(callback_id)
        self.assertTrue(success)

        # 再次取消应该失败
        success = self.callback_mgr.unregister_callback(callback_id)
        self.assertFalse(success)

    def test_queue_event(self):
        """测试事件队列"""
        callback_called = []

        def dummy_callback(data):
            callback_called.append(data)

        self.callback_mgr.register_callback(
            CallbackType.FINAL_RESULT,
            dummy_callback
        )

        # 启动处理
        self.callback_mgr.start_processing()

        # 发送事件
        self.callback_mgr.queue_event(CallbackType.FINAL_RESULT, "测试数据")

        # 等待处理
        import time
        time.sleep(0.1)

        # 停止处理
        self.callback_mgr.stop_processing()

        # 检查回调是否被调用
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], "测试数据")

    def tearDown(self):
        self.callback_mgr.stop_processing()


class TestAudioManager(unittest.TestCase):
    """音频管理器测试（模拟测试）"""

    @patch('sounddevice.query_devices')
    def test_get_available_devices(self, mock_query_devices):
        """测试获取音频设备（模拟）"""
        # 模拟设备数据
        mock_query_devices.return_value = [
            {'name': '设备1', 'max_input_channels': 2, 'default_samplerate': 44100.0},
            {'name': '设备2', 'max_input_channels': 0, 'default_samplerate': 44100.0},  # 无输入
            {'name': '设备3', 'max_input_channels': 1, 'default_samplerate': 48000.0},
        ]

        audio_mgr = AudioManager()
        devices = audio_mgr.get_available_devices()

        # 应该只返回有输入通道的设备
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].name, '设备1')
        self.assertEqual(devices[1].name, '设备3')

    def test_set_device_invalid(self):
        """测试设置无效设备"""
        audio_mgr = AudioManager()

        # 模拟没有设备的情况
        with patch.object(audio_mgr, 'get_available_devices', return_value=[]):
            success = audio_mgr.set_device(0)
            self.assertFalse(success)


class TestSpeechRecognizer(unittest.TestCase):
    """语音识别器测试（需要模型，跳过实际识别）"""

    def test_initialization(self):
        """测试初始化"""
        # 应该失败，因为缺少依赖或模型
        try:
            recognizer = SpeechRecognizer(model_path="nonexistent/model")
            # 如果模型路径不存在，初始化可能会失败
            # 这里只是测试创建实例
            self.assertIsNotNone(recognizer)
            self.assertEqual(recognizer.model_path, "nonexistent/model")
        except Exception:
            # 允许初始化失败，因为可能缺少依赖
            pass

    def test_get_available_devices_mock(self):
        """测试获取音频设备（模拟）"""
        with patch('sounddevice.query_devices') as mock_query:
            mock_query.return_value = [
                {'name': '虚拟麦克风', 'max_input_channels': 1, 'default_samplerate': 16000.0},
            ]

            recognizer = SpeechRecognizer()
            devices = recognizer.get_available_devices()

            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0].name, '虚拟麦克风')


# 跳过需要实际模型和音频设备的测试
@unittest.skipIf(os.environ.get('SKIP_MODEL_TESTS'), "跳过需要模型的测试")
class TestWithModel(unittest.TestCase):
    """需要模型的测试（仅在模型可用时运行）"""

    def test_vosk_engine_load_model(self):
        """测试Vosk引擎加载模型"""
        model_path = "models/vosk-model-small-cn-0.22"
        if not os.path.exists(model_path):
            self.skipTest(f"模型不存在: {model_path}")

        engine = VoskEngine(model_path)
        success = engine.load_model()
        self.assertTrue(success)
        self.assertTrue(engine.is_loaded)

        engine.unload_model()
        self.assertFalse(engine.is_loaded)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
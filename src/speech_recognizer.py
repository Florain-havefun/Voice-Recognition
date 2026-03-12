"""
语音识别模块主API接口

提供简洁的API供其他模块调用，实现实时离线语音识别。
"""

import os
import threading
import queue
import json
import time
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import numpy as np
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False
    print("警告: 缺少依赖包，请运行: pip install vosk sounddevice numpy")


class LanguageCode(Enum):
    """支持的语言代码"""
    CHINESE = "cn"
    ENGLISH = "en"
    CHINESE_ENGLISH = "cn-en"


class RecognitionMode(Enum):
    """识别模式"""
    STREAMING = "streaming"      # 实时流式识别
    SINGLE = "single"           # 单次录音识别


@dataclass
class AudioDevice:
    """音频设备信息"""
    index: int
    name: str
    input_channels: int
    default_samplerate: float


class SpeechRecognizer:
    """语音识别器主类

    提供实时离线语音识别功能，支持中文和英文混合识别。

    Attributes:
        model_path: Vosk模型路径
        language: 识别语言
        sample_rate: 音频采样率
        is_listening: 是否正在监听
    """

    def __init__(self,
                 model_path: str = "models/vosk-model-small-cn-0.22",
                 language: str = "cn",
                 sample_rate: int = 16000):
        """初始化语音识别器

        Args:
            model_path: Vosk模型路径，默认为中文小型模型
            language: 语言代码，可选 'cn'(中文), 'en'(英文), 'cn-en'(中英文混合)
            sample_rate: 音频采样率，默认16000Hz

        Raises:
            ImportError: 缺少必要的依赖包
            FileNotFoundError: 模型文件不存在
        """
        if not HAS_DEPENDENCIES:
            raise ImportError(
                "缺少必要的依赖包。请运行: pip install vosk sounddevice numpy pyaudio"
            )

        self.model_path = model_path
        self.language = language
        self.sample_rate = sample_rate

        # 状态变量
        self.is_listening = False
        self.is_initialized = False
        self.current_device_index = None

        # 组件
        self.model = None
        self.recognizer = None
        self.audio_queue = None
        self.audio_stream = None

        # 线程
        self.recognition_thread = None
        self.audio_thread = None

        # 回调函数
        self.callback = None
        self.partial_callback = None

        # 初始化日志
        print(f"语音识别器初始化:")
        print(f"  模型路径: {model_path}")
        print(f"  语言: {language}")
        print(f"  采样率: {sample_rate}Hz")

    def initialize(self) -> bool:
        """初始化识别器组件

        Returns:
            bool: 初始化是否成功
        """
        if self.is_initialized:
            return True

        try:
            # 1. 检查模型路径
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"模型路径不存在: {self.model_path}\n"
                    f"请下载Vosk模型并放置到正确位置。"
                )

            # 2. 加载模型
            print(f"正在加载模型: {self.model_path}")
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)  # 获取单词时间戳

            # 3. 初始化队列
            self.audio_queue = queue.Queue(maxsize=100)

            self.is_initialized = True
            print("模型加载成功!")
            return True

        except Exception as e:
            print(f"初始化失败: {e}")
            return False

    def get_available_devices(self) -> List[AudioDevice]:
        """获取可用音频输入设备列表

        Returns:
            List[AudioDevice]: 音频设备列表
        """
        devices = []
        try:
            system_devices = sd.query_devices()
            for i, device in enumerate(system_devices):
                if device['max_input_channels'] > 0:
                    audio_device = AudioDevice(
                        index=i,
                        name=device['name'],
                        input_channels=device['max_input_channels'],
                        default_samplerate=device['default_samplerate']
                    )
                    devices.append(audio_device)
        except Exception as e:
            print(f"获取音频设备失败: {e}")

        return devices

    def set_device(self, device_index: int) -> bool:
        """设置音频输入设备

        Args:
            device_index: 音频设备索引

        Returns:
            bool: 设置是否成功
        """
        devices = self.get_available_devices()
        device_indices = [d.index for d in devices]

        if device_index not in device_indices:
            print(f"错误: 设备索引 {device_index} 不可用")
            print(f"可用设备索引: {device_indices}")
            return False

        self.current_device_index = device_index
        print(f"已设置音频设备: {device_index}")
        return True

    def set_language(self, language: str) -> bool:
        """设置识别语言

        Args:
            language: 语言代码 'cn', 'en', 或 'cn-en'

        Returns:
            bool: 设置是否成功
        """
        valid_languages = ["cn", "en", "cn-en"]
        if language not in valid_languages:
            print(f"错误: 不支持的语言代码 '{language}'")
            print(f"支持的语言: {valid_languages}")
            return False

        self.language = language
        print(f"已设置识别语言: {language}")

        # 注意: 切换语言需要重新加载模型
        # 目前实现使用单一模型，中英文混合模型需要特殊处理
        return True

    def _audio_callback(self, indata, frames, time_info, status):
        """音频回调函数，将音频数据放入队列"""
        if status:
            print(f"音频状态: {status}")

        if self.is_listening:
            # 将音频数据转换为Vosk需要的格式
            audio_data = indata.copy()
            try:
                self.audio_queue.put(audio_data, block=False)
            except queue.Full:
                # 队列满时丢弃最旧的数据
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put(audio_data, block=False)
                except queue.Empty:
                    pass

    def _recognition_worker(self):
        """识别工作线程"""
        print("识别线程启动")

        while self.is_listening:
            try:
                # 从队列获取音频数据
                audio_data = self.audio_queue.get(timeout=0.1)

                # 转换为字节格式
                audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()

                # 发送到识别器
                if self.recognizer.AcceptWaveform(audio_bytes):
                    # 最终结果
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text and self.callback:
                        # 在独立线程中调用回调，避免阻塞识别线程
                        threading.Thread(
                            target=self.callback,
                            args=(text,),
                            daemon=True
                        ).start()
                else:
                    # 部分结果
                    partial = json.loads(self.recognizer.PartialResult())
                    text = partial.get('partial', '').strip()
                    if text and self.partial_callback:
                        threading.Thread(
                            target=self.partial_callback,
                            args=(text,),
                            daemon=True
                        ).start()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"识别错误: {e}")
                break

        print("识别线程结束")

    def start_listening(self,
                       callback: Optional[Callable[[str], None]] = None,
                       partial_callback: Optional[Callable[[str], None]] = None,
                       device_index: Optional[int] = None) -> bool:
        """开始实时语音识别

        Args:
            callback: 识别完成回调函数，接收识别的文本
            partial_callback: 部分结果回调函数，接收部分识别的文本
            device_index: 音频设备索引，如果为None则使用默认设备

        Returns:
            bool: 是否成功启动
        """
        if self.is_listening:
            print("警告: 已经在监听状态")
            return False

        # 初始化组件
        if not self.initialize():
            return False

        # 设置回调函数
        self.callback = callback
        self.partial_callback = partial_callback

        # 设置音频设备
        if device_index is not None:
            if not self.set_device(device_index):
                print("使用默认音频设备")
        else:
            self.current_device_index = None  # 使用默认设备

        # 启动识别线程
        self.is_listening = True
        self.recognition_thread = threading.Thread(
            target=self._recognition_worker,
            daemon=True
        )
        self.recognition_thread.start()

        # 启动音频流
        try:
            channels = 1  # 单声道
            dtype = 'float32'
            blocksize = 8000  # 每次处理的采样点数

            print(f"启动音频流...")
            print(f"设备: {self.current_device_index or '默认'}")
            print(f"采样率: {self.sample_rate}Hz")
            print(f"按 Ctrl+C 停止监听")

            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=channels,
                dtype=dtype,
                blocksize=blocksize,
                device=self.current_device_index,
                callback=self._audio_callback
            )
            self.audio_stream.start()

            print("语音识别已启动，正在监听...")
            return True

        except Exception as e:
            print(f"启动音频流失败: {e}")
            self.is_listening = False
            if self.recognition_thread:
                self.recognition_thread.join(timeout=1)
            return False

    def stop_listening(self):
        """停止语音识别"""
        if not self.is_listening:
            return

        print("正在停止语音识别...")
        self.is_listening = False

        # 停止音频流
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None

        # 等待识别线程结束
        if self.recognition_thread:
            self.recognition_thread.join(timeout=2)

        # 清空队列
        if self.audio_queue:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break

        print("语音识别已停止")

    def is_listening(self) -> bool:
        """检查是否正在监听

        Returns:
            bool: 监听状态
        """
        return self.is_listening

    def get_status(self) -> Dict[str, Any]:
        """获取识别器状态

        Returns:
            Dict[str, Any]: 状态信息字典
        """
        return {
            "is_listening": self.is_listening,
            "is_initialized": self.is_initialized,
            "model_path": self.model_path,
            "language": self.language,
            "sample_rate": self.sample_rate,
            "current_device": self.current_device_index,
            "queue_size": self.audio_queue.qsize() if self.audio_queue else 0
        }

    def __del__(self):
        """析构函数，确保资源释放"""
        if self.is_listening:
            self.stop_listening()


# 使用示例
if __name__ == "__main__":
    def on_recognition(text):
        print(f"\n识别结果: {text}")

    def on_partial(text):
        print(f"\r部分结果: {text}", end='', flush=True)

    try:
        recognizer = SpeechRecognizer()
        print("\n可用音频设备:")
        devices = recognizer.get_available_devices()
        for device in devices:
            print(f"  [{device.index}] {device.name}")

        print("\n开始语音识别演示...")
        recognizer.start_listening(
            callback=on_recognition,
            partial_callback=on_partial
        )

        # 保持程序运行，直到用户中断
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n收到停止信号")

    except Exception as e:
        print(f"程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        recognizer.stop_listening()
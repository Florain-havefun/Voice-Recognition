"""
Vosk识别引擎

负责Vosk模型加载、管理和语音识别逻辑。
"""

import os
import json
import threading
import queue
from typing import Optional, Callable, Dict, Any
from vosk import Model, KaldiRecognizer


class VoskEngine:
    """Vosk识别引擎类"""

    def __init__(self, model_path: str, sample_rate: int = 16000):
        """初始化Vosk引擎

        Args:
            model_path: Vosk模型路径
            sample_rate: 音频采样率，默认16000Hz

        Raises:
            FileNotFoundError: 模型文件不存在
        """
        self.model_path = model_path
        self.sample_rate = sample_rate

        # Vosk组件
        self.model = None
        self.recognizer = None

        # 状态
        self.is_loaded = False
        self.is_processing = False

        # 处理线程
        self.processing_thread = None
        self.audio_queue = None
        self.result_queue = None

        # 回调函数
        self.final_callback = None
        self.partial_callback = None

        print(f"Vosk引擎初始化:")
        print(f"  模型路径: {model_path}")
        print(f"  采样率: {sample_rate}Hz")

    def load_model(self) -> bool:
        """加载Vosk模型

        Returns:
            bool: 加载是否成功
        """
        if self.is_loaded:
            return True

        try:
            # 检查模型路径
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"模型路径不存在: {self.model_path}\n"
                    f"请下载Vosk模型并放置到正确位置。"
                )

            # 加载模型
            print(f"正在加载Vosk模型: {self.model_path}")
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)  # 获取单词时间戳

            self.is_loaded = True
            print("Vosk模型加载成功!")
            return True

        except Exception as e:
            print(f"加载Vosk模型失败: {e}")
            return False

    def unload_model(self):
        """卸载Vosk模型"""
        if not self.is_loaded:
            return

        self.is_loaded = False
        self.recognizer = None
        self.model = None
        print("Vosk模型已卸载")

    def set_callbacks(self,
                     final_callback: Optional[Callable[[str], None]] = None,
                     partial_callback: Optional[Callable[[str], None]] = None):
        """设置回调函数

        Args:
            final_callback: 最终结果回调函数
            partial_callback: 部分结果回调函数
        """
        self.final_callback = final_callback
        self.partial_callback = partial_callback

    def _processing_worker(self):
        """处理工作线程"""
        print("Vosk处理线程启动")

        while self.is_processing:
            try:
                # 从音频队列获取数据
                audio_data = self.audio_queue.get(timeout=0.1)

                # 转换为Vosk需要的字节格式
                import numpy as np
                audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()

                # 发送到识别器
                if self.recognizer.AcceptWaveform(audio_bytes):
                    # 最终结果
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        # 调用最终结果回调
                        if self.final_callback:
                            threading.Thread(
                                target=self.final_callback,
                                args=(text,),
                                daemon=True
                            ).start()

                        # 同时放入结果队列（如果存在）
                        if self.result_queue is not None:
                            try:
                                self.result_queue.put({
                                    'type': 'final',
                                    'text': text,
                                    'result': result
                                }, block=False)
                            except queue.Full:
                                pass
                else:
                    # 部分结果
                    partial = json.loads(self.recognizer.PartialResult())
                    text = partial.get('partial', '').strip()
                    if text:
                        # 调用部分结果回调
                        if self.partial_callback:
                            threading.Thread(
                                target=self.partial_callback,
                                args=(text,),
                                daemon=True
                            ).start()

                        # 放入结果队列（如果存在）
                        if self.result_queue is not None:
                            try:
                                self.result_queue.put({
                                    'type': 'partial',
                                    'text': text,
                                    'result': partial
                                }, block=False)
                            except queue.Full:
                                pass

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Vosk处理错误: {e}")
                break

        print("Vosk处理线程结束")

    def start_processing(self,
                        audio_queue: queue.Queue,
                        result_queue: Optional[queue.Queue] = None) -> bool:
        """开始语音识别处理

        Args:
            audio_queue: 音频数据队列
            result_queue: 结果队列（可选），用于存储识别结果

        Returns:
            bool: 是否成功启动
        """
        if not self.is_loaded:
            if not self.load_model():
                return False

        if self.is_processing:
            print("警告: 已经在处理状态")
            return False

        self.audio_queue = audio_queue
        self.result_queue = result_queue
        self.is_processing = True

        # 启动处理线程
        self.processing_thread = threading.Thread(
            target=self._processing_worker,
            daemon=True
        )
        self.processing_thread.start()

        print("Vosk处理已启动")
        return True

    def stop_processing(self):
        """停止语音识别处理"""
        if not self.is_processing:
            return

        print("正在停止Vosk处理...")
        self.is_processing = False

        # 等待处理线程结束
        if self.processing_thread:
            self.processing_thread.join(timeout=2)

        # 清空队列引用
        self.audio_queue = None
        self.result_queue = None

        print("Vosk处理已停止")

    def recognize_audio_bytes(self, audio_bytes: bytes) -> Optional[Dict[str, Any]]:
        """识别单段音频字节数据

        Args:
            audio_bytes: 音频字节数据

        Returns:
            Optional[Dict[str, Any]]: 识别结果，失败返回None
        """
        if not self.is_loaded:
            if not self.load_model():
                return None

        try:
            if self.recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(self.recognizer.Result())
                return {
                    'type': 'final',
                    'text': result.get('text', '').strip(),
                    'result': result
                }
            else:
                partial = json.loads(self.recognizer.PartialResult())
                return {
                    'type': 'partial',
                    'text': partial.get('partial', '').strip(),
                    'result': partial
                }
        except Exception as e:
            print(f"识别音频字节失败: {e}")
            return None

    def reset_recognizer(self):
        """重置识别器状态"""
        if self.recognizer:
            self.recognizer.Reset()

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            Dict[str, Any]: 模型信息字典
        """
        if not self.model:
            return {}

        # Vosk模型没有直接的属性访问，返回路径信息
        return {
            'model_path': self.model_path,
            'sample_rate': self.sample_rate,
            'is_loaded': self.is_loaded
        }

    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态

        Returns:
            Dict[str, Any]: 状态信息字典
        """
        return {
            'is_loaded': self.is_loaded,
            'is_processing': self.is_processing,
            'model_path': self.model_path,
            'sample_rate': self.sample_rate,
            'has_audio_queue': self.audio_queue is not None,
            'has_result_queue': self.result_queue is not None
        }

    def __del__(self):
        """析构函数，确保资源释放"""
        if self.is_processing:
            self.stop_processing()
        if self.is_loaded:
            self.unload_model()


# 测试代码
if __name__ == "__main__":
    import numpy as np
    import time

    def test_vosk_engine():
        print("测试Vosk引擎...")

        # 创建Vosk引擎
        model_path = "models/vosk-model-small-cn-0.22"
        engine = VoskEngine(model_path)

        # 加载模型
        if not engine.load_model():
            print("模型加载失败，跳过测试")
            return

        # 测试单段音频识别
        print("\n测试单段音频识别...")
        # 生成测试音频数据（静音）
        test_audio = np.zeros(16000, dtype=np.float32)  # 1秒的静音
        audio_bytes = (test_audio * 32767).astype(np.int16).tobytes()

        result = engine.recognize_audio_bytes(audio_bytes)
        if result:
            print(f"识别结果: {result}")
        else:
            print("无识别结果（静音）")

        # 测试流式处理
        print("\n测试流式处理...")
        audio_queue = queue.Queue(maxsize=10)
        result_queue = queue.Queue(maxsize=10)

        def on_final(text):
            print(f"最终结果回调: {text}")

        def on_partial(text):
            print(f"部分结果回调: {text}")

        engine.set_callbacks(final_callback=on_final,
                            partial_callback=on_partial)

        if engine.start_processing(audio_queue, result_queue):
            # 发送一些测试音频数据
            for i in range(3):
                test_chunk = np.random.randn(8000).astype(np.float32) * 0.01  # 小声噪声
                audio_queue.put(test_chunk)
                print(f"发送音频块 {i+1}/3")
                time.sleep(0.5)

            # 停止处理
            time.sleep(1)
            engine.stop_processing()
            print("流式处理测试完成")
        else:
            print("启动流式处理失败")

    test_vosk_engine()
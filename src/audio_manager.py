"""
音频管理器

负责音频设备检测、配置和实时音频流捕获。
"""

import queue
from typing import Optional, List, Dict, Any
import sounddevice as sd
import numpy as np


class AudioDevice:
    """音频设备信息类"""

    def __init__(self, index: int, name: str, input_channels: int,
                 default_samplerate: float):
        self.index = index
        self.name = name
        self.input_channels = input_channels
        self.default_samplerate = default_samplerate

    def __str__(self):
        return f"AudioDevice[{self.index}]: {self.name} " \
               f"(输入通道: {self.input_channels}, 采样率: {self.default_samplerate}Hz)"


class AudioManager:
    """音频管理器类"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """初始化音频管理器

        Args:
            sample_rate: 音频采样率，默认16000Hz
            channels: 音频通道数，默认1（单声道）
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = None
        self.audio_stream = None
        self.audio_queue = None
        self.is_recording = False

        print(f"音频管理器初始化: {sample_rate}Hz, {channels}通道")

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

        self.device_index = device_index
        print(f"已设置音频设备: {device_index}")
        return True

    def _audio_callback(self, indata, frames, time_info, status):
        """音频回调函数，将音频数据放入队列"""
        if status:
            print(f"音频状态: {status}")

        if self.is_recording and self.audio_queue is not None:
            # 将音频数据转换为需要的格式
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

    def start_recording(self, audio_queue: queue.Queue,
                       device_index: Optional[int] = None) -> bool:
        """开始录音

        Args:
            audio_queue: 音频数据队列，用于存储捕获的音频
            device_index: 音频设备索引，如果为None则使用默认设备

        Returns:
            bool: 是否成功启动
        """
        if self.is_recording:
            print("警告: 已经在录音状态")
            return False

        # 设置设备
        if device_index is not None:
            if not self.set_device(device_index):
                print("使用默认音频设备")
                self.device_index = None
        else:
            self.device_index = device_index

        # 设置队列
        self.audio_queue = audio_queue
        self.is_recording = True

        # 启动音频流
        try:
            dtype = 'float32'
            blocksize = 8000  # 每次处理的采样点数

            print(f"启动音频流...")
            print(f"设备: {self.device_index or '默认'}")
            print(f"采样率: {self.sample_rate}Hz")
            print(f"通道数: {self.channels}")

            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=dtype,
                blocksize=blocksize,
                device=self.device_index,
                callback=self._audio_callback
            )
            self.audio_stream.start()

            print("音频流已启动")
            return True

        except Exception as e:
            print(f"启动音频流失败: {e}")
            self.is_recording = False
            self.audio_queue = None
            return False

    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return

        print("正在停止音频流...")
        self.is_recording = False

        # 停止音频流
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None

        # 清空队列引用
        self.audio_queue = None

        print("音频流已停止")

    def get_status(self) -> Dict[str, Any]:
        """获取音频管理器状态

        Returns:
            Dict[str, Any]: 状态信息字典
        """
        return {
            "is_recording": self.is_recording,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "device_index": self.device_index,
            "has_audio_queue": self.audio_queue is not None
        }

    def __del__(self):
        """析构函数，确保资源释放"""
        if self.is_recording:
            self.stop_recording()


# 测试代码
if __name__ == "__main__":
    import time

    def test_audio_manager():
        print("测试音频管理器...")

        # 创建音频管理器
        audio_mgr = AudioManager(sample_rate=16000, channels=1)

        # 列出可用设备
        print("\n可用音频设备:")
        devices = audio_mgr.get_available_devices()
        for device in devices:
            print(f"  [{device.index}] {device.name}")

        # 创建音频队列
        audio_queue = queue.Queue(maxsize=100)

        # 开始录音
        print("\n开始录音测试（5秒）...")
        if audio_mgr.start_recording(audio_queue):
            # 等待5秒
            for i in range(5):
                print(f"录音中... {i+1}/5 秒")
                time.sleep(1)

                # 检查队列中的数据
                queue_size = audio_queue.qsize()
                if queue_size > 0:
                    print(f"  音频队列大小: {queue_size}")

            # 停止录音
            audio_mgr.stop_recording()
            print("录音测试完成")
        else:
            print("启动录音失败")

    test_audio_manager()
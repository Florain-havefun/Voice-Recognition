#!/usr/bin/env python3
"""
语音识别模块高级使用示例

演示高级功能：
1. 多回调处理
2. 状态监控
3. 错误处理
4. 配置管理
"""

import sys
import os
import time
import json
import threading
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.speech_recognizer import SpeechRecognizer
from src.callback_manager import CallbackManager, CallbackType


class AdvancedSpeechRecognizer:
    """高级语音识别器，包含状态监控和错误处理"""

    def __init__(self, config_file=None):
        """初始化高级识别器

        Args:
            config_file: 配置文件路径
        """
        self.config = self._load_config(config_file)
        self.recognizer = None
        self.callback_mgr = CallbackManager(max_queue_size=50)

        # 状态
        self.is_running = False
        self.start_time = None
        self.recognition_count = 0
        self.error_count = 0

        # 初始化回调
        self._setup_callbacks()

        print("高级语音识别器初始化完成")

    def _load_config(self, config_file):
        """加载配置文件"""
        default_config = {
            "model_path": "models/vosk-model-small-cn-0.22",
            "language": "cn-en",
            "sample_rate": 16000,
            "audio_device": None,  # 使用默认设备
            "enable_partial_results": True,
            "log_level": "INFO",
            "save_logs": False,
            "log_file": "speech_recognition.log"
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                print(f"已加载配置文件: {config_file}")
            except Exception as e:
                print(f"加载配置文件失败: {e}，使用默认配置")

        return default_config

    def _setup_callbacks(self):
        """设置回调函数"""

        # 最终结果回调
        def on_final_result(text):
            self.recognition_count += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 记录日志
            log_msg = f"[{timestamp}] 识别结果: {text}"
            print(f"\n{log_msg}")

            # 保存到文件（如果启用）
            if self.config["save_logs"]:
                self._save_log(log_msg)

            # 业务逻辑处理
            self._process_command(text)

        # 部分结果回调
        def on_partial_result(text):
            if self.config["enable_partial_results"]:
                # 在同一行更新显示
                print(f"\r部分结果: {text}", end='', flush=True)

        # 错误回调
        def on_error(error_msg):
            self.error_count += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_msg = f"[{timestamp}] 错误: {error_msg}"

            print(f"\n{log_msg}")

            if self.config["save_logs"]:
                self._save_log(log_msg)

        # 状态变化回调
        def on_status_change(status_info):
            # 可以在这里添加状态监控逻辑
            pass

        # 注册回调
        self.callback_mgr.register_final_result_callback(
            on_final_result,
            priority=1,
            description="处理最终识别结果"
        )

        self.callback_mgr.register_partial_result_callback(
            on_partial_result,
            priority=2,
            description="显示部分识别结果"
        )

        self.callback_mgr.register_error_callback(
            on_error,
            priority=0,
            description="处理错误信息"
        )

        # 启动回调处理
        self.callback_mgr.start_processing()

    def _save_log(self, message):
        """保存日志到文件"""
        try:
            with open(self.config["log_file"], 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except Exception as e:
            print(f"保存日志失败: {e}")

    def _process_command(self, text):
        """处理识别的命令

        这里可以添加自定义的命令处理逻辑
        """
        text_lower = text.lower()

        # 示例命令
        commands = {
            "打开浏览器": self._open_browser,
            "关闭程序": self._shutdown,
            "显示状态": self._show_status,
            "清除日志": self._clear_logs,
        }

        for cmd, handler in commands.items():
            if cmd in text:
                print(f"执行命令: {cmd}")
                handler()
                break

    def _open_browser(self):
        """打开浏览器（示例）"""
        print("命令: 打开浏览器")
        # 实际实现可以使用webbrowser模块
        # import webbrowser
        # webbrowser.open("https://www.google.com")

    def _shutdown(self):
        """关闭程序"""
        print("命令: 关闭程序")
        self.stop()

    def _show_status(self):
        """显示状态"""
        print("\n" + "=" * 40)
        print("系统状态:")
        print(f"  运行时间: {time.time() - self.start_time:.1f} 秒")
        print(f"  识别次数: {self.recognition_count}")
        print(f"  错误次数: {self.error_count}")
        print(f"  是否运行: {self.is_running}")
        print("=" * 40)

    def _clear_logs(self):
        """清除日志"""
        if os.path.exists(self.config["log_file"]):
            os.remove(self.config["log_file"])
            print("日志已清除")

    def start(self):
        """开始语音识别"""
        if self.is_running:
            print("已经在运行中")
            return False

        print("=" * 60)
        print("高级语音识别器启动")
        print("=" * 60)

        try:
            # 创建识别器
            self.recognizer = SpeechRecognizer(
                model_path=self.config["model_path"],
                language=self.config["language"],
                sample_rate=self.config["sample_rate"]
            )

            # 列出音频设备
            print("\n可用音频设备:")
            devices = self.recognizer.get_available_devices()
            for device in devices:
                print(f"  [{device.index}] {device.name}")

            # 设置音频设备（如果配置中指定）
            if self.config["audio_device"] is not None:
                self.recognizer.set_device(self.config["audio_device"])

            # 开始识别
            print("\n开始语音识别...")
            print("支持的命令:")
            print("  - 打开浏览器")
            print("  - 关闭程序")
            print("  - 显示状态")
            print("  - 清除日志")
            print("-" * 40)

            # 定义回调包装器
            def final_callback_wrapper(text):
                self.callback_mgr.queue_final_result(text)

            def partial_callback_wrapper(text):
                self.callback_mgr.queue_partial_result(text)

            success = self.recognizer.start_listening(
                callback=final_callback_wrapper,
                partial_callback=partial_callback_wrapper,
                device_index=self.config["audio_device"]
            )

            if not success:
                print("启动语音识别失败")
                return False

            self.is_running = True
            self.start_time = time.time()

            # 启动状态监控线程
            self.monitor_thread = threading.Thread(
                target=self._monitor_status,
                daemon=True
            )
            self.monitor_thread.start()

            print("语音识别已启动，正在监听...")
            return True

        except Exception as e:
            print(f"启动失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def stop(self):
        """停止语音识别"""
        if not self.is_running:
            return

        print("\n正在停止语音识别...")

        if self.recognizer:
            self.recognizer.stop_listening()

        self.callback_mgr.stop_processing()
        self.is_running = False

        print("语音识别已停止")

    def _monitor_status(self):
        """状态监控线程"""
        while self.is_running:
            try:
                # 每30秒显示一次状态
                time.sleep(30)
                if self.is_running:
                    self._show_status()
            except Exception:
                break

    def get_status(self):
        """获取状态信息"""
        if self.recognizer:
            recognizer_status = self.recognizer.get_status()
        else:
            recognizer_status = {}

        return {
            "advanced": {
                "is_running": self.is_running,
                "recognition_count": self.recognition_count,
                "error_count": self.error_count,
                "uptime": time.time() - self.start_time if self.start_time else 0,
            },
            "recognizer": recognizer_status,
            "callback_manager": self.callback_mgr.get_status(),
        }

    def __del__(self):
        """析构函数"""
        self.stop()


def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="高级语音识别示例")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--device", type=int, help="音频设备索引")
    parser.add_argument("--language", choices=["cn", "en", "cn-en"],
                       default="cn-en", help="识别语言")
    parser.add_argument("--log", action="store_true", help="启用日志记录")
    args = parser.parse_args()

    # 创建配置字典
    config = {}
    if args.config:
        config["config_file"] = args.config
    if args.device:
        config["audio_device"] = args.device
    if args.language:
        config["language"] = args.language
    if args.log:
        config["save_logs"] = True

    # 创建高级识别器
    recognizer = AdvancedSpeechRecognizer(config_file=args.config)

    # 更新配置
    for key, value in config.items():
        if key in recognizer.config:
            recognizer.config[key] = value

    try:
        # 启动
        if recognizer.start():
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n收到停止信号")
        else:
            print("启动失败")

    except Exception as e:
        print(f"程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        recognizer.stop()
        print("程序结束")


if __name__ == "__main__":
    main()
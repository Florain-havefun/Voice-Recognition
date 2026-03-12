#!/usr/bin/env python3
"""
语音识别模块基本使用示例

演示如何使用SpeechRecognizer类进行实时语音识别。
"""

import sys
import os
import time

# 添加父目录到路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.speech_recognizer import SpeechRecognizer


def main():
    """主函数"""
    print("=" * 60)
    print("语音识别模块 - 基本使用示例")
    print("=" * 60)

    # 定义回调函数
    def on_final_result(text):
        """最终识别结果回调"""
        print(f"\n[{time.strftime('%H:%M:%S')}] 识别结果: {text}")

        # 这里可以添加业务逻辑，例如：
        # - 将文本发送给其他模块
        # - 执行命令
        # - 记录日志
        # - 更新UI

    def on_partial_result(text):
        """部分识别结果回调"""
        # 在同一行更新显示，实现实时效果
        if text:
            print(f"\r部分结果: {text}", end='', flush=True)

    def on_error(error_msg):
        """错误回调"""
        print(f"\n[错误] {error_msg}")

    try:
        # 1. 创建语音识别器实例
        print("初始化语音识别器...")
        recognizer = SpeechRecognizer(
            model_path="models/vosk-model-small-cn-0.22",
            language="cn-en",  # 中英文混合
            sample_rate=16000
        )

        # 2. 列出可用音频设备
        print("\n可用音频设备:")
        devices = recognizer.get_available_devices()
        for device in devices:
            print(f"  [{device.index}] {device.name}")

        # 3. 开始语音识别
        print("\n开始语音识别...")
        print("请对着麦克风说话，按 Ctrl+C 停止")
        print("-" * 40)

        # 开始监听
        success = recognizer.start_listening(
            callback=on_final_result,
            partial_callback=on_partial_result
        )

        if not success:
            print("启动语音识别失败")
            return

        # 4. 保持程序运行，直到用户中断
        try:
            while True:
                # 可以在这里添加其他逻辑
                # 例如：检查状态、更新UI等
                time.sleep(1)

                # 示例：定期显示状态
                # status = recognizer.get_status()
                # print(f"\r状态: 监听中... 队列大小: {status['queue_size']}", end='')

        except KeyboardInterrupt:
            print("\n\n收到停止信号")

    except ImportError as e:
        print(f"\n导入错误: {e}")
        print("请确保已安装所有依赖:")
        print("  pip install vosk sounddevice numpy pyaudio")
    except FileNotFoundError as e:
        print(f"\n文件错误: {e}")
        print("请确保已下载Vosk模型:")
        print("  1. 创建 models/ 目录")
        print("  2. 下载模型: vosk-model-small-cn-0.22.zip")
        print("  3. 解压到 models/vosk-model-small-cn-0.22/")
    except Exception as e:
        print(f"\n程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 5. 确保停止识别
        print("\n清理资源...")
        recognizer.stop_listening()
        print("程序结束")


if __name__ == "__main__":
    main()
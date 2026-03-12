"""
语音识别模块包

提供实时离线语音识别功能，支持中文和英文混合识别。
基于Vosk/Kaldi技术，完全本地运行。
"""

__version__ = "0.1.0"
__author__ = "AI桌面软件团队"

from .speech_recognizer import SpeechRecognizer

__all__ = [
    'SpeechRecognizer',
]
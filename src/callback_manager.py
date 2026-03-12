"""
回调管理器

负责管理识别结果的回调函数，支持多消费者和线程安全的事件分发。
"""

import threading
import queue
import time
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class CallbackType(Enum):
    """回调类型"""
    FINAL_RESULT = "final_result"      # 最终识别结果
    PARTIAL_RESULT = "partial_result"  # 部分识别结果
    ERROR = "error"                    # 错误信息
    STATUS_CHANGE = "status_change"    # 状态变化


@dataclass
class CallbackRegistration:
    """回调注册信息"""
    callback_id: str
    callback_type: CallbackType
    callback_func: Callable[[Any], None]
    priority: int = 0
    description: str = ""


class CallbackManager:
    """回调管理器类"""

    def __init__(self, max_queue_size: int = 100):
        """初始化回调管理器

        Args:
            max_queue_size: 事件队列最大大小
        """
        self.max_queue_size = max_queue_size

        # 回调注册表：类型 -> [注册信息列表]
        self.registrations: Dict[CallbackType, List[CallbackRegistration]] = {
            callback_type: [] for callback_type in CallbackType
        }

        # 事件队列
        self.event_queue = queue.Queue(maxsize=max_queue_size)

        # 处理线程
        self.is_running = False
        self.processing_thread = None

        # 锁，用于保护注册表
        self.registration_lock = threading.RLock()

        # 回调ID计数器
        self.callback_id_counter = 0

        print(f"回调管理器初始化 (队列大小: {max_queue_size})")

    def _generate_callback_id(self) -> str:
        """生成唯一的回调ID

        Returns:
            str: 回调ID
        """
        with self.registration_lock:
            self.callback_id_counter += 1
            return f"callback_{self.callback_id_counter}_{int(time.time())}"

    def register_callback(self,
                         callback_type: CallbackType,
                         callback_func: Callable[[Any], None],
                         priority: int = 0,
                         description: str = "") -> str:
        """注册回调函数

        Args:
            callback_type: 回调类型
            callback_func: 回调函数
            priority: 优先级（数字越大优先级越高）
            description: 描述信息

        Returns:
            str: 回调ID，用于后续取消注册
        """
        callback_id = self._generate_callback_id()

        registration = CallbackRegistration(
            callback_id=callback_id,
            callback_type=callback_type,
            callback_func=callback_func,
            priority=priority,
            description=description
        )

        with self.registration_lock:
            registrations = self.registrations[callback_type]
            registrations.append(registration)
            # 按优先级排序
            registrations.sort(key=lambda x: x.priority, reverse=True)

        print(f"注册回调: {callback_id} ({callback_type.value}), 优先级: {priority}")
        return callback_id

    def unregister_callback(self, callback_id: str) -> bool:
        """取消注册回调函数

        Args:
            callback_id: 回调ID

        Returns:
            bool: 是否成功取消注册
        """
        with self.registration_lock:
            for callback_type, registrations in self.registrations.items():
                for i, registration in enumerate(registrations):
                    if registration.callback_id == callback_id:
                        registrations.pop(i)
                        print(f"取消注册回调: {callback_id}")
                        return True

        print(f"警告: 未找到回调ID: {callback_id}")
        return False

    def register_final_result_callback(self,
                                      callback_func: Callable[[str], None],
                                      priority: int = 0,
                                      description: str = "") -> str:
        """注册最终结果回调函数（便捷方法）

        Args:
            callback_func: 回调函数，接收识别的文本
            priority: 优先级
            description: 描述信息

        Returns:
            str: 回调ID
        """
        return self.register_callback(
            CallbackType.FINAL_RESULT,
            callback_func,
            priority,
            description
        )

    def register_partial_result_callback(self,
                                        callback_func: Callable[[str], None],
                                        priority: int = 0,
                                        description: str = "") -> str:
        """注册部分结果回调函数（便捷方法）

        Args:
            callback_func: 回调函数，接收部分识别的文本
            priority: 优先级
            description: 描述信息

        Returns:
            str: 回调ID
        """
        return self.register_callback(
            CallbackType.PARTIAL_RESULT,
            callback_func,
            priority,
            description
        )

    def register_error_callback(self,
                               callback_func: Callable[[str], None],
                               priority: int = 0,
                               description: str = "") -> str:
        """注册错误回调函数（便捷方法）

        Args:
            callback_func: 回调函数，接收错误信息
            priority: 优先级
            description: 描述信息

        Returns:
            str: 回调ID
        """
        return self.register_callback(
            CallbackType.ERROR,
            callback_func,
            priority,
            description
        )

    def queue_event(self, callback_type: CallbackType, data: Any) -> bool:
        """将事件加入队列

        Args:
            callback_type: 回调类型
            data: 事件数据

        Returns:
            bool: 是否成功加入队列
        """
        try:
            self.event_queue.put({
                'type': callback_type,
                'data': data,
                'timestamp': time.time()
            }, block=False)
            return True
        except queue.Full:
            # 队列满时，丢弃最旧的事件
            try:
                self.event_queue.get_nowait()
                self.event_queue.put({
                    'type': callback_type,
                    'data': data,
                    'timestamp': time.time()
                }, block=False)
                print(f"警告: 事件队列满，丢弃旧事件")
                return True
            except queue.Empty:
                return False

    def queue_final_result(self, text: str) -> bool:
        """将最终结果加入队列（便捷方法）

        Args:
            text: 识别结果文本

        Returns:
            bool: 是否成功加入队列
        """
        return self.queue_event(CallbackType.FINAL_RESULT, text)

    def queue_partial_result(self, text: str) -> bool:
        """将部分结果加入队列（便捷方法）

        Args:
            text: 部分识别结果文本

        Returns:
            bool: 是否成功加入队列
        """
        return self.queue_event(CallbackType.PARTIAL_RESULT, text)

    def queue_error(self, error_message: str) -> bool:
        """将错误信息加入队列（便捷方法）

        Args:
            error_message: 错误信息

        Returns:
            bool: 是否成功加入队列
        """
        return self.queue_event(CallbackType.ERROR, error_message)

    def queue_status_change(self, status_info: Dict[str, Any]) -> bool:
        """将状态变化信息加入队列（便捷方法）

        Args:
            status_info: 状态信息

        Returns:
            bool: 是否成功加入队列
        """
        return self.queue_event(CallbackType.STATUS_CHANGE, status_info)

    def _process_events(self):
        """处理事件的工作线程函数"""
        print("回调处理线程启动")

        while self.is_running:
            try:
                # 从队列获取事件
                event = self.event_queue.get(timeout=0.1)

                callback_type = event['type']
                data = event['data']

                # 获取对应的回调函数
                with self.registration_lock:
                    registrations = self.registrations.get(callback_type, []).copy()

                # 调用所有注册的回调函数
                for registration in registrations:
                    try:
                        registration.callback_func(data)
                    except Exception as e:
                        print(f"回调函数执行错误 ({registration.callback_id}): {e}")

                # 标记任务完成
                self.event_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"事件处理错误: {e}")

        print("回调处理线程结束")

    def start_processing(self) -> bool:
        """开始处理事件

        Returns:
            bool: 是否成功启动
        """
        if self.is_running:
            print("警告: 已经在处理状态")
            return False

        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._process_events,
            daemon=True
        )
        self.processing_thread.start()

        print("回调处理已启动")
        return True

    def stop_processing(self):
        """停止处理事件"""
        if not self.is_running:
            return

        print("正在停止回调处理...")
        self.is_running = False

        # 等待处理线程结束
        if self.processing_thread:
            self.processing_thread.join(timeout=2)

        print("回调处理已停止")

    def get_registration_count(self) -> Dict[CallbackType, int]:
        """获取各类回调的注册数量

        Returns:
            Dict[CallbackType, int]: 类型到数量的映射
        """
        with self.registration_lock:
            return {
                callback_type: len(registrations)
                for callback_type, registrations in self.registrations.items()
            }

    def get_status(self) -> Dict[str, Any]:
        """获取回调管理器状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        reg_counts = self.get_registration_count()

        return {
            "is_running": self.is_running,
            "event_queue_size": self.event_queue.qsize(),
            "event_queue_max": self.max_queue_size,
            "registration_counts": {k.value: v for k, v in reg_counts.items()},
            "total_registrations": sum(reg_counts.values())
        }

    def clear_all_callbacks(self):
        """清除所有回调注册"""
        with self.registration_lock:
            for callback_type in self.registrations:
                self.registrations[callback_type].clear()

        print("已清除所有回调注册")

    def __del__(self):
        """析构函数，确保资源释放"""
        if self.is_running:
            self.stop_processing()


# 测试代码
if __name__ == "__main__":
    def test_callback_manager():
        print("测试回调管理器...")

        # 创建回调管理器
        callback_mgr = CallbackManager(max_queue_size=10)

        # 定义回调函数
        def on_final_result(text):
            print(f"[最终结果] {text}")

        def on_partial_result(text):
            print(f"[部分结果] {text}")

        def on_error(error_msg):
            print(f"[错误] {error_msg}")

        # 注册回调函数
        final_id = callback_mgr.register_final_result_callback(
            on_final_result,
            priority=1,
            description="处理最终识别结果"
        )

        partial_id = callback_mgr.register_partial_result_callback(
            on_partial_result,
            priority=2,
            description="处理部分识别结果"
        )

        error_id = callback_mgr.register_error_callback(
            on_error,
            priority=0,
            description="处理错误信息"
        )

        # 启动处理
        callback_mgr.start_processing()

        # 发送一些测试事件
        print("\n发送测试事件...")
        callback_mgr.queue_final_result("你好，世界！")
        callback_mgr.queue_partial_result("你好")
        callback_mgr.queue_error("音频设备未找到")
        callback_mgr.queue_final_result("Hello, world!")

        # 等待事件处理
        time.sleep(1)

        # 显示状态
        status = callback_mgr.get_status()
        print(f"\n回调管理器状态:")
        for key, value in status.items():
            print(f"  {key}: {value}")

        # 取消一个回调
        print(f"\n取消回调: {partial_id}")
        callback_mgr.unregister_callback(partial_id)

        # 发送更多事件
        callback_mgr.queue_partial_result("这个回调应该不会被调用")

        # 等待处理
        time.sleep(0.5)

        # 停止处理
        callback_mgr.stop_processing()

        print("回调管理器测试完成")

    test_callback_manager()
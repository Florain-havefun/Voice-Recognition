#!/usr/bin/env python3
"""
语音识别模块启动脚本

提供统一的入口点，支持多种运行模式。
"""

import os
import sys
import argparse
import subprocess

def check_dependencies():
    """检查依赖是否已安装"""
    print("检查依赖...")

    required_packages = [
        "vosk",
        "sounddevice",
        "numpy",
        "pyaudio"
    ]

    missing = []
    for package in required_packages:
        try:
            module_name = package.replace("-", "_")
            __import__(module_name)
            print(f"  [OK] {package}")
        except ImportError as e:
            print(f"  [FAIL] {package} (导入错误: {e})")
            missing.append(package)

    return missing

def check_model():
    """检查模型是否存在"""
    print("\n检查模型...")

    model_path = "models/vosk-model-small-cn-0.22"
    if os.path.exists(model_path):
        print(f"  [OK] 模型存在: {model_path}")
        return True
    else:
        print(f"  [FAIL] 模型不存在: {model_path}")
        print(f"    请运行: python download_model.py")
        return False

def run_basic_example():
    """运行基础示例"""
    print("\n运行基础示例...")
    try:
        import examples.basic_usage
        examples.basic_usage.main()
    except Exception as e:
        print(f"运行基础示例失败: {e}")
        return False
    return True

def run_advanced_example():
    """运行高级示例"""
    print("\n运行高级示例...")
    try:
        import examples.advanced_usage
        examples.advanced_usage.main()
    except Exception as e:
        print(f"运行高级示例失败: {e}")
        return False
    return True

def download_model_interactive():
    """交互式下载模型"""
    print("\n下载模型...")
    try:
        import download_model
        download_model.main()
    except Exception as e:
        print(f"下载模型失败: {e}")
        return False
    return True

def run_tests():
    """运行测试"""
    print("\n运行测试...")
    try:
        import pytest
        # 切换到项目根目录
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])
        return result.returncode == 0
    except Exception as e:
        print(f"运行测试失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="语音识别模块启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                    # 交互式菜单
  %(prog)s --basic           # 运行基础示例
  %(prog)s --advanced        # 运行高级示例
  %(prog)s --download-model  # 下载模型
  %(prog)s --test           # 运行测试
  %(prog)s --check          # 检查环境和依赖
        """
    )

    parser.add_argument("--basic", action="store_true", help="运行基础示例")
    parser.add_argument("--advanced", action="store_true", help="运行高级示例")
    parser.add_argument("--download-model", action="store_true", help="下载Vosk模型")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--check", action="store_true", help="检查环境和依赖")

    args = parser.parse_args()

    print("=" * 60)
    print("语音识别模块启动脚本")
    print("=" * 60)

    # 如果指定了参数，直接执行对应操作
    if args.check:
        missing = check_dependencies()
        model_ok = check_model()
        if missing:
            print(f"\n缺少依赖包: {missing}")
            print("请运行: pip install " + " ".join(missing))
        elif not model_ok:
            print("\n模型未安装")
        else:
            print("\n[OK] 所有依赖和模型已就绪")
        return

    if args.download_model:
        download_model_interactive()
        return

    if args.test:
        run_tests()
        return

    if args.basic:
        missing = check_dependencies()
        if missing:
            print(f"\n缺少依赖包: {missing}")
            print("请先安装依赖: pip install " + " ".join(missing))
            return

        if not check_model():
            response = input("\n模型不存在，是否现在下载？ (y/N): ")
            if response.lower() == 'y':
                if download_model_interactive():
                    run_basic_example()
            return

        run_basic_example()
        return

    if args.advanced:
        missing = check_dependencies()
        if missing:
            print(f"\n缺少依赖包: {missing}")
            print("请先安装依赖: pip install " + " ".join(missing))
            return

        if not check_model():
            response = input("\n模型不存在，是否现在下载？ (y/N): ")
            if response.lower() == 'y':
                if download_model_interactive():
                    run_advanced_example()
            return

        run_advanced_example()
        return

    # 交互式菜单
    while True:
        print("\n请选择操作:")
        print("  1. 检查环境和依赖")
        print("  2. 下载Vosk模型")
        print("  3. 运行基础示例")
        print("  4. 运行高级示例")
        print("  5. 运行测试")
        print("  6. 退出")

        try:
            choice = input("\n请输入选项 (1-6): ").strip()

            if choice == "1":
                missing = check_dependencies()
                model_ok = check_model()
                if missing:
                    print(f"\n缺少依赖包: {missing}")
                    print("请运行: pip install " + " ".join(missing))
                elif not model_ok:
                    print("\n模型未安装")
                else:
                    print("\n[OK] 所有依赖和模型已就绪")

            elif choice == "2":
                download_model_interactive()

            elif choice == "3":
                missing = check_dependencies()
                if missing:
                    print(f"\n缺少依赖包: {missing}")
                    print("请先安装依赖: pip install " + " ".join(missing))
                    continue

                if not check_model():
                    response = input("模型不存在，是否现在下载？ (y/N): ")
                    if response.lower() == 'y':
                        if download_model_interactive():
                            run_basic_example()
                    continue

                run_basic_example()

            elif choice == "4":
                missing = check_dependencies()
                if missing:
                    print(f"\n缺少依赖包: {missing}")
                    print("请先安装依赖: pip install " + " ".join(missing))
                    continue

                if not check_model():
                    response = input("模型不存在，是否现在下载？ (y/N): ")
                    if response.lower() == 'y':
                        if download_model_interactive():
                            run_advanced_example()
                    continue

                run_advanced_example()

            elif choice == "5":
                run_tests()

            elif choice == "6":
                print("\n退出")
                break

            else:
                print("无效选项，请重新选择")

        except KeyboardInterrupt:
            print("\n\n收到中断信号")
            break
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
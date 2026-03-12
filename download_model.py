#!/usr/bin/env python3
"""
Vosk模型下载脚本

自动下载并解压Vosk中文小模型 (vosk-model-small-cn-0.22)
支持断点续传和进度显示
"""

import os
import sys
import zipfile
import hashlib
import argparse
import tempfile
import shutil
from pathlib import Path

# 尝试导入requests，如果失败则提示安装
try:
    import requests
except ImportError:
    print("错误: requests库未安装")
    print("请运行: pip install requests")
    sys.exit(1)

# 模型信息
MODEL_NAME = "vosk-model-small-cn-0.22"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)

# 可能的下载源（按优先级排序）
DOWNLOAD_URLS = [
    # 官方源
    f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip",
    # SourceForge镜像
    f"https://sourceforge.net/projects/vosk/files/{MODEL_NAME}.zip/download",
    # GitHub镜像
    f"https://github.com/alphacep/vosk-models/releases/download/{MODEL_NAME}/{MODEL_NAME}.zip",
]

# 模型文件的预期MD5校验和（用于验证下载完整性）
# 注意：实际校验和可能需要从官方源获取，这里仅为示例
MODEL_MD5 = None  # 暂时不验证


def download_file(url, destination, chunk_size=8192):
    """
    下载文件并显示进度

    Args:
        url: 下载URL
        destination: 保存路径
        chunk_size: 块大小

    Returns:
        bool: 是否成功
    """
    try:
        # 发送HEAD请求获取文件大小
        headers = {}
        if os.path.exists(destination):
            # 断点续传：获取已下载文件大小
            file_size = os.path.getsize(destination)
            headers['Range'] = f'bytes={file_size}-'
            print(f"检测到部分下载的文件 ({file_size} bytes)，尝试断点续传...")

        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        # 处理断点续传的206状态码
        if response.status_code == 206:
            mode = 'ab'  # 追加模式
            downloaded = file_size
            total_size = int(response.headers.get('content-range').split('/')[-1])
        else:
            mode = 'wb'  # 写入模式
            downloaded = 0
            total_size = int(response.headers.get('content-length', 0))

        # 开始下载
        print(f"开始下载: {url}")
        print(f"目标文件: {destination}")
        if total_size:
            print(f"文件大小: {total_size / (1024*1024):.2f} MB")

        with open(destination, mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 显示进度
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        print(f"\r下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
                    else:
                        print(f"\r已下载: {downloaded} bytes", end='', flush=True)

        print()  # 换行
        return True

    except requests.exceptions.RequestException as e:
        print(f"\n下载失败: {e}")
        return False
    except Exception as e:
        print(f"\n下载过程中发生错误: {e}")
        return False


def verify_file(file_path, expected_md5=None):
    """
    验证文件的完整性

    Args:
        file_path: 文件路径
        expected_md5: 预期的MD5值（如果为None则不验证）

    Returns:
        bool: 是否验证通过
    """
    if not expected_md5:
        print("跳过MD5验证（未提供校验和）")
        return True

    print("正在验证文件完整性...")
    try:
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)

        actual_md5 = md5_hash.hexdigest()
        if actual_md5 == expected_md5:
            print("✓ 文件完整性验证通过")
            return True
        else:
            print(f"✗ 文件完整性验证失败")
            print(f"  预期MD5: {expected_md5}")
            print(f"  实际MD5: {actual_md5}")
            return False
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        return False


def extract_zip(zip_path, extract_to):
    """
    解压ZIP文件

    Args:
        zip_path: ZIP文件路径
        extract_to: 解压目标目录

    Returns:
        bool: 是否成功
    """
    print(f"正在解压: {zip_path}")
    print(f"解压到: {extract_to}")

    try:
        # 确保目标目录存在
        os.makedirs(extract_to, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取文件列表
            file_list = zip_ref.namelist()
            total_files = len(file_list)

            # 解压所有文件
            for i, file in enumerate(file_list, 1):
                try:
                    zip_ref.extract(file, extract_to)
                    # 显示进度
                    print(f"\r解压进度: {i}/{total_files} ({file})", end='', flush=True)
                except Exception as e:
                    print(f"\n解压文件 {file} 时出错: {e}")
                    return False

            print()  # 换行

        print("✓ 解压完成")
        return True

    except zipfile.BadZipFile:
        print("✗ ZIP文件损坏或不是有效的ZIP文件")
        return False
    except Exception as e:
        print(f"✗ 解压过程中发生错误: {e}")
        return False


def check_model():
    """
    检查模型是否已存在

    Returns:
        bool: 模型是否存在
    """
    if os.path.exists(MODEL_PATH):
        print(f"✓ 模型已存在: {MODEL_PATH}")
        # 检查模型是否完整（至少包含一些关键文件）
        required_files = ["am/final.mdl", "graph/HCLG.fst", "conf/model.conf"]
        missing_files = []
        for file in required_files:
            if not os.path.exists(os.path.join(MODEL_PATH, file)):
                missing_files.append(file)

        if missing_files:
            print(f"  警告: 模型文件不完整，缺少: {missing_files}")
            return False
        return True
    return False


def cleanup_temp_files(temp_files):
    """
    清理临时文件

    Args:
        temp_files: 临时文件列表
    """
    for file in temp_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"清理临时文件: {file}")
        except Exception as e:
            print(f"清理文件 {file} 时出错: {e}")


def main():
    """主函数"""
    global MODEL_DIR, MODEL_PATH
    parser = argparse.ArgumentParser(
        description="下载Vosk中文小模型 (vosk-model-small-cn-0.22)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                    # 交互式下载
  %(prog)s --url URL          # 指定下载URL
  %(prog)s --force            # 强制重新下载
  %(prog)s --check-only       # 仅检查模型状态
        """
    )

    parser.add_argument("--url", help="指定下载URL（覆盖默认URL）")
    parser.add_argument("--force", action="store_true", help="强制重新下载（即使模型已存在）")
    parser.add_argument("--check-only", action="store_true", help="仅检查模型状态，不下载")
    parser.add_argument("--output-dir", default=None, help="模型输出目录（默认: models）")

    args = parser.parse_args()

    print("=" * 60)
    print("Vosk模型下载工具")
    print("=" * 60)

    # 更新模型路径
    MODEL_DIR = args.output_dir or "models"
    MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)

    # 检查模型状态
    if check_model() and not args.force:
        if args.check_only:
            print("\n✓ 模型已就绪")
            return 0

        response = input("\n模型已存在，是否重新下载？ (y/N): ")
        if response.lower() != 'y':
            print("取消下载")
            return 0

    if args.check_only:
        print("\n模型不存在或需要更新")
        return 1

    # 准备下载
    os.makedirs(MODEL_DIR, exist_ok=True)
    temp_files = []

    try:
        # 确定下载URL
        download_urls = []
        if args.url:
            download_urls = [args.url]
        else:
            download_urls = DOWNLOAD_URLS

        # 尝试从各个URL下载
        success = False
        zip_path = os.path.join(tempfile.gettempdir(), f"{MODEL_NAME}.zip")
        temp_files.append(zip_path)

        for url in download_urls:
            print(f"\n尝试从源下载: {url}")
            if download_file(url, zip_path):
                # 验证文件
                if verify_file(zip_path, MODEL_MD5):
                    success = True
                    break
                else:
                    print("文件验证失败，尝试下一个源...")
                    # 删除损坏的文件
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
            else:
                print("下载失败，尝试下一个源...")

        if not success:
            print("\n✗ 所有下载源都失败")
            print("请尝试:")
            print("  1. 检查网络连接")
            print("  2. 使用 --url 参数指定下载URL")
            print("  3. 手动下载模型并解压到 models/ 目录")
            print(f"     模型名称: {MODEL_NAME}")
            return 1

        # 解压文件
        print("\n" + "=" * 40)
        if not extract_zip(zip_path, MODEL_DIR):
            print("✗ 解压失败")
            return 1

        # 验证解压结果
        print("\n验证模型安装...")
        if check_model():
            print("\n" + "=" * 60)
            print("✓ 模型下载并安装成功！")
            print(f"  模型路径: {MODEL_PATH}")
            print("=" * 60)
        else:
            print("\n✗ 模型安装不完整")
            print("请检查解压过程或手动解压文件")
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\n下载被用户中断")
        return 1
    except Exception as e:
        print(f"\n✗ 下载过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # 清理临时文件
        cleanup_temp_files(temp_files)


if __name__ == "__main__":
    sys.exit(main())
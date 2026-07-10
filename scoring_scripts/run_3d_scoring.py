# -*- coding: utf-8 -*-
"""
大模型自动评分启动脚本

使用方式:
    python run_3d_scoring.py              # 断点续跑: 不清空缓存，跳过已评分小组继续运行
    python run_3d_scoring.py --regrade    # 强制重新评分: 清空缓存 + 重新评分
"""

import argparse
import shutil
import subprocess
import sys
import os
from pathlib import Path

# Add current dir to sys.path so we can import core
sys.path.insert(0, str(Path(__file__).parent))

from core.config import settings

# 数据目录 (从 settings 统一获取)
RESULT_DIR = settings.RESULT_DIR
THUMBNAIL_CACHE = settings.THUMBNAIL_CACHE_DIR

# 子项目目录
BATCH_GRADER_DIR = settings.BATCH_GRADER_DIR


def clear_cache():
    """清空所有缓存和评分结果"""
    print("\n[*] 清空缓存和旧评分数据...")
    
    import time
    import stat
    def handle_remove_readonly(func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == 13:
            try:
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) # 0777
                func(path)
                return
            except Exception:
                pass
        
        # 对于网络驱动器的延迟删除(WinError 5/32)，尝试重试几次
        for _ in range(3):
            try:
                time.sleep(0.5)
                func(path)
                return
            except Exception:
                pass
        print(f"  [!] 警告: 无法删除 {path}")

    # 清空 result 目录内容 (保留目录本身)
    if RESULT_DIR.exists():
        import os
        for item in RESULT_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item, onerror=handle_remove_readonly)
                print(f"  [√] 删除: {item.name}/")
            else:
                # 保留 Excel 模板文件
                if not item.name.endswith('.xlsx'):
                    try:
                        item.unlink()
                        print(f"  [√] 删除: {item.name}")
                    except Exception as e:
                        print(f"  [!] 警告: 无法删除 {item.name}: {e}")
    
    # 清空缩略图缓存
    if THUMBNAIL_CACHE.exists():
        shutil.rmtree(THUMBNAIL_CACHE)
        print(f"  [√] 删除: thumbnail_cache/")
    
    print("  缓存清理完成。")


def run_batch_grading():
    """运行批量评分程序"""
    print("\n[*] 运行批量评分...")
    
    batch_script = BATCH_GRADER_DIR / "grader_app.py"
    if not batch_script.exists():
        print(f"  [x] 错误: 找不到评分脚本 {batch_script}")
        return False
    
    result = subprocess.run(
        [sys.executable, str(batch_script)],
        cwd=str(BATCH_GRADER_DIR)
    )
    
    if result.returncode == 0:
        print("  批量评分完成。")
        return True
    else:
        print(f"  [x] 评分程序异常退出 (code: {result.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="大模型评分启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_3d_scoring.py              # 断点续跑: 不清空缓存，跳过已评分小组继续运行
  python run_3d_scoring.py --regrade    # 强制重新评分: 清空缓存 + 重新评分
        """
    )
    parser.add_argument(
        "--regrade", 
        action="store_true",
        help="强制重新评分: 清空缓存 → 运行评分"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("大模型评分启动脚本")
    print("=" * 50)
    
    if args.regrade:
        print(f"模式: 强制重新评分")
        clear_cache()
        
        if not run_batch_grading():
            print("\n评分失败，终止。")
            sys.exit(1)
            
    else:
        print(f"模式: 断点续跑 (保留现有进度)")
        
        if not run_batch_grading():
            print("\n评分失败，终止。")
            sys.exit(1)


if __name__ == "__main__":
    main()

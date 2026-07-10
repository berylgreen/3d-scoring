import os
import yaml
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path="config.yaml"):
    """Load configuration from config.yaml"""
    project_root = Path(__file__).resolve().parent.parent.parent
    config_file = project_root / config_path
    
    if not config_file.exists():
        logging.error(f"Config file not found at {config_file}")
        return None
        
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def organize_files(data_dir):
    """
    整理 data_dir 下的文件。
    请根据具体需求修改此处的逻辑。
    例如：
    - 解压所有的 zip/rar 文件
    - 将特定类型的文件（如 .blend, .mp4）移动到统一的文件夹
    - 按照学号重命名文件夹
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logging.error(f"Data directory does not exist: {data_path}")
        return

    logging.info(f"开始整理目录: {data_path}")
    
    # 遍历目录示例
    for item in data_path.iterdir():
        if item.is_file():
            # 处理文件，例如判断扩展名
            ext = item.suffix.lower()
            # if ext == '.zip':
            #     logging.info(f"找到压缩包: {item.name}")
        elif item.is_dir():
            # 处理子目录
            pass

    logging.info("整理完成！")

def main():
    config = load_config()
    if not config:
        return
        
    data_dir = config.get("data_dir")
    if not data_dir:
        logging.error("data_dir is not defined in config.yaml")
        return
        
    organize_files(data_dir)

if __name__ == "__main__":
    main()

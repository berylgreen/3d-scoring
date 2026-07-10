import os
import yaml
import shutil
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path="config.yaml"):
    """Load configuration from config.yaml"""
    # Assuming config.yaml is in the project root
    project_root = Path(__file__).resolve().parent.parent.parent
    config_file = project_root / config_path
    
    if not config_file.exists():
        logging.error(f"Config file not found at {config_file}")
        return None
        
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_base_name(filename):
    """
    获取去除重复标记后的基础文件名。
    例如: "张三(1).zip" -> "张三"
    """
    stem = Path(filename).stem
    # 匹配结尾的 (1), (2), ( 1 ) 等格式，允许前面有空格
    base = re.sub(r'\s*\(\d+\)$', '', stem)
    return base

def organize_files(data_dir, min_normal_size_kb=50):
    """
    整理 data_dir 下的文件。
    规则: 如果文件名几乎相同（如含有 (1), (2) ），则只保留时间最近、且文件大小正常的文件。
    多余的文件将被移动到 duplicates 文件夹中，以防误删。
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logging.error(f"Data directory does not exist: {data_path}")
        return

    logging.info(f"开始整理目录: {data_path}")
    
    # 1. 先删除以 upload-tmp 结尾的文件或目录
    deleted_tmp_count = 0
    for item in data_path.iterdir():
        if item.name.endswith("upload-tmp"):
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                logging.info(f"已删除临时文件: {item.name}")
                deleted_tmp_count += 1
            except Exception as e:
                logging.error(f"删除临时文件 {item.name} 失败: {e}")
                
    if deleted_tmp_count > 0:
        logging.info(f"共清理了 {deleted_tmp_count} 个 upload-tmp 结尾的临时文件。")
    
    duplicates_dir = data_path / "duplicates"
    
    # 获取所有文件并分组
    file_groups = {}
    for item in data_path.iterdir():
        if item.is_file():
            base_name = get_base_name(item.name)
            ext = item.suffix.lower()
            group_key = f"{base_name}{ext}"
            
            if group_key not in file_groups:
                file_groups[group_key] = []
            file_groups[group_key].append(item)

    processed_groups = 0
    moved_files = 0
    
    for group_key, files in file_groups.items():
        if len(files) <= 1:
            continue
            
        processed_groups += 1
        
        # 提取文件信息: (path, size_kb, mtime)
        file_infos = []
        for f in files:
            stat = f.stat()
            size_kb = stat.st_size / 1024
            mtime = stat.st_mtime
            file_infos.append({"path": f, "size_kb": size_kb, "mtime": mtime})
            
        # 过滤大小正常的文件
        normal_files = [info for info in file_infos if info["size_kb"] >= min_normal_size_kb]
        
        # 如果过滤后没有文件，说明所有文件都很小，则在所有文件中选择
        if not normal_files:
            normal_files = file_infos
            
        # 按修改时间降序排序（最新的是第一个）
        normal_files.sort(key=lambda x: x["mtime"], reverse=True)
        
        # 保留的文件
        keep_file = normal_files[0]
        
        # 找出需要移动的文件（包括原本大小不正常的，以及虽然正常但较旧的）
        files_to_remove = [info["path"] for info in file_infos if info["path"] != keep_file["path"]]
        
        if files_to_remove:
            logging.info(f"处理组 [{group_key}]:")
            logging.info(f"  -> 保留: {keep_file['path'].name} (大小: {keep_file['size_kb']:.1f} KB, 时间: {keep_file['mtime']})")
            
            if not duplicates_dir.exists():
                duplicates_dir.mkdir()
                
            for f in files_to_remove:
                logging.info(f"  -> 移走: {f.name}")
                dest_path = duplicates_dir / f.name
                
                # 处理目标文件夹可能存在同名文件的情况
                counter = 1
                while dest_path.exists():
                    dest_path = duplicates_dir / f"{f.stem}_dup{counter}{f.suffix}"
                    counter += 1
                    
                shutil.move(str(f), str(dest_path))
                moved_files += 1

    logging.info(f"整理完成！共处理了 {processed_groups} 组重复文件，移除了 {moved_files} 个重复文件到 duplicates 文件夹。")

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

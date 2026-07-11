import sys
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# 引入项目配置
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from core.config import settings
from core.data_loader import find_max_files
from core.logger import logger

def check_blender(item_index, item):
    group_info = item.get("group_info", {})
    folder_path = group_info.get("folder_path")
    
    # 如果 group_info 没写 folder_path，去外层找找
    if not folder_path:
        folder_path = item.get("folder_path", "")

    if folder_path:
        max_files = find_max_files(folder_path)
        is_blender = any(f.get("name", "").lower().endswith(".blend") for f in max_files) if max_files else False
    else:
        is_blender = False
        
    return item_index, is_blender

def main():
    json_path = settings.GRADING_RESULTS_JSON
    if not json_path.exists():
        logger.info(f"找不到评分数据: {json_path}")
        logger.info("请确认已经执行过评分或者数据文件存在。")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    logger.info(f"正在启动多线程扫描 {len(data)} 个作品的 Blender 文件...")

    # 用多线程加速扫描，8线程大概率能跑满磁盘IO
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_index = {executor.submit(check_blender, i, item): i for i, item in enumerate(data)}
        
        count = 0
        blender_count = 0
        for future in as_completed(future_to_index):
            i, is_blender = future.result()
            
            # 确保 group_info 存在
            if "group_info" not in data[i]:
                data[i]["group_info"] = {}
                
            data[i]["group_info"]["is_blender"] = is_blender
            
            count += 1
            if is_blender:
                blender_count += 1
                
            print(f"\r进度: {count}/{len(data)}", end="")

    logger.info(f"\n扫描完成！共发现 {blender_count} 个 Blender 作品。")
    
    # 将更新后的数据写回 JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    logger.info(f"已将 is_blender 标记持久化写入到 {json_path.name} 中。")
    logger.info("您可以重新启动服务器 (.\\server.bat restart)，现在作品列表页面将会秒开。")

if __name__ == "__main__":
    main()

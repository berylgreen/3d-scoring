import os
import sys
import json
import pandas as pd
from pathlib import Path

# 引入项目配置
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.logger import logger

def main():
    json_path = settings.GRADING_RESULTS_JSON
    
    if not json_path.exists():
        logger.error(f"错误: 找不到文件 {json_path}")
        return
    
    logger.info(f"正在读取 JSON 数据: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        all_results = json.load(f)
        
    if not all_results:
        logger.warning("JSON 文件中没有数据！")
        return
        
    # 转换为 DataFrame
    df = pd.DataFrame(all_results)
    
    # 导出到 Excel
    excel_path = settings.EXCEL_PATH
    if not excel_path:
        excel_path = settings.RESULT_DIR / "评分记录表.xlsx"
        
    logger.info(f"正在生成 Excel 表格...")
    df.to_excel(excel_path, index=False)
    
    logger.info(f"成功！Excel 表格已保存至: {excel_path}")

if __name__ == "__main__":
    main()

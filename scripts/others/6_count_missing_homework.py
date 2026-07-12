import pandas as pd
import glob
import os
import sys
import yaml
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

CONFIG_PATH = os.path.join(Path(__file__).resolve().parent.parent.parent, "config.yaml")
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        app_config = yaml.safe_load(f)
        base_dir = app_config.get("data_dir")
        if not base_dir:
            print("错误: config.yaml 中未配置 data_dir")
            sys.exit(1)
except Exception as e:
    print(f"错误: 读取 config.yaml 失败: {e}")
    sys.exit(1)

score_dir = os.path.join(base_dir, "平时成绩")
target_files = [f for f in glob.glob(os.path.join(score_dir, "*.xlsx")) if not os.path.basename(f).startswith('~$')]
if not target_files:
    print(f"错误: 未在 {score_dir} 找到目标汇总 Excel 文件")
    sys.exit(1)
target_file = target_files[0]
print(f"找到目标汇总文件: {target_file}")

missing_hw_dir = os.path.join(score_dir, "缺交作品名单")
if not os.path.exists(missing_hw_dir):
    print(f"错误: 未找到缺交作品名单目录: {missing_hw_dir}")
    sys.exit(1)

hw_files = [f for f in os.listdir(missing_hw_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
if not hw_files:
    print(f"错误: 在 {missing_hw_dir} 中没有找到任何缺交作业文件")
    sys.exit(1)

# Load target file to get the correct column names
df_target = pd.read_excel(target_file)
print("Target file columns:", df_target.columns.tolist())

# Process missing homework files
missing_counts = {}

for hw_file in hw_files:
    file_path = os.path.join(missing_hw_dir, hw_file)
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue
    
    df_hw = pd.read_excel(file_path)
    # The student ID column might be named '学号/工号' or '学号'
    id_col = None
    for col in df_hw.columns:
        if '学号' in col:
            id_col = col
            break
            
    if not id_col:
        print(f"Could not find student ID column in {file_path}. Columns: {df_hw.columns.tolist()}")
        continue
        
    for student_id in df_hw[id_col].dropna():
        # Convert to string to avoid float/int mismatches
        sid = str(student_id).strip()
        if sid.endswith('.0'):
            sid = sid[:-2]
        missing_counts[sid] = missing_counts.get(sid, 0) + 1

print(f"Total students with missing homeworks: {len(missing_counts)}")
print("Sample missing counts:", list(missing_counts.items())[:5])

# Find student ID column in target file
target_id_col = None
for col in df_target.columns:
    if '学号' in col:
        target_id_col = col
        break

if not target_id_col:
    print(f"Could not find student ID column in target file. Columns: {df_target.columns.tolist()}")
    exit(1)

# Initialize "缺交作业次数" column
if "缺交作业次数" not in df_target.columns:
    df_target["缺交作业次数"] = 0

# Update the target dataframe
for index, row in df_target.iterrows():
    sid = str(row[target_id_col]).strip()
    if sid.endswith('.0'):
        sid = sid[:-2]
    
    if sid in missing_counts:
        df_target.at[index, "缺交作业次数"] = missing_counts[sid]
    else:
        df_target.at[index, "缺交作业次数"] = 0

df_target.to_excel(target_file, index=False)
print("Target file updated successfully.")

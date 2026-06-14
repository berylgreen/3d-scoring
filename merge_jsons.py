import os
import json
import glob

base_dir = r"Z:\学生文件\考试学生答卷\2025-2026上\计算机三维动画设计提高\result"
output_file = os.path.join(base_dir, "grading_results.json")

all_data = []

pattern = os.path.join(base_dir, "**", "*_评分数据.json")
files = glob.glob(pattern, recursive=True)

for file_path in files:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_data.append(data)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")

# 根据学号排序，让数据更好看一些
try:
    all_data.sort(key=lambda x: x.get("student_info", {}).get("student_id", ""))
except:
    pass

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"Successfully merged {len(all_data)} json files into {output_file}")

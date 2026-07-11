import os
import re
import shutil
from pathlib import Path
from collections import defaultdict
import datetime

def main():
    target_dir = r"\\UGREEN-FF03\cc_4TRaid1\学生文件\考试学生答卷\2025-2026下\计算机三维动画设计基础\课堂考察"
    target_path = Path(target_dir)
    
    if not target_path.exists():
        print(f"Directory not found: {target_dir}")
        return

    student_files = defaultdict(list)
    id_pattern = re.compile(r'^(\d{10,})') # match at least 10 digits to be safe as student ID

    for item in target_path.iterdir():
        match = id_pattern.search(item.name)
        if match:
            student_id = match.group(1)
            try:
                mtime = item.stat().st_mtime
                student_files[student_id].append({
                    'path': item,
                    'mtime': mtime,
                    'name': item.name
                })
            except Exception as e:
                pass

    to_delete = []

    for student_id, files in student_files.items():
        if len(files) > 1:
            files.sort(key=lambda x: x['mtime'], reverse=True)
            print(f"\nStudent ID: {student_id} has {len(files)} files/folders:")
            for i, f in enumerate(files):
                dt = datetime.datetime.fromtimestamp(f['mtime'])
                print(f"  [{i}] {f['name']} (Last Modified: {dt})")
            
            # keep the first (newest), delete the rest
            to_delete.extend(files[1:])

    print(f"\nTotal files/folders to delete: {len(to_delete)}")
    
    deleted_count = 0
    for item in to_delete:
        path_to_delete = item['path']
        try:
            if path_to_delete.is_dir():
                shutil.rmtree(path_to_delete)
            else:
                path_to_delete.unlink()
            print(f"Successfully deleted: {item['name']}")
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {item['name']}: {e}")

    print(f"Cleanup finished. Deleted {deleted_count} items.")

if __name__ == "__main__":
    main()

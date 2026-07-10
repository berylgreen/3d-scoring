import json
import os
import re
import shutil
import pandas as pd

def fix_missing_student_ids():
    json_path = r'z:\学生文件\考试学生答卷\2025-2026下\三维动画技术\result\grading_results.json'
    excel_path = r'z:\学生文件\考试学生答卷\2025-2026下\三维动画技术\student.xlsx'
    
    print("开始从 Excel 加载官方学生名单...")
    df = pd.read_excel(excel_path)
    official_students = {}
    official_names_to_ids = {}
    for _, row in df.iterrows():
        sid = None
        sname = None
        for val in row.values:
            val_str = str(val).strip()
            if not sid and re.match(r'^\d{11,13}$', val_str):
                sid = val_str
            elif not sname and isinstance(val, str) and 1 < len(val) <= 4 and re.match(r'^[\u4e00-\u9fa5]+$', val_str):
                sname = val_str
        if sid and sname:
            official_students[sid] = sname
            if sname not in official_names_to_ids:
                official_names_to_ids[sname] = []
            official_names_to_ids[sname].append(sid)

    print(f"成功加载 {len(official_students)} 名学生信息。")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changed = False
    
    for group in data:
        group_name = group.get('group_info', {}).get('group_name')
        if not group_name:
            continue
            
        for ind in group.get('individuals', []):
            stu_name = ind.get('student_name', '').strip()
            sid = str(ind.get('student_id', '')).strip()
            
            # 如果学号不存在，或者学号对应的官方姓名与当前姓名不符
            if not sid or sid == 'N/A' or official_students.get(sid) != stu_name:
                possible_ids = official_names_to_ids.get(stu_name, [])
                if len(possible_ids) == 1:
                    matched_id = possible_ids[0]
                    if sid != matched_id:
                        ind['student_id'] = matched_id
                        print(f"成功修复 -> 组别: {group_name} | 姓名: {stu_name} | 原学号: {sid if sid and sid != 'N/A' else '无'} -> 新学号: {matched_id}")
                        changed = True
                elif len(possible_ids) > 1:
                    print(f"修复失败 -> 姓名 '{stu_name}' 在名单中存在重名，无法唯一确定学号。")
                elif not possible_ids:
                    print(f"未能修复 -> 组别: {group_name} | 姓名: {stu_name} (在Excel名单中未找到该姓名)")

        # Cleanup phase: remove individuals that are likely project names / garbage
        official_names = set(official_students.values())
        original_inds = group.get('individuals', [])
        original_len = len(original_inds)
        
        if original_len <= 1:
            valid_inds = original_inds
        else:
            valid_inds = []
            deleted_inds = []
            for ind in original_inds:
                sid = ind.get('student_id')
                sname = ind.get('student_name', '')
                
                # Keep if: 1) Has valid numeric student ID, OR 2) Name is an official student name
                if (sid and sid != 'N/A' and str(sid).isdigit()) or (sname in official_names):
                    valid_inds.append(ind)
                else:
                    deleted_inds.append(ind)
                    
            # 保证每个作品下至少有一个学生信息
            if len(valid_inds) == 0 and len(deleted_inds) > 0:
                valid_inds = original_inds
            else:
                for ind in deleted_inds:
                    print(f"清理错误人名 (可能是项目名/乱码) -> 组别: {group_name} | 删除姓名: '{ind.get('student_name', '')}'")
                    changed = True
                
        if len(valid_inds) != original_len:
            group['individuals'] = valid_inds

    if changed:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\n修复与清理完成，已更新 grading_results.json")
    else:
        print("\n没有需要修复或清理的数据。")

if __name__ == '__main__':
    fix_missing_student_ids()

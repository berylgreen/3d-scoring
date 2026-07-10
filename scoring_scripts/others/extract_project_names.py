import os
import re
import pandas as pd

def extract_project_name(folder_name, all_student_names):
    # Clean suffix like (1), (2)
    name = re.sub(r'\(\d+\)$', '', folder_name).strip()
    
    # Replace common words with separators
    name = name.replace('组长', '_').replace('组员', '_')
    
    # Split by separators
    parts = re.split(r'[_\-\s]+', name)
    
    project_name = parts[0]
    
    # If the project name still contains student names without separators
    for student_name in all_student_names:
        if student_name in project_name and len(project_name) > len(student_name):
            project_name = project_name.replace(student_name, '')
            
    return project_name.strip()

def main():
    excel_path = r'\\ugreen-ff03\cc_4TRaid1\学生文件\考试学生答卷\2025-2026下\计算机三维动画设计基础\24数媒.xlsx'
    work_dir = r'\\ugreen-ff03\cc_4TRaid1\学生文件\考试学生答卷\2025-2026下\计算机三维动画设计基础\作品'
    
    print(f"Reading excel file: {excel_path}")
    df = pd.read_excel(excel_path, dtype=str)
    
    print(f"Scanning directory: {work_dir}")
    dirs = [d for d in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, d))]
    
    student_id_col = None
    student_name_col = None
    
    for col in df.columns:
        if '学号' in col:
            student_id_col = col
        elif '姓名' in col:
            student_name_col = col
            
    if not student_id_col or not student_name_col:
        print("Error: Could not find '学号' or '姓名' columns in the excel file.")
        return
        
    all_student_names = [str(x).strip() for x in df[student_name_col].tolist()]
    
    # Initialize the new column
    df['项目名称'] = ''
    match_count = 0
    
    for index, row in df.iterrows():
        student_id = str(row[student_id_col]).strip()
        student_name = str(row[student_name_col]).strip()
        
        # Find which directory belongs to this student
        matched_dir = None
        for d in dirs:
            if student_name in d or student_id in d:
                matched_dir = d
                break
                
        if matched_dir:
            project_name = extract_project_name(matched_dir, all_student_names)
            df.at[index, '项目名称'] = project_name
            match_count += 1
            
    # Save back to the excel file
    print(f"Matched {match_count} out of {len(df)} students.")
    df.to_excel(excel_path, index=False, engine='openpyxl')
    print("Successfully updated the excel file with project names.")

if __name__ == '__main__':
    main()

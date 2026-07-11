import json
import pandas as pd
from pathlib import Path

def main():
    # File paths
    script_dir = Path(__file__).resolve().parent
    json_path = script_dir / 'grading_results.json'
    excel_path = r'\\ugreen-ff03\cc_4TRaid1\学生文件\考试学生答卷\2025-2026下\计算机三维动画设计基础\24数媒.xlsx'
    output_excel_path = script_dir / 'grading_results.xlsx'

    print(f"Loading JSON from: {json_path}")
    if not json_path.exists():
        print(f"Error: JSON file not found at {json_path}")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        grading_results = json.load(f)

    print(f"Loading Excel from: {excel_path}")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error reading excel file: {e}")
        return

    # Prepare new columns
    df['成绩'] = None
    df['评语'] = ''

    matched_count = 0
    # Match and fill data
    for index, row in df.iterrows():
        student_id = str(row['学号']).strip()
        student_name = str(row['姓名']).strip()
        
        # Find matching key in JSON
        match_found = False
        for key, value in grading_results.items():
            if student_id in key:
                df.at[index, '成绩'] = value.get('score')
                df.at[index, '评语'] = value.get('comment')
                match_found = True
                matched_count += 1
                break
        
        # Fallback to name matching if ID not found
        if not match_found:
            for key, value in grading_results.items():
                if student_name in key:
                    df.at[index, '成绩'] = value.get('score')
                    df.at[index, '评语'] = value.get('comment')
                    matched_count += 1
                    break
                    
    print(f"Matched {matched_count} out of {len(df)} students.")

    # Save to new Excel file
    try:
        df.to_excel(output_excel_path, index=False)
        print(f"Successfully saved graded results to {output_excel_path}")
    except Exception as e:
        print(f"Error saving excel file: {e}")

if __name__ == '__main__':
    main()

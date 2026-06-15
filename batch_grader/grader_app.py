import os
import sys
import json
import traceback
from pathlib import Path

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import settings
from core.factory import LLMFactory
from core.data_loader import (
    collect_targets_from_disk,
    find_video_file,
    find_docx_file,
    extract_docx_content,
    JSON_DATA_PATH
)
from batch_grader import prompts
import re

def extract_names_from_string(text):
    """提取组长、组员名字的简单启发式"""
    names = []
    leaders = re.findall(r'组长([\u4e00-\u9fa5]{2,4})', text)
    members = re.findall(r'组员([\u4e00-\u9fa5]{2,4})', text)
    for l in leaders: names.append(f"组长: {l}")
    for m in members: names.append(f"组员: {m}")
    if not names:
        clean_text = re.sub(r'组长|组员|23数媒|3D建模|三维', ' ', text)
        clean_text = re.sub(r'[0-9\(\)\.（）\-_]', ' ', clean_text)
        parts = clean_text.split()
        for p in parts:
             if len(p) >= 2 and len(p) <= 4 and p not in ['作业', '作品', '提交', '考试', '最终', '渲染']:
                 names.append(p)
    return names

def get_file_structure(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), directory)
            files.append(rel_path)
    return files

class Evaluator:
    def __init__(self):
        print("Initializing LLM...")
        factory = LLMFactory(config_path=str(PROJECT_ROOT / "config" / "settings.yaml"))
        self.llm = factory.create_llm()

    def grade_target(self, target: dict) -> dict:
        """根据配置，对目标（学生或小组）进行评分"""
        folder_path = target["folder_path"]
        target_name = target.get("folder_name", "")
        
        # 提取共有资源：文档
        docx_path = find_docx_file(folder_path)
        if docx_path:
            document_content = extract_docx_content(docx_path, as_html=False)
            if len(document_content) > 6000:
                document_content = document_content[:6000] + "...[截断]"
        else:
            document_content = "未找到报告文档。"

        # 区分课程和模式
        if settings.COURSE_TYPE == "animation":
            return self._grade_animation(target_name, folder_path, document_content)
        else:
            return self._grade_modeling(target_name, folder_path, document_content)

    def _grade_animation(self, target_name, folder_path, document_content):
        # Animation 模式下，上传视频
        video_path = find_video_file(folder_path)
        uploaded_video = None
        if video_path and settings.ENABLE_LLM_GRADING:
            try:
                uploaded_video = self.llm.upload_file(video_path)
            except Exception as e:
                print(f"  [警告] 视频上传失败: {e}")
        
        try:
            if settings.GRADING_MODE == "individual":
                prompt = prompts.ANIMATION_INDIVIDUAL_PROMPT.format(
                    target_name=target_name,
                    document_content=document_content
                )
            else:
                # Group
                known_names = extract_names_from_string(target_name)
                prompt = prompts.ANIMATION_GROUP_PROMPT.format(
                    target_name=target_name,
                    known_names=known_names,
                    document_content=document_content
                )
                
            schema = {
                "type": "object",
                "properties": {
                    "group_info": {
                        "type": "object",
                        "properties": {
                            "scores": {
                                "type": "object",
                                "properties": {
                                    "creativity": {"type": "number"},
                                    "storyboard": {"type": "number"},
                                    "modeling": {"type": "number"},
                                    "basic_tech": {"type": "number"},
                                    "adv_tech": {"type": "number"},
                                    "fluency": {"type": "number"},
                                    "rendering": {"type": "number"},
                                    "document": {"type": "number"}
                                }
                            },
                            "workload_comment": {"type": "string"},
                            "comments": {"type": "string"}
                        }
                    },
                    "individuals": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "student_name": {"type": "string"},
                                "task_description": {"type": "string"},
                                "individual_score": {"type": "number"},
                                "individual_comment": {"type": "string"}
                            }
                        }
                    }
                }
            }

            files = [uploaded_video] if uploaded_video else []
            result = self.llm.generate_structured(prompt, schema=schema, files=files)
            
            # Post process format into consistent JSON format for data loader
            import os
            class_name = os.path.basename(os.path.dirname(folder_path))
            extracted_names = extract_names_from_string(target_name)
            student_id = extracted_names[0] if extracted_names else target_name
            
            group_info = result.setdefault("group_info", {})
            group_info["class_name"] = class_name
            group_info["folder_path"] = folder_path
            group_info["student_id"] = student_id
            group_info["name"] = target_name
            group_info["project_name"] = target_name
            
            scores = group_info.get("scores", {})
            group_info["total_score"] = sum(scores.values()) if scores else 0
            group_info["max_score"] = 100
            
            return result
                
        finally:
            if uploaded_video:
                self.llm.delete_file(uploaded_video)

    def _grade_modeling(self, target_name, folder_path, document_content):
        file_list = get_file_structure(folder_path)
        file_list_str = "\n".join(file_list[:100]) # limit to 100 files
        
        if settings.GRADING_MODE == "group":
            known_names = extract_names_from_string(target_name)
            prompt = prompts.MODELING_GROUP_PROMPT.format(
                target_name=target_name,
                known_names=known_names,
                file_list_str=file_list_str,
                document_content=document_content
            )
        else:
            # Individual modeling logic
            prompt = prompts.MODELING_INDIVIDUAL_PROMPT.format(
                file_list_str=file_list_str,
                document_content=document_content
            )
            
        schema = {
            "type": "object",
            "properties": {
                "group_info": {
                    "type": "object",
                    "properties": {
                        "scores": {
                            "type": "object",
                            "properties": {
                                "theme_difficulty": {"type": "number"},
                                "modeling_accuracy": {"type": "number"},
                                "topology": {"type": "number"},
                                "materials_textures": {"type": "number"},
                                "uv_mapping": {"type": "number"},
                                "lighting_rendering": {"type": "number"},
                                "visual_quality": {"type": "number"},
                                "documentation": {"type": "number"}
                            }
                        },
                        "workload_comment": {"type": "string"},
                        "comments": {"type": "string"}
                    }
                },
                "individuals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "student_name": {"type": "string"},
                            "task_description": {"type": "string"},
                            "individual_score": {"type": "number"},
                            "individual_comment": {"type": "string"}
                        }
                    }
                }
            }
        }
            
        result = self.llm.generate_structured(prompt, schema=schema)
        
        # Post process format into consistent JSON format for data loader
        import os
        class_name = os.path.basename(os.path.dirname(folder_path))
        extracted_names = extract_names_from_string(target_name)
        student_id = extracted_names[0] if extracted_names else target_name
        
        group_info = result.setdefault("group_info", {})
        group_info["class_name"] = class_name
        group_info["folder_path"] = folder_path
        group_info["student_id"] = student_id
        group_info["name"] = target_name
        group_info["project_name"] = target_name
        
        scores = group_info.get("scores", {})
        group_info["total_score"] = sum(scores.values()) if scores else 0
        group_info["max_score"] = 100
        
        return result

def run_batch():
    print("=" * 60)
    print(f"3D 评分系统 - {settings.COURSE_TYPE.upper()} - {settings.GRADING_MODE.upper()}")
    print("=" * 60)
    
    if not settings.ENABLE_LLM_GRADING:
        print("大模型评分已禁用。")
        return
        
    targets = collect_targets_from_disk()
    print(f"找到 {len(targets)} 个待评分目标。")
    
    results = []
    if JSON_DATA_PATH.exists():
        try:
            with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except Exception as e:
            print(f"Error loading existing results: {e}")
            
    # Processed names
    processed_names = set()
    for item in results:
        info = item.get("group_info", {}) or item.get("student_info", {}) or item
        name = info.get("name", "")
        if not name: 
            name = info.get("folder_name", "")
        if name:
            processed_names.add(name)

    targets_to_process = [t for t in targets if t["folder_name"] not in processed_names]
    print(f"需要处理: {len(targets_to_process)}")
    
    evaluator = Evaluator()
    
    for target in targets_to_process:
        print(f"\nProcessing: {target['folder_name']}")
        try:
            result = evaluator.grade_target(target)
            results.append(result)
            
            # Atomic save
            JSON_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            temp_file = JSON_DATA_PATH.with_name(JSON_DATA_PATH.name + '.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, JSON_DATA_PATH)
            
        except Exception as e:
            print(f"Error processing {target['folder_name']}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    run_batch()

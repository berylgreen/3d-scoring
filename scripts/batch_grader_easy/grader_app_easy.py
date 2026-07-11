# -*- coding: utf-8 -*-
"""
简单课堂评分脚本
用于自动读取学生的课堂截图与参考图并发送给大模型进行评分
"""

import os
import sys
import glob
import json
import shutil
import zipfile
from pathlib import Path

# 将 scripts 目录加入 sys.path 以便导入 core 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.factory import LLMFactory
from core.logger import logger
import yaml

CONFIG_PATH = os.path.join(Path(__file__).resolve().parent.parent.parent, "config.yaml")
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        app_config = yaml.safe_load(f)
        base_dir = app_config.get("data_dir", r"\\ugreen-ff03\cc_4TRaid1\学生文件\考试学生答卷\2025-2026下\计算机三维动画设计基础")
except Exception as e:
    logger.warning(f"读取 config.yaml 失败，使用默认路径: {e}")
    base_dir = r"\\ugreen-ff03\cc_4TRaid1\学生文件\考试学生答卷\2025-2026下\计算机三维动画设计基础"

TARGET_DIR = os.path.join(base_dir, "课堂考察")
REFERENCE_IMG = os.path.join(TARGET_DIR, "2.jpg")
PIC_DIR = os.path.join(TARGET_DIR, "pic")
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "grading_results.json")

def extract_images_from_docx(docx_path, output_dir):
    """从docx文档中提取图片并保存到目标目录"""
    extracted = []
    try:
        with zipfile.ZipFile(docx_path, 'r') as zip_ref:
            for item in zip_ref.namelist():
                if item.startswith('word/media/'):
                    filename = os.path.basename(item)
                    if not filename:
                        continue
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in ['.jpg', '.jpeg', '.png']:
                        continue
                    
                    target_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(docx_path))[0]}_{filename}")
                    # 避免重复提取
                    if not os.path.exists(target_path):
                        with open(target_path, "wb") as target:
                            with zip_ref.open(item) as source:
                                shutil.copyfileobj(source, target)
                    extracted.append(target_path)
    except Exception as e:
        logger.warning(f"从文档 {os.path.basename(docx_path)} 提取图片失败: {e}")
    return extracted

def get_latest_image(folder_path):
    """获取文件夹下最新的一张图片"""
    def find_images():
        extensions = ('*.jpg', '*.jpeg', '*.png')
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(folder_path, '**', ext), recursive=True))
            files.extend(glob.glob(os.path.join(folder_path, '**', ext.upper()), recursive=True))
        return files
        
    files = find_images()
    
    if not files:
        # 如果没找到图片，尝试查找docx文档并提取图片
        docx_files = glob.glob(os.path.join(folder_path, '**', '*.docx'), recursive=True)
        docx_files.extend(glob.glob(os.path.join(folder_path, '**', '*.DOCX'), recursive=True))
        
        for docx_path in docx_files:
            logger.info(f"未找到直接的图片，尝试从 {os.path.basename(docx_path)} 提取...")
            extract_images_from_docx(docx_path, os.path.dirname(docx_path))
            
        # 提取完后再查找一次图片
        files = find_images()
    
    if not files:
        return None
        
    # 按修改时间降序排序，取最新的一张
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files[0]

def main():
    logger.info("正在初始化大模型客户端...")
    try:
        factory = LLMFactory()
        llm = factory.create_llm()
    except Exception as e:
        logger.error(f"大模型初始化失败: {e}")
        return

    results = {}
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            try:
                results = json.load(f)
                logger.info(f"已加载之前的评分记录，共 {len(results)} 条")
            except Exception as e:
                logger.warning(f"无法加载现有的 JSON 记录: {e}")

    schema = {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "评分，1到10之间的整数"
            },
            "comment": {
                "type": "string",
                "description": "简短的评价，说明给分的理由，例如与参考图的相似度、建模细节等"
            }
        },
        "required": ["score", "comment"]
    }
    
    prompt = (
        "我将提供两张图片。第一张是参考标准图，第二张是学生的课堂建模成果图。\n"
        "请你对比学生的成果和参考图，给学生的成果打分（1-10分），并给出简短评价。\n"
        "参考图中如果有多个视角，请综合评估学生成果与参考模型的相似度、细节完成度和结构比例等。"
    )

    if not os.path.exists(TARGET_DIR):
        logger.error(f"找不到目标文件夹: {TARGET_DIR}")
        return
        
    if not os.path.exists(REFERENCE_IMG):
        logger.error(f"找不到参考图: {REFERENCE_IMG}")
        return

    if not os.path.exists(PIC_DIR):
        os.makedirs(PIC_DIR, exist_ok=True)

    student_folders = [f for f in os.listdir(TARGET_DIR) if os.path.isdir(os.path.join(TARGET_DIR, f)) and f != "pic"]
    total = len(student_folders)
    
    logger.info(f"找到 {total} 个学生文件夹。")

    for i, student_name in enumerate(student_folders, 1):
        folder_path = os.path.join(TARGET_DIR, student_name)
        
        # 如果已经有有效的评分结果，则跳过（支持断点续跑）
        if student_name in results and "score" in results[student_name] and results[student_name]["score"] != 0:
            logger.info(f"[{i}/{total}] 跳过 {student_name}，已存在评分。")
            continue
            
        latest_img = get_latest_image(folder_path)
        if not latest_img:
            logger.warning(f"[{i}/{total}] {student_name} 文件夹下没有找到图片。")
            results[student_name] = {"error": "未找到图片", "score": 0, "comment": "缺少作品图片"}
            continue
            
        logger.info(f"[{i}/{total}] 正在为 {student_name} 评分，使用图片: {os.path.basename(latest_img)}")
        
        try:
            ext = os.path.splitext(latest_img)[1]
            dest_img = os.path.join(PIC_DIR, f"{student_name}{ext}")
            shutil.copy2(latest_img, dest_img)
        except Exception as e:
            logger.warning(f"复制图片失败: {e}")

        files = [REFERENCE_IMG, latest_img]
        
        try:
            res = llm.generate_structured(prompt=prompt, schema=schema, files=files)
            logger.info(f"  -> 结果: {res}")
            results[student_name] = res
        except Exception as e:
            logger.error(f"  -> 评分失败: {e}")
            results[student_name] = {"error": str(e), "score": 0, "comment": f"评分出错: {e}"}
            
        # 实时保存到 JSON，防止中断丢失进度
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
            
    logger.info(f"\n全部评分已完成！结果已保存在: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
统一版 3D 评分管理 Web 系统
"""

import sys
import os
import json
import base64
import re
from pathlib import Path

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, render_template, request, jsonify, send_file, abort, Response
from core.config import settings
from core.data_loader import (
    load_all_targets,
    get_target_by_id,
    find_video_file,
    find_docx_file,
    extract_docx_content,
    find_thumbnail,
    find_effect_images,
    find_personal_images,
    find_max_files
)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.route('/')
def index():
    """首页 - 列表"""
    return render_template('index.html', mode=settings.GRADING_MODE, course=settings.COURSE_TYPE)

@app.route('/api/targets')
def api_targets():
    """获取所有目标数据"""
    targets = load_all_targets()
    # Sort by score desc by default
    targets.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    return jsonify({"success": True, "data": targets})

@app.route('/detail/<path:target_id>')
def detail(target_id):
    """详情页"""
    target = get_target_by_id(target_id)
    if not target:
        abort(404, description="Target not found")
        
    return render_template('detail.html', 
                          target_id=target_id,
                          mode=settings.GRADING_MODE, 
                          course=settings.COURSE_TYPE)

@app.route('/students')
def students():
    """学生列表页"""
    return render_template('students.html', mode=settings.GRADING_MODE, course=settings.COURSE_TYPE)

@app.route('/api/students')
def api_students():
    """获取所有学生及其成绩（兼容旧UI）"""
    targets = load_all_targets()
    students_list = []
    
    for t in targets:
        group_score = t.get("total_score", 0)
        inds = t.get("individuals", [])
        if not inds:
            # If no individuals defined, treat target as individual
            students_list.append({
                "student_name": t.get("name", "Unknown"),
                "student_id": "N/A",
                "group_name": t.get("name", "Unknown"),
                "group_score": group_score,
                "individual_score": 0,
                "total_score": group_score
            })
            continue
            
        for ind in inds:
            ind_score = ind.get("individual_score", 0)
            students_list.append({
                "student_name": ind.get("student_name", "Unknown"),
                "student_id": ind.get("student_id", "N/A"),
                "group_name": t.get("name", "Unknown"),
                "group_score": group_score,
                "individual_score": ind_score,
                "total_score": group_score + ind_score
            })
            
    # Default sort
    students_list.sort(key=lambda x: x["total_score"], reverse=True)
    return jsonify({"students": students_list, "total": len(students_list)})

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    path = request.json.get('folder_path')
    if path and os.path.exists(path):
        # 优先打开包含 Word 文档的子目录
        docx_path = find_docx_file(path)
        open_path = os.path.dirname(docx_path) if docx_path and os.path.exists(docx_path) else path
        os.startfile(open_path)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Folder not found"}), 404

@app.route('/api/open-file', methods=['POST'])
def open_file():
    path = request.json.get('file_path')
    if path and os.path.exists(path):
        os.startfile(path)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "File not found"}), 404

@app.route('/api/target/<path:target_id>')
def api_target_detail(target_id):
    """获取目标详细数据"""
    target = get_target_by_id(target_id)
    if not target:
        return jsonify({"success": False, "error": "Not found"}), 404
        
    folder_path = target.get("folder_path")
    
    # 获取文档内容
    docx_path = find_docx_file(folder_path)
    docx_html = extract_docx_content(docx_path, as_html=True) if docx_path else "<p class='text-gray-500 italic'>未找到报告文档 (.docx)</p>"
    
    response_data = {
        "success": True,
        "target": target,
        "document_html": docx_html,
        "media": {}
    }
    
    if settings.COURSE_TYPE == "animation":
        video_path = find_video_file(folder_path)
        if video_path:
            response_data["media"]["video_url"] = f"/api/video/{target_id}"
    else:
        # Modeling: effect images, personal images, max files
        effect_images = find_effect_images(folder_path)
        response_data["media"]["effect_images"] = [f"/api/image/{target_id}/effect/{i}" for i in range(len(effect_images))]
        
        if settings.GRADING_MODE == "group":
            personal_images = find_personal_images(folder_path, target.get("individuals", []))
            response_data["media"]["personal_images"] = {name: f"/api/image/{target_id}/personal/{name}" for name in personal_images}
            
    max_files = find_max_files(folder_path)
    response_data["media"]["max_files"] = max_files

    return jsonify(response_data)

@app.route('/api/thumbnail/<path:target_id>')
def api_thumbnail(target_id):
    target = get_target_by_id(target_id)
    if not target: abort(404)
    
    if settings.COURSE_TYPE == "animation":
        video_path = find_video_file(target.get("folder_path"))
        if video_path and os.path.exists(video_path):
            cache_dir = os.path.join(PROJECT_ROOT, "thumbnail_cache")
            os.makedirs(cache_dir, exist_ok=True)
            safe_id = target_id.replace('/', '_').replace('\\', '_')
            cached_thumb = os.path.join(cache_dir, f"{safe_id}_frame_5s.jpg")
            
            if os.path.exists(cached_thumb):
                return send_file(cached_thumb)
            else:
                try:
                    import cv2
                    cap = cv2.VideoCapture(video_path)
                    
                    # 尝试跳到第5秒 (5000毫秒)
                    cap.set(cv2.CAP_PROP_POS_MSEC, 5000)
                    ret, frame = cap.read()
                    
                    # 如果视频长度不足5秒或读取失败，则回退读取第一帧
                    if not ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        
                    cap.release()
                    
                    if ret:
                        # 解决 OpenCV 在 Windows 下写入中文路径失败的问题
                        is_success, buffer = cv2.imencode(".jpg", frame)
                        if is_success:
                            with open(cached_thumb, "wb") as f:
                                f.write(buffer)
                        return send_file(cached_thumb)
                except Exception as e:
                    print(f"提取视频帧失败 {video_path}: {e}")

    thumb_path = find_thumbnail(target.get("folder_path"))
    if thumb_path and os.path.exists(thumb_path):
        return send_file(thumb_path)
        
    # Default thumbnail if missing
    return jsonify({"error": "No thumbnail"}), 404

@app.route('/api/video/<path:target_id>')
def api_video(target_id):
    target = get_target_by_id(target_id)
    if not target: abort(404)
    
    video_path = find_video_file(target.get("folder_path"))
    if not video_path or not os.path.exists(video_path):
        abort(404)
        
    return _stream_video(video_path)

@app.route('/api/image/<path:target_id>/<image_type>/<image_key>')
def api_image(target_id, image_type, image_key):
    target = get_target_by_id(target_id)
    if not target: abort(404)
    
    folder_path = target.get("folder_path")
    if image_type == "effect":
        idx = int(image_key)
        images = find_effect_images(folder_path)
        if 0 <= idx < len(images) and os.path.exists(images[idx]):
            return send_file(images[idx])
    elif image_type == "personal":
        images = find_personal_images(folder_path, target.get("individuals", []))
        if image_key in images and os.path.exists(images[image_key]):
            return send_file(images[image_key])
            
    abort(404)

def _stream_video(video_path):
    range_header = request.headers.get('Range', None)
    file_size = os.path.getsize(video_path)
    
    if not range_header:
        return send_file(video_path, mimetype='video/mp4')
        
    byte1, byte2 = 0, None
    match = re.search(r'(\d+)-(\d*)', range_header)
    g = match.groups()
    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])
        
    length = file_size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1
        
    with open(video_path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)
        
    rv = Response(data, 206, mimetype='video/mp4', content_type='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{file_size}')
    return rv

if __name__ == '__main__':
    import re
    print(f"Starting Web UI - Course: {settings.COURSE_TYPE}, Mode: {settings.GRADING_MODE}")
    app.run(host='0.0.0.0', port=5000, debug=True)

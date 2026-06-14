# -*- coding: utf-8 -*-
"""
统一版 3D 评分管理 Web 系统
"""

import sys
import os
import json
import base64
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

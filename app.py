#!/usr/bin/env python3
"""
Flask Web Application for Minecraft Resource Pack Merger
提供友好的用户界面来合并Minecraft资源包
"""
from flask import Flask, render_template, request, send_file, jsonify, url_for
import shutil
from pathlib import Path
from werkzeug.utils import secure_filename

# Import merge functionality from merge_packs.py
from merge_packs import (
    load_pack_info, Merger, is_valid_resource_pack,
    extract_zip_pack
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload
app.config['UPLOAD_FOLDER'] = Path('uploads')
app.config['OUTPUT_FOLDER'] = Path('outputs')
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Ensure folders exist
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'zip'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files(folder, max_age_hours=24):
    """清理超过指定时间的旧文件"""
    import time
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    for item in folder.iterdir():
        if item.is_file() or item.is_dir():
            age = now - item.stat().st_mtime
            if age > max_age_seconds:
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception as e:
                    print(f"Failed to delete {item}: {e}")


@app.route('/')
def index():
    """主页 - 显示上传界面"""
    cleanup_old_files(app.config['UPLOAD_FOLDER'])
    cleanup_old_files(app.config['OUTPUT_FOLDER'])
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """处理资源包上传"""
    if 'packs' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    files = request.files.getlist('packs')
    if not files or len(files) == 0:
        return jsonify({'error': '请至少上传一个资源包'}), 400

    # Create a unique session directory
    import uuid
    session_id = str(uuid.uuid4())
    session_dir = app.config['UPLOAD_FOLDER'] / session_id
    session_dir.mkdir(exist_ok=True)

    uploaded_packs = []
    temp_dir = session_dir / 'temp'
    temp_dir.mkdir(exist_ok=True)

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = session_dir / filename
            file.save(filepath)

            # Extract and validate the pack
            extracted = extract_zip_pack(filepath, temp_dir)
            if extracted:
                pack_info = load_pack_info(extracted)
                uploaded_packs.append({
                    'name': pack_info.name,
                    'path': str(extracted.relative_to(session_dir)),
                    'pack_format': pack_info.pack_format,
                    'description': pack_info.description,
                    'has_png': pack_info.has_pack_png
                })

    if not uploaded_packs:
        shutil.rmtree(session_dir)
        return jsonify({'error': '没有找到有效的资源包'}), 400

    return jsonify({
        'session_id': session_id,
        'packs': uploaded_packs
    })


@app.route('/merge', methods=['POST'])
def merge_packs():
    """执行资源包合并"""
    data = request.json
    session_id = data.get('session_id')
    pack_order = data.get('pack_order', [])  # List of pack names in priority order
    output_name = data.get('output_name', 'merged_pack')
    description = data.get('description', '')
    pack_format = data.get('pack_format')
    create_zip = data.get('create_zip', True)

    if not session_id:
        return jsonify({'error': '无效的会话ID'}), 400

    session_dir = app.config['UPLOAD_FOLDER'] / session_id
    if not session_dir.exists():
        return jsonify({'error': '会话不存在或已过期'}), 404

    temp_dir = session_dir / 'temp'
    if not temp_dir.exists():
        return jsonify({'error': '没有找到上传的资源包'}), 404

    # Detect all packs in temp directory
    detected_packs = []
    for item in temp_dir.iterdir():
        if item.is_dir() and is_valid_resource_pack(item):
            detected_packs.append(item)

    if not detected_packs:
        return jsonify({'error': '没有找到有效的资源包'}), 400

    # Order packs according to user preference
    if pack_order:
        pack_dict = {p.name: p for p in detected_packs}
        ordered_packs = []
        for name in pack_order:
            if name in pack_dict:
                ordered_packs.append(pack_dict[name])
        # Add any packs not in the order list
        for p in detected_packs:
            if p not in ordered_packs:
                ordered_packs.append(p)
        pack_paths = ordered_packs
    else:
        pack_paths = sorted(detected_packs, key=lambda p: p.name.lower())

    packs = [load_pack_info(p) for p in pack_paths]

    # Create output directory
    output_id = f"{session_id}_{output_name}"
    output_dir = app.config['OUTPUT_FOLDER'] / output_id

    if output_dir.exists():
        shutil.rmtree(output_dir)

    try:
        # Run merger
        merger = Merger(
            packs,
            out_dir=output_dir,
            dry_run=False,
            clean=False,
            exclude_patterns=[],
            pack_format_override=pack_format,
            description_override=description if description else None,
        )
        merger.run()

        # Create zip if requested
        zip_path = None
        if create_zip:
            zip_path = app.config['OUTPUT_FOLDER'] / f"{output_id}.zip"
            if zip_path.exists():
                zip_path.unlink()
            shutil.make_archive(str(zip_path.with_suffix('')), 'zip', root_dir=output_dir)

        return jsonify({
            'success': True,
            'output_id': output_id,
            'stats': {
                'copied': merger.stats.copied,
                'overwritten': merger.stats.overwritten,
                'merged_json': merger.stats.merged_json,
                'skipped': merger.stats.skipped,
                'errors': merger.stats.errors
            },
            'download_url': url_for('download', output_id=output_id) if create_zip else None
        })

    except Exception as e:
        return jsonify({'error': f'合并失败: {str(e)}'}), 500


@app.route('/download/<output_id>')
def download(output_id):
    """下载合并后的资源包"""
    zip_path = app.config['OUTPUT_FOLDER'] / f"{output_id}.zip"
    if not zip_path.exists():
        return "文件不存在", 404

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"{output_id}.zip",
        mimetype='application/zip'
    )


if __name__ == '__main__':
    print("=" * 60)
    print("Minecraft 资源包合并器 Web 应用")
    print("=" * 60)
    print("访问: http://localhost:5001")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)


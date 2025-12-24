"""
路由定义
"""
import csv
import io
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, Response, abort

from core import models as db
from core.services import feedback_classifier, user_type_parser, csv_column_detector, kanban_category_generator

# 创建蓝图
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)


# ============ 页面路由 ============

@main_bp.route('/')
def index():
    """首页"""
    batches = db.get_all_batches()
    latest_batch = db.get_latest_batch()
    
    stats = None
    grouped_feedbacks = None
    
    if latest_batch:
        stats = db.get_batch_statistics(latest_batch['id'])
        grouped_feedbacks = db.get_all_feedbacks_grouped(latest_batch['id'])
    
    return render_template('index.html',
                           batches=batches,
                           current_batch=latest_batch,
                           stats=stats,
                           grouped_feedbacks=grouped_feedbacks)


@main_bp.route('/batch/<int:batch_id>')
def view_batch(batch_id):
    """查看指定批次"""
    batches = db.get_all_batches()
    current_batch = db.get_batch_by_id(batch_id)
    
    if not current_batch:
        abort(404, description="批次不存在")
    
    stats = db.get_batch_statistics(batch_id)
    grouped_feedbacks = db.get_all_feedbacks_grouped(batch_id)
    
    return render_template('index.html',
                           batches=batches,
                           current_batch=current_batch,
                           stats=stats,
                           grouped_feedbacks=grouped_feedbacks)


@main_bp.route('/upload', methods=['POST'])
def upload_csv():
    """上传CSV文件并分析"""
    if 'file' not in request.files:
        return jsonify({"success": False, "detail": "没有上传文件"}), 400
    
    file = request.files['file']
    
    if not file.filename.endswith('.csv'):
        return jsonify({"success": False, "detail": "请上传CSV文件"}), 400
    
    try:
        # 读取文件内容
        contents = file.read()
        
        # 尝试不同编码
        decoded_content = None
        for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
            try:
                decoded_content = contents.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if decoded_content is None:
            return jsonify({"success": False, "detail": "无法解析文件编码"}), 400
        
        # 解析CSV
        csv_reader = csv.reader(io.StringIO(decoded_content))
        rows = list(csv_reader)
        
        if len(rows) < 2:
            return jsonify({"success": False, "detail": "CSV文件内容为空或格式不正确"}), 400
        
        headers = rows[0]
        data_rows = rows[1:]
        
        # 自动检测列
        col_indices = csv_column_detector.detect(headers)
        content_col = col_indices['content']
        user_type_col = col_indices['user_type']
        attachment_col = col_indices['attachment']
        
        if content_col is None:
            # 如果没找到，默认使用第一列
            content_col = 0
        
        # 创建批次（存储表头信息）
        headers_json = json.dumps(headers, ensure_ascii=False)
        batch_id = db.create_upload_batch(file.filename, len(data_rows), headers_json)
        
        # 处理每行数据
        feedbacks = []
        for row in data_rows:
            if len(row) <= content_col:
                continue
            
            content = row[content_col].strip()
            if not content:
                continue
            
            user_type = "未知"
            if user_type_col is not None and len(row) > user_type_col:
                user_type = user_type_parser.parse(row[user_type_col])
            
            # 提取附件信息
            attachment = ""
            if attachment_col is not None and len(row) > attachment_col:
                raw_attachment = row[attachment_col].strip()
                # 处理特殊格式：第一行可能是数字（附件数量），后面才是URL
                if raw_attachment:
                    lines = raw_attachment.split('\n')
                    urls = []
                    for line in lines:
                        line = line.strip()
                        if line and (line.startswith('http://') or line.startswith('https://')):
                            urls.append(line)
                    if urls:
                        # 如果找到URL，用换行符连接
                        attachment = '\n'.join(urls)
                    elif not raw_attachment.isdigit():
                        # 如果不是纯数字，保留原内容
                        attachment = raw_attachment
            
            category = feedback_classifier.classify(content)
            
            feedbacks.append({
                'user_type': user_type,
                'content': content,
                'category': category,
                'attachment': attachment,
                'original_row': json.dumps(row, ensure_ascii=False)
            })
        
        # 批量插入
        db.insert_feedbacks_batch(batch_id, feedbacks)
        
        # 统计有附件的数量
        attachment_count = sum(1 for fb in feedbacks if fb.get('attachment'))
        
        # 查找包含"附件"的列（用于调试）
        attachment_related_cols = [(i, h) for i, h in enumerate(headers) if '附件' in h]
        
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "total_processed": len(feedbacks),
            "message": f"成功处理 {len(feedbacks)} 条反馈",
            "debug_info": {
                "headers": headers,
                "headers_count": len(headers),
                "detected_content_col": content_col,
                "detected_user_type_col": user_type_col,
                "detected_attachment_col": attachment_col,
                "content_col_name": headers[content_col] if content_col is not None and content_col < len(headers) else None,
                "user_type_col_name": headers[user_type_col] if user_type_col is not None and user_type_col < len(headers) else None,
                "attachment_col_name": headers[attachment_col] if attachment_col is not None and attachment_col < len(headers) else None,
                "attachment_related_cols": attachment_related_cols,
                "feedbacks_with_attachment": attachment_count,
                "sample_attachment": feedbacks[0].get('attachment', '') if feedbacks else None
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "detail": f"处理文件时出错: {str(e)}"}), 500


@main_bp.route('/batch/<int:batch_id>', methods=['DELETE'])
def delete_batch(batch_id):
    """删除批次"""
    db.delete_batch(batch_id)
    return jsonify({"success": True, "message": "批次已删除"})


@main_bp.route('/export/<int:batch_id>')
def export_batch(batch_id):
    """导出批次数据为CSV"""
    stats = db.get_batch_statistics(batch_id)
    grouped = db.get_all_feedbacks_grouped(batch_id)
    
    # 生成CSV内容
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["分类", "内容", "用户类型"])
    
    for category, feedbacks in grouped.items():
        for fb in feedbacks:
            writer.writerow([category, fb['content'], fb['user_type']])
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=feedback_export_{batch_id}.csv"}
    )


@api_bp.route('/feedback/<int:feedback_id>/detail', methods=['GET'])
def get_feedback_detail(feedback_id):
    """获取反馈详情（包括原始行数据和表头）"""
    feedback = db.get_feedback_by_id(feedback_id)
    if not feedback:
        return jsonify({"success": False, "detail": "反馈不存在"}), 404
    
    # 获取批次信息以获取表头
    batch = db.get_batch_by_id(feedback['upload_batch_id'])
    headers = []
    if batch and batch.get('headers'):
        try:
            headers = json.loads(batch['headers'])
        except:
            pass
    
    # 解析原始行数据
    original_row = []
    if feedback.get('original_row'):
        try:
            original_row = json.loads(feedback['original_row'])
        except:
            pass
    
    # 组合表头和数据
    detail_fields = []
    for i, value in enumerate(original_row):
        field_name = headers[i] if i < len(headers) else f"字段{i+1}"
        detail_fields.append({
            "name": field_name,
            "value": value
        })
    
    return jsonify({
        "success": True,
        "feedback_id": feedback_id,
        "content": feedback.get('content', ''),
        "user_type": feedback.get('user_type', ''),
        "category": feedback.get('category', ''),
        "attachment": feedback.get('attachment', ''),
        "fields": detail_fields
    })


@api_bp.route('/feedback/<int:feedback_id>/category', methods=['PUT'])
def update_feedback_category(feedback_id):
    """更新反馈分类"""
    data = request.get_json()
    new_category = data.get('category', '').strip()
    
    if not new_category:
        return jsonify({"success": False, "detail": "分类名称不能为空"}), 400
    
    feedback = db.get_feedback_by_id(feedback_id)
    if not feedback:
        return jsonify({"success": False, "detail": "反馈不存在"}), 404
    
    db.update_feedback_category(feedback_id, new_category)
    
    # 返回更新后的统计信息
    stats = db.get_batch_statistics(feedback['upload_batch_id'])
    
    return jsonify({
        "success": True,
        "message": f"已移动到 {new_category}",
        "stats": stats
    })


@api_bp.route('/batch/<int:batch_id>/categories', methods=['GET'])
def get_batch_categories(batch_id):
    """获取批次的所有分类"""
    categories = db.get_all_categories_for_batch(batch_id)
    return jsonify({"success": True, "categories": categories})


@api_bp.route('/batch/<int:batch_id>/category/rename', methods=['PUT'])
def rename_category(batch_id):
    """重命名分类"""
    data = request.get_json()
    old_name = data.get('old_name', '').strip()
    new_name = data.get('new_name', '').strip()
    
    if not old_name or not new_name:
        return jsonify({"success": False, "detail": "分类名称不能为空"}), 400
    
    if old_name == new_name:
        return jsonify({"success": False, "detail": "新名称与原名称相同"}), 400
    
    # 检查新名称是否已存在
    existing = db.get_all_categories_for_batch(batch_id)
    if new_name in existing:
        return jsonify({"success": False, "detail": f"分类「{new_name}」已存在"}), 400
    
    affected = db.rename_category(batch_id, old_name, new_name)
    
    if affected == 0:
        return jsonify({"success": False, "detail": "未找到该分类"}), 404
    
    # 返回更新后的统计
    stats = db.get_batch_statistics(batch_id)
    
    return jsonify({
        "success": True,
        "message": f"已将「{old_name}」重命名为「{new_name}」，共更新 {affected} 条反馈",
        "affected": affected,
        "stats": stats
    })


@main_bp.route('/kanban')
def kanban():
    """看板页面"""
    categories = db.get_all_kanban_categories()
    kanban_data = db.get_all_kanban_items()
    stats = db.get_kanban_statistics()
    
    return render_template('kanban.html',
                           categories=categories,
                           kanban_data=kanban_data,
                           stats=stats)


# ============ API路由 ============

@api_bp.route('/stats/<int:batch_id>')
def get_stats(batch_id):
    """获取统计数据API"""
    stats = db.get_batch_statistics(batch_id)
    grouped = db.get_all_feedbacks_grouped(batch_id)
    return jsonify({
        "stats": stats,
        "grouped_feedbacks": grouped
    })


@api_bp.route('/category/<int:batch_id>/<category>')
def get_category_feedbacks(batch_id, category):
    """获取指定分类的反馈"""
    feedbacks = db.get_feedbacks_by_category(batch_id, category)
    return jsonify({"feedbacks": feedbacks})


@api_bp.route('/categories')
def get_categories():
    """获取所有分类"""
    return jsonify({"categories": feedback_classifier.get_categories()})


@api_bp.route('/health')
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "message": "服务运行正常"})


# ============ 看板API路由 ============

@api_bp.route('/kanban/add', methods=['POST'])
def add_to_kanban():
    """将反馈添加到看板"""
    data = request.get_json()
    feedback_id = data.get('feedback_id')
    category_id = data.get('category_id')
    note = data.get('note', '')
    
    if not feedback_id:
        return jsonify({"success": False, "detail": "缺少反馈ID"}), 400
    
    # 检查反馈是否存在
    feedback = db.get_feedback_by_id(feedback_id)
    if not feedback:
        return jsonify({"success": False, "detail": "反馈不存在"}), 404
    
    item_id = db.add_feedback_to_kanban(feedback_id, category_id, note)
    
    return jsonify({
        "success": True,
        "item_id": item_id,
        "message": "已添加到看板"
    })


@api_bp.route('/kanban/remove', methods=['POST'])
def remove_from_kanban():
    """从看板中移除反馈"""
    data = request.get_json()
    feedback_id = data.get('feedback_id')
    
    if not feedback_id:
        return jsonify({"success": False, "detail": "缺少反馈ID"}), 400
    
    db.remove_feedback_from_kanban(feedback_id)
    
    return jsonify({
        "success": True,
        "message": "已从看板移除"
    })


@api_bp.route('/kanban/move', methods=['POST'])
def move_kanban_item():
    """移动看板项目到新分类"""
    data = request.get_json()
    feedback_id = data.get('feedback_id')
    new_category_id = data.get('category_id')
    
    if not feedback_id:
        return jsonify({"success": False, "detail": "缺少反馈ID"}), 400
    
    # 获取看板项目
    item = db.get_kanban_item_by_feedback_id(feedback_id)
    if not item:
        return jsonify({"success": False, "detail": "项目不存在"}), 404
    
    db.move_kanban_item(item['id'], new_category_id)
    
    return jsonify({
        "success": True,
        "message": "已移动到新分类"
    })


@api_bp.route('/kanban/all', methods=['GET'])
def get_all_kanban_data():
    """获取所有看板数据，按批次过滤"""
    batch_id = request.args.get('batch_id', type=int)
    # 分类也按批次过滤，确保每个文件的分类独立
    categories = db.get_all_kanban_categories(batch_id)
    kanban_data = db.get_all_kanban_items(batch_id)
    return jsonify({
        "success": True,
        "categories": categories,
        "kanban_data": kanban_data,
        "batch_id": batch_id
    })


@api_bp.route('/kanban/category', methods=['POST'])
def add_kanban_category():
    """添加看板分类"""
    data = request.get_json()
    batch_id = data.get('batch_id')
    name = data.get('name', '').strip()
    color = data.get('color', '#3B82F6')
    
    if not batch_id:
        return jsonify({"success": False, "detail": "缺少批次ID"}), 400
    
    if not name:
        return jsonify({"success": False, "detail": "分类名称不能为空"}), 400
    
    category_id = db.create_kanban_category(batch_id, name, color)
    
    return jsonify({
        "success": True,
        "category_id": category_id,
        "message": f"分类 '{name}' 创建成功"
    })


@api_bp.route('/kanban/categories', methods=['GET'])
def get_kanban_categories():
    """获取所有看板分类"""
    categories = db.get_all_kanban_categories()
    return jsonify({"categories": categories})


@api_bp.route('/kanban/categories', methods=['POST'])
def create_kanban_category_api():
    """创建看板分类"""
    data = request.get_json()
    batch_id = data.get('batch_id')
    name = data.get('name', '').strip()
    color = data.get('color', '#3B82F6')
    
    if not batch_id:
        return jsonify({"success": False, "detail": "缺少批次ID"}), 400
    
    if not name:
        return jsonify({"success": False, "detail": "分类名称不能为空"}), 400
    
    category_id = db.create_kanban_category(batch_id, name, color)
    
    return jsonify({
        "success": True,
        "category_id": category_id,
        "message": f"分类 '{name}' 创建成功"
    })


@api_bp.route('/kanban/categories/<int:category_id>', methods=['PUT'])
def update_kanban_category(category_id):
    """更新看板分类"""
    data = request.get_json()
    name = data.get('name')
    color = data.get('color')
    
    db.update_kanban_category(category_id, name, color)
    
    return jsonify({
        "success": True,
        "message": "分类已更新"
    })


@api_bp.route('/kanban/categories/<int:category_id>', methods=['DELETE'])
def delete_kanban_category(category_id):
    """删除看板分类"""
    db.delete_kanban_category(category_id)
    
    return jsonify({
        "success": True,
        "message": "分类已删除"
    })


@api_bp.route('/kanban/generate-category-name', methods=['POST'])
def generate_category_name():
    """根据内容自动生成分类名称"""
    data = request.get_json()
    feedback_ids = data.get('feedback_ids', [])
    
    if not feedback_ids:
        return jsonify({"success": False, "detail": "缺少反馈ID列表"}), 400
    
    # 获取反馈内容
    contents = []
    for fid in feedback_ids:
        feedback = db.get_feedback_by_id(fid)
        if feedback:
            contents.append(feedback['content'])
    
    if not contents:
        return jsonify({"success": False, "detail": "未找到有效反馈"}), 404
    
    # 生成分类名
    suggested_name = kanban_category_generator.generate_category_name(contents)
    
    return jsonify({
        "success": True,
        "suggested_name": suggested_name
    })


@api_bp.route('/kanban/data')
def get_kanban_data():
    """获取看板所有数据"""
    kanban_data = db.get_all_kanban_items()
    stats = db.get_kanban_statistics()
    categories = db.get_all_kanban_categories()
    
    return jsonify({
        "kanban_data": kanban_data,
        "stats": stats,
        "categories": categories
    })


@api_bp.route('/kanban/check/<int:feedback_id>')
def check_in_kanban(feedback_id):
    """检查反馈是否在看板中"""
    in_kanban = db.is_feedback_in_kanban(feedback_id)
    item = None
    if in_kanban:
        item = db.get_kanban_item_by_feedback_id(feedback_id)
    
    return jsonify({
        "in_kanban": in_kanban,
        "item": item
    })


@api_bp.route('/migrate/update-headers', methods=['POST'])
def migrate_update_headers():
    """为旧批次更新表头信息"""
    # 获取所有批次
    batches = db.get_all_batches()
    
    # 找到有 headers 的最新批次
    source_batch = None
    for batch in batches:
        if batch.get('headers'):
            source_batch = batch
            break
    
    if not source_batch:
        return jsonify({"success": False, "detail": "没有找到包含表头的批次"}), 400
    
    headers = source_batch['headers']
    updated_count = 0
    
    # 更新所有没有 headers 的批次
    conn = db.get_connection()
    cursor = conn.cursor()
    
    for batch in batches:
        if not batch.get('headers'):
            db.execute_query(cursor, "UPDATE upload_batches SET headers = ? WHERE id = ?", (headers, batch['id']))
            updated_count += 1
    
    conn.commit()
    
    return jsonify({
        "success": True,
        "message": f"已更新 {updated_count} 个批次的表头信息",
        "headers_source": source_batch['filename'],
        "updated_count": updated_count
    })


@api_bp.route('/batches/info', methods=['GET'])
def get_batches_info():
    """获取所有批次的信息（包括 headers 状态）"""
    batches = db.get_all_batches()
    result = []
    for batch in batches:
        result.append({
            "id": batch['id'],
            "filename": batch['filename'],
            "has_headers": bool(batch.get('headers')),
            "total_count": batch.get('total_count', 0)
        })
    return jsonify({"batches": result})


# 注册数据库连接清理
@main_bp.teardown_app_request
def teardown_db(exception):
    """请求结束时关闭数据库连接"""
    db.close_connection(exception)


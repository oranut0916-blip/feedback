"""
路由定义
"""
import csv
import io
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, Response, abort

from app import models as db
from app.services import feedback_classifier, user_type_parser, csv_column_detector

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
        
        if content_col is None:
            # 如果没找到，默认使用第一列
            content_col = 0
        
        # 创建批次
        batch_id = db.create_upload_batch(file.filename, len(data_rows))
        
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
            
            category = feedback_classifier.classify(content)
            
            feedbacks.append({
                'user_type': user_type,
                'content': content,
                'category': category,
                'original_row': json.dumps(row, ensure_ascii=False)
            })
        
        # 批量插入
        db.insert_feedbacks_batch(batch_id, feedbacks)
        
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "total_processed": len(feedbacks),
            "message": f"成功处理 {len(feedbacks)} 条反馈",
            "debug_info": {
                "headers": headers,
                "detected_content_col": content_col,
                "detected_user_type_col": user_type_col,
                "content_col_name": headers[content_col] if content_col is not None and content_col < len(headers) else None,
                "user_type_col_name": headers[user_type_col] if user_type_col is not None and user_type_col < len(headers) else None
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


# 注册数据库连接清理
@main_bp.teardown_app_request
def teardown_db(exception):
    """请求结束时关闭数据库连接"""
    db.close_connection(exception)


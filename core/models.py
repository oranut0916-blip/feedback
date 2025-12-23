"""
数据库模型和操作
"""
import sqlite3
from typing import List, Dict, Optional
import os
from flask import current_app, g


def get_db_path():
    """获取数据库路径"""
    try:
        return current_app.config['DATABASE_PATH']
    except RuntimeError:
        # 如果不在应用上下文中，使用默认路径
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'feedback.db')


def get_connection():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(get_db_path())
        g.db.row_factory = sqlite3.Row
    return g.db


def close_connection(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_standalone_connection():
    """获取独立数据库连接（非Flask上下文）"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_standalone_connection()
    cursor = conn.cursor()
    
    # 创建反馈表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_batch_id INTEGER NOT NULL,
            user_type TEXT,
            content TEXT NOT NULL,
            category TEXT,
            original_row TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建上传批次表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS upload_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            total_count INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def create_upload_batch(filename: str, total_count: int) -> int:
    """创建上传批次记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO upload_batches (filename, total_count) VALUES (?, ?)",
        (filename, total_count)
    )
    batch_id = cursor.lastrowid
    conn.commit()
    return batch_id


def insert_feedbacks_batch(batch_id: int, feedbacks: List[Dict]):
    """批量插入反馈"""
    conn = get_connection()
    cursor = conn.cursor()
    for fb in feedbacks:
        cursor.execute(
            """INSERT INTO feedbacks (upload_batch_id, user_type, content, category, original_row) 
               VALUES (?, ?, ?, ?, ?)""",
            (batch_id, fb['user_type'], fb['content'], fb['category'], fb['original_row'])
        )
    conn.commit()


def get_all_batches() -> List[Dict]:
    """获取所有上传批次"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_batches ORDER BY uploaded_at DESC")
    batches = [dict(row) for row in cursor.fetchall()]
    return batches


def get_batch_by_id(batch_id: int) -> Optional[Dict]:
    """根据ID获取批次"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_batches WHERE id = ?", (batch_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_batch_statistics(batch_id: int) -> Dict:
    """获取指定批次的统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 总数
    cursor.execute("SELECT COUNT(*) as total FROM feedbacks WHERE upload_batch_id = ?", (batch_id,))
    total = cursor.fetchone()['total']
    
    # 用户类型分布
    cursor.execute("""
        SELECT user_type, COUNT(*) as count 
        FROM feedbacks 
        WHERE upload_batch_id = ? 
        GROUP BY user_type
    """, (batch_id,))
    user_distribution = {row['user_type']: row['count'] for row in cursor.fetchall()}
    
    # 分类统计
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM feedbacks 
        WHERE upload_batch_id = ? 
        GROUP BY category 
        ORDER BY count DESC
    """, (batch_id,))
    category_stats = [{'category': row['category'], 'count': row['count']} for row in cursor.fetchall()]
    
    return {
        'total': total,
        'user_distribution': user_distribution,
        'category_stats': category_stats
    }


def get_feedbacks_by_category(batch_id: int, category: str) -> List[Dict]:
    """获取指定批次和分类的所有反馈"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM feedbacks 
           WHERE upload_batch_id = ? AND category = ? 
           ORDER BY created_at DESC""",
        (batch_id, category)
    )
    feedbacks = [dict(row) for row in cursor.fetchall()]
    return feedbacks


def get_all_feedbacks_grouped(batch_id: int) -> Dict[str, List[Dict]]:
    """获取指定批次所有反馈，按分类分组"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM feedbacks 
           WHERE upload_batch_id = ? 
           ORDER BY category, created_at DESC""",
        (batch_id,)
    )
    feedbacks = [dict(row) for row in cursor.fetchall()]
    
    # 按分类分组
    grouped = {}
    for fb in feedbacks:
        cat = fb['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(fb)
    
    return grouped


def delete_batch(batch_id: int):
    """删除指定批次及其所有反馈"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM feedbacks WHERE upload_batch_id = ?", (batch_id,))
    cursor.execute("DELETE FROM upload_batches WHERE id = ?", (batch_id,))
    conn.commit()


def get_latest_batch() -> Optional[Dict]:
    """获取最新的上传批次"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_batches ORDER BY uploaded_at DESC LIMIT 1")
    row = cursor.fetchone()
    return dict(row) if row else None


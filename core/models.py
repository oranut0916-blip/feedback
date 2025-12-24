"""
数据库模型和操作
支持 SQLite (本地开发) 和 PostgreSQL (Vercel Postgres)
"""
import os
from typing import List, Dict, Optional
from flask import current_app, g


# ============ 数据库连接管理 ============

def is_postgres():
    """检查是否使用 PostgreSQL"""
    try:
        return current_app.config.get('USE_POSTGRES', False)
    except RuntimeError:
        return os.environ.get('POSTGRES_URL') is not None


def get_postgres_url():
    """获取 PostgreSQL 连接URL"""
    try:
        return current_app.config.get('POSTGRES_URL')
    except RuntimeError:
        return os.environ.get('POSTGRES_URL')


def get_db_path():
    """获取 SQLite 数据库路径"""
    try:
        return current_app.config['DATABASE_PATH']
    except RuntimeError:
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'feedback.db')


def get_connection():
    """获取数据库连接"""
    if 'db' not in g:
        if is_postgres():
            import psycopg2
            import psycopg2.extras
            g.db = psycopg2.connect(get_postgres_url())
            g.db_type = 'postgres'
        else:
            import sqlite3
            g.db = sqlite3.connect(get_db_path())
            g.db.row_factory = sqlite3.Row
            g.db_type = 'sqlite'
    return g.db


def close_connection(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_standalone_connection():
    """获取独立数据库连接（非Flask上下文）"""
    if os.environ.get('POSTGRES_URL'):
        import psycopg2
        return psycopg2.connect(os.environ.get('POSTGRES_URL'))
    else:
        import sqlite3
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'feedback.db')
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn


def execute_query(cursor, query, params=None):
    """执行查询，自动处理占位符差异"""
    if is_postgres():
        # PostgreSQL 使用 %s 占位符
        query = query.replace('?', '%s')
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)


def dict_from_row(row, cursor=None):
    """将数据库行转换为字典"""
    if is_postgres():
        if cursor and hasattr(cursor, 'description'):
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return dict(row) if hasattr(row, 'keys') else row
    else:
        return dict(row)


def fetchall_as_dict(cursor):
    """获取所有结果并转为字典列表"""
    rows = cursor.fetchall()
    if is_postgres():
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    else:
        return [dict(row) for row in rows]


def fetchone_as_dict(cursor):
    """获取单个结果并转为字典"""
    row = cursor.fetchone()
    if row is None:
        return None
    if is_postgres():
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    else:
        return dict(row)


# ============ 数据库初始化 ============

def init_db():
    """初始化数据库表"""
    conn = get_standalone_connection()
    cursor = conn.cursor()
    
    use_pg = os.environ.get('POSTGRES_URL') is not None
    
    if use_pg:
        # PostgreSQL 语法
        # 创建反馈表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id SERIAL PRIMARY KEY,
                upload_batch_id INTEGER NOT NULL,
                user_type TEXT,
                content TEXT NOT NULL,
                category TEXT,
                attachment TEXT,
                original_row TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建上传批次表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_batches (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                total_count INTEGER DEFAULT 0,
                headers TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建看板分类表（每个批次独立的分类）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_categories (
                id SERIAL PRIMARY KEY,
                batch_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#3B82F6',
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES upload_batches(id)
            )
        """)
        
        # 创建看板项目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_items (
                id SERIAL PRIMARY KEY,
                feedback_id INTEGER NOT NULL,
                category_id INTEGER,
                note TEXT,
                sort_order INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feedback_id) REFERENCES feedbacks(id),
                FOREIGN KEY (category_id) REFERENCES kanban_categories(id)
            )
        """)
    else:
        # SQLite 语法
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_batch_id INTEGER NOT NULL,
                user_type TEXT,
                content TEXT NOT NULL,
                category TEXT,
                attachment TEXT,
                original_row TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 尝试添加 attachment 列
        try:
            cursor.execute("ALTER TABLE feedbacks ADD COLUMN attachment TEXT")
        except:
            pass
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                total_count INTEGER DEFAULT 0,
                headers TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 尝试添加 headers 列（如果表已存在但没有这个列）
        try:
            cursor.execute("ALTER TABLE upload_batches ADD COLUMN headers TEXT")
        except:
            pass
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#3B82F6',
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES upload_batches(id)
            )
        """)
        
        # 尝试添加 batch_id 列（如果表已存在但没有这个列）
        try:
            cursor.execute("ALTER TABLE kanban_categories ADD COLUMN batch_id INTEGER DEFAULT 0")
        except:
            pass
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_id INTEGER NOT NULL,
                category_id INTEGER,
                note TEXT,
                sort_order INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feedback_id) REFERENCES feedbacks(id),
                FOREIGN KEY (category_id) REFERENCES kanban_categories(id)
            )
        """)
    
    conn.commit()
    conn.close()


# ============ 上传批次操作 ============

def create_upload_batch(filename: str, total_count: int, headers: str = None) -> int:
    """创建上传批次记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_postgres():
        cursor.execute(
            "INSERT INTO upload_batches (filename, total_count, headers) VALUES (%s, %s, %s) RETURNING id",
            (filename, total_count, headers)
        )
        batch_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            "INSERT INTO upload_batches (filename, total_count, headers) VALUES (?, ?, ?)",
            (filename, total_count, headers)
        )
        batch_id = cursor.lastrowid
    
    conn.commit()
    return batch_id


def insert_feedbacks_batch(batch_id: int, feedbacks: List[Dict]):
    """批量插入反馈"""
    conn = get_connection()
    cursor = conn.cursor()
    
    for fb in feedbacks:
        if is_postgres():
            cursor.execute(
                """INSERT INTO feedbacks (upload_batch_id, user_type, content, category, attachment, original_row) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (batch_id, fb['user_type'], fb['content'], fb['category'], fb.get('attachment', ''), fb['original_row'])
            )
        else:
            cursor.execute(
                """INSERT INTO feedbacks (upload_batch_id, user_type, content, category, attachment, original_row) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (batch_id, fb['user_type'], fb['content'], fb['category'], fb.get('attachment', ''), fb['original_row'])
            )
    conn.commit()


def get_all_batches() -> List[Dict]:
    """获取所有上传批次"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_batches ORDER BY uploaded_at DESC")
    return fetchall_as_dict(cursor)


def get_batch_by_id(batch_id: int) -> Optional[Dict]:
    """根据ID获取批次"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT * FROM upload_batches WHERE id = ?", (batch_id,))
    return fetchone_as_dict(cursor)


def get_batch_statistics(batch_id: int) -> Dict:
    """获取指定批次的统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 总数
    execute_query(cursor, "SELECT COUNT(*) as total FROM feedbacks WHERE upload_batch_id = ?", (batch_id,))
    total = fetchone_as_dict(cursor)['total']
    
    # 用户类型分布
    execute_query(cursor, """
        SELECT user_type, COUNT(*) as count 
        FROM feedbacks 
        WHERE upload_batch_id = ? 
        GROUP BY user_type
    """, (batch_id,))
    user_distribution = {row['user_type']: row['count'] for row in fetchall_as_dict(cursor)}
    
    # 分类统计
    execute_query(cursor, """
        SELECT category, COUNT(*) as count 
        FROM feedbacks 
        WHERE upload_batch_id = ? 
        GROUP BY category 
        ORDER BY count DESC
    """, (batch_id,))
    category_stats = [{'category': row['category'], 'count': row['count']} for row in fetchall_as_dict(cursor)]
    
    return {
        'total': total,
        'user_distribution': user_distribution,
        'category_stats': category_stats
    }


def get_feedbacks_by_category(batch_id: int, category: str) -> List[Dict]:
    """获取指定批次和分类的所有反馈"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor,
        """SELECT * FROM feedbacks 
           WHERE upload_batch_id = ? AND category = ? 
           ORDER BY created_at DESC""",
        (batch_id, category)
    )
    return fetchall_as_dict(cursor)


def get_all_feedbacks_grouped(batch_id: int) -> Dict[str, List[Dict]]:
    """获取指定批次所有反馈，按分类分组"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor,
        """SELECT * FROM feedbacks 
           WHERE upload_batch_id = ? 
           ORDER BY category, created_at DESC""",
        (batch_id,)
    )
    feedbacks = fetchall_as_dict(cursor)
    
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
    execute_query(cursor, "DELETE FROM feedbacks WHERE upload_batch_id = ?", (batch_id,))
    execute_query(cursor, "DELETE FROM upload_batches WHERE id = ?", (batch_id,))
    conn.commit()


def get_latest_batch() -> Optional[Dict]:
    """获取最新的上传批次"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upload_batches ORDER BY uploaded_at DESC LIMIT 1")
    return fetchone_as_dict(cursor)


# ============ 看板相关操作 ============

def create_kanban_category(batch_id: int, name: str, color: str = '#3B82F6') -> int:
    """创建看板分类（每个批次独立）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取该批次的最大排序值
    if is_postgres():
        cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM kanban_categories WHERE batch_id = %s", (batch_id,))
    else:
        cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM kanban_categories WHERE batch_id = ?", (batch_id,))
    sort_order = cursor.fetchone()[0]
    
    if is_postgres():
        cursor.execute(
            "INSERT INTO kanban_categories (batch_id, name, color, sort_order) VALUES (%s, %s, %s, %s) RETURNING id",
            (batch_id, name, color, sort_order)
        )
        category_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            "INSERT INTO kanban_categories (batch_id, name, color, sort_order) VALUES (?, ?, ?, ?)",
            (batch_id, name, color, sort_order)
        )
        category_id = cursor.lastrowid
    
    conn.commit()
    return category_id


def get_all_kanban_categories(batch_id: int = None) -> List[Dict]:
    """获取看板分类（按批次过滤）"""
    conn = get_connection()
    cursor = conn.cursor()
    if batch_id is not None:
        if is_postgres():
            cursor.execute("SELECT * FROM kanban_categories WHERE batch_id = %s ORDER BY sort_order", (batch_id,))
        else:
            cursor.execute("SELECT * FROM kanban_categories WHERE batch_id = ? ORDER BY sort_order", (batch_id,))
    else:
        cursor.execute("SELECT * FROM kanban_categories ORDER BY sort_order")
    return fetchall_as_dict(cursor)


def get_kanban_category_by_id(category_id: int) -> Optional[Dict]:
    """根据ID获取看板分类"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT * FROM kanban_categories WHERE id = ?", (category_id,))
    return fetchone_as_dict(cursor)


def update_kanban_category(category_id: int, name: str = None, color: str = None):
    """更新看板分类"""
    conn = get_connection()
    cursor = conn.cursor()
    updates = []
    params = []
    
    placeholder = '%s' if is_postgres() else '?'
    
    if name is not None:
        updates.append(f"name = {placeholder}")
        params.append(name)
    if color is not None:
        updates.append(f"color = {placeholder}")
        params.append(color)
    if updates:
        params.append(category_id)
        query = f"UPDATE kanban_categories SET {', '.join(updates)} WHERE id = {placeholder}"
        cursor.execute(query, params)
        conn.commit()


def delete_kanban_category(category_id: int):
    """删除看板分类（分类下的项目会变成未分类）"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "UPDATE kanban_items SET category_id = NULL WHERE category_id = ?", (category_id,))
    execute_query(cursor, "DELETE FROM kanban_categories WHERE id = ?", (category_id,))
    conn.commit()


def add_feedback_to_kanban(feedback_id: int, category_id: int = None, note: str = None) -> int:
    """将反馈添加到看板"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查是否已在看板中
    execute_query(cursor, "SELECT id FROM kanban_items WHERE feedback_id = ?", (feedback_id,))
    existing = cursor.fetchone()
    
    if existing:
        # 如果已存在，更新分类
        if is_postgres():
            cursor.execute(
                "UPDATE kanban_items SET category_id = %s, note = %s WHERE feedback_id = %s",
                (category_id, note, feedback_id)
            )
            return existing[0]
        else:
            cursor.execute(
                "UPDATE kanban_items SET category_id = ?, note = ? WHERE feedback_id = ?",
                (category_id, note, feedback_id)
            )
            return existing['id']
    
    # 获取最大排序值
    if is_postgres():
        if category_id is None:
            cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM kanban_items WHERE category_id IS NULL")
        else:
            cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM kanban_items WHERE category_id = %s", (category_id,))
    else:
        cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM kanban_items WHERE category_id IS ?", (category_id,))
    
    sort_order = cursor.fetchone()[0]
    
    if is_postgres():
        cursor.execute(
            "INSERT INTO kanban_items (feedback_id, category_id, note, sort_order) VALUES (%s, %s, %s, %s) RETURNING id",
            (feedback_id, category_id, note, sort_order)
        )
        item_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            "INSERT INTO kanban_items (feedback_id, category_id, note, sort_order) VALUES (?, ?, ?, ?)",
            (feedback_id, category_id, note, sort_order)
        )
        item_id = cursor.lastrowid
    
    conn.commit()
    return item_id


def remove_feedback_from_kanban(feedback_id: int):
    """从看板中移除反馈"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "DELETE FROM kanban_items WHERE feedback_id = ?", (feedback_id,))
    conn.commit()


def move_kanban_item(item_id: int, new_category_id: int = None):
    """移动看板项目到新分类"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "UPDATE kanban_items SET category_id = ? WHERE id = ?", (new_category_id, item_id))
    conn.commit()


def get_kanban_items_by_category(category_id: int = None, batch_id: int = None) -> List[Dict]:
    """获取指定分类的看板项目（包含反馈详情），可按批次过滤"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if category_id is None:
        if batch_id is not None:
            if is_postgres():
                cursor.execute("""
                    SELECT ki.*, f.content, f.user_type, f.category as original_category, 
                           f.attachment, f.upload_batch_id, ub.filename as batch_name
                    FROM kanban_items ki
                    JOIN feedbacks f ON ki.feedback_id = f.id
                    LEFT JOIN upload_batches ub ON f.upload_batch_id = ub.id
                    WHERE ki.category_id IS NULL AND f.upload_batch_id = %s
                    ORDER BY ki.sort_order
                """, (batch_id,))
            else:
                cursor.execute("""
                    SELECT ki.*, f.content, f.user_type, f.category as original_category, 
                           f.attachment, f.upload_batch_id, ub.filename as batch_name
                    FROM kanban_items ki
                    JOIN feedbacks f ON ki.feedback_id = f.id
                    LEFT JOIN upload_batches ub ON f.upload_batch_id = ub.id
                    WHERE ki.category_id IS NULL AND f.upload_batch_id = ?
                    ORDER BY ki.sort_order
                """, (batch_id,))
        else:
            cursor.execute("""
                SELECT ki.*, f.content, f.user_type, f.category as original_category, 
                       f.attachment, f.upload_batch_id, ub.filename as batch_name
                FROM kanban_items ki
                JOIN feedbacks f ON ki.feedback_id = f.id
                LEFT JOIN upload_batches ub ON f.upload_batch_id = ub.id
                WHERE ki.category_id IS NULL
                ORDER BY ki.sort_order
            """)
    else:
        if batch_id is not None:
            if is_postgres():
                cursor.execute("""
                    SELECT ki.*, f.content, f.user_type, f.category as original_category,
                           f.attachment, f.upload_batch_id, ub.filename as batch_name
                    FROM kanban_items ki
                    JOIN feedbacks f ON ki.feedback_id = f.id
                    LEFT JOIN upload_batches ub ON f.upload_batch_id = ub.id
                    WHERE ki.category_id = %s AND f.upload_batch_id = %s
                    ORDER BY ki.sort_order
                """, (category_id, batch_id))
            else:
                cursor.execute("""
                    SELECT ki.*, f.content, f.user_type, f.category as original_category,
                           f.attachment, f.upload_batch_id, ub.filename as batch_name
                    FROM kanban_items ki
                    JOIN feedbacks f ON ki.feedback_id = f.id
                    LEFT JOIN upload_batches ub ON f.upload_batch_id = ub.id
                    WHERE ki.category_id = ? AND f.upload_batch_id = ?
                    ORDER BY ki.sort_order
                """, (category_id, batch_id))
        else:
            if is_postgres():
                cursor.execute("""
                    SELECT ki.*, f.content, f.user_type, f.category as original_category,
                           f.attachment, f.upload_batch_id, ub.filename as batch_name
                    FROM kanban_items ki
                    JOIN feedbacks f ON ki.feedback_id = f.id
                    LEFT JOIN upload_batches ub ON f.upload_batch_id = ub.id
                    WHERE ki.category_id = %s
                    ORDER BY ki.sort_order
                """, (category_id,))
            else:
                cursor.execute("""
                    SELECT ki.*, f.content, f.user_type, f.category as original_category,
                           f.attachment, f.upload_batch_id, ub.filename as batch_name
                    FROM kanban_items ki
                    JOIN feedbacks f ON ki.feedback_id = f.id
                    LEFT JOIN upload_batches ub ON f.upload_batch_id = ub.id
                    WHERE ki.category_id = ?
                    ORDER BY ki.sort_order
                """, (category_id,))
    
    return fetchall_as_dict(cursor)


def get_all_kanban_items(batch_id: int = None) -> Dict[str, List[Dict]]:
    """获取所有看板项目，按分类分组，可按批次过滤"""
    # 获取该批次的分类
    categories = get_all_kanban_categories(batch_id)
    
    result = {}
    
    # 获取未分类的项目
    uncategorized = get_kanban_items_by_category(None, batch_id)
    if uncategorized:
        result['未分类'] = {'feedback_list': uncategorized, 'category_id': None, 'color': '#6B7280'}
    
    # 获取各分类的项目
    for cat in categories:
        feedback_list = get_kanban_items_by_category(cat['id'], batch_id)
        result[cat['name']] = {
            'feedback_list': feedback_list,
            'category_id': cat['id'],
            'color': cat['color']
        }
    
    return result


def is_feedback_in_kanban(feedback_id: int) -> bool:
    """检查反馈是否已在看板中"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT 1 FROM kanban_items WHERE feedback_id = ?", (feedback_id,))
    return cursor.fetchone() is not None


def get_kanban_item_by_feedback_id(feedback_id: int) -> Optional[Dict]:
    """根据反馈ID获取看板项目"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_postgres():
        cursor.execute("""
            SELECT ki.*, kc.name as category_name, kc.color
            FROM kanban_items ki
            LEFT JOIN kanban_categories kc ON ki.category_id = kc.id
            WHERE ki.feedback_id = %s
        """, (feedback_id,))
    else:
        cursor.execute("""
            SELECT ki.*, kc.name as category_name, kc.color
            FROM kanban_items ki
            LEFT JOIN kanban_categories kc ON ki.category_id = kc.id
            WHERE ki.feedback_id = ?
        """, (feedback_id,))
    
    return fetchone_as_dict(cursor)


def get_kanban_statistics() -> Dict:
    """获取看板统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 总数
    cursor.execute("SELECT COUNT(*) as total FROM kanban_items")
    total = fetchone_as_dict(cursor)['total']
    
    # 各分类数量
    cursor.execute("""
        SELECT kc.id, kc.name, kc.color, COUNT(ki.id) as count
        FROM kanban_categories kc
        LEFT JOIN kanban_items ki ON kc.id = ki.category_id
        GROUP BY kc.id, kc.name, kc.color
        ORDER BY kc.sort_order
    """)
    category_stats = fetchall_as_dict(cursor)
    
    # 未分类数量
    cursor.execute("SELECT COUNT(*) as count FROM kanban_items WHERE category_id IS NULL")
    uncategorized_count = fetchone_as_dict(cursor)['count']
    
    return {
        'total': total,
        'category_stats': category_stats,
        'uncategorized_count': uncategorized_count
    }


def get_feedback_by_id(feedback_id: int) -> Optional[Dict]:
    """根据ID获取反馈详情"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "SELECT * FROM feedbacks WHERE id = ?", (feedback_id,))
    return fetchone_as_dict(cursor)


def update_feedback_category(feedback_id: int, new_category: str):
    """更新反馈的分类"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, "UPDATE feedbacks SET category = ? WHERE id = ?", (new_category, feedback_id))
    conn.commit()


def create_custom_category(batch_id: int, category_name: str) -> bool:
    """创建自定义分类（通过更新一个占位反馈的分类来实现）"""
    # 自定义分类会在反馈移动到该分类时自动创建
    return True


def get_all_categories_for_batch(batch_id: int) -> List[str]:
    """获取指定批次的所有分类名称"""
    conn = get_connection()
    cursor = conn.cursor()
    execute_query(cursor, """
        SELECT DISTINCT category FROM feedbacks 
        WHERE upload_batch_id = ? 
        ORDER BY category
    """, (batch_id,))
    return [row['category'] for row in fetchall_as_dict(cursor)]


def rename_category(batch_id: int, old_name: str, new_name: str) -> int:
    """重命名分类（批量更新该分类下所有反馈）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_postgres():
        cursor.execute(
            "UPDATE feedbacks SET category = %s WHERE upload_batch_id = %s AND category = %s",
            (new_name, batch_id, old_name)
        )
    else:
        cursor.execute(
            "UPDATE feedbacks SET category = ? WHERE upload_batch_id = ? AND category = ?",
            (new_name, batch_id, old_name)
        )
    
    affected = cursor.rowcount
    conn.commit()
    return affected

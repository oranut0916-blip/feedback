"""
配置文件
"""
import os

class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-feedback-analysis'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'feedback.db')
    USE_POSTGRES = False
    POSTGRES_URL = None


class VercelConfig(Config):
    """Vercel 部署配置 - 使用 PostgreSQL"""
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = 8000
    
    # 使用 Vercel Postgres
    USE_POSTGRES = True
    # Vercel 会自动设置 POSTGRES_URL 环境变量
    POSTGRES_URL = os.environ.get('POSTGRES_URL')
    
    # 备用 SQLite（如果 Postgres 不可用）
    DATABASE_PATH = '/tmp/feedback.db'
    
    # 上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'csv'}


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 8001
    USE_POSTGRES = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = 8001
    # 生产环境也可以使用 Postgres
    USE_POSTGRES = os.environ.get('POSTGRES_URL') is not None
    POSTGRES_URL = os.environ.get('POSTGRES_URL')


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'vercel': VercelConfig,
    'default': DevelopmentConfig
}


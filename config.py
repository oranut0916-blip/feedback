"""
配置文件
"""
import os

class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-feedback-analysis'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'feedback.db')
    
    # 上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'csv'}


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 8000


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = 8000


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


"""
Flask 应用工厂
"""
from flask import Flask
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 初始化数据库
    from core.models import init_db
    with app.app_context():
        init_db()
    
    # 注册蓝图
    from core.routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app


"""
应用入口文件
"""
import os
from app import create_app
from config import config

# 获取环境配置
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    config_obj = config[env]
    
    print("=" * 60)
    print("📊 用户反馈分析系统 - Flask 版")
    print("=" * 60)
    print(f"\n🌐 运行环境: {env}")
    print(f"💻 访问地址: http://{config_obj.HOST}:{config_obj.PORT}")
    print(f"📁 数据库: {config_obj.DATABASE_PATH}")
    print("\n" + "=" * 60)
    
    app.run(
        host=config_obj.HOST,
        port=config_obj.PORT,
        debug=config_obj.DEBUG
    )


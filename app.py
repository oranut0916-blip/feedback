"""
Vercel 部署入口文件
导出 Flask 应用实例
"""
import os
import sys

# 确保能找到 app 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# 检测是否在 Vercel 环境
is_vercel = os.environ.get('VERCEL', False)

# Vercel 需要的 app 变量
app = create_app('vercel' if is_vercel else 'production')

# 本地运行支持
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)


# 用户反馈分析系统

一个基于 FastAPI + Tailwind CSS 的用户反馈自动分类分析系统。

## 功能特性

- 📤 **CSV文件上传**：支持拖拽上传，自动检测文件编码（UTF-8、GBK等）
- 🏷️ **智能分类**：基于关键词自动将反馈分类为：
  - 功能建议
  - Bug反馈
  - 使用体验
  - 性能问题
  - 账号问题
  - 支付问题
  - 内容问题
  - 客服服务
  - 其他
- 📊 **统计分析**：
  - 总反馈数量
  - 用户类型分布（会员/普通用户）
  - 各分类数量及占比
- 🎨 **手风琴式详情**：点击分类卡片展开查看详细反馈内容
- 📁 **历史记录**：支持查看历史上传批次

## 技术栈

- **后端**：FastAPI + Jinja2 Templates
- **前端**：HTML + Tailwind CSS + JavaScript
- **数据库**：SQLite

## 快速开始

### 1. 安装依赖

```bash
cd "D:\cursor日常\12月\自动分析用户反馈"
pip install -r requirements.txt
```

### 2. 运行服务

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 访问系统

打开浏览器访问：http://127.0.0.1:8000

## CSV文件格式

系统会自动检测CSV中的以下字段：

- **内容字段**：包含 "内容"、"反馈"、"content"、"feedback" 等关键词的列
- **用户类型字段**：包含 "用户类型"、"会员"、"user_type" 等关键词的列

### 示例CSV格式

```csv
用户类型,内容,时间
会员,希望能增加夜间模式功能,2024-01-01
普通用户,登录时经常闪退,2024-01-02
VIP,界面操作不太方便,2024-01-03
```

## 项目结构

```
自动分析用户反馈/
├── main.py              # FastAPI 主程序
├── database.py          # 数据库操作
├── requirements.txt     # Python 依赖
├── feedback.db          # SQLite 数据库（自动生成）
├── templates/
│   └── index.html       # 前端页面
└── README.md            # 说明文档
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 首页 |
| GET | `/batch/{batch_id}` | 查看指定批次 |
| POST | `/upload` | 上传CSV文件 |
| DELETE | `/batch/{batch_id}` | 删除批次 |
| GET | `/api/stats/{batch_id}` | 获取统计数据 |
| GET | `/api/category/{batch_id}/{category}` | 获取指定分类反馈 |

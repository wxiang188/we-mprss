# WeChat MP RSS - 微信公众号 RSS 生成器 (复刻版)

微信公众号 RSS 订阅工具，支持扫码授权获取公众号文章，AI 自动总结打标签分类，支持多种格式导出。

## 核心功能

- 📱 **公众号订阅** - 扫码授权获取公众号信息
- 📝 **文章抓取** - 获取公众号文章标题、内容
- 🤖 **AI 智能处理** - 自动总结、标签、分类
- 📤 **数据导出** - 支持 CSV、JSON、PDF、DOCX、Markdown

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制配置文件：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，配置：

- `ai.api_key` - AI API 密钥
- `wechat.cookies` - 微信 Cookie（可选，用于增强抓取）
- `server.port` - 服务端口

### 3. 启动服务

```bash
python main.py
```

访问 http://localhost:8000

## 项目结构

```
we-mprss/
├── apis/              # API 路由
│   ├── auth.py        # 认证
│   ├── mps.py         # 公众号管理
│   ├── article.py     # 文章管理
│   ├── tags.py        # 标签管理
│   ├── export.py      # 数据导出
│   └── ai.py          # AI 处理
├── core/              # 核心模块
│   ├── models/        # 数据模型
│   ├── db.py          # 数据库
│   ├── config.py      # 配置
│   ├── auth.py        # 授权
│   ├── wx/            # 微信相关
│   └── ai/            # AI 处理
├── driver/            # 网页驱动
├── tools/             # 工具脚本
├── web_ui/           # 前端界面
├── config.example.yaml
├── requirements.txt
└── main.py
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/wx/mps` | GET | 获取公众号列表 |
| `/api/wx/mps` | POST | 添加公众号 |
| `/api/wx/mps/scan` | POST | 扫码授权 |
| `/api/wx/articles` | GET | 获取文章列表 |
| `/api/wx/articles/{id}` | GET | 获取文章详情 |
| `/api/wx/ai/summary` | POST | AI 总结文章 |
| `/api/wx/ai/category` | POST | AI 分类文章 |
| `/api/wx/export/articles` | POST | 导出文章 |
| `/api/wx/export/mps` | GET | 导出公众号列表 |

## 使用说明

### 添加公众号

1. 进入管理页面
2. 点击"添加公众号"
3. 使用微信扫描二维码
4. 授权后自动获取公众号信息

### 导出文章

选择导出格式：
- CSV - 表格形式，适合数据分析
- JSON - 结构化数据
- PDF/DOCX - 文档形式
- Markdown - 笔记格式

## License

MIT

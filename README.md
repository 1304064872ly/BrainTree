# 🌳 思维树 (BrainTree)

一个基于 AI 的智能思维树生成工具，能够将 PDF、DOCX、TXT 等格式的文档自动转换为可视化的知识图谱。

## ✨ 功能特点

- 📄 **多格式支持** - 支持 PDF、DOCX、TXT 文件上传和解析
- 🤖 **AI 智能分析** - 自动提取文档中的关键概念和层级关系
- 🌳 **知识图谱** - 3D 交互式知识图谱可视化展示
- ✏️ **手动编辑** - 支持节点和连接的添加、删除、修改
- 📤 **多格式导出** - 支持 JSON、Markdown、CSV 导出
- 💾 **数据持久化** - MySQL 数据库存储，数据不丢失
- 🎨 **美观界面** - 基于 Ant Design 的现代化用户界面
- 🔌 **多模型支持** - 支持 DeepSeek、OpenAI、Claude、智谱AI 等多种大模型

## 🛠️ 技术栈

### 前端
| 技术 | 说明 |
|------|------|
| React 18 | UI 框架 |
| TypeScript | 类型安全 |
| Vite | 构建工具 |
| Ant Design | UI 组件库 |
| react-force-graph-3d | 3D 图谱可视化 |
| Zustand | 状态管理 |
| Axios | HTTP 客户端 |

### 后端
| 技术 | 说明 |
|------|------|
| Python | 运行环境 |
| FastAPI | Web 框架 |
| SQLAlchemy | ORM 框架 |
| PyMySQL | MySQL 驱动 |
| PyPDF2 | PDF 解析 |
| python-docx | DOCX 解析 |
| httpx | HTTP 客户端 |

### 数据库
| 技术 | 说明 |
|------|------|
| MySQL | 关系型数据库 |

## 📁 项目结构

```
BrainTree/
├── frontend/                    # 前端项目
│   └── frontend/
│       ├── src/
│       │   ├── components/      # React 组件
│       │   │   ├── Export/      # 导出功能
│       │   │   ├── FileUpload/  # 文件上传
│       │   │   ├── MindMap/     # 知识图谱
│       │   │   ├── NodeEditor/  # 节点编辑器
│       │   │   └── Sidebar/     # 侧边栏
│       │   ├── services/        # API 服务
│       │   ├── stores/          # 状态管理
│       │   └── types/           # TypeScript 类型
│       ├── package.json
│       └── vite.config.ts
├── backend/                     # 后端项目
│   ├── app/
│   │   ├── api/                 # API 路由
│   │   │   ├── analyze.py       # AI 分析接口
│   │   │   ├── export.py        # 导出接口
│   │   │   ├── files.py         # 文件管理接口
│   │   │   ├── models.py        # 模型管理接口
│   │   │   └── trees.py         # 思维树接口
│   │   ├── core/                # 核心配置
│   │   │   └── database.py      # 数据库配置
│   │   ├── models/              # 数据模型
│   │   │   ├── db_models.py     # ORM 模型
│   │   │   └── schemas.py       # Pydantic 模型
│   │   └── services/            # 业务逻辑
│   │       ├── ai_analyzer.py   # AI 分析服务
│   │       └── file_parser.py   # 文件解析服务
│   ├── .env                     # 环境变量
│   ├── .env.example             # 环境变量示例
│   ├── init_db.py               # 数据库初始化脚本
│   ├── main.py                  # 应用入口
│   └── requirements.txt         # Python 依赖
├── README.md
└── .gitignore
```

## 🚀 快速开始

### 前置要求

- **Node.js** 16+
- **Python** 3.7+
- **MySQL** 5.7+

### 1. 克隆项目

```bash
git clone <repository-url>
cd BrainTree
```

### 2. 数据库准备

确保 MySQL 服务已运行，然后执行：

```bash
cd backend
python init_db.py
```

这将自动创建 `brain_tree` 数据库和相关表。

### 3. 配置环境变量

编辑 `backend/.env` 文件：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://用户名:密码@localhost:3306/brain_tree

# AI 模型配置 (以 DeepSeek 为例)
LLM_PROVIDER=deepseek
LLM_API_KEY=your_deepseek_api_key
LLM_MODEL=deepseek-chat
```

### 4. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 5. 安装前端依赖

```bash
cd frontend/frontend
npm install
```

### 6. 启动项目

**启动后端** (终端 1)：
```bash
cd backend
python main.py
```

**启动前端** (终端 2)：
```bash
cd frontend/frontend
npm run dev
```

### 7. 访问应用

- 🌐 **前端界面**: http://localhost:3000
- 📚 **API 文档**: http://localhost:8000/docs
- ❤️ **健康检查**: http://localhost:8000/health

## 🤖 支持的 AI 模型

### DeepSeek (推荐)

| 模型 | 说明 | 用途 |
|------|------|------|
| `deepseek-chat` | DeepSeek-V3 通用模型 | 通用文本分析 ⭐ 默认 |
| `deepseek-coder` | 代码专用模型 | 技术文档分析 |
| `deepseek-reasoner` | DeepSeek-R1 推理模型 | 复杂逻辑分析 |
| `deepseek-v3` | DeepSeek-V3 最新版 | 最新通用分析 |
| `deepseek-r1` | DeepSeek-R1 | 深度推理任务 |

获取 API Key: https://platform.deepseek.com

### OpenAI

| 模型 | 说明 |
|------|------|
| `gpt-3.5-turbo` | GPT-3.5 Turbo |
| `gpt-4` | GPT-4 |
| `gpt-4-turbo` | GPT-4 Turbo |
| `gpt-4o` | GPT-4o |

### Claude

| 模型 | 说明 |
|------|------|
| `claude-3-sonnet-20240229` | Claude 3 Sonnet |
| `claude-3-opus-20240229` | Claude 3 Opus |
| `claude-3-haiku-20240307` | Claude 3 Haiku |

### 智谱 AI

| 模型 | 说明 |
|------|------|
| `glm-4` | GLM-4 |
| `glm-4-flash` | GLM-4 Flash |
| `glm-4v` | GLM-4V (多模态) |

## 📡 API 接口

### 文件管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/files/upload` | 上传文件 |
| GET | `/api/files` | 获取文件列表 |
| GET | `/api/files/{id}` | 获取文件详情 |
| DELETE | `/api/files/{id}` | 删除文件 |

### 思维树管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trees` | 创建思维树 |
| GET | `/api/trees` | 获取思维树列表 |
| GET | `/api/trees/{id}` | 获取思维树详情 |
| PUT | `/api/trees/{id}` | 更新思维树 |
| DELETE | `/api/trees/{id}` | 删除思维树 |
| POST | `/api/trees/{id}/nodes` | 添加节点 |
| PUT | `/api/trees/{id}/nodes/{nodeId}` | 更新节点 |
| DELETE | `/api/trees/{id}/nodes/{nodeId}` | 删除节点 |
| POST | `/api/trees/{id}/edges` | 添加连接 |
| DELETE | `/api/trees/{id}/edges/{edgeId}` | 删除连接 |

### AI 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 分析文件生成思维树 |
| POST | `/api/analyze/refine` | 优化现有思维树 |

### 模型管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/models/providers` | 获取服务商列表 |
| GET | `/api/models/models` | 获取所有模型 |
| GET | `/api/models/models/{provider}` | 获取指定服务商模型 |

### 导出功能

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trees/{id}/export/json` | 导出 JSON |
| GET | `/api/trees/{id}/export/markdown` | 导出 Markdown |
| GET | `/api/trees/{id}/export/csv` | 导出 CSV |

## 💡 使用指南

### 1. 上传文件

- 点击左侧菜单「上传文件」
- 拖拽或点击上传 PDF、DOCX、TXT 文件
- 支持批量上传

### 2. AI 生成思维树

- 上传文件后，选择要分析的文件
- 点击「AI 分析」按钮
- 等待 AI 分析完成，自动生成知识图谱

### 3. 手动编辑

- 在图谱中点击节点进行编辑
- 可添加、删除节点和连接
- 修改节点属性（名称、描述、类型、层级）

### 4. 导出数据

- 选择要导出的思维树
- 点击「导出」按钮
- 选择导出格式（JSON、Markdown、CSV）

## ⚙️ 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | MySQL 连接字符串 | - |
| `LLM_PROVIDER` | AI 服务商 | `deepseek` |
| `LLM_API_KEY` | API 密钥 | - |
| `LLM_API_BASE` | API 基础 URL | 自动 |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |

## 🔧 常见问题

### Q: 数据库连接失败？

A: 检查以下配置：
1. MySQL 服务是否已启动
2. `DATABASE_URL` 中的用户名、密码是否正确
3. 数据库 `brain_tree` 是否已创建（运行 `python init_db.py`）

### Q: AI 分析失败？

A: 检查以下配置：
1. `LLM_API_KEY` 是否正确
2. 网络连接是否正常
3. 查看后端日志获取详细错误信息

### Q: 如何切换 AI 模型？

A: 修改 `backend/.env` 文件：
```env
LLM_PROVIDER=deepseek    # 服务商
LLM_MODEL=deepseek-r1    # 模型名称
```
然后重启后端服务。

### Q: 支持多大的文件？

A: 单个文件最大支持 50MB，建议文件内容不超过 10 万字以获得最佳 AI 分析效果。

## 📝 开发说明

### 添加新的 AI 服务商

1. 在 `backend/app/services/ai_analyzer.py` 中添加调用方法
2. 在 `backend/app/api/models.py` 中注册服务商和模型
3. 更新 `.env.example` 配置说明

### 添加新的文件格式支持

1. 在 `backend/app/services/file_parser.py` 中添加解析方法
2. 更新 `FileParser.parse()` 方法
3. 更新前端的文件类型验证

### 添加新的导出格式

1. 在 `backend/app/api/export.py` 中添加导出路由
2. 在 `frontend/src/services/api.ts` 中添加 API 调用
3. 在 `frontend/src/components/Export/` 中添加导出选项

## 📄 许可证

MIT License

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Ant Design](https://ant.design/)
- [DeepSeek](https://deepseek.com/)
- [react-force-graph](https://github.com/vasturiano/react-force-graph)

---

如有问题或建议，欢迎提交 Issue！

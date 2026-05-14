# PhotoAutoPick

AI 照片自动筛选工具 — 基于多维度分析智能挑选最佳照片。

## 功能特性

- **技术质量分析** — 曝光、锐度、噪点、动态范围、对焦质量、色彩丰富度
- **构图分析** — 三分法、水平线、对称性、留白、景深
- **语义识别** — 场景分类（人像/日落/风景/夜景等）、情绪分析、人脸检测
- **美学评分** — 基于 NIMA 深度学习模型 + 对比度/色彩和谐度
- **独特性评分** — pHash 去重 + EXIF 拍摄意图分析
- **场景自适应权重** — 针对不同场景（人像/风景/夜景等）自动调整评分权重
- **七级评分体系** — S / A / B+ / B / C+ / C / D
- **改进建议** — 根据各项得分生成针对性拍摄建议
- **多格式支持** — JPEG、PNG、HEIC、RAW（CR2/NEF/ARW 等）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ / FastAPI / SQLAlchemy / OpenCV |
| 前端 | React 18 / Vite / Recharts |
| AI 模型 | NIMA（MobileNet backbone，ONNX Runtime 推理） |
| 打包 | PyInstaller（一键生成 EXE） |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm

### 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 运行开发服务器

```bash
# 终端 1：启动后端
cd backend
python run.py

# 终端 2：启动前端
cd frontend
npm run dev
```

浏览器访问 `http://localhost:5173`

### 一键打包 EXE

```bash
python build.py
```

生成的可执行文件位于 `dist/PhotoAutoPick.exe`，双击即可运行，自动打开浏览器界面。

## 项目结构

```
photo-auto-pick/
├── backend/
│   ├── app/
│   │   ├── analysis/       # 分析模块（技术/构图/语义/美学）
│   │   ├── api/            # API 路由
│   │   ├── core/           # 配置
│   │   ├── models/         # 数据库模型 & 数据结构
│   │   └── utils/          # 工具函数
│   ├── weights/            # ONNX 模型权重
│   ├── scripts/            # 模型转换脚本
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── api.js          # API 调用
│   │   └── App.jsx         # 主应用
│   └── package.json
├── build.py                # 一键打包脚本
└── README.md
```

## 使用方式

1. 打开应用后，可以通过 **拖拽上传** 或 **指定文件夹路径** 导入照片
2. 系统自动分析所有照片，实时显示进度
3. 分析完成后按评分排序展示，支持按等级/分数筛选
4. 点击照片查看详细评分和改进建议

## 评分体系

| 等级 | 分数范围 | 含义 |
|------|----------|------|
| S | 90-100 | 顶级 — 专业级作品 |
| A | 80-89 | 优秀 — 直接可用 |
| B+ | 70-79 | 良好 — 质量上乘 |
| B | 60-69 | 中等偏上 — 不错 |
| C+ | 50-59 | 中等 — 有瑕疵 |
| C | 40-49 | 一般 — 瑕疵较多 |
| D | 0-39 | 较差 — 不建议使用 |

## License

MIT

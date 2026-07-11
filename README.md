# 3D 评分管理 Web 系统 (3D Scoring System)

这是一个用于 3D 课程（如三维动画设计基础、3D建模等）的大模型自动化评分与结果管理系统。系统结合了大模型（LLM）自动化文档、图片、视频多模态分析评分脚本，以及一个基于 Flask 的 Web 管理前端，方便教师审阅、修改和导出学生作业成绩。

## 项目结构 (Project Structure)

- **`config.yaml`**: 系统核心配置文件，包含课程类型（`animation`, `modeling`, `3d_comprehensive`）、打分模式（`individual`, `group`）、数据目录及评分相关参数。
- **`scoring_scripts/`**: 自动化评分核心后端脚本集。
  - `batch_grader/grader_app.py`: 批处理评分核心，自动收集数据、组织提示词并调用大模型（多模态能力）对提交的报告、图片、视频进行分析并得出结构化分数。
  - `batch_grader/prompts.py`: 定义各课程不同模式（小组/个人）的评分 Prompt 模板。
- **`scoring_web/`**: 基于 Flask 构建的 Web 管理端。
  - `app.py`: Web 端主程序，提供学生列表、目标详情、媒体资源加载、成绩手动修正及重新评分的 RESTful 接口。
- **`server.bat`**: Windows 环境下快速启动 Web 服务的批处理脚本。
- **`thumbnail_cache/`**: 缓存提取的视频封面/缩略图。

## 核心功能 (Key Features)

1. **多模式/多课程支持**: 内置 `animation`（动画）、`modeling`（建模）、`3d_comprehensive`（3D综合）不同课程的专属评分指标。支持 `group`（小组协作，自动解析组长组员）与 `individual`（个人）模式。
2. **LLM 智能自动化评分 (Automated Grading)**: 自动提取目标文件夹内的 Word 文档（支持富文本/图片解析）、渲染图和视频预览；结合多模态大模型自动给出各维度的打分（例如：创意、建模、材质、灯光、文档规范等）和评语。
3. **Web 可视化审查前端 (Web Review UI)**:
   - **多维度视图**: 提供概览页与学生细分列表，支持按总分、组分、个人分等多种维度排序。
   - **在线阅卷体验**: 教师可直接在 Web 界面阅览解析后的学生报告，并横向对比提交的渲染图及视频片段。
   - **成绩微调与确认**: 支持教师对 AI 生成的各个维度成绩、评语进行覆盖调整并标记已确认。
   - **本地穿透**: 阅卷时可点击按钮直接调起系统资源管理器，定位到具体作业目录或源文件。

## 使用说明 (Getting Started)

1. **环境准备 (Prerequisites)**:
   - Python 3.8+ 环境。
   - 安装依赖项（Flask, OpenCV-Python, 及其它相关 SDK）。
2. **基础配置 (Configuration)**:
   - 修改项目根目录下的 `config.yaml`，调整 `course_type`, `grading_mode` 以及指向学生作业的 `data_dir` 绝对路径。
   - 确保存在相关的大模型配置文件（如 `config/settings.yaml`）。
3. **运行批处理打分 (Run Batch Grading)**:
   - 在 `scoring_scripts/` 目录下执行启动脚本（例如 `run_3d_scoring.py` 或由其他调度器启动）。
   - 评分过程会结合 `api_delay_seconds` 的配置，安全稳妥地完成所有作业的 AI 分析。
4. **启动管理面板 (Start Web Server)**:
   - 运行项目根目录下的 `server.bat` 或者执行 `python scoring_web/app.py`。
   - 浏览器访问终端提示的本地地址（默认 `http://127.0.0.1:5000`）即可进行审查。

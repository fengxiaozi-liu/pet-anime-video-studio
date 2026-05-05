# Video Studio

一个基于 FastAPI 的基础视频创作工具。当前仓库形态是“后端服务 + 服务端模板页面”，页面资源放在 `front/` 下，由后端直接挂载，不包含独立的前端构建工程。

## 项目简介

当前项目包含这些核心部分：

- `backend/`：FastAPI 应用、任务流程、素材与 provider 配置逻辑
- `front/`：Jinja2 模板和静态资源
- `docker-compose.yml` 与根目录 `Dockerfile`：本地容器化启动入口
- `config.yaml`：默认运行配置

网页入口和 API 都由同一个服务提供，默认地址为 `http://127.0.0.1:8000`，接口文档为 `http://127.0.0.1:8000/docs`。

## 本地启动

推荐只保留一个虚拟环境位置。默认使用仓库根目录 `.venv/`，不要再在 `backend/` 下额外创建 `.venv/`。

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- 首页：`http://127.0.0.1:8000/`
- 工作台：`http://127.0.0.1:8000/studio`
- 任务列表：`http://127.0.0.1:8000/tasks`
- 配置中心：`http://127.0.0.1:8000/config`
- 健康检查：`http://127.0.0.1:8000/health`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

默认配置来自根目录 `config.yaml`。如果只做本地流程验证，可以先不配置云端 provider；如果要创建云端任务，请在 `config.yaml` 中启用对应凭据。

## Docker 启动

```bash
docker-compose up -d --build
docker-compose logs -f
```

停止服务：

```bash
docker-compose down
```

容器启动后会挂载这些本地目录：

- `backend/uploads/`：上传文件与素材
- `backend/outputs/`：生成的视频结果
- `backend/data/`：任务和配置数据

## 快速使用

最直接的使用方式是先启动服务，再进入 `/studio`：

1. 输入视频创意或脚本方向
2. 生成并编辑故事、角色和分镜
3. 选择画面风格、首尾帧、配音和音乐
4. 提交视频生成任务
5. 在 `/tasks` 查看结果、封面和导出包

创建任务时，当前 `/api/jobs` 接口以表单提交为主，常用字段包括：

- `prompt`
- `backend`
- `provider`
- `template_id`
- `storyboard_json`
- `subtitles`
- `bgm_volume`
- `bgm`
- `opening_frame`
- `ending_frame`

也可以先检查 provider 和模板：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/providers
curl http://127.0.0.1:8000/api/platform-templates
```

如果启用了鉴权，请按启动环境中的 `API_KEY_USERNAME` 和 `API_KEY_PASSWORD` 访问 API。

## 目录结构

```text
video-studio/
├── backend/
│   ├── app/
│   ├── tests/
│   └── requirements.txt
├── front/
│   ├── templates/
│   └── static/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── config.yaml
└── README.md
```

补充说明：

- `front/` 只是页面资源目录，不是独立 SPA 工程
- `uploads/`、`outputs/`、`backend/data/` 属于运行期数据目录
- `.venv/`、`front/htmlcov/`、`.pytest_cache/` 都不是项目运行必需文件

## 开发说明

运行测试：

```bash
pytest backend/tests -v
```

生成覆盖率报告：

```bash
pytest backend/tests --cov=backend/app --cov-report=html
```

架构说明见 [docs/architecture.md](./docs/architecture.md)。

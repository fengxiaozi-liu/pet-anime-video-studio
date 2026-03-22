# Workflow Config - Pet Anime Video 自动化优化工作流
# 目标: 将生图助手重构为父子类模型，兼容不同类型的文生图 API

TASKS = [
    {
        "id": "t2i-001",
        "title": "创建 TextToImageProvider 基类（父子类架构）",
        "description": "在 providers/ 目录下创建 text_to_image_provider.py，作为所有文生图provider的基类。基类定义统一接口：generate_image(prompt, size, style) -> ImageResult(url, raw_response)。包含抽象方法submit()和查询方法poll()，以及通用错误处理。",
        "priority": 1,
        "status": "pending",
        "estimated_hours": 1,
    },
    {
        "id": "t2i-002",
        "title": "创建即梦(Jimeng) T2I Provider 子类",
        "description": "创建 providers/jimeng_t2i_provider.py，继承TextToImageProvider。实现submit()提交图片生成任务，poll()轮询结果。提供完整的API URL（submit_url和get_url）、JSON请求体格式、JSON响应解析。",
        "priority": 2,
        "status": "pending",
        "estimated_hours": 1,
    },
    {
        "id": "t2i-003",
        "title": "创建通义万相(TongyiWanxiang) T2I Provider 子类",
        "description": "创建 providers/tongyi_t2i_provider.py，继承TextToImageProvider。实现submit()和poll()。提供完整的API URL、JSON请求/响应格式。",
        "priority": 3,
        "status": "pending",
        "estimated_hours": 1,
    },
    {
        "id": "t2i-004",
        "title": "创建 OpenAI DALL-E T2I Provider 子类",
        "description": "创建 providers/dalle_t2i_provider.py，继承TextToImageProvider。实现submit()和poll()。提供完整的API URL(v1/images/generations)、JSON请求/响应格式。",
        "priority": 4,
        "status": "pending",
        "estimated_hours": 1,
    },
    {
        "id": "t2i-005",
        "title": "创建 Stable Diffusion T2I Provider 子类",
        "description": "创建 providers/sd_t2i_provider.py，继承TextToImageProvider。支持本地和远程SD API。实现submit()（同步模式）和poll()。提供完整的API URL、JSON请求/响应格式。",
        "priority": 5,
        "status": "pending",
        "estimated_hours": 1,
    },
    {
        "id": "t2i-006",
        "title": "创建生图助手调度器 T2IDispatcher",
        "description": "创建 image_dispatcher.py，作为所有T2I Provider的统一调度器。根据配置自动选择Provider，支持Provider切换。提供统一接口：generate(prompt, provider_code, **kwargs)。",
        "priority": 6,
        "status": "pending",
        "estimated_hours": 1,
    },
    {
        "id": "t2i-007",
        "title": "更新 character_image_assistants.py 使用新架构",
        "description": "修改 character_image_assistants.py，集成新的T2I Provider体系。将现有的generate_character_preview改为使用T2IDispatcher。",
        "priority": 7,
        "status": "pending",
        "estimated_hours": 1,
    },
    {
        "id": "t2i-008",
        "title": "编写测试用例验证所有 T2I Provider",
        "description": "为每个T2I Provider编写单元测试和集成测试，确保submit/poll/URL/JSON格式正确。",
        "priority": 8,
        "status": "pending",
        "estimated_hours": 1,
    },
]

COMPLETION_PLAN_FILE = ".completion-plan.json"
WORKFLOW_STATE_FILE = ".workflow-state.json"

# 每次运行时的标准流程
WORKFLOW_STEPS = [
    "git checkout main",
    "git pull origin main",
    "读取当前 .workflow-state.json 获取下一个 pending 任务",
    "执任务代码",
    "git add . && git commit -m 'feat: {task_id} {title}'",
    "git push origin main",
    "更新 .workflow-state.json 状态",
    "更新 .completion-plan.json 进度",
]

# 即梦 Provider 接入与云端任务架构文档

## 说明

本轮只更新规划文档，不修改前端或后端代码。

本文档用于统一以下几个方向的讨论与后续实现：

- 即梦 Provider 的标准化接入方式
- 任务系统从本地 JSON/线程模型迁移到云端任务模型
- Job 实体设计
- Provider 抽象模板设计
- 前端 Provider 列表与配置界面的改造
- 分镜视频生成后的最终合成职责

后续所有 Provider 的接入，都应参考本文档定义的统一模板，而不是按厂商各自风格自由扩展。

## 官方文档阅读结论

本次参考的官方文档：

1. 火山引擎 SDK 文档  
   `https://www.volcengine.com/docs/6444/1340578?lang=zh`
2. 即梦 AI 视频生成 3.0 Pro 接口文档  
   `https://www.volcengine.com/docs/85621/1777001?lang=zh`

通过官方文档和渲染后的正文页面，可以确认以下事实：

- 即梦视频生成属于火山引擎官方提供的云端异步任务式能力
- 官方文档归属为“即梦AI-视频生成3.0 Pro-接口文档”
- 文档最近更新时间为 `2025-12-01`
- 火山引擎接入方式应优先走官方 SDK / OpenAPI 签名体系
- 即梦视频 3.0 Pro 的官方异步接口是：
  - 提交任务：`CVSync2AsyncSubmitTask`
  - 查询结果：`CVSync2AsyncGetResult`

### 即梦提交任务接口

#### URL

- Host: `https://visual.volcengineapi.com`
- Method: `POST`
- Content-Type: `application/json`
- 完整接口：
  `https://visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31`

#### Request Body

```json
{
  "req_key": "jimeng_ti2v_v30_pro",
  "prompt": "用于生成视频的提示词",
  "binary_data_base64": ["base64_image"],
  "image_urls": ["https://example.com/image.png"],
  "seed": -1,
  "frames": 121,
  "aspect_ratio": "16:9"
}
```

#### 字段说明

- `req_key`
  - 必选
  - 固定值：`jimeng_ti2v_v30_pro`
- `prompt`
  - 文生视频场景必选
  - 建议 400 字以内，不超过 800 字
- `binary_data_base64`
  - 图生视频场景与 `prompt` 二选一必选
  - 与 `image_urls` 二选一
  - 当前只支持 1 张首帧图
- `image_urls`
  - 图生视频场景可传 1 张首帧图 URL
- `seed`
  - 可选
  - 默认 `-1`
- `frames`
  - 可选
  - 可选值：`121`、`241`
  - 对应约 `5s`、`10s`
- `aspect_ratio`
  - 可选
  - 仅文生视频场景生效
  - 可选值：`16:9`、`4:3`、`1:1`、`3:4`、`9:16`、`21:9`

#### Response

```json
{
  "task_id": "string"
}
```

#### 返回字段说明

- `task_id`
  - 即梦云端任务 ID
  - 用于后续查询生成状态和结果

### 即梦查询任务接口

#### URL

- Host: `https://visual.volcengineapi.com`
- Method: `POST`
- Content-Type: `application/json`
- 完整接口：
  `https://visual.volcengineapi.com?Action=CVSync2AsyncGetResult&Version=2022-08-31`

#### Request Body

```json
{
  "req_key": "jimeng_ti2v_v30_pro",
  "task_id": "提交任务接口返回的 task_id",
  "req_json": "{\"aigc_meta\": {\"content_producer\": \"xxxxxx\", \"producer_id\": \"xxxxxx\", \"content_propagator\": \"xxxxxx\", \"propagate_id\": \"xxxxxx\"}}"
}
```

#### 字段说明

- `req_key`
  - 必选
  - 固定值：`jimeng_ti2v_v30_pro`
- `task_id`
  - 必选
  - 提交任务接口返回的任务 ID
- `req_json`
  - 可选
  - 当前支持隐性水印 `aigc_meta`

#### Response

```json
{
  "video_url": "string",
  "aigc_meta_tagged": true,
  "status": "in_queue"
}
```

#### 返回字段说明

- `video_url`
  - 生成的视频 URL
  - 有效期为 1 小时
- `aigc_meta_tagged`
  - 隐式标识是否打标成功
- `status`
  - `in_queue`: 任务已提交
  - `generating`: 任务处理中
  - `done`: 任务完成，成功或失败需结合外层 `code/message` 判断
  - `not_found`: 任务不存在或已过期
  - `expired`: 任务已过期，需要重新提交

### SDK 参考入口

SDK 文档中可以确认火山引擎已提供对应异步视觉接口的官方示例：

- Python 提交任务示例：
  `https://github.com/volcengine/volc-sdk-python/blob/main/volcengine/example/visual/cv_sync2async_submit_task.py`
- Python 查询结果示例：
  `https://github.com/volcengine/volc-sdk-python/blob/main/volcengine/example/visual/cv_sync2async_get_result.py`
- Java/Go/PHP 也提供同名异步示例

结论：

- 即梦 Provider 的官方接入模式已经明确是“提交异步任务 + 查询异步结果”
- 因此我们内部的 Provider 模型必须围绕 `create_task / get_task / update_task` 设计，而不是同步 `render()`

## 当前问题

当前系统存在这些问题：

- Provider 能力抽象过于粗糙，只有 `render(ctx)`，不适合对接云端异步任务模型
- 前端 Provider 列表写死在 `static/app.js`
- 工作区里只能选 Provider，不能配置 Provider
- 当前任务模型围绕本地文件和本地线程设计，不适合云厂商异步任务
- 当前 `local` 链路承担了过多职责，把“镜头生成”和“最终合成”混在一起

## 本次理解

### 1. 即梦这类云端视频 Provider 的本质

我们的理解是：

- 即梦应按“创建远端任务 -> 查询远端任务 -> 获取结果资源”的方式接入
- 它不是本地直接返回最终视频的同步接口
- 我们内部不应继续把云端 Provider 简化成一个同步 `render()` 方法

因此，即梦 Provider 至少要拆成两类方法：

- 创建任务
- 获取任务

如果要做得可扩展，则还需要补：

- 能力元信息
- 配置检查
- 参数构建
- 状态归一化
- 结果提取

### 2. 我们的业务不是生成一整条视频，而是生成分镜视频

当前业务目标应明确为：

- 用户输入故事文本
- 系统将文本拆解为若干分镜
- 每个分镜分别提交给云端 Provider 去生成视频片段
- 每个分镜生成成功后，我们拿到多个视频片段
- 最终由我们在本地完成视频片段的拼接与后处理

因此最终职责边界应调整为：

- 云厂商负责：生成单个分镜视频片段
- 我们负责：分镜组织、任务编排、状态汇总、最终视频合成

### 3. 我们不应依赖本地存储二进制文件作为主流程

如果云厂商已经提供结果文件地址或其托管存储：

- 我们不需要把所有源视频片段长期落地为本地二进制文件
- Job 主要存云端任务 ID、状态、云端资源 URL、最终合成结果 URL
- 本地可以只保留短期缓存或最终成片

长期方向是：

- 云端结果作为主数据源
- 本地只承担编排与最终合成，而不是长期素材仓库

## 目标架构

### 总体目标

后续系统要从“本地渲染脚本 + 本地任务文件”重构为：

- Provider 标准化接入层
- 云端任务编排层
- 分镜子任务模型
- 最终视频合成层
- 后端 Provider 配置管理
- 前端动态 Provider 获取与配置界面

### 任务创建原则

- 任务只能通过点击“生成视频”创建
- 不提供“手动新增空任务”
- 一个用户可见的成片任务，对应一个父任务
- 父任务下面包含多个分镜子任务

### 后续职责拆分

#### 云端 Provider

负责：

- 接收单个分镜生成请求
- 返回云端任务 ID
- 提供任务状态查询能力
- 提供结果资源地址

不负责：

- 直接编排整条故事视频
- 直接定义我们的最终任务状态模型
- 直接承担最终多段视频合成

#### 我们的后端

负责：

- 故事拆分为分镜
- 为每个分镜创建云端任务
- 聚合子任务状态
- 汇总结果地址
- 最终拼接多个分镜视频
- 输出最终成片与任务状态

#### ffmpeg

后续建议收缩为：

- 视频片段拼接
- 字幕烧录
- BGM 混音
- 导出处理
- 封面抽帧

不再鼓励用 ffmpeg 继续承担“本地模拟每个分镜生成”的主链路。

## Provider 标准模板

后续所有 Provider 都应参考这一套模板，不再使用“单一 render(ctx)”风格。

### Provider 基础能力

每个 Provider 至少应实现这些方法：

#### 1. `code() -> str`

返回内部唯一标识，例如：

- `jimeng`
- `kling`
- `openai`
- `doubao`

#### 2. `display_name() -> str`

返回前端展示名称。

#### 3. `is_configured(settings) -> bool`

判断当前 Provider 是否已配置完成。

#### 4. `get_capabilities() -> dict`

返回能力描述，例如：

- 是否支持文生视频
- 是否支持图生视频
- 是否支持首帧参考
- 是否支持异步任务
- 是否支持片段输出
- 支持的分辨率/时长范围

#### 5. `validate_config(settings) -> list[str]`

返回配置缺失项或校验错误列表。

#### 6. `build_scene_request(scene, job_context) -> dict`

把内部统一分镜模型转换为该 Provider 的请求参数。

#### 7. `create_remote_task(scene_request, settings) -> ProviderTaskCreateResult`

创建云端任务。  
这是所有云端 Provider 的核心创建方法。

返回结果至少应包含：

- `provider_task_id`
- `raw_response`
- 可选 `request_id`

#### 8. `get_remote_task(provider_task_id, settings) -> ProviderTaskStatusResult`

查询云端任务状态。  
这是所有云端 Provider 的核心获取方法。

返回结果至少应包含：

- `provider_task_id`
- `provider_status`
- `normalized_status`
- `progress`
- `result_urls`
- `cover_url`
- `raw_response`

#### 9. `extract_result_assets(task_status_result) -> ProviderAssets`

从厂商返回结果中提取统一资产结构。

#### 10. `normalize_status(provider_status) -> SceneTaskStatus`

把厂商状态映射为内部统一状态。

#### 11. `list_config_fields() -> list[ProviderConfigField]`

返回前端配置界面需要展示的字段定义。

#### 12. `healthcheck(settings) -> ProviderHealthResult`

做轻量连通性/配置健康检查，用于配置界面和后台告警。

### Provider 最小创建/获取方法

如果只讨论最小闭环，即梦 Provider 必须先实现：

- `create_remote_task(...)`
- `get_remote_task(...)`

这两个方法是接入即梦的最低要求。

## 即梦 Provider 设计

### 接入方式

即梦 Provider 应作为我们的第一个标准模板实现。

建议内部命名：

- Provider code：`jimeng`
- SDK / OpenAPI 适配实现：`JimengProvider`

### 即梦接口与内部方法映射

#### 1. `create_task`

内部方法：

- `create_task(scene, job_context, provider_config_json)`

对应官方接口：

- `POST https://visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31`

内部职责：

- 根据分镜内容构造即梦请求体
- 填充 `req_key = jimeng_ti2v_v30_pro`
- 根据场景选择传 `prompt` 或首帧图
- 提交任务后提取 `task_id`
- 保存到 `scene_jobs.provider_task_id`

#### 2. `get_task`

内部方法：

- `get_task(provider_task_id, provider_config_json)`

对应官方接口：

- `POST https://visual.volcengineapi.com?Action=CVSync2AsyncGetResult&Version=2022-08-31`

内部职责：

- 用 `provider_task_id` 查询即梦任务
- 读取返回中的：
  - `status`
  - `video_url`
  - `aigc_meta_tagged`
- 返回统一状态结果给系统内部使用

#### 3. `update_task`

内部方法：

- `update_task(scene_job, provider_task_result)`

内部职责：

- 把即梦返回状态映射为内部状态
- 把 `video_url` 写回 `scene_jobs.result_video_url`
- 记录原始响应到 `response_payload_json`
- 更新父任务聚合状态

### 即梦状态映射

即梦返回的 `status` 需要映射到内部状态：

- `in_queue` -> `queued`
- `generating` -> `running`
- `done` -> `succeeded` 或 `failed`
  - 需要结合外层 `code/message`
- `not_found` -> `failed`
- `expired` -> `failed`

### 即梦 Provider 应具有的方法

即梦接入最少应包含：

- `is_configured`
- `validate_config`
- `get_capabilities`
- `build_scene_request`
- `create_remote_task`
- `get_remote_task`
- `extract_result_assets`
- `normalize_status`
- `list_config_fields`
- `healthcheck`

其中真正必须先打通的是：

- `create_remote_task`
- `get_remote_task`

### 即梦 Provider 结果理解

即梦返回的结果，无论官方最终字段名如何，我们内部都应统一抽象成：

- 云端任务 ID
- 云端状态
- 进度
- 单个分镜视频 URL
- 封面 URL
- 厂商原始返回

在当前已读取到的官方文档中，可以明确映射这些字段：

- 云端任务 ID -> `task_id`
- 云端状态 -> `status`
- 单个分镜视频 URL -> `video_url`
- 隐式打标结果 -> `aigc_meta_tagged`
- 厂商原始返回 -> 整个查询接口 response

## Job 实体设计

如果我们按“父任务 + 分镜子任务”的方式落地，则不能只有一个简单 Job 表。

建议至少拆成两层：

### 1. `render_jobs`

表示用户视角的一条成片任务。

建议字段：

- `id`
- `user_id`
- `title`
- `prompt`
- `story_text`
- `story_summary`
- `storyboard_json`
- `provider_code`
- `provider_config_snapshot_json`
- `status`
- `stage`
- `status_text`
- `scene_count`
- `finished_scene_count`
- `failed_scene_count`
- `compose_status`
- `compose_error`
- `final_video_url`
- `final_cover_url`
- `final_duration_s`
- `aspect_ratio`
- `template_id`
- `template_name`
- `bgm_config_json`
- `subtitle_config_json`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`
- `deleted_at`

说明：

- `final_video_url` 应优先存最终成片地址，而不是本地文件路径
- `provider_config_snapshot_json` 用于保留任务创建时的配置快照
- `provider_code` 表示当前父任务默认使用的 Provider

### 2. `scene_jobs`

表示每个分镜对应的一条云端子任务。

建议字段：

- `id`
- `render_job_id`
- `scene_index`
- `scene_title`
- `scene_prompt`
- `scene_duration_s`
- `provider_code`
- `provider_task_id`
- `provider_status`
- `normalized_status`
- `progress`
- `request_payload_json`
- `response_payload_json`
- `result_video_url`
- `result_cover_url`
- `error_message`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

说明：

- 每个分镜必须单独记录 `provider_task_id`
- 这样才能真正支持按分镜轮询、失败重试、状态聚合
- 当前默认同一父任务下所有分镜使用同一 Provider
- 如果后续允许不同分镜使用不同 Provider，则以 `scene_jobs.provider_code` 为准
- 对于 `jimeng`，这些字段应重点使用：
  - `provider_task_id` <- `task_id`
  - `provider_status` <- `status`
  - `result_video_url` <- `video_url`
  - `response_payload_json` <- 查询接口原始返回

### 3. `provider_configs`

因为后续前端要有配置界面，所以还需要 Provider 配置实体。

这里需要采用“公共头 + 私有配置 JSON”的统一模型。

#### 公共字段

- `id`
- `provider_code`
- `display_name`
- `enabled`
- `sort_order`
- `description`
- `config_version`
- `provider_config_json`
- `is_valid`
- `last_checked_at`
- `last_error`
- `created_at`
- `updated_at`

说明：

- `provider_code` 是唯一内部标识
- `display_name` 用于前端展示
- `enabled` 控制是否对前端可选
- `sort_order` 控制前端展示顺序
- `description` 用于配置页说明
- `config_version` 用于后续配置迁移
- `provider_config_json` 存放厂商私有字段
- `is_valid / last_checked_at / last_error` 用于展示配置健康状态

#### 私有配置 JSON 规则

Provider 的专有鉴权字段和运行参数统一存到 `provider_config_json` 中。

##### `jimeng`

- `app_key`
- `app_secret`
- 可选：`base_url`
- 可选：`region`
- 可选：`req_key`
- 可选：`callback_url`

##### `openai`

- `api_key`
- `model`
- 可选：`base_url`
- 可选：`timeout_s`

说明：

- `openai` 也是标准 Provider，不是特殊分支
- `model` 按当前约定放在私有配置 JSON 中，不提升为公共字段
- 文档明确反对把所有 Provider 字段都做成数据库结构化列

## 统一 Provider 字段模型

### 总体原则

所有 Provider 都使用统一配置模型：

- 公共头字段：系统级通用元数据
- 私有配置 JSON：厂商专有鉴权与参数字段

这套模型要同时覆盖：

- `jimeng`
- `openai`
- 后续其他 Provider

### 不采用的方案

以下两种方案明确不采用：

- 前端写死 Provider 字段
- 把所有 Provider 字段都做成数据库表列

原因：

- 前端写死字段会导致无法动态扩展 Provider 配置页
- 全结构化列会导致每接一个新 Provider 都改表结构，扩展性差

### 最终配置分层

#### 公共头字段

所有 Provider 共用：

- `provider_code`
- `display_name`
- `enabled`
- `sort_order`
- `description`
- `config_version`
- `is_valid`
- `last_checked_at`
- `last_error`

#### 私有配置 JSON

每个 Provider 自己定义：

- `jimeng`: `app_key/app_secret/...`
- `openai`: `api_key/model/...`

### 使用方式

- 后端配置界面基于公共头字段管理 Provider 列表
- 认证字段和厂商专有参数从 `provider_config_json` 中读取
- 任务创建时把当前使用的配置写入 `provider_config_snapshot_json`

## 前端 Provider 获取与配置

### 当前问题

当前前端 Provider 列表写死在 `static/app.js`，这是错误方向。

问题在于：

- 后端没配置的 Provider 也会显示在前端
- 无法动态反映 Provider 是否可用
- 无法扩展 Provider 配置界面

### 目标原则

前端 Provider 列表必须由后端接口返回，而不是写死。

### 建议接口

#### 1. `GET /api/providers`

返回当前系统中“已注册且已配置”的 Provider 列表。

返回内容建议包括：

- `code`
- `display_name`
- `enabled`
- `configured`
- `capabilities`
- `configurable`

工作区顶部或侧栏的 Provider 选择器应基于该接口渲染。

#### 2. `GET /api/provider-configs`

返回配置界面所需的 Provider 配置列表。

#### 3. `PUT /api/provider-configs/{provider_code}`

保存指定 Provider 的配置。

#### 4. `POST /api/provider-configs/{provider_code}/validate`

触发校验，检查配置是否可用。

#### 5. 配置字段定义

前端配置页不应写死 `api_key/app_key/app_secret/model` 这些字段。

配置页字段应由后端返回，来源可以是：

- `BaseProvider.list_config_fields()`
- 或统一的 Provider 元数据接口返回字段定义

这样前端才能按不同 Provider 动态渲染表单。

### 前端 UI 规划

工作区里应区分两件事：

#### 1. 选择 Provider

这是创作行为。  
用户在生成任务时选择用哪个 Provider。

#### 2. 配置 Provider

这是系统配置行为。  
用户或管理员配置 AK/SK、区域、模型默认值等。

因此，前端应新增一个 Provider 配置 Tab 或页面，而不是把“选择”和“配置”混在一个入口里。

建议最少有两个区域：

- 工作区中的 Provider 选择器
- 独立的 Provider 配置 Tab / 设置页

## BaseProvider 模板

当前 Provider 抽象过于粗糙，只有单一 `render(ctx)`，不适合云端异步任务模式。

后续 BaseProvider 应按统一模板设计，不再围绕固定 `api_key` 字段。

### 最小核心方法

每个 Provider 至少实现：

- `code() -> str`
- `display_name() -> str`
- `validate_config(provider_config_json) -> list[str]`
- `get_capabilities() -> dict`
- `create_task(scene, job_context, provider_config_json)`
- `get_task(provider_task_id, provider_config_json)`
- `update_task(scene_job, provider_task_result)`

### 扩展能力方法

可选扩展接口：

- `normalize_status(provider_status)`
- `extract_result_assets(task_status_result)`
- `list_config_fields()`
- `healthcheck(provider_config_json)`

### 设计原则

- BaseProvider 不要求固定存在 `api_key`
- 鉴权字段完全由 `provider_config_json` 决定
- 所有 Provider 都必须遵循 `create_task / get_task / update_task` 模板

## 典型 Provider 映射

### `jimeng`

- `provider_code`: `jimeng`
- `display_name`: `即梦`
- `provider_config_json`:
  - `app_key`
  - `app_secret`
  - 可选：`base_url`
  - 可选：`region`
  - 可选：`req_key`
  - 可选：`callback_url`
- 核心方法：
  - `create_task`
  - `get_task`
  - `update_task`

### `openai`

- `provider_code`: `openai`
- `display_name`: `OpenAI`
- `provider_config_json`:
  - `api_key`
  - `model`
  - 可选：`base_url`
  - 可选：`timeout_s`
- 核心方法：
  - `create_task`
  - `get_task`
  - `update_task`

说明：

- `openai` 与 `jimeng` 同属于标准 Provider
- 差异只体现在私有配置字段，不体现在 Provider 接入模板上

## 视频合成职责

### 当前目标

我们的业务链路不应理解为“让单个 Provider 直接生成整条故事视频”。

更合理的理解是：

1. 文本拆成分镜
2. 每个分镜生成视频片段
3. 所有分镜片段完成后
4. 我们自己进行最终视频合成

### 合成层职责

最终合成层至少负责：

- 按分镜顺序拼接片段
- 处理时长与转场
- 烧录字幕
- 混入 BGM
- 输出最终成片
- 可选抽取封面

### ffmpeg 的未来定位

ffmpeg 后续更适合固定在“合成与后处理层”，而不是“镜头生成层”。

即：

- 分镜视频生成：交给云端 Provider
- 视频合成与后处理：由我们本地合成层完成

## 后续实现约束

### 第一原则

所有 Provider 都必须参考即梦模板，不允许每个 Provider 自己定义完全不同的接入方式。

### 第二原则

前端 Provider 列表与配置不允许写死。

### 第二点五原则

Provider 配置必须走统一字段模型：

- 公共头字段
- 私有配置 JSON

不能因为 `openai` 只有 `api_key/model`、`jimeng` 需要 `app_key/app_secret`，就让 Provider 结构分裂。

### 第三原则

Job 设计必须支持“父任务 + 分镜子任务”，否则后续无法稳定支持多分镜视频生成。

### 第四原则

不再以本地二进制文件作为主存储设计前提。

## 待核对项

以下内容已经通过渲染后的官方文档确认：

- 提交接口 URL
- 查询接口 URL
- `task_id`
- `status`
- `video_url`
- `req_key = jimeng_ti2v_v30_pro`
- `frames` 可选值
- `aspect_ratio` 可选值

以下内容仍建议在正式开发前通过 API Explorer 或控制台样例补充核对：

- 外层通用返回结构中的 `code`、`message`、`request_id`
- 是否存在封面图专用字段
- 官方 SDK 客户端初始化的推荐参数写法
- 即梦是否支持回调通知替代轮询
- 图生视频请求里 URL 图和 Base64 图的边界限制是否还有新增约束

## 本次结论

本次我们的理解可以总结为：

- 即梦接入应以“创建任务 + 获取任务”两类方法为核心
- Job 不应再只是一条简单任务记录，而应拆成父任务和分镜子任务
- Provider 基类必须标准化，后面所有 Provider 都按同一模板接
- 前端获取 Provider 不应写死，应由后端接口动态提供
- 前端需要新增 Provider 配置界面，不能只做 Provider 选择
- 如果依赖云厂商存储，我们不需要把所有二进制长期保存在本地
- 我们真正负责的是：分镜编排、任务调度、结果聚合、最终视频合成
- ffmpeg 的未来职责应收缩到最终拼接与后处理，而不是继续承担主生成链路

## 实施任务拆解

以下任务用于指导后续代码实施，按阶段推进。

### 阶段 1：任务模型与数据层

- 新建 `render_jobs` 实体与数据访问层
- 新建 `scene_jobs` 实体与数据访问层
- 新建 `provider_configs` 实体与数据访问层
- 将当前基于 `jobs.json` 的任务存储迁移为数据库持久化
- 为父任务与分镜子任务建立状态聚合逻辑
- 在任务实体中落地 `provider_config_snapshot_json`

### 阶段 2：BaseProvider 与 Provider 注册中心

- 重构当前 Provider 抽象，移除单一 `render(ctx)` 设计
- 定义统一 `BaseProvider` 接口：
  - `code`
  - `display_name`
  - `validate_config`
  - `get_capabilities`
  - `create_task`
  - `get_task`
  - `update_task`
  - `list_config_fields`
  - `healthcheck`
- 建立 Provider Registry，统一注册 `jimeng`、`openai` 等 Provider
- 提供“已注册 / 已启用 / 已配置”的统一查询能力

### 阶段 3：即梦 Provider 落地

- 新建 `JimengProvider`
- 根据官方接口实现 `create_task`
- 根据官方接口实现 `get_task`
- 根据内部状态模型实现 `update_task`
- 写清 `task_id -> provider_task_id` 的映射
- 写清 `status -> normalized_status` 的映射
- 写清 `video_url -> result_video_url` 的映射
- 保存厂商原始响应到 `response_payload_json`

### 阶段 4：OpenAI Provider 模板化接入

- 新建 `OpenAIProvider`
- 使用与 `JimengProvider` 相同的 BaseProvider 模板
- 按 `provider_config_json` 读取：
  - `api_key`
  - `model`
  - 可选 `base_url`
- 保证 OpenAI 不是特殊实现，而是标准 Provider 的一个实例

### 阶段 5：任务编排与轮询

- 父任务创建时将故事拆分为多个分镜
- 为每个分镜创建一个 `scene_job`
- Worker 为每个 `scene_job` 调用对应 Provider 的 `create_task`
- 定时任务轮询未完成的 `scene_jobs`
- 轮询时调用 Provider 的 `get_task`
- 查询结果后调用 Provider 的 `update_task`
- 所有子任务完成后，更新父任务为可合成状态

### 阶段 6：最终视频合成

- 基于 `scene_jobs.result_video_url` 获取片段资源
- 按分镜顺序进行拼接
- 混入字幕
- 混入 BGM
- 输出最终成片
- 将最终成片地址写回 `render_jobs.final_video_url`
- 生成封面并写回 `render_jobs.final_cover_url`

### 阶段 7：Provider 配置接口

- 新增 `GET /api/providers`
- 新增 `GET /api/provider-configs`
- 新增 `PUT /api/provider-configs/{provider_code}`
- 新增 `POST /api/provider-configs/{provider_code}/validate`
- 返回字段定义，供前端动态渲染 Provider 配置表单

### 阶段 8：前端改造

- 工作区 Provider 选择器改为请求后端 `GET /api/providers`
- 移除前端硬编码 Provider 数组
- 新增 Provider 配置 Tab / 页面
- 配置页通过后端字段定义动态渲染：
  - `jimeng` 展示 `app_key/app_secret`
  - `openai` 展示 `api_key/model`
- 任务页展示父任务与分镜任务的状态聚合结果

### 阶段 9：测试与验收

- 验证 `jimeng` 配置校验通过与失败场景
- 验证 `openai` 配置校验通过与失败场景
- 验证 `create_task / get_task / update_task` 模板可覆盖不同 Provider
- 验证父任务创建后能够正确拆分分镜并创建 `scene_jobs`
- 验证轮询更新后能正确推进任务状态
- 验证所有分镜完成后触发最终合成
- 验证前端 Provider 列表不再写死
- 验证 Provider 配置页按后端字段定义动态渲染

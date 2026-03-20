# 🤖 Automated Optimization Workflow - Quick Start

## 什么是自动化优化工作流？

这是一个基于 **OpenClaw 心跳机制**的智能定时任务系统，可以每 2 小时自动执行 pet-anime-video 项目的优化任务。无需配置外部 cron，完全通过 OpenClaw 原生功能实现。

## ✨ 主要特点

✅ **零配置启动** - 利用 OpenClaw 内置心跳机制  
⏰ **智能调度** - 每 2 小时自动检查并执行下一个任务  
🤖 **Agent 工作流** - 使用专业的子 agent 完成具体优化  
📊 **状态追踪** - 完整记录每个任务的进度和时间  
🔄 **断点续传** - 支持暂停、恢复、重试  

## 🎯 当前任务清单

### ✅ 已完成
- [x] **配置管理优化** (2026-03-19)
  - API key 统一管理
  - 环境变量处理
  - `.env.example` 模板

### ⏳ 待执行（按优先级排序）

| # | 任务 | 预计耗时 | 说明 |
|---|------|----------|------|
| 1 | Docker 化部署 | 2-3 小时 | Dockerfile + docker-compose 一键部署 |
| 2 | 单元测试覆盖 | 3-4 小时 | pytest 框架 + 70%+代码覆盖率 |
| 3 | 文档完善 | 2-3 小时 | API/部署/贡献指南 |
| 4 | 前端体验优化 | 3-5 小时 | 响应式设计 + 拖拽上传 + 进度可视化 |
| 5 | 代码质量提升 | 2-3 小时 | 类型注解 + 日志标准化 + pre-commit |

**总计**: 约 12-18 小时的优化工作

## 🚀 工作原理

```
每天早上/每 2 小时的偶数点 (00:00, 02:00, 04:00...)
    ↓
OpenClaw 心跳检查 HEARTBEAT.md
    ↓
运行 scripts/check-heartbeat-task.py
    ↓
检查条件:
  ✓ 当前是偶数小时
  ✓ 距离上次运行超过 2 小时
  ✓ 有待执行的任务
    ↓ YES
spawn sub-agent via sessions_spawn()
    ↓
Developer Agent 执行详细优化任务
    ↓
完成后更新 .workflow-state.json
    ↓
下次心跳继续下一个任务
```

## 📋 快速操作

### 查看当前状态

```bash
cd /home/fengxiaozi/.openclaw/workspace/pet-anime-video

# 查看任务状态
python scripts/workflow-agent.py --status

# 检查心跳条件
python scripts/check-heartbeat-task.py
```

输出示例：
```
============================================================
Pet Anime Video - Workflow Status
============================================================
✅ config-management: COMPLETED 2026-03-19
⏳ docker-setup: PENDING 
⏳ unit-tests: PENDING 
...

🎯 Next task: docker-setup
============================================================
```

### 手动触发任务

如果你想立即开始优化（不需要等待 2 小时）：

```bash
# 手动重置时间戳以触发任务
echo '{"last_run": null}' > memory/pet-workflow-state.json

# 然后检查是否可以执行
python scripts/check-heartbeat-task.py
```

如果显示 "Ready to execute task: docker-setup"，则可以 spawn 对应的 agent。

### 启动交互式仪表板

```bash
bash scripts/dashboard.sh
```

提供菜单驱动的界面来：
- 查看详细任务描述
- 手动触发下一个任务
- 标记任务完成
- 查看实时日志

## 📁 关键文件

```
pet-anime-video/
├── scripts/
│   ├── workflow-agent.py          # 主调度器 (备用)
│   ├── check-heartbeat-task.py    # 心跳检查脚本 ⭐
│   └── workflow-config.py         # 任务定义和详细说明 ⭐
├── .workflow-state.json           # 任务状态跟踪 ⭐
├── memory/
│   └── pet-workflow-state.json   # 最后运行时间 ⭐
├── OPENCLAW_WORKFLOW.md           # 完整技术文档
└── AUTO_WORKFLOW_README.md        # 本文档
```

标注 ⭐ 的是核心运行文件。

## ⏰ 调度规则

### 执行时间
- **频率**: 每 2 小时检查一次
- **时段**: 偶数小时 (00:00, 02:00, 04:00, ... 22:00)
- **间隔**: 至少 2 小时才能再次执行

### 为什么这样设计？
- ✅ 避免连续 spawn 多个 agent 造成资源竞争
- ✅ 给每个任务充足的时间完成（2-5 小时）
- ✅ 用户可以在白天看到进度（早中晚都有执行机会）
- ✅ 夜间也有优化机会但不会太频繁打扰

### 自定义时间

如果想修改为特定时间（如只在工作时间），编辑 `scripts/check-heartbeat-task.py`:

```python
# 改为只在工作时间运行 (9am-6pm)
if current_hour < 9 or current_hour > 18:
    return False, "Outside work hours"
```

## 🔍 监控与调试

### 查看下次运行时间

```bash
python scripts/check-heartbeat-task.py
```

输出会告诉你是"正在等待 X 小时后"还是"准备执行 Y 任务"。

### 查看最近活动时间

```bash
cat memory/pet-workflow-state.json
```

### 查看所有任务状态

```bash
cat .workflow-state.json | python -m json.tool
```

### 实时监控进程

如果有活跃的 agent session：

```bash
# 列出所有活跃会话
openclaw sessions list

# 查看特定会话历史
openclaw sessions history <session_key>
```

## 🛠️ 常见问题

### Q: 如何确认系统在工作？

A: 运行以下命令查看状态：
```bash
python scripts/check-heartbeat-task.py
```

如果显示 "Skipping this heartbeat cycle" 并说明原因（如"wait 1.5h more"），说明系统在正常工作，只是在等待时机。

### Q: 我可以加速这个过程吗？

A: 有几种方式：
1. **立即执行**: 重置时间戳（见上方"手动触发任务"）
2. **缩短间隔**: 修改 `check-heartbeat-task.py` 中的 2 小时限制
3. **并行执行**: 不推荐，但可以手动 spawn 多个 agent

### Q: 如果我想要暂停优化怎么办？

A: 两种方式：
1. **临时暂停**: 将所有任务改为 `in_progress` 状态
2. **永久停止**: 删除 HEARTBEAT.md 中的第 3 节（Pet Anime Video 部分）

### Q: 如何在任务之间插入新任务？

A: 编辑 `scripts/workflow-config.py`，添加新的 task 到 TASKS 字典，然后更新 `.workflow-state.json` 和优先级顺序。

### Q: 如果 agent 失败了怎么办？

A: 
1. 检查会话日志了解失败原因
2. 手动修复问题（如果是环境问题等）
3. 将任务状态改回 `pending` 以便重新执行
4. 或者标记为 `completed` 跳过该任务

## 🎓 最佳实践

### ✅ 建议做的事

- **定期检查进度**: 每天运行一次 `--status` 查看整体进展
- **验证关键更改**: Docker 配置、测试代码等重要修改要人工审查
- **保留版本控制**: 大改动前提交 git commit，便于回退
- **阅读 agent 报告**: 完成后查看 agent 的输出总结

### ❌ 避免做的事

- **不要频繁手动干预**: 让 agent 完成整个任务再检查
- **不要在 in_progress 时修改状态**: 可能导致状态混乱
- **不要期望即时完成**: 复杂任务需要数小时
- **不要同时运行多个实例**: 可能导致冲突

## 📈 预期时间表

假设从明天 00:00 开始：

```
Day 1, 00:00 → docker-setup 开始
Day 1, 02:00 → 跳过（任务进行中）
Day 1, 04:00 → 跳过（任务进行中）
Day 1, 06:00 → docker-setup 完成 ✅

Day 1, 08:00 → unit-tests 开始
Day 1, 10:00 → 跳过（任务进行中）
Day 1, 12:00 → 跳过（任务进行中）
Day 1, 14:00 → unit-tests 完成 ✅

... 继续直到所有任务完成
```

**总时长**: 预计 1-2 个工作日完成全部 5 个任务

## 🔗 相关文档

- **完整技术文档**: [OPENCLAW_WORKFLOW.md](./OPENCLAW_WORKFLOW.md)
- **实现总结**: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- **任务详情**: 在 `scripts/workflow-config.py` 中查看每个任务的详细说明

## 💡 高级用法

### 查看某个任务的详细要求

```bash
# 查看 docker-setup 的详细说明
python -c "
from scripts.workflow_config import TASKS
import textwrap
print(TASKS['docker-setup']['description'])
"
```

### 导出任务清单为 Markdown

```bash
python -c "
from scripts.workflow_config import TASKS
for name, info in TASKS.items():
    print(f'## {info[\"priority\"]}. {info[\"title\"]}')
    print(f'Priority: {info[\"priority\"]}\n')
"
```

---

**创建日期**: 2026-03-20  
**版本**: 2.0 (基于 OpenClaw heartbeat)  
**状态**: ✅ 已激活  
**下次检查**: 下一偶数小时（大约 1-2 小时后）

**需要帮助？** 查看 [OPENCLAW_WORKFLOW.md](./OPENCLAW_WORKFLOW.md) 获取完整技术细节。

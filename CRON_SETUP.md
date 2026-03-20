# Pet Anime Video - Self-Wake Cron System

## 方案设计

使用 **OpenClaw sessions + heartbeat** 实现自我唤醒机制。

### 架构

```
主会话 (Main Session)
    ↓ 每 ~30 分钟接收 heartbeat
读取 HEARTBEAT.md
    ↓ 执行检查逻辑
spawn pet-optimizer session (如果条件满足)
    ↓ 独立的持久化会话
pet-optimizer 执行具体优化任务
    ↓
完成 → 退出 session
等待 → 下次 heartbeat 继续
```

### 关键文件

1. **HEARTBEAT.md** (~/) - 心跳触发器定义
2. **.workflow-state.json** (项目目录) - 任务状态追踪
3. **memory/pet-workflow-state.json** - 时间戳记录
4. **scripts/pet-optimizer.py** - 自动化 optimizer agent

## 工作流程

### Step 1: Heartbeat 检查 (~每 30 分钟)
- 读取 HEARTBEAT.md 第 3 节
- 运行 `scripts/check-heartbeat-task.py`
- 输出是否应该触发下一个任务

### Step 2: 条件判断
```python
if 当前是偶数小时 and 距离上次 >2 小时 and 有待执行任务:
    # 触发 optimizer
else:
    # 跳过本次 heartbeat
```

### Step 3: Spawn Sub-Agent
当条件满足时，spawn 一个新的 session：
```python
sessions_spawn(
    agent_id="developer",
    task="""[从 workflow-config.py 获取详细任务描述]""",
    mode="session",  # 持久化会话
    cwd="/home/fengxiaozi/.openclaw/workspace/pet-anime-video"
)
```

### Step 4: 独立执行
Sub-agent 在独立会话中工作：
- 可以持续数小时
- 不受主会话影响
- 完成后自动标记任务完成

### Step 5: 状态更新
- 更新 `.workflow-state.json`
- 更新 `memory/pet-workflow-state.json:last_run`
- 下次 heartbeat 检查新状态

## 实现细节

### 核心脚本：`scripts/pet-optimizer.py`

这个脚本被 spawn 的 sub-agent 调用，负责：
1. 读取当前待执行任务
2. 加载详细任务描述
3. 执行具体的优化代码
4. 完成后更新状态

### 心跳检查：`scripts/check-heartbeat-task.py`

由 HEARTBEAT.md 触发，负责：
1. 验证时间条件（偶数小时）
2. 检查间隔条件（>2 小时）
3. 查找待执行任务
4. 决定是否应该 spawn optimizer

## 启动方式

### 方法 1：通过 HEARTBEAT.md（推荐）

主会话的心跳会自动检查并触发。无需手动干预。

### 方法 2：手动触发测试

```bash
cd /home/fengxiaozi/.openclaw/workspace/pet-anime-video

# 重置时间戳以强制触发
echo '{"last_run": null}' > memory/pet-workflow-state.json

# 验证准备就绪
python scripts/check-heartbeat-task.py

# 手动 spawn optimizer（模拟 heartbeat）
# 这需要在 OpenClaw 会话中通过 sessions_spawn 工具完成
```

## 监控和维护

### 查看状态
```bash
python scripts/workflow-agent.py --status
```

### 查看活跃会话
```bash
openclaw sessions list | grep pet
```

### 查看日志
```bash
tail -f logs/workflow.log
```

## 优势

✅ **完全集成**: 利用 OpenClaw 现有机制  
✅ **零配置**: 不需要外部 cron 服务  
✅ **可靠**: 心跳保证定期检查  
✅ **灵活**: 可随时调整频率和规则  
✅ **透明**: 所有操作都有日志可查

## 缺点

⚠️ **依赖主会话在线**: 需要 OpenClaw 主进程运行  
⚠️ **检查间隔不精确**: heartbeat 是~30 分钟而非固定  

## 故障排除

### Q: 为什么不触发？
A: 检查三个条件：
1. 当前小时是否是偶数？
2. 距离上次运行是否超过 2 小时？
3. `.workflow-state.json` 中是否有 pending 任务？

### Q: Session 卡住了怎么办？
A: 
```bash
# 杀死卡住的会话
openclaw sessions kill <session_key>

# 重置任务状态为 pending
python scripts/workflow-agent.py --reset <task_name>
```

### Q: 如何临时禁用自动化？
A: 
```bash
# 将所有任务标记为 completed
cat .workflow-state.json | jq '.tasks |= with_entries(.value.status = "completed")' > temp.json && mv temp.json .workflow-state.json

# 或删除 HEARTBEAT.md 的第 3 节
```

---

**创建时间**: 2026-03-20  
**版本**: 1.0  
**状态**: 配置完成，等待第一次 heartbeat 触发

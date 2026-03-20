# OpenClaw Automated Workflow Guide

## Overview

This project uses **OpenClaw's heartbeat mechanism** to automatically optimize the codebase every 2 hours. No external cron jobs required - everything runs through OpenClaw's native scheduling.

## How It Works

### Architecture

```
OpenClaw Heartbeat (every ~30 min)
          ↓
   Check HEARTBEAT.md rules
          ↓
  scripts/check-heartbeat-task.py
          ↓
    ┌───── Conditions met? ─────┐
    │  1. Current hour is even  │
    │  2. 2+ hours since last   │
    │  3. Pending tasks exist   │
    └──────────────┬─────────────┘
                   ↓ YES
       sessions_spawn() 
                   ↓
      Sub-agent (developer)
    executes optimization task
                   ↓
      Updates .workflow-state.json
```

### Scheduling Logic

The workflow runs **every 2 hours on even hours**:
- ✅ Runs at: 00:00, 02:00, 04:00, 06:00, ... 22:00
- ❌ Skips at: 01:00, 03:00, 05:00, 07:00, ... 23:00

Minimum interval: **2 hours** between executions

## File Structure

```
pet-anime-video/
├── scripts/
│   ├── check-heartbeat-task.py   # Heartbeat condition checker
│   └── workflow-config.py        # Task definitions & descriptions
├── .workflow-state.json          # Task status tracking
└── memory/
    └── pet-workflow-state.json   # Last run timestamp
```

## Usage

### Automatic Execution

Nothing to configure! The workflow automatically:
1. Runs during heartbeat checks (every ~30 minutes)
2. Checks if 2 hours have passed since last run
3. Spawns sub-agent for next pending task
4. Updates state files

### Manual Trigger

You can manually trigger the next task:

```bash
cd /home/fengxiaozi/.openclaw/workspace/pet-anime-video
python scripts/check-heartbeat-task.py
```

If conditions are met, it will print instructions for spawning the agent.

### Check Current Status

```bash
# View workflow status
python scripts/workflow-agent.py --status

# Test heartbeat conditions
python scripts/check-heartbeat-task.py

# Interactive dashboard
bash scripts/dashboard.sh
```

## State Files

### .workflow-state.json

Tracks task completion status:

```json
{
  "tasks": {
    "docker-setup": {"status": "pending"},
    "unit-tests": {"status": "pending"}
  },
  "current_task": null,
  "last_check": "2026-03-20T00:00:00"
}
```

### memory/pet-workflow-state.json

Tracks execution timing:

```json
{
  "last_run": "2026-03-20T00:00:00",
  "notes": "Last workflow execution timestamp"
}
```

## Task Flow

When heartbeat triggers:

1. **Condition Check** (`check-heartbeat-task.py`)
   - Verifies current hour is even
   - Checks 2+ hours elapsed since last run
   - Finds next pending task

2. **State Update**
   - Marks task as `in_progress`
   - Updates last run timestamp

3. **Agent Spawn** (via OpenClaw `sessions_spawn`)
   ```python
   sessions_spawn(
       agent_id="developer",
       mode="session",
       cwd="/home/fengxiaozi/.openclaw/workspace/pet-anime-video",
       task="""[Detailed task from workflow-config.py]"""
   )
   ```

4. **Execution**
   - Sub-agent works independently in persistent session
   - Can take multiple hours to complete complex tasks
   - Reports progress and results

5. **Completion**
   - User or agent marks task as completed
   - Next heartbeat picks up following task

## Tasks

| Priority | Task | Estimated Duration | Description |
|----------|------|-------------------|-------------|
| 1 | docker-setup | 2-3 hours | Dockerfile, docker-compose, deployment docs |
| 2 | unit-tests | 3-4 hours | pytest suite with 70%+ coverage |
| 3 | docs-improve | 2-3 hours | API, deployment, contributing guides |
| 4 | ui-improve | 3-5 hours | Responsive design, drag-drop, progress UI |
| 5 | code-quality | 2-3 hours | Type hints, logging, pre-commit hooks |

Total estimated time: ~12-18 hours across all tasks

## Monitoring

### View Recent Activity

```bash
# Check when last task ran
cat memory/pet-workflow-state.json

# Check task statuses
cat .workflow-state.json | python -m json.tool
```

### Logs

Agent sessions will log to their respective session logs. Check via:

```bash
# List active sessions
openclaw sessions list

# View session history
openclaw sessions history <session_key>
```

## Advantages vs System Cron

| Feature | OpenClaw Heartbeat | Linux Cron |
|---------|------------------|------------|
| Setup | Zero configuration | Manual crontab editing |
| Persistence | Survives reboots automatically | Requires cron service running |
| Integration | Native sessions_spawn support | External script invocation |
| Visibility | In OpenClaw session logs | Separate log files |
| Control | Via HEARTBEAT.md | Via crontab file |
| Reliability | Depends on OpenClaw uptime | OS-level reliability |

## Troubleshooting

### Issue: Task not running every 2 hours

**Check:**
1. Is OpenClaw heartbeat enabled?
2. Is HEARTBEAT.md properly configured?
3. Are there pending tasks in `.workflow-state.json`?

**Debug:**
```bash
python scripts/check-heartbeat-task.py
```

This will show exactly why a task is/wasn't triggered.

### Issue: Agent spawn fails

**Check:**
1. OpenClaw is running: `openclaw status`
2. Network connectivity is available
3. Agent has necessary permissions

**Action:** Try manual spawn with detailed error messages

### Issue: Task stuck in "in_progress"

**Resolution:**
```bash
# Option 1: Mark as complete if actually done
python scripts/workflow-agent.py --complete <task_name>

# Option 2: Reset to pending if needs retry
python -c "
import json
with open('.workflow-state.json') as f:
    state = json.load(f)
state['tasks']['<task_name>'] = {'status': 'pending'}
state['current_task'] = None
with open('.workflow-state.json', 'w') as f:
    json.dump(state, f, indent=2)
print('Reset complete')
"
```

## Customization

### Change Frequency

Edit `HEARTBEAT.md` section 3 to change from 2 hours to different interval.

### Adjust Schedule

Modify `check-heartbeat-task.py`:
```python
# Change from even hours to specific hours
if current_hour not in [9, 13, 17, 21]:  # Run at 9am, 1pm, 5pm, 9pm
    return False, "Not in scheduled window"
```

### Add New Tasks

1. Add entry to `scripts/workflow-config.py` TASKS dict
2. Add to priority order in both config files
3. Initialize status in `.workflow-state.json`

## Best Practices

✅ **DO:**
- Let tasks complete before triggering next one
- Review agent output regularly
- Manually verify critical changes
- Keep task descriptions clear and actionable

❌ **DON'T:**
- Modify state files while task is in_progress
- Skip verification of completed work
- Expect instant completion (tasks take hours)
- Run multiple instances simultaneously

## Example Timeline

```
Day 1, 00:00 - docker-setup starts (spawned by heartbeat)
Day 1, 02:00 - heartbeat skips (task in progress)
Day 1, 04:00 - heartbeat skips (task in progress)
Day 1, 06:00 - docker-setup completes, marked done
Day 1, 08:00 - unit-tests starts (next pending task)
Day 1, 10:00 - heartbeat skips (task in progress)
... continues until all tasks complete
```

Estimated total duration: 1-2 days for all 5 tasks

---

**Created**: 2026-03-20  
**Updated**: Using OpenClaw native heartbeat instead of system cron  
**Next Run**: Next even hour (check `python scripts/check-heartbeat-task.py`)

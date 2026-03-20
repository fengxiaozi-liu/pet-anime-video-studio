# Automated Workflow Agent System

This document describes the automated workflow agent system for continuous project optimization.

## Overview

The workflow agent is an automated task orchestration system that:
- Tracks pending optimization tasks from `AUDIT_REPORT.md`
- Automatically executes the next highest priority task daily at 9:00 AM
- Uses OpenClaw's multi-agent capability to delegate work to specialized agents
- Maintains state persistence across runs
- Logs all activities for auditing and debugging

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Cron / Systemd Timer                   │
│           (Daily at 9:00 AM trigger)                │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   scheduled-workflow.py      │
        │   (Scheduler & Logger)       │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   workflow-agent.py          │
        │   (Task Orchestrator)        │
        │                              │
        │  - Loads workflow state      │
        │  - Identifies next task      │
        │  - Spawns sub-agents         │
        │  - Updates completion status │
        └──────────────┬───────────────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
           ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │ Docker │  │Testing│  │Docs    │
    │ Agent  │  │Agent  │  │Agent   │
    └────────┘  └────────┘  └────────┘
```

## Task Priority Order

Tasks are executed in this fixed order:

1. **config-management** ✅ Completed (2026-03-19)
   - API key management with Pydantic Settings
   - Environment variable handling
   - `.env.example` template

2. **docker-setup** ⏳ Pending
   - Create production-ready Dockerfile
   - docker-compose.yml for one-click deployment
   - Multi-stage builds for optimal image size

3. **unit-tests** ⏳ Pending
   - pytest framework setup
   - Test coverage for core modules (70%+)
   - Mock external API calls

4. **docs-improve** ⏳ Pending
   - API.md - Complete REST API reference
   - DEPLOYMENT.md - Deployment guide
   - CONTRIBUTING.md - Contribution guidelines
   - Enhanced README.md

5. **ui-improve** ⏳ Pending
   - Responsive design (mobile-first)
   - Drag & drop file upload
   - Progress visualization
   - Improved error handling

6. **code-quality** ⏳ Pending
   - Type annotations (90%+ coverage)
   - Logging standardization
   - Docstrings (Google style)
   - Pre-commit hooks setup

## Setup Instructions

### Option A: Cron Job (Simple)

```bash
cd /home/fengxiaozi/.openclaw/workspace/pet-anime-video
bash scripts/cron-setup.sh
```

This installs a cron job that runs daily at 9:00 AM.

View logs:
```bash
tail -f logs/workflow.log
```

Remove cron job:
```bash
bash scripts/cron-setup.sh --remove
```

### Option B: Systemd Timer (Production)

```bash
# Copy systemd units to system directory
sudo cp systemd/pet-workflow.service /etc/systemd/system/
sudo cp systemd/pet-workflow.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable --now pet-workflow.timer

# Check status
systemctl list-timers | grep pet-workflow
```

View logs:
```bash
journalctl -u pet-workflow.service -f
```

Disable timer:
```bash
sudo systemctl disable --now pet-workflow.timer
```

## Manual Commands

You can also trigger tasks manually:

### View current status
```bash
python scripts/workflow-agent.py --status
```

### Auto-execute next task
```bash
python scripts/workflow-agent.py --auto
```

### Execute specific task
```bash
python scripts/workflow-agent.py --task docker-setup
```

### Mark task as complete
```bash
python scripts/workflow-agent.py --complete unit-tests
```

## State Management

Workflow state is stored in `.workflow-state.json`:

```json
{
  "tasks": {
    "config-management": {
      "status": "completed",
      "completed_at": "2026-03-19"
    },
    "docker-setup": {
      "status": "in_progress"
    },
    "unit-tests": {
      "status": "pending"
    }
  },
  "last_run": "2026-03-19T09:00:00",
  "current_task": "docker-setup"
}
```

Task states:
- `pending`: Not yet started
- `in_progress`: Currently being worked on by agent
- `completed`: Finished and verified

## Integration with OpenClaw Agents

When the workflow agent spawns a sub-agent, it uses `sessions_spawn` with:

- **agentId**: Selected based on task type (developer, reviewer, etc.)
- **task**: Detailed task description including:
  - Context and requirements
  - Specific deliverables
  - Constraints and guidelines
  - Project location

Example agent spawn for Docker setup:
```python
sessions_spawn(
    agent_id="developer",
    task="""
# Docker Setup Task

## Requirements
1. Create Dockerfile for FastAPI backend
2. Create docker-compose.yml
3. Add .dockerignore
...
""",
    mode="session",
    cwd="/home/fengxiaozi/.openclaw/workspace/pet-anime-video"
)
```

## Logging

All workflow activities are logged to `logs/workflow.log`:

```
[2026-03-19 09:00:15] ============================================================
[2026-03-19 09:00:15] Scheduled Workflow Runner Started
[2026-03-19 09:00:15] ============================================================
[2026-03-19 09:00:15] 🚀 Triggering workflow agent...
[2026-03-19 09:00:16] 📤 🤖 Auto-selected task: docker-setup
[2026-03-19 09:00:16] 📤 🚀 Spawning agent 'developer' for task: docker-setup
[2026-03-19 09:00:16] 📤 Task description preview: # Docker Setup Task for Pet Anime Video...
[2026-03-19 09:00:16] ✅ Workflow agent executed successfully
```

## Monitoring

Check if workflow is running properly:

```bash
# View recent activity
tail -n 50 logs/workflow.log

# Check state
python scripts/workflow-agent.py --status

# Verify cron job
crontab -l | grep workflow

# For systemd
systemctl list-timers | grep pet-workflow
journalctl -u pet-workflow.service --since "1 hour ago"
```

## Troubleshooting

### Issue: Workflow not running daily
- Check cron service: `systemctl status cron`
- Verify cron entry: `crontab -l`
- Check permissions: `ls -la scripts/scheduled-workflow.py`

### Issue: Agent spawns fail
- Verify OpenClaw installation: `which openclaw`
- Check OpenClaw status: `openclaw status`
- Review error logs: `tail -f logs/workflow.log`

### Issue: Task stuck in "in_progress"
- Manually mark complete: `python scripts/workflow-agent.py --complete <task_name>`
- Or reset state: Delete `.workflow-state.json` and recreate

## Future Enhancements

Potential improvements:

1. **Slack/Discord notifications** when tasks complete
2. **Progress tracking dashboard** with web UI
3. **Dynamic priority adjustment** based on project needs
4. **Parallel task execution** for independent items
5. **Automated code review** integration with GitHub PRs
6. **Performance metrics** tracking over time

---

**Last Updated**: 2026-03-19  
**Version**: 1.0

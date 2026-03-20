# Pet Anime Video - OpenClaw Cron Schedule

This document describes the automated optimization workflow using OpenClaw's built-in cron system.

## Overview

Instead of using Linux system cron, we leverage OpenClaw's native scheduling capabilities to run optimization tasks via sub-agents.

## Schedule Configuration

### Task: Daily Optimization Workflow
- **Frequency**: Every 2 hours (as requested)
- **Trigger**: OpenClaw heartbeat/cron mechanism
- **Executor**: Sub-agent spawned via `sessions_spawn`
- **Task Queue**: Managed in `.workflow-state.json`

## Implementation Approach

We'll use two complementary methods:

### Method 1: Heartbeat-Based Scheduling
The heartbeat checks every ~30 minutes and triggers tasks when conditions are met.

### Method 2: Manual Trigger via Slash Command
Users can manually trigger workflow execution with `/optimize-pet-project` command.

## Task Priority Order

1. docker-setup → Docker deployment support
2. unit-tests → Test coverage implementation  
3. docs-improve → Documentation enhancements
4. ui-improve → Frontend UX improvements
5. code-quality → Type hints & code standards

## State Management

Workflow state is tracked in `.workflow-state.json`:
```json
{
  "tasks": {
    "docker-setup": {"status": "pending"},
    "unit-tests": {"status": "pending"}
  },
  "last_check": "2026-03-19T20:00:00",
  "next_run_in_hours": 2
}
```

## Integration Points

### HEARTBEAT.md Update
Add check for pet project optimization every 2 hours

### Agent Selection
- Use `developer` agent for all technical tasks
- Spawn persistent sessions (`mode: session`) for complex work
- Track completion via file system changes or manual confirmation

---

**Created**: 2026-03-20  
**Version**: 1.0

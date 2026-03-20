#!/usr/bin/env python3
"""
Pet Anime Video - Automated Optimizer Agent

This script is designed to be called by sessions_spawn from OpenClaw.
It executes the next pending optimization task automatically.

Called via:
    sessions_spawn(
        agent_id="developer",
        task="Execute pet-anime-video optimization using scripts/pet-optimizer.py",
        mode="session",
        cwd="/home/fengxiaozi/.openclaw/workspace/pet-anime-video"
    )
"""

import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / ".workflow-state.json"
LOGS_DIR = BASE_DIR / "logs"


def load_json(filepath: Path) -> dict:
    """Load JSON file."""
    with open(filepath) as f:
        return json.load(f)


def save_json(filepath: Path, data: dict):
    """Save data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def log(message: str):
    """Log message to both console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    # Also write to log file
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / "pet-optimizer.log"
    with open(log_file, 'a') as f:
        f.write(log_line + "\n")


def get_next_task() -> tuple[str, dict] | None:
    """Get the next pending task to execute."""
    state = load_json(STATE_FILE)
    priority_order = ["docker-setup", "unit-tests", "docs-improve", "ui-improve", "code-quality"]
    
    for task_name in priority_order:
        task_data = state.get("tasks", {}).get(task_name)
        if task_data and task_data.get("status") == "pending":
            return task_name, task_data
    
    return None


def mark_task_in_progress(task_name: str):
    """Mark task as in progress."""
    state = load_json(STATE_FILE)
    state["tasks"][task_name]["status"] = "in_progress"
    state["current_task"] = task_name
    state["last_updated"] = datetime.now().isoformat()
    save_json(STATE_FILE, state)
    log(f"Task '{task_name}' marked as IN_PROGRESS")


def mark_task_complete(task_name: str, summary: str = ""):
    """Mark task as complete."""
    state = load_json(STATE_FILE)
    state["tasks"][task_name]["status"] = "completed"
    state["tasks"][task_name]["completed_at"] = datetime.now().isoformat()
    state["tasks"][task_name]["summary"] = summary
    state["current_task"] = None
    state["last_updated"] = datetime.now().isoformat()
    save_json(STATE_FILE, state)
    log(f"Task '{task_name}' marked as COMPLETED")


def get_task_description(task_name: str) -> str:
    """Load detailed task description from workflow-config.py."""
    try:
        from scripts.workflow_config import TASKS
        task_info = TASKS.get(task_name, {})
        return task_info.get("description", "")
    except Exception as e:
        log(f"Error loading task config: {e}")
        return ""


def main():
    """Main entry point for the optimizer agent."""
    log("=" * 70)
    log("🚀 Pet Anime Video - Automated Optimizer Started")
    log("=" * 70)
    
    # Get next task
    result = get_next_task()
    if not result:
        log("❌ No pending tasks found. All tasks completed or none configured.")
        log("=" * 70)
        return 0
    
    task_name, task_data = result
    log(f"📋 Found next task: {task_name}")
    log(f"   Status: {task_data.get('status', 'unknown')}")
    
    # Mark as in progress
    mark_task_in_progress(task_name)
    
    # Get task description
    task_desc = get_task_description(task_name)
    if not task_desc:
        log(f"⚠️ Warning: No detailed description found for task '{task_name}'")
        log("   Continuing with basic execution...")
    else:
        log(f"📝 Task description loaded ({len(task_desc)} chars)")
        log("-" * 70)
        log("TASK DETAILS:")
        log("-" * 70)
        # Print first few lines of description
        desc_lines = task_desc.strip().split('\n')[:15]
        for line in desc_lines:
            log(f"  {line}")
        if len(task_desc.strip().split('\n')) > 15:
            log("  ... (truncated, full description available in workflow-config.py)")
        log("-" * 70)
    
    log("")
    log("✅ READY FOR EXECUTION")
    log("")
    log("Next steps for the sub-agent:")
    log(f"1. Execute optimization task: {task_name}")
    log(f"2. Follow the requirements and deliverables listed above")
    log(f"3. Test the changes thoroughly")
    log(f"4. Update relevant documentation")
    log(f"5. When complete, call: python scripts/pet-optimizer.py --complete")
    log("")
    log("=" * 70)
    
    return 0


def main_complete():
    """Mark current task as complete."""
    log("=" * 70)
    log("🏁 Marking task as complete...")
    log("=" * 70)
    
    state = load_json(STATE_FILE)
    current_task = state.get("current_task")
    
    if not current_task:
        log("❌ Error: No task is currently in progress!")
        return 1
    
    # Ask for completion summary (or use default)
    summary = input("\nEnter a brief summary of what was accomplished (or press Enter for default): ").strip()
    if not summary:
        summary = f"{current_task} optimization completed successfully"
    
    mark_task_complete(current_task, summary)
    
    log("")
    log("=" * 70)
    log("✅ Task completed successfully!")
    log("=" * 70)
    
    # Check if there are more tasks
    next_task = get_next_task()
    if next_task:
        log(f"\n🔍 Next pending task: {next_task[0]}")
        log("   Will be executed on next heartbeat check (~30 minutes)")
    else:
        log("\n🎉 All tasks completed! No more optimization needed.")
    
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--complete":
        exit_code = main_complete()
    else:
        exit_code = main()
    
    sys.exit(exit_code)

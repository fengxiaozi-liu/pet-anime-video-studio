#!/usr/bin/env python3
"""
Pet Anime Video - Heartbeat Task Checker

This script is designed to be called from HEARTBEAT.md checks.
It determines if a workflow task should be triggered based on:
1. Time since last run (every 2 hours)
2. Pending tasks available
3. Current hour alignment (even hours: 0, 2, 4, ... 22)

Usage from HEARTBEAT.md:
    python scripts/check-heartbeat-task.py
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / ".workflow-state.json"
HEARTBEAT_STATE_FILE = BASE_DIR.parent / "memory" / "pet-workflow-state.json"


def load_json(filepath: Path) -> dict:
    """Load JSON file or return empty dict if not exists."""
    if filepath.exists():
        with open(filepath) as f:
            return json.load(f)
    return {}


def save_json(filepath: Path, data: dict):
    """Save data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def should_run_task() -> tuple[bool, str]:
    """
    Check if we should trigger the next optimization task.
    
    Returns:
        (should_run, reason) tuple
    """
    current_time = datetime.now()
    current_hour = current_time.hour
    
    # Rule 1: Only run on even hours (0, 2, 4, ..., 22)
    if current_hour % 2 != 0:
        return False, f"Current hour {current_hour} is odd, skipping (runs on even hours)"
    
    # Load heartbeat state
    heartbeat_state = load_json(HEARTBEAT_STATE_FILE)
    last_run_str = heartbeat_state.get("last_run")
    
    # Rule 2: At least 2 hours must have passed since last run
    if last_run_str:
        last_run = datetime.fromisoformat(last_run_str)
        hours_since_last_run = (current_time - last_run).total_seconds() / 3600
        
        if hours_since_last_run < 2:
            remaining_hours = 2 - hours_since_last_run
            return False, f"Only {hours_since_last_run:.1f}h since last run (need 2h), wait {remaining_hours:.1f}h more"
    
    # Rule 3: Check for pending tasks
    workflow_state = load_json(STATE_FILE)
    priority_order = ["docker-setup", "unit-tests", "docs-improve", "ui-improve", "code-quality"]
    
    next_task = None
    for task_name in priority_order:
        task_status = workflow_state.get("tasks", {}).get(task_name, {}).get("status")
        if task_status == "pending":
            next_task = task_name
            break
    
    if not next_task:
        return False, "No pending tasks found (all complete or none configured)"
    
    # All conditions met!
    return True, f"Ready to execute task: {next_task}"


def get_next_task_details() -> dict | None:
    """Get details about the next pending task."""
    workflow_state = load_json(STATE_FILE)
    priority_order = ["docker-setup", "unit-tests", "docs-improve", "ui-improve", "code-quality"]
    
    for task_name in priority_order:
        if workflow_state.get("tasks", {}).get(task_name, {}).get("status") == "pending":
            return {
                "task_name": task_name,
                "status": "pending"
            }
    
    return None


def mark_task_in_progress(task_name: str):
    """Mark a task as in progress in the workflow state."""
    workflow_state = load_json(STATE_FILE)
    workflow_state["tasks"][task_name]["status"] = "in_progress"
    workflow_state["current_task"] = task_name
    workflow_state["last_check"] = datetime.now().isoformat()
    save_json(STATE_FILE, workflow_state)


def update_heartbeat_state():
    """Update heartbeat state with current timestamp."""
    heartbeat_state = load_json(HEARTBEAT_STATE_FILE)
    heartbeat_state["last_run"] = datetime.now().isoformat()
    save_json(HEARTBEAT_STATE_FILE, heartbeat_state)


def main():
    """Main entry point for heartbeat check."""
    print("="*60)
    print("Pet Anime Video - Heartbeat Task Check")
    print("="*60)
    
    # Check if we should run a task
    should_run, reason = should_run_task()
    print(f"\n🔍 Check result: {reason}")
    
    if not should_run:
        print("\n⏭️  Skipping this heartbeat cycle.")
        print("="*60)
        return 0  # No action needed
    
    # Get next task details
    task_info = get_next_task_details()
    if not task_info:
        print("\n❌ No task to execute.")
        return 1
    
    print(f"\n✅ Should spawn agent for task: {task_info['task_name']}")
    print(f"   Status: {task_info['status']}")
    
    # Mark task as in progress
    mark_task_in_progress(task_info['task_name'])
    print(f"   → Marked as 'in_progress'")
    
    # Update heartbeat state
    update_heartbeat_state()
    print(f"   → Updated heartbeat timestamp")
    
    print("\n📋 Next steps:")
    print(f"   Spawn sub-agent with sessions_spawn:")
    print(f"   - agent_id: developer")
    print(f"   - mode: session")
    print(f"   - cwd: {BASE_DIR.absolute()}")
    print(f"   - task: Load detailed description from scripts/workflow-config.py")
    
    print("\n" + "="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

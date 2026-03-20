#!/usr/bin/env python3
"""
Pet Anime Video - Scheduled Workflow Runner

This script is designed to be called by a cron job or system timer.
It automatically triggers the next optimization task using the workflow agent.

Recommended cron schedule (run every day at 9:00 AM):
0 9 * * * cd /home/fengxiaozi/.openclaw/workspace/pet-anime-video && \
    python scripts/scheduled-workflow.py --auto >> logs/workflow.log 2>&1

Or use systemd timer for more reliable scheduling.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "workflow.log"


def log(message: str):
    """Log message to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    
    print(log_message)
    
    LOG_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_message + "\n")


def main():
    log("="*60)
    log("Scheduled Workflow Runner Started")
    log("="*60)
    
    # Check if OpenClaw is available
    try:
        result = subprocess.run(
            ["which", "openclaw"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            log("⚠️ Warning: OpenClaw CLI not found in PATH")
            log("Please ensure OpenClaw is installed and accessible")
    except Exception as e:
        log(f"Error checking OpenClaw: {e}")
    
    # Run workflow agent in auto mode
    workflow_script = BASE_DIR / "scripts" / "workflow-agent.py"
    
    if not workflow_script.exists():
        log(f"❌ Error: workflow-agent.py not found at {workflow_script}")
        sys.exit(1)
    
    log("🚀 Triggering workflow agent...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(workflow_script), "--auto"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                log(f"📤 {line}")
        
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                log(f"⚠️ {line}")
        
        if result.returncode == 0:
            log("✅ Workflow agent executed successfully")
        else:
            log(f"❌ Workflow agent failed with exit code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        log("❌ Workflow agent timed out after 5 minutes")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Error executing workflow agent: {e}")
        sys.exit(1)
    
    log("="*60)
    log("Scheduled Workflow Runner Completed")
    log("="*60)


if __name__ == "__main__":
    main()

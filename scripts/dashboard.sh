#!/bin/bash
#
# Pet Anime Video - Workflow Dashboard
# 
# A simple interactive dashboard to view and manage workflow tasks.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORKFLOW_AGENT="$SCRIPT_DIR/workflow-agent.py"
LOG_FILE="$PROJECT_DIR/logs/workflow.log"
STATE_FILE="$PROJECT_DIR/.workflow-state.json"

clear
echo "============================================================"
echo "   🐱 Pet Anime Video - Workflow Dashboard"
echo "============================================================"
echo ""

# Show status
python3 "$WORKFLOW_AGENT" --status

echo "📋 Menu:"
echo "  1. View current task details"
echo "  2. Manually trigger next task"
echo "  3. Mark a task as complete"
echo "  4. View recent logs (tail)"
echo "  5. Watch logs in real-time"
echo "  6. Setup cron job"
echo "  7. Remove cron job"
echo "  8. Reset workflow state"
echo "  0. Exit"
echo ""

read -p "Choose an option [0-8]: " choice

case $choice in
    1)
        # Show next task details
        NEXT_TASK=$(python3 -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)
priority = ['config-management', 'docker-setup', 'unit-tests', 'docs-improve', 'ui-improve', 'code-quality']
for task in priority:
    if state['tasks'].get(task, {}).get('status') == 'pending':
        print(task)
        break
else:
    print('none')
")
        
        if [ "$NEXT_TASK" != "none" ]; then
            echo ""
            echo "📝 Next Task: $NEXT_TASK"
            echo "------------------------------------------------------------"
            grep -A 50 "\"$NEXT_TASK\":" "$WORKFLOW_AGENT" | head -60
        else
            echo ""
            echo "✅ All tasks completed!"
        fi
        ;;
    
    2)
        echo ""
        echo "🚀 Triggering next task..."
        python3 "$WORKFLOW_AGENT" --auto
        ;;
    
    3)
        echo ""
        echo "Available tasks:"
        echo "  - docker-setup"
        echo "  - unit-tests"
        echo "  - docs-improve"
        echo "  - ui-improve"
        echo "  - code-quality"
        read -p "Enter task name to mark complete: " task_name
        if [ -n "$task_name" ]; then
            python3 "$WORKFLOW_AGENT" --complete "$task_name"
        fi
        ;;
    
    4)
        if [ -f "$LOG_FILE" ]; then
            tail -n 50 "$LOG_FILE"
        else
            echo "No logs found yet."
        fi
        ;;
    
    5)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "Starting log watch (logs will appear once workflow runs)..."
            sleep 1
            touch "$LOG_FILE"
            tail -f "$LOG_FILE"
        fi
        ;;
    
    6)
        bash "$SCRIPT_DIR/cron-setup.sh"
        ;;
    
    7)
        # Remove cron job
        if crontab -l 2>/dev/null | grep -q "workflow"; then
            echo "Removing workflow cron job..."
            crontab -l 2>/dev/null | grep -v "workflow" | crontab -
            echo "✅ Cron job removed."
        else
            echo "❌ No workflow cron job found."
        fi
        ;;
    
    8)
        read -p "⚠️  This will reset all task statuses! Continue? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            python3 -c "
import json
state = {
    'tasks': {
        'config-management': {'status': 'pending'},
        'docker-setup': {'status': 'pending'},
        'unit-tests': {'status': 'pending'},
        'docs-improve': {'status': 'pending'},
        'ui-improve': {'status': 'pending'},
        'code-quality': {'status': 'pending'}
    },
    'last_run': None,
    'current_task': None
}
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
print('✅ Workflow state reset.')
"
        fi
        ;;
    
    0)
        echo "Goodbye!"
        exit 0
        ;;
    
    *)
        echo "Invalid option."
        ;;
esac

echo ""
read -p "Press Enter to return to dashboard..."
exec "$0"

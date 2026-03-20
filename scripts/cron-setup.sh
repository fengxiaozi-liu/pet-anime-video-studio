#!/bin/bash
#
# Pet Anime Video - Cron Job Setup Script
# 
# This script sets up automated daily optimization tasks using cron.
# It runs the workflow agent every day at 9:00 AM to execute the next pending task.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CRON_SCRIPT="$SCRIPT_DIR/scheduled-workflow.py"
LOG_FILE="$PROJECT_DIR/logs/workflow.log"

echo "=================================================="
echo "Pet Anime Video - Cron Job Setup"
echo "=================================================="
echo ""

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Define the cron job (runs daily at 9:00 AM)
CRON_JOB="0 9 * * * cd $PROJECT_DIR && $(which python3) $CRON_SCRIPT --auto >> $LOG_FILE 2>&1"

echo "This will install a cron job that:"
echo "  • Runs every day at 9:00 AM"
echo "  • Automatically executes the next highest priority task"
echo "  • Logs output to: $LOG_FILE"
echo ""
echo "Cron entry:"
echo "  $CRON_JOB"
echo ""

read -p "Do you want to install this cron job? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "$CRON_SCRIPT"; then
        echo "⚠️  Cron job already exists!"
        read -p "Do you want to replace it? (y/N) " -n 1 -r
        echo ""
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
        
        # Remove existing cron job
        crontab -l 2>/dev/null | grep -v "$CRON_SCRIPT" | crontab -
    fi
    
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    
    echo ""
    echo "✅ Cron job installed successfully!"
    echo ""
    echo "Current cron jobs:"
    crontab -l
    echo ""
    echo "To view logs: tail -f $LOG_FILE"
    echo "To remove cron job: $0 --remove"
else
    echo "Installation cancelled."
    exit 0
fi

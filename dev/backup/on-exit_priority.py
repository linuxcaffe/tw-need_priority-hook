#!/usr/bin/env python3
"""
on-exit_priority.py - Update context filter on task completion
Part of tw-priority-hook project

NOTE: This hook only triggers on 'task done', NOT on 'task delete'.
Deletions are handled by on-modify_priority.py which detects status=deleted.

Recalculates and updates context filter when tasks are completed.
"""

import sys
import json
import os
import subprocess
from datetime import datetime

# Configuration
HOOK_DIR = os.path.expanduser("~/.task/hooks/priority")
LOG_DIR = os.path.join(HOOK_DIR, "logs")
CONFIG_FILE = os.path.join(HOOK_DIR, "need.rc")
LOG_FILE = os.path.join(LOG_DIR, "on-exit.log")

def log(message):
    """Write to hook log file"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"LOG ERROR: {e}", file=sys.stderr)

def get_config_value(key, default=None):
    """Read configuration value from need.rc"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + '='):
                    return line.split('=', 1)[1]
    except:
        pass
    return default

def get_lowest_priority():
    """Find the lowest priority level with pending tasks"""
    try:
        for level in ['1', '2', '3', '4', '5', '6']:
            result = subprocess.run(
                ['task', 'rc.hooks=off', f'priority:{level}', 'status:pending', 'count'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                count = int(result.stdout.strip() or 0)
                if count > 0:
                    return level
    except Exception as e:
        log(f"Error getting lowest priority: {e}")
    return None

def build_context_filter(min_priority, span, lookahead, lookback):
    """Build context filter expression using pri.after"""
    min_pri = int(min_priority)
    max_pri = min(min_pri + int(span) - 1, 6)
    
    # Use pri.after:N to show priorities below N
    # pri.after:3 shows pri:1 and pri:2
    # So to show min_pri to max_pri, we use pri.after:(max_pri+1)
    if max_pri < 6:
        pri_expr = f"pri.after:{max_pri + 1}"
    else:
        # If max is 6, just show all priorities
        pri_expr = "pri.any:"
    
    # Add due/scheduled with user-specified time formats
    due_expr = f"( due.before:today+{lookahead} and due.after:today-{lookback} )"
    sched_expr = f"( scheduled.before:today+{lookahead} and sched.after:today-{lookback} )"
    
    return f"{pri_expr} or {sched_expr} or {due_expr}"

def update_context_in_config():
    """Update context.need.read in need.rc based on current lowest priority"""
    try:
        lowest = get_lowest_priority()
        if not lowest:
            log("No pending tasks, clearing context filter")
            filter_expr = ""
        else:
            span = get_config_value('priority.span', '2')
            lookahead = get_config_value('priority.lookahead', '2d')
            lookback = get_config_value('priority.lookback', '1w')
            filter_expr = build_context_filter(lowest, span, lookahead, lookback)
            log(f"Lowest priority: {lowest}, filter: {filter_expr}")
        
        # Update need.rc
        lines = []
        found = False
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if line.startswith('context.need.read='):
                    lines.append(f'context.need.read={filter_expr}\n')
                    found = True
                else:
                    lines.append(line)
        
        if not found:
            lines.append(f'\ncontext.need.read={filter_expr}\n')
        
        with open(CONFIG_FILE, 'w') as f:
            f.writelines(lines)
        
        log(f"Updated context.need.read={filter_expr}")
        return True
        
    except Exception as e:
        log(f"Error updating context: {e}")
        return False

def main():
    """Hook entry point"""
    try:
        # Read task input (on-exit receives task input but doesn't output)
        input_data = sys.stdin.read()
        
        log("=== ON-EXIT TRIGGERED ===")
        log(f"Input received: {len(input_data)} bytes")
        
        # Update context filter
        log("Calling update_context_in_config()")
        result = update_context_in_config()
        log(f"Update completed: {result}")
        
        return 0
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        return 1

if __name__ == '__main__':
    sys.exit(main())

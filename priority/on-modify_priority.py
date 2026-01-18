#!/usr/bin/env python3
"""
on-modify_priority.py - Validate and enforce priority requirements
Part of tw-priority-hook project

Ensures priority is always set on task modifications.
Prevents clearing or setting invalid priority values.
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
LOG_FILE = os.path.join(LOG_DIR, "on-modify.log")

VALID_PRIORITIES = ['1', '2', '3', '4', '5', '6']
DEFAULT_PRIORITY = '4'

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

def get_lowest_priority(exclude_uuid=None):
    """
    Find the lowest priority level with pending tasks
    exclude_uuid: UUID of task to exclude (being deleted/completed)
    """
    try:
        for level in ['1', '2', '3', '4', '5', '6']:
            result = subprocess.run(
                ['task', f'priority:{level}', 'status:pending', 'count'],
                capture_output=True,
                text=True
            )
            count = 0
            if result.returncode == 0:
                count = int(result.stdout.strip() or 0)
            
            # If we're excluding a task at this level, decrement count
            if exclude_uuid and count > 0:
                # Check if the excluded task is at this level
                check_result = subprocess.run(
                    ['task', f'uuid:{exclude_uuid}', f'priority:{level}', 'count'],
                    capture_output=True,
                    text=True
                )
                if check_result.returncode == 0:
                    exclude_count = int(check_result.stdout.strip() or 0)
                    count -= exclude_count
            
            if count > 0:
                return level
    except Exception as e:
        log(f"Error getting lowest priority: {e}")
    return None

def build_context_filter(min_priority, span, lookahead, lookback):
    """Build context filter expression"""
    min_pri = int(min_priority)
    max_pri = min(min_pri + int(span) - 1, 6)
    
    # Build priority filter
    pri_filters = [f"priority:{p}" for p in range(min_pri, max_pri + 1)]
    pri_expr = " or ".join(pri_filters)
    
    # Add due/scheduled with user-specified time formats
    # User can specify: 2d, 1w, 3m, etc.
    due_expr = f"( due.before:today+{lookahead} and due.after:today-{lookback} )"
    sched_expr = f"( scheduled.before:today+{lookahead} and sched.after:today-{lookback} )"
    
    return f"{pri_expr} or {due_expr} or {sched_expr}"

def update_context_in_config(exclude_uuid=None):
    """
    Update context.needs.read in need.rc based on current lowest priority
    exclude_uuid: UUID of task to exclude (being deleted/completed)
    """
    try:
        lowest = get_lowest_priority(exclude_uuid)
        if not lowest:
            log("No pending tasks, clearing context filter")
            filter_expr = ""
        else:
            span = get_config_value('priority.span', '2')
            lookahead = get_config_value('priority.lookahead', '2d')
            lookback = get_config_value('priority.lookback', '1w')
            filter_expr = build_context_filter(lowest, span, lookahead, lookback)
            log(f"Lowest priority (excluding {exclude_uuid}): {lowest}, filter: {filter_expr}")
        
        # Update need.rc
        lines = []
        found = False
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if line.startswith('context.needs.read='):
                    lines.append(f'context.needs.read={filter_expr}\n')
                    found = True
                else:
                    lines.append(line)
        
        if not found:
            lines.append(f'\ncontext.needs.read={filter_expr}\n')
        
        with open(CONFIG_FILE, 'w') as f:
            f.writelines(lines)
        
        log(f"Updated context.needs.read={filter_expr}")
        return True
        
    except Exception as e:
        log(f"Error updating context: {e}")
        return False

def main():
    """Hook entry point"""
    try:
        # Read original and modified task
        original_json = sys.stdin.readline()
        modified_json = sys.stdin.readline()
        
        original = json.loads(original_json)
        modified = json.loads(modified_json)
        
        desc = modified.get('description', 'NO DESC')[:50]
        
        # Check if task is being deleted
        is_deletion = modified.get('status') == 'deleted'
        is_completion = modified.get('status') == 'completed'
        
        log(f"=== ON-MODIFY: {desc} ===")
        log(f"Original status: {original.get('status')}, Modified status: {modified.get('status')}")
        log(f"Is deletion: {is_deletion}, Is completion: {is_completion}")
        
        # Check if priority was removed
        if 'priority' not in modified or not modified['priority']:
            if not is_deletion:  # Don't enforce priority on deletions
                log(f"Priority missing on modify, restoring to default: {desc}")
                modified['priority'] = DEFAULT_PRIORITY
        
        # Validate priority value
        elif modified['priority'] not in VALID_PRIORITIES:
            old_pri = modified['priority']
            log(f"Invalid priority '{old_pri}', setting to default: {desc}")
            modified['priority'] = DEFAULT_PRIORITY
        
        # Output modified task
        print(json.dumps(modified))
        
        # Update context filter in background
        # For deletions/completions, exclude this task from the count
        if is_deletion or is_completion:
            log(f"Task {'deleted' if is_deletion else 'completed'}, updating context (excluding UUID)")
            update_context_in_config(modified.get('uuid'))
        else:
            log(f"Regular modification, updating context")
            update_context_in_config()
        
        return 0
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        # On error, output modified task unchanged
        print(modified_json)
        return 1

if __name__ == '__main__':
    sys.exit(main())

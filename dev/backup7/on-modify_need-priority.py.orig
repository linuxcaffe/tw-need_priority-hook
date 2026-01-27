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

def get_lowest_priority_with_change(exclude_uuid=None, new_priority=None):
    """
    Find the lowest priority level with pending tasks
    Takes into account a task that's changing priority (not yet in DB)
    
    exclude_uuid: UUID of task being modified (still at old priority in DB)
    new_priority: The new priority level this task will have
    """
    try:
        log(f"get_lowest_priority_with_change: exclude_uuid={exclude_uuid}, new_priority={new_priority}")
        
        for level in ['1', '2', '3', '4', '5', '6']:
            result = subprocess.run(
                ['task', 'rc.hooks=off', f'priority:{level}', 'status:pending', 'count'],
                capture_output=True,
                text=True
            )
            count = 0
            if result.returncode == 0:
                count = int(result.stdout.strip() or 0)
            
            log(f"  Priority {level}: {count} tasks (DB)")
            
            # If we're excluding a task at this level, decrement count
            if exclude_uuid and count > 0:
                check_result = subprocess.run(
                    ['task', 'rc.hooks=off', f'uuid:{exclude_uuid}', f'priority:{level}', 'count'],
                    capture_output=True,
                    text=True
                )
                if check_result.returncode == 0:
                    exclude_count = int(check_result.stdout.strip() or 0)
                    if exclude_count > 0:
                        log(f"    Excluding {exclude_count} task(s) at level {level} (old priority)")
                        count -= exclude_count
            
            # If this is the new priority level, add 1 for the task being moved here
            if new_priority and level == new_priority:
                log(f"    Adding 1 task at level {level} (new priority)")
                count += 1
            
            log(f"  Priority {level}: {count} tasks (adjusted)")
            
            if count > 0:
                log(f"  Returning lowest priority: {level}")
                return level
        
        log("  No tasks found, returning None")
    except Exception as e:
        log(f"Error getting lowest priority: {e}")
    return None

def get_lowest_priority(exclude_uuid=None):
    """
    Find the lowest priority level with pending tasks
    exclude_uuid: UUID of task to exclude (being deleted/completed)
    """
    try:
        log(f"get_lowest_priority called, exclude_uuid={exclude_uuid}")
        for level in ['1', '2', '3', '4', '5', '6']:
            result = subprocess.run(
                ['task', 'rc.hooks=off', f'priority:{level}', 'status:pending', 'count'],
                capture_output=True,
                text=True
            )
            count = 0
            if result.returncode == 0:
                count = int(result.stdout.strip() or 0)
            
            log(f"  Priority {level}: {count} tasks")
            
            # If we're excluding a task at this level, decrement count
            if exclude_uuid and count > 0:
                # Check if the excluded task is at this level
                check_result = subprocess.run(
                    ['task', 'rc.hooks=off', f'uuid:{exclude_uuid}', f'priority:{level}', 'count'],
                    capture_output=True,
                    text=True
                )
                if check_result.returncode == 0:
                    exclude_count = int(check_result.stdout.strip() or 0)
                    if exclude_count > 0:
                        log(f"    Excluding {exclude_count} task(s) at level {level}")
                    count -= exclude_count
            
            if count > 0:
                log(f"  Returning lowest priority: {level}")
                return level
        
        log("  No tasks found, returning None")
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
    
    return f"{pri_expr} or {due_expr} or {sched_expr}"

def update_context_in_config(exclude_uuid=None, new_priority=None):
    """
    Update context.needs.read in need.rc based on current lowest priority
    exclude_uuid: UUID of task to exclude (being deleted/completed/moved)
    new_priority: New priority level for the excluded task (if being moved)
    """
    try:
        # If we have both exclude and new_priority, use the specialized function
        if exclude_uuid and new_priority:
            lowest = get_lowest_priority_with_change(exclude_uuid, new_priority)
        else:
            lowest = get_lowest_priority(exclude_uuid)
        
        if not lowest:
            log("No pending tasks, clearing context filter")
            filter_expr = ""
        else:
            span = get_config_value('priority.span', '2')
            lookahead = get_config_value('priority.lookahead', '2d')
            lookback = get_config_value('priority.lookback', '1w')
            filter_expr = build_context_filter(lowest, span, lookahead, lookback)
            log(f"Lowest priority (excluding {exclude_uuid}, new={new_priority}): {lowest}, filter: {filter_expr}")
        
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
        # Read original and modified task
        original_json = sys.stdin.readline()
        modified_json = sys.stdin.readline()
        
        original = json.loads(original_json)
        modified = json.loads(modified_json)
        
        desc = modified.get('description', 'NO DESC')[:50]
        
        # Check if task is being deleted or completed
        is_deletion = modified.get('status') == 'deleted'
        is_completion = modified.get('status') == 'completed'
        
        # Check if priority changed
        old_priority = original.get('priority', '')
        new_priority = modified.get('priority', '')
        priority_changed = old_priority != new_priority
        
        log(f"=== ON-MODIFY: {desc} ===")
        log(f"Original status: {original.get('status')}, Modified status: {modified.get('status')}")
        log(f"Original priority: '{old_priority}', Modified priority: '{new_priority}'")
        log(f"Priority changed: {priority_changed}")
        log(f"Old in VALID: {old_priority in VALID_PRIORITIES}, New in VALID: {new_priority in VALID_PRIORITIES}")
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
        # CRITICAL: At this point, the database still has the OLD priority!
        # The change hasn't been committed yet. We need to account for this.
        
        if is_deletion or is_completion:
            log(f"Task {'deleted' if is_deletion else 'completed'}, updating context (excluding UUID)")
            # Task is leaving - exclude it from counts
            update_context_in_config(modified.get('uuid'), None)
        elif priority_changed and old_priority in VALID_PRIORITIES and new_priority in VALID_PRIORITIES:
            # Priority changed - database still shows old priority
            # We simulate: remove from old_priority, add to new_priority
            log(f"Priority changed from {old_priority} to {new_priority}")
            log(f"Database still shows task at pri:{old_priority}")
            log(f"Simulating move: exclude from {old_priority}, add to {new_priority}")
            # Pass both UUID (to exclude from old level) and new priority (to add to new level)
            update_context_in_config(modified.get('uuid'), new_priority)
        else:
            log(f"Regular modification (no priority change), updating context")
            update_context_in_config(None, None)
        
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

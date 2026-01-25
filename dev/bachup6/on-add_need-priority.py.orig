#!/usr/bin/env python3
"""
on-add_priority.py - Automatic priority assignment hook
Part of tw-priority-hook project

Automatically assigns priority based on tags, projects, and description
patterns defined in need.rc auto-assignment rules.
"""

import sys
import json
import os
import re
import subprocess
from datetime import datetime

# Configuration
TASK_DIR = os.path.expanduser("~/.task")
LOG_DIR = os.path.join(TASK_DIR, "logs", "need-priority")
CONFIG_FILE = os.path.join(TASK_DIR, "config", "need.rc")
LOG_FILE = os.path.join(LOG_DIR, "on-add.log")

def log(message):
    """Write to hook log file"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"LOG ERROR: {e}", file=sys.stderr)

def parse_auto_rules(config_file):
    """
    Parse priority.N.auto rules from need.rc
    Returns dict: {priority_level: [filter1, filter2, ...]}
    """
    rules = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Match: priority.N.auto=filter,filter,filter
                match = re.match(r'^priority\.([1-6])\.auto=(.+)$', line)
                if match:
                    level = match.group(1)
                    filters = [f.strip() for f in match.group(2).split(',')]
                    rules[level] = filters
    except Exception as e:
        log(f"ERROR parsing config: {e}")
        return {}
    
    return rules

def task_matches_filter(task, filter_expr):
    """
    Check if task matches a filter expression
    Supports: +tag, proj:name, proj.has:name, desc.has:text
    """
    # Tag match: +tag
    if filter_expr.startswith('+'):
        tag = filter_expr[1:]
        return tag in task.get('tags', [])
    
    # Project exact match: proj:name
    if filter_expr.startswith('proj:'):
        proj = filter_expr[5:]
        return task.get('project', '') == proj
    
    # Project contains: proj.has:name
    if filter_expr.startswith('proj.has:'):
        proj = filter_expr[9:]
        return proj in task.get('project', '')
    
    # Description contains: desc.has:text
    if filter_expr.startswith('desc.has:'):
        text = filter_expr[9:]
        return text.lower() in task.get('description', '').lower()
    
    return False

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

def get_lowest_priority(new_task_priority=None):
    """
    Find the lowest priority level with pending tasks
    new_task_priority: Consider a task being added (not yet in database)
    """
    try:
        # Check each priority level
        for level in ['1', '2', '3', '4', '5', '6']:
            # Count existing tasks at this level
            result = subprocess.run(
                ['task', 'rc.hooks=off', f'priority:{level}', 'status:pending', 'count'],
                capture_output=True,
                text=True
            )
            count = 0
            if result.returncode == 0:
                count = int(result.stdout.strip() or 0)
            
            # Consider new task being added
            if new_task_priority == level:
                count += 1
            
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
    
    return f"{pri_expr} or {due_expr} or {sched_expr}"

def update_context_in_config(new_task_priority=None):
    """
    Update context.needs.read in need.rc based on current lowest priority
    new_task_priority: Consider a task being added (not yet in database)
    """
    try:
        lowest = get_lowest_priority(new_task_priority)
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

def determine_priority(task, rules):
    """
    Determine priority based on auto-assignment rules
    Returns priority level (1-6) or None if no match
    """
    # Check each priority level in order (1-6)
    for level in ['1', '2', '3', '4', '5', '6']:
        if level not in rules:
            continue
        
        filters = rules[level]
        for filter_expr in filters:
            if task_matches_filter(task, filter_expr):
                log(f"Matched '{filter_expr}' -> pri:{level}")
                return level
    
    return None

def main():
    """Hook entry point"""
    try:
        # Read new task from stdin
        task_json = sys.stdin.readline()
        task = json.loads(task_json)
        
        log(f"Processing task: {task.get('description', 'NO DESC')}")
        
        # Check if priority already set by user
        if 'priority' in task and task['priority']:
            log(f"Priority already set to {task['priority']}")
            print(json.dumps(task))
            update_context_in_config(task['priority'])
            return 0
        
        # Parse auto-assignment rules
        rules = parse_auto_rules(CONFIG_FILE)
        assigned_priority = None
        
        if rules:
            # Try auto-assignment based on rules
            assigned_priority = determine_priority(task, rules)
            
        if assigned_priority:
            # Auto-assignment succeeded - silent
            task['priority'] = assigned_priority
            log(f"Auto-assigned priority: {assigned_priority}")
        else:
            # No auto-match - use default (user can change later)
            task['priority'] = '4'
            log("No rule matched, using default pri:4")
        
        log(f"Final priority: {task['priority']}")
        
        # Output modified task
        print(json.dumps(task))
        
        # Update context filter, considering this new task
        update_context_in_config(task['priority'])
        
        return 0
        
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        # On error, output original task unchanged
        print(task_json)
        return 1

if __name__ == '__main__':
    sys.exit(main())

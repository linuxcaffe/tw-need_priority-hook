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
from datetime import datetime

# Configuration
HOOK_DIR = os.path.expanduser("~/.task/hooks/priority")
LOG_DIR = os.path.join(HOOK_DIR, "logs")
CONFIG_FILE = os.path.join(HOOK_DIR, "need.rc")
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
        
        # Skip if priority already set
        if 'priority' in task and task['priority']:
            log(f"Priority already set to {task['priority']}, skipping")
            print(task_json)
            return 0
        
        # Parse auto-assignment rules
        rules = parse_auto_rules(CONFIG_FILE)
        if not rules:
            log("No auto-assignment rules found, using default")
            task['priority'] = '4'  # Default from need.rc
        else:
            # Determine priority
            priority = determine_priority(task, rules)
            if priority:
                task['priority'] = priority
            else:
                log("No rule matched, using default pri:4")
                task['priority'] = '4'
        
        log(f"Assigned priority: {task['priority']}")
        
        # Output modified task
        print(json.dumps(task))
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

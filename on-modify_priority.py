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
from datetime import datetime

# Configuration
HOOK_DIR = os.path.expanduser("~/.task/hooks/priority")
LOG_DIR = os.path.join(HOOK_DIR, "logs")
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

def main():
    """Hook entry point"""
    try:
        # Read original and modified task
        original_json = sys.stdin.readline()
        modified_json = sys.stdin.readline()
        
        original = json.loads(original_json)
        modified = json.loads(modified_json)
        
        desc = modified.get('description', 'NO DESC')[:50]
        
        # Check if priority was removed
        if 'priority' not in modified or not modified['priority']:
            log(f"Priority missing on modify, restoring to default: {desc}")
            modified['priority'] = DEFAULT_PRIORITY
        
        # Validate priority value
        elif modified['priority'] not in VALID_PRIORITIES:
            old_pri = modified['priority']
            log(f"Invalid priority '{old_pri}', setting to default: {desc}")
            modified['priority'] = DEFAULT_PRIORITY
        
        # Output modified task
        print(json.dumps(modified))
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

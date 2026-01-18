#!/usr/bin/env python3
"""
need.py - Priority hierarchy report for Taskwarrior
Part of tw-priority-hook project

The hooks automatically maintain context.needs.read in need.rc.
This script shows the current state and adjusts configuration.

Usage:
    need              - Show priority report
    need span <N>     - Set priority span (how many levels to show)
    need update       - Manually recalculate and update context filter
"""

import sys
import os
import subprocess

# Configuration
HOOK_DIR = os.path.expanduser("~/.task/hooks/priority")
CONFIG_FILE = os.path.join(HOOK_DIR, "need.rc")

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

def set_config_value(key, value):
    """Set configuration value in need.rc"""
    lines = []
    found = False
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            lines = f.readlines()
        
        with open(CONFIG_FILE, 'w') as f:
            for line in lines:
                if line.strip().startswith(key + '='):
                    f.write(f"{key}={value}\n")
                    found = True
                else:
                    f.write(line)
            
            if not found:
                f.write(f"\n{key}={value}\n")
        
        return True
    except Exception as e:
        print(f"Error updating config: {e}", file=sys.stderr)
        return False

def get_task_counts():
    """Get count of tasks at each priority level (ignores active context)"""
    counts = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}
    
    try:
        for level in ['1', '2', '3', '4', '5', '6']:
            # Use rc.context=none to ignore active context
            result = subprocess.run(
                ['task', 'rc.context=none', f'priority:{level}', 'status:pending', 'count'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                counts[level] = int(result.stdout.strip() or 0)
    except Exception as e:
        print(f"Error getting task counts: {e}", file=sys.stderr)
    
    return counts

def get_lowest_priority():
    """Find the lowest priority level with pending tasks"""
    counts = get_task_counts()
    for level in ['1', '2', '3', '4', '5', '6']:
        if counts[level] > 0:
            return level
    return None

def build_context_filter(min_priority, span, lookahead, lookback):
    """Build context filter expression"""
    min_pri = int(min_priority)
    max_pri = min(min_pri + int(span) - 1, 6)
    
    # Build priority filter
    pri_filters = [f"priority:{p}" for p in range(min_pri, max_pri + 1)]
    pri_expr = " or ".join(pri_filters)
    
    # Add due/scheduled with user-specified time formats
    due_expr = f"( due.before:today+{lookahead} and due.after:today-{lookback} )"
    sched_expr = f"( scheduled.before:today+{lookahead} and sched.after:today-{lookback} )"
    
    return f"{pri_expr} or {due_expr} or {sched_expr}"

def update_context():
    """Manually recalculate and update context filter"""
    try:
        lowest = get_lowest_priority()
        if not lowest:
            print("No pending tasks, clearing context filter")
            filter_expr = ""
        else:
            span = get_config_value('priority.span', '2')
            lookahead = get_config_value('priority.lookahead', '2d')
            lookback = get_config_value('priority.lookback', '1w')
            filter_expr = build_context_filter(lowest, span, lookahead, lookback)
            print(f"Lowest priority: {lowest}")
            print(f"Filter: {filter_expr}")
        
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
        
        print("Context updated successfully")
        return True
        
    except Exception as e:
        print(f"Error updating context: {e}", file=sys.stderr)
        return False

def get_active_context():
    """Check if 'needs' context is currently active"""
    try:
        result = subprocess.run(
            ['task', '_get', 'rc.context'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip() == 'needs'
    except:
        pass
    return False

def show_report():
    """Display priority pyramid report"""
    counts = get_task_counts()
    context_filter = get_config_value('context.needs.read', '')
    is_active = get_active_context()
    span = get_config_value('priority.span', '2')
    lookahead = get_config_value('priority.lookahead', '2d')
    lookback = get_config_value('priority.lookback', '1w')
    
    print()
    print("Priority Hierarchy Status")
    print("=" * 80)
    print()
    
    # Determine which level is lowest (has tasks)
    lowest_level = None
    for level in ['1', '2', '3', '4', '5', '6']:
        if counts[level] > 0:
            lowest_level = level
            break
    
    # Draw pyramid - simpler, fixed-width layout
    pyramid = [
        ('6', 'Higher Goals'),
        ('5', 'Self Actualization'),
        ('4', 'Esteem, Respect & Recognition'),
        ('3', 'Love & Belonging, Friends & Family'),
        ('2', 'Personal safety, security, health, financial'),
        ('1', 'Physiological; Air, Water, Food & Shelter')
    ]
    
    for level, label in pyramid:
        marker = ' -->' if level == lowest_level else '    '
        count = counts[level]
        # Fixed format: marker + level + label (left) + count (right)
        print(f"{marker}{level}  {label:<55} ({count})")
    
    print()
    print(f"Config: span={span}, lookahead={lookahead}, lookback={lookback}")
    print()
    
    # Show current context status
    if context_filter:
        print(f"Context filter (auto-updated by hooks):")
        print(f"  {context_filter}")
        print()
        if is_active:
            print("Status: Context 'needs' is ACTIVE")
            print("  Deactivate: task context none")
        else:
            print("Status: Context 'needs' is defined but NOT active")
            print("  Activate: task context needs")
    else:
        print("No pending tasks - context filter is empty")
        print("Add tasks to automatically update the filter")
    
    print()

def cmd_span(new_span):
    """Set priority span value"""
    try:
        span = int(new_span)
        if span < 1 or span > 6:
            raise ValueError
        
        if set_config_value('priority.span', str(span)):
            print(f"Priority span set to {span}")
            print("Context filter will update automatically on next task change")
            return 0
        else:
            return 1
    except ValueError:
        print(f"Invalid span value: {new_span}", file=sys.stderr)
        return 1

def main():
    """Main entry point"""
    args = sys.argv[1:]
    
    if not args:
        show_report()
        return 0
    
    cmd = args[0].lower()
    
    if cmd == 'span':
        if len(args) < 2:
            print("Usage: need span <N>", file=sys.stderr)
            return 1
        return cmd_span(args[1])
    elif cmd == 'update':
        return 0 if update_context() else 1
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        return 1

if __name__ == '__main__':
    sys.exit(main())

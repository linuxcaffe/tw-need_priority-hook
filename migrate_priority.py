#!/usr/bin/env python3
"""
migrate_priority.py - Convert H/M/L priorities to numeric 1-6 scale

Handles migration from taskwarrior's built-in priority (H/M/L) to 
the new numeric priority UDA (1-6).

Default mapping:
  H (High) -> pri:2 (Safety/Security - high urgency)
  M (Medium) -> pri:4 (Esteem - default level)
  L (Low) -> pri:5 (Self-actualization - nice to have)
  (none) -> pri:4 (default)

Usage:
    python3 migrate_priority.py [--dry-run] [--mapping H:N,M:N,L:N]
    
Options:
    --dry-run     Show what would change without modifying tasks
    --mapping     Custom mapping (e.g., --mapping H:1,M:3,L:5)
"""

import sys
import subprocess
import json
import argparse

DEFAULT_MAPPING = {
    'H': '2',  # High urgency -> Safety/Security
    'M': '4',  # Medium -> Esteem (default)
    'L': '5',  # Low -> Self-actualization
}

def get_pending_tasks():
    """Get all pending tasks"""
    try:
        result = subprocess.run(
            ['task', 'status:pending', 'export'],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting tasks: {e}", file=sys.stderr)
        return []

def parse_mapping(mapping_str):
    """Parse mapping string like 'H:1,M:3,L:5'"""
    mapping = {}
    for pair in mapping_str.split(','):
        old, new = pair.split(':')
        mapping[old.strip().upper()] = new.strip()
    return mapping

def migrate_task(task, mapping, dry_run=False):
    """Migrate a single task's priority"""
    uuid = task['uuid']
    old_pri = task.get('priority', None)
    
    # Already has numeric priority - skip
    if 'priority' in task and task['priority'] in ['1','2','3','4','5','6']:
        return None
    
    # Determine new priority
    if old_pri in mapping:
        new_pri = mapping[old_pri]
    else:
        # No old priority or unmapped value -> use default
        new_pri = '4'
    
    if dry_run:
        print(f"Would migrate: {uuid[:8]} | {old_pri or '(none)'} -> pri:{new_pri} | {task['description'][:50]}")
        return None
    else:
        try:
            # Modify task
            subprocess.run(
                ['task', uuid, 'modify', f'priority:{new_pri}'],
                capture_output=True,
                check=True
            )
            print(f"Migrated: {uuid[:8]} | {old_pri or '(none)'} -> pri:{new_pri}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error migrating {uuid[:8]}: {e}", file=sys.stderr)
            return False

def main():
    parser = argparse.ArgumentParser(description='Migrate H/M/L priorities to numeric scale')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show changes without modifying tasks')
    parser.add_argument('--mapping', type=str,
                       help='Custom mapping (e.g., H:1,M:3,L:5)')
    
    args = parser.parse_args()
    
    # Determine mapping
    if args.mapping:
        mapping = parse_mapping(args.mapping)
    else:
        mapping = DEFAULT_MAPPING
    
    print("Priority Migration")
    print("=" * 60)
    print(f"Mapping: {mapping}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    print()
    
    # Get all tasks
    tasks = get_pending_tasks()
    if not tasks:
        print("No pending tasks found")
        return 0
    
    # Migrate each task
    migrated = 0
    skipped = 0
    errors = 0
    
    for task in tasks:
        result = migrate_task(task, mapping, args.dry_run)
        if result is True:
            migrated += 1
        elif result is False:
            errors += 1
        else:
            skipped += 1
    
    print()
    print("=" * 60)
    print(f"Total tasks: {len(tasks)}")
    if args.dry_run:
        print(f"Would migrate: {migrated + len([t for t in tasks if t.get('priority') in mapping or 'priority' not in t])}")
    else:
        print(f"Migrated: {migrated}")
        print(f"Errors: {errors}")
        print(f"Skipped (already numeric): {skipped}")
    
    if args.dry_run:
        print()
        print("Run without --dry-run to perform migration")
    
    return 0 if errors == 0 else 1

if __name__ == '__main__':
    sys.exit(main())

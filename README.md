# tw-priority-hook

Priority-based task filtering for Taskwarrior based on Maslow's hierarchy of needs.

## Overview

Automatically assigns and filters tasks based on a 6-level priority hierarchy:

1. **Physiological** - Air, water, food, shelter, medical
2. **Safety** - Security, health, financial stability  
3. **Love & Belonging** - Friends, family, relationships
4. **Esteem** - Respect, recognition, achievements
5. **Self-Actualization** - Personal growth, creativity
6. **Higher Goals** - Life purpose, legacy

## Features

- **Auto-assignment**: Tasks automatically get priority based on tags/projects
  - If task matches an auto-rule → priority assigned silently
  - If task has `priority:N` already → kept as-is
  - If no match and no priority → defaults to pri:4 (user can change)
- **Priority effectively required**: Every task gets a priority (no blank values)
- **Dynamic context**: Shows only most important tasks (configurable span)
- **Smart lookahead**: Always shows upcoming due/scheduled tasks
- **Smart lookback**: Excludes ancient overdue tasks from context
- **Visual report**: Pyramid display of task distribution
- **Urgency integration**: Higher priorities boost urgency scores

## Installation

### First-Time Setup

1. **Migrate existing priorities (if needed):**
   ```bash
   # Preview migration from H/M/L to numeric
   python3 ~/.task/hooks/priority/migrate_priority.py --dry-run
   
   # Perform migration (default: H->2, M->4, L->5)
   python3 ~/.task/hooks/priority/migrate_priority.py
   
   # Custom mapping if desired
   python3 ~/.task/hooks/priority/migrate_priority.py --mapping H:1,M:3,L:6
   ```

2. **Copy files:**
   ```bash
   # Project is in ~/.task/hooks/priority/
   ```

3. **Create symlinks:**
   ```bash
   ln -s ~/.task/hooks/priority/on-add_priority.py ~/.task/hooks/
   ln -s ~/.task/hooks/priority/on-modify_priority.py ~/.task/hooks/
   ln -s ~/.task/hooks/priority/on-exit_priority.py ~/.task/hooks/
   ln -s ~/.task/hooks/priority/nn.py ~/.task/scripts/nn
   ```

4. **Include configuration:**
   Add to `~/.taskrc`:
   ```
   include ~/.task/hooks/priority/need.rc
   ```
   
   This provides:
   - UDA definition for priority
   - Auto-assignment rules
   - Urgency coefficients
   - Context definition (auto-maintained by hooks)
   - Command alias: `task nn` (Needs Navigator)

5. **Add scripts to PATH** (optional alternative to alias):
   ```bash
   export PATH="$PATH:$HOME/.task/scripts"
   ```

## Configuration

Edit `need.rc` to customize auto-assignment rules:

```
# Automatically assign pri:1 to tasks with these attributes
priority.1.auto=+meds,+oxygen,desc.has:hospital,proj:medical

# Adjust context span (how many levels to show above minimum)
priority.span=2

# Due/scheduled lookahead (show upcoming tasks)
# Format: <number><unit> where unit = d(ays), w(eeks), m(onths), y(ears)
priority.lookahead=2d

# Due/scheduled lookback (exclude old overdue tasks)
# Format: <number><unit> where unit = d(ays), w(eeks), m(onths), y(ears)
priority.lookback=1w
```

Examples of time formats:
- `2d` = 2 days
- `1w` = 1 week
- `3m` = 3 months
- `1y` = 1 year

### Auto-Assignment Rules

Rules are checked in priority order (1-6). First match wins.

Supported filters:
- `+tag` - Has tag
- `proj:name` - Exact project match
- `proj.has:name` - Project contains text
- `desc.has:text` - Description contains text

## Usage

### Context Activation

The `needs` script defines the context filter, but you control activation:

```bash
# Define auto-context (happens automatically via hooks)
# Just check status:
task needs

# Activate the context
task context needs

# Work with filtered tasks
task list

# Deactivate when you want to see everything
task context none
```

### Companion Script Commands

The `need.rc` file includes an alias for `nn` (Needs Navigator):

```bash
# Show priority report
task nn

# Review and assign priorities to tasks
task nn review

# Adjust span (context auto-updates on next task change)
task nn span 3

# Manually force context recalculation (if hooks missed an update)
task nn update
```

Note: The alias passes arguments, so all commands work correctly.

The hooks handle all context management automatically. Just use `task context needs` / `task context none` to control activation.

## How Auto-Context Works

The hooks automatically maintain `context.needs.read` in need.rc:

**Automatic updates:**
- When you add a task → on-add recalculates and updates filter
- When you modify a task → on-modify recalculates and updates filter  
- When you delete a task → on-modify detects deletion and updates filter
- When you complete a task (`task done`) → on-exit updates filter

**The filter is always current** - just activate when you want it:

```bash
task context needs   # Use the auto-maintained filter
task context none    # See everything
```

With `priority.span=2`, `priority.lookahead=2d`, and `priority.lookback=1w`:

1. **You have pri:1 tasks:**
   ```
   context.needs.read=priority:1 or priority:2 or ( due.before:today+2d and due.after:today-1w ) or ( scheduled.before:today+2d and sched.after:today-1w )
   ```
   Shows: pri:1-2 tasks, plus tasks due/scheduled in the next 2 days (but not older than 1 week overdue)

2. **All pri:1 tasks completed:**
   - on-exit hook automatically updates to show pri:2-3 range

3. **Check current state:**
   ```bash
   task nn  # Shows pyramid + current filter
   ```

### Example Workflow

```bash
# Add task with medical tag - auto-assigned pri:1
task add Get prescription refilled +meds
# Hook automatically updates context.needs.read

# Add task with bill tag - auto-assigned pri:2  
task add Pay electricity bill +bills

# Check current status
task nn

# Review and assign priorities to tasks that need them
task nn review

# Activate the context
task context needs

# View filtered list (only lowest priority levels + upcoming)
task list

# Complete high-priority task
task 1 done
# Hook automatically recalculates and updates filter

# Still in context - now showing next priority level
task list

# Check what changed
task nn

# Temporarily see everything
task context none
task list

# Back to filtered view
task context needs
```

## Priority Report

```
Priority Hierarchy Status
======================================================================

    6              Higher Goals                          (2)
    5            Self Actualization                      (3)
    4       Esteem, Respect & Recognition               (15)
    3      Love & Belonging, Friends & Family           (24)
 -->2   Personal safety, security, health, financial    (8)
    1     Physiological; Air, Water, Food & Shelter     (2)

Active context: need
Filter: ( pri:1 or pri:2 or due.before:today+2d or scheduled.before:today+2d )
```

## Manual Priority Assignment

You can always manually set or override priority:

```bash
task add "Critical project deadline" pri:1
task 42 mod pri:3
```

## Integration with Urgency

Priority levels boost urgency scores (configured in `need.rc`):
- pri:1 = +10.0 urgency
- pri:2 = +8.0 urgency
- pri:3 = +6.0 urgency
- pri:4 = +4.0 urgency
- pri:5 = +2.0 urgency
- pri:6 = +0.0 urgency

## Files

```
~/.task/hooks/priority/
├── need.rc                # Configuration (includes context.needs.read)
├── need.py                # Status report script (aliased as 'task needs')
├── on-add_priority.py     # Auto-assignment + context update
├── on-modify_priority.py  # Validation + context update
├── on-exit_priority.py    # Context update on completion/deletion
├── migrate_priority.py    # Migration tool for H/M/L
├── logs/                  # Hook execution logs
│   ├── on-add.log
│   ├── on-modify.log
│   └── on-exit.log
├── CHANGES.txt            # Version history
├── README.md              # This file
└── VERSION                # Current version
```

## Philosophy

Based on the original [tw-needs-hook](https://github.com/linuxcaffe/tw-needs-hook) by linuxcaffe.

The priority hierarchy helps prevent distraction by higher-level tasks when lower-level needs aren't met. You can track everything, but only focus on what matters most right now.

**Key insight:** You won't achieve self-actualization if you're behind on bills. The system enforces this reality while still letting you plan for bigger goals.

## Compatibility

- Requires Taskwarrior 2.6.2
- Python 3.6+
- For Taskwarrior 3.x support, submit a pull request

## Version

Current version: 0.1.0

See `CHANGES.txt` for version history.

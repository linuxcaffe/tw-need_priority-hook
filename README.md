- Project: https://github.com/linuxcaffe/tw-need_priority-hook
- Issues: https://github.com/linuxcaffe/tw-need_priority-hook/issues

# need-priority

Priority-based task filtering for Taskwarrior, inspired by Maslow's hierarchy of needs.

---

## TL;DR

- Every task gets a 1–6 priority based on Maslow's hierarchy
- Auto-assigns priority on add, based on tags/projects/description
- Dynamic context filter shows only what matters most right now
- `nn` companion script for status, review, and configuration
- Designed for Taskwarrior 2.6.2

---

## Why this exists

You won't achieve self-actualization if you're behind on bills. Taskwarrior
tracks everything equally — this hook enforces a hierarchy, so you focus on
what matters most right now while still planning for bigger goals. 
This hook helps you focus on the most vital tasks first. 


---

## Core concepts

- **Priority levels (1–6)**
  Mapped to Maslow's hierarchy, from physiological needs (1) to higher goals (6).

- **Auto-assignment**
  Tasks get priority automatically based on tags, projects, and description
  patterns defined in `need.rc`. No match defaults to pri:4.

- **Span**
  How many priority levels to show at once. With span=2 and lowest tasks at
  pri:2, you see pri:2 and pri:3. Also supports ranges like `2-4`.

- **Lookahead / Lookback**
  Always show tasks due or scheduled within the lookahead window. Exclude
  ancient overdue tasks beyond the lookback window.

- **Context filter**
  `context.need.read` in `need.rc` is auto-maintained by hooks. Activate it
  with `task context need`, deactivate with `task context none`.

---

## The six levels
```
      /               Higher Goals               \        (6)
     /             Self Actualization             \       (5)
    /         Esteem, Respect & Recognition        \      (4) ← default
   /       Love & Belonging, Friends & Family       \     (3)
  /   Personal safety, security, health, financial   \    (2)
 /      Physiological; Air, Water, Food & Shelter     \   (1)
```

---

## Installation
### Option #1 - clone this repo and use the included install file
```
./need-priority.install
```

Copies hooks, scripts, rc file and README.md to correct directories under ~/.task

### Option #2 - via [awesome-taskwarrior](https://github.com/linuxcaffe/awesome-taskwarrior)'s package manager

```
tw -I need-priority
```

### Option #3 - manual install

```bash
# Copy hooks and config
cp on-add_need-priority.py ~/.task/hooks/
cp on-exit_need-priority.py ~/.task/hooks/
cp nn ~/.task/scripts/nn
cp need.rc ~/.task/config/

# Make executable
chmod +x ~/.task/hooks/on-add_need-priority.py
chmod +x ~/.task/hooks/on-exit_need-priority.py
chmod +x ~/.task/scripts/nn

# Include config in .taskrc
echo 'include ~/.task/config/need.rc' >> ~/.taskrc

# Optional: shell alias for nn with arguments
echo "alias nn='~/.task/scripts/nn'" >> ~/.bashrc
```

---

## Configuration

Edit `need.rc` to customize:
```
# Auto-assignment rules (first match wins, checked 1→6)
priority.1.auto=+meds,+oxygen,desc.has:emergency,proj:medical
priority.2.auto=+job,+bills,+rent,proj:financial
priority.3.auto=+family,+friends,proj:relationships
priority.4.auto=+work,+career,proj:education
priority.5.auto=+creative,+art,+writing,proj:personal
priority.6.auto=+goals,+dreams,proj:vision

# Context span — how many levels to show
span=2

# Due/scheduled lookahead and lookback
lookahead=2d
lookback=1w
```

Supported filter types: `+tag`, `proj:name`, `proj.has:text`, `desc.has:text`

Set span via: `nn span 3` or `nn span 2-4` (range)

---

## Usage
```bash
# Add task — auto-assigned pri:1 based on +meds tag
task add Get prescription refilled +meds

# Add task with explicit priority — kept as-is
task add Critical deadline pri:1

# Add unmatched task — defaults to pri:4
task add Buy new headphones

# Show priority pyramid and current filter
nn

# Review and assign priorities interactively
nn review

# Adjust span
nn span 3

# Manually recalculate context filter
nn update

# Activate/deactivate context
task context need
task context none
```

---

## How it works

**on-add** checks the new task against auto-assignment rules. First match
wins. If no match and no user-set priority, defaults to pri:4. Then
recalculates and writes the context filter.

**on-exit** recalculates the context filter after task completion or deletion,
so the filter adjusts as you clear lower-level tasks.

**nn** shows the priority pyramid, current configuration, and active filter.
Also handles span changes, manual updates, and interactive review.

---

## Urgency integration

Higher priorities boost urgency scores (configured in `need.rc`):

| Priority | Coefficient |
|----------|-------------|
| 1        | +20.0       |
| 2        | +16.0       |
| 3        | +12.0       |
| 4        | +8.0        |
| 5        | +4.0        |
| 6        | +0.0        |

---

## Files
```
on-add_need-priority.py    # Auto-assignment + context update
on-exit_need-priority.py   # Context update on completion/deletion
nn                         # Companion script (Needs Navigator)
need.rc                    # Configuration + UDA + context definition
```

---

## Compatibility

- Taskwarrior 2.6.2
- Python 3.6+

---

## Project status

⚠️ Active development — working and in daily use, but interfaces may change.


# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Scheduled (highest priority first, earliest fitting slot):
  08:00 — Feeding for Mochi (10 min) [high]
  08:10 — Morning walk for Mochi (30 min) [high]
  08:40 — Enrichment play for Biscuit (20 min) [medium]
  09:00 — Feeding for Biscuit (10 min) [high]
  09:10 — Grooming for Mochi (40 min) [low]
Total time used: 110 min.

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

Beyond the basic "order by priority and fill the day" plan, PawPal+ implements
several smarter scheduling behaviors. Each is summarized below and mapped to the
method that implements it (all in [`pawpal_system.py`](pawpal_system.py)).

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `sort_by_time()`, `Owner.tasks_by_time()`, `Task.time_sort_key()`, `Scheduler.sort_tasks()` | Chronological by time; priority/duration for the plan |
| Filtering | `Owner.filter_tasks()`, `tasks_for_pet()`, `completed_tasks()`, `pending_tasks()`, `due_tasks()` | By pet, completion status, and/or due date |
| Conflict detection | `Scheduler.detect_overlaps()`, `Owner.find_conflicts()`, `Scheduler.conflict_warning()`, `DailyPlan.conflict_warning()` | Same-pet vs different-pet; warns instead of crashing |
| Recurring tasks | `Task.is_due_on()`, `Task.next_occurrence()`, `Pet.complete_task()`, `Owner.complete_task()` | daily / weekly / once; auto-rolls over on completion |

### Sorting behavior

Tasks can be ordered **chronologically** with `sort_by_time(tasks)` (or the
convenience wrapper `Owner.tasks_by_time()`). The ordering rule lives on the task
itself in `Task.time_sort_key()`: anchored tasks (those with a `preferred_time`)
come first by start time, flexible tasks follow, and ties break by priority
(high → low) then shortest duration. Keeping the key on `Task` makes it
None-safe (a mixed list never raises) and reusable.

The scheduler also has a separate `Scheduler.sort_tasks()` that orders by
**priority then duration** — this is what decides which flexible tasks win the
remaining time when the day is tight.

### Filtering behavior

`Owner.filter_tasks(pet=None, completed=None, due_on=None)` is the one unified
filter — every argument is optional and they compose:

- **By pet** — `filter_tasks(pet="Mochi")` or the wrapper `tasks_for_pet("Mochi")`
  (accepts a `Pet` object or a name string).
- **By completion status** — `filter_tasks(completed=True)` / `completed_tasks()`
  for finished tasks, `pending_tasks()` for open ones.
- **By due date** — `filter_tasks(due_on=some_date)` / `due_tasks(today)` keeps
  only tasks actually due that day (recurrence-aware, see below).

Combine them freely, e.g. `filter_tasks(pet="Mochi", completed=False)` for
Mochi's open tasks. These power the sort/filter controls in the Streamlit UI.

### Conflict detection logic

Conflicts are detected on **full `[start, start+duration)` intervals**, not just
identical start times, so a 09:00 feeding and a 09:05 medication are correctly
flagged as overlapping.

- **During scheduling**, `Scheduler._has_conflict()` and
  `Scheduler._earliest_free()` prevent overlaps from ever being placed (the owner
  is a single timeline).
- **`Scheduler.detect_overlaps(plan)`** scans a plan's slots and returns every
  colliding pair tagged **same-pet vs different-pet** (a sort-then-sweep,
  `O(n log n)`). `Owner.find_conflicts()` does the equivalent check on the input
  anchored tasks *before* scheduling.
- **`Scheduler.conflict_warning()`** (pre-schedule) and
  **`DailyPlan.conflict_warning()`** (post-schedule) return a human-readable
  warning **string** — and are written to never raise, so the program shows a
  warning instead of crashing. Both `main.py` and `app.py` surface these.

### Recurring task logic

Each `Task` has a `recurrence` of `"daily"`, `"weekly"`, or `"once"` (weekly
tasks also carry a `weekday`).

- **`Task.is_due_on(today)`** decides whether a task appears in a given day's
  plan: daily → always, weekly → only on its weekday, once → until completed.
  The `Scheduler` and `due_tasks()` use this so weekly/one-off tasks don't
  clutter every day.
- **`Task.next_occurrence()`** returns a fresh, incomplete copy of a recurring
  task for its next occurrence (or `None` for a one-off).
- **`Pet.complete_task()` / `Owner.complete_task()`** mark a task done and, if it
  recurs, automatically append that next instance — so the completed task becomes
  history while the next occurrence is ready to schedule.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

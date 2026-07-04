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

### Running

```bash
# Launch the Streamlit UI:
streamlit run app.py

# Or run the command-line demo (builds a sample owner + pets and prints a plan):
python main.py
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

Running `python main.py` prints the sorting/filtering demo, a conflict check,
and today's generated schedule:

```
Conflict check
--------------
  ⚠️ 1 time conflict — Feeding & Medication at 09:00 (same pet: Biscuit)

Today's schedule (day starts 08:00, 120 min available)
==================================================
Scheduled (highest priority first, earliest fitting slot):
  08:00 — Morning walk for Mochi (30 min) [high]
  08:30 — Vet visit for Mochi (20 min) [medium]
  09:00 — Feeding for Biscuit (10 min) [high]
  09:10 — Enrichment play for Biscuit (20 min) [medium]
Total time used: 80 min.

Skipped:
  Medication — preferred time conflicts with another task
  Grooming — no free time slot large enough remains in the day window
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
platform darwin -- Python 3.13.2, pytest-9.1.1, pluggy-1.6.0
collected 32 items

tests/test_pawpal.py ................................                    [100%]

============================== 32 passed in 0.02s ==============================
```

### Confidence Level: ★★★★☆ (4 / 5)

Based on the test results and a review of the code:

**What earns 4 stars**

- **32/32 tests pass** in ~0.02s, with no failures, warnings, or flakiness.
- **Coverage is meaningful, not superficial.** The suite exercises real behaviors
  across every core feature: scheduling (gap-filling, over-window skips,
  no-overlap guarantees), sorting (anchored-then-flexible, tiebreaks), filtering
  (by pet, status, combined), conflict detection (same-pet, different-pet,
  adjacent-slot edge cases), and recurring tasks (daily/weekly/once rollover,
  weekday preservation).
- **Edge cases and failure modes are tested**, not just happy paths — e.g.
  `test_conflict_warning_does_not_crash_on_bad_data` confirms the
  "warn instead of crash" design actually holds.
- **The CLI demo runs cleanly end-to-end** and its output matches the documented
  behavior.

**Why not 5 stars**

- **Coverage has not been measured.** Quality is inferred from test intent, not a
  `pytest --cov` report.
- **The Streamlit UI (`app.py`) has no automated tests.** All 32 tests target the
  logic in `pawpal_system.py`; the UI wiring is only verified by manual inspection.
- **No property/fuzz tests** — the "no overlaps" invariant is proven only on
  hand-picked cases, not randomized inputs.

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

Launch the UI with `streamlit run app.py`, then:

1. **Add a Pet** — enter a name and pick a species (dog / cat / other). Added
   pets are listed back to you so you can build a household of several pets.
2. **Add a Task** — choose which pet it's for, then set a title, duration,
   priority (low / medium / high), and an optional preferred time (`HH:MM`) to
   anchor it to a fixed slot.
3. **Review current tasks** — the table below supports filtering by pet and by
   status (pending / completed) and sorting either as-added or chronologically
   by time.
4. **Set plan settings** — adjust the total minutes available for the day.
5. **Build Schedule** — click *Generate schedule*. PawPal+ warns about any
   time conflicts (without crashing), then displays the ordered plan plus an
   explanation of what was scheduled and what was skipped and why.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

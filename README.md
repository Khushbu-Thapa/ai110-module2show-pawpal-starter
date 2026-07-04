# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## ✨ Features

PawPal+ turns a loose list of pet-care tasks into a single, conflict-free daily
plan. The scheduling engine lives in [`pawpal_system.py`](pawpal_system.py); each
feature below names the algorithm and the method(s) that implement it.

- **Multi-pet task management** — one owner manages many pets, each with its own
  task list; every task is tagged with its pet so identical chores on different
  pets stay distinct. *(`Owner`, `Pet`, `Task`)*
- **Priority-and-duration scheduling** — flexible tasks are placed
  highest-priority first, shortest-duration breaking ties, into the earliest gap
  that fits. *(`Scheduler.sort_tasks()`, `Scheduler.build_plan()`)*
- **Fixed-time anchoring** — tasks with a `preferred_time` are locked to that slot
  first; the rest of the day is filled around them. *(`Scheduler.build_plan()`)*
- **Sorting by time** — orders tasks chronologically (anchored-then-flexible,
  earliest first, ties by priority then duration) with a `None`-safe key that
  never raises on a mixed list. *(`sort_by_time()`, `Task.time_sort_key()`,
  `Owner.tasks_by_time()`)*
- **Priority-first sorting** — an alternate ordering where **priority dominates
  and time is only the tiebreaker**, so a high-priority 10:00 med outranks a
  low-priority 08:00 grooming. *(`sort_by_priority_then_time()`,
  `Task.priority_time_sort_key()`, `Scheduler.sort_by_priority_then_time()`)*
- **Next available slot** — a "when can I fit this?" query that returns the
  earliest free start time a new task of a given length could take today (or
  `None` if the day is full), reusing the scheduler's interval sweep.
  *(`Scheduler.next_available_slot()`)*
- **JSON persistence** — pets, tasks, and constraints are saved to and restored
  from `data.json`, so the app remembers everything between runs. Custom
  dict-conversion handles the non-JSON types (`Priority` enum, `time`).
  *(`Owner.save_to_json()`, `Owner.load_from_json()`, `to_dict()`/`from_dict()`)*
- **Filtering** — one composable filter by pet, completion status, and/or
  due-date. *(`Owner.filter_tasks()`, `tasks_for_pet()`, `pending_tasks()`,
  `completed_tasks()`, `due_tasks()`)*
- **Conflict detection & warnings** — overlaps are found on full
  `[start, start+duration)` intervals via an `O(n log n)` sort-then-sweep, tagged
  **same-pet vs different-pet**, both before scheduling and as post-plan
  validation. The warning helpers never raise, so the app shows a message instead
  of crashing. *(`Owner.find_conflicts()`, `Scheduler.detect_overlaps()`,
  `Scheduler.conflict_warning()`, `DailyPlan.conflict_warning()`)*
- **Daily / weekly / one-off recurrence** — each task repeats daily, weekly (on a
  set weekday), or once; only tasks actually due on a given day enter that day's
  plan. *(`Task.is_due_on()`)*
- **Auto roll-over on completion** — completing a recurring task marks it done and
  automatically queues a fresh next instance. *(`Task.next_occurrence()`,
  `Pet.complete_task()`, `Owner.complete_task()`)*
- **Explainable plans** — every plan reports what was scheduled, the total time
  used, and *why* each skipped task didn't fit. *(`DailyPlan.explain()`,
  `Scheduler._skip_reason()`)*
- **Professional CLI formatting** — the command-line demo renders boxed tables
  (via `tabulate`), task-type emojis (🚶 walk, 🍽️ feeding, 💊 meds, ✂️ grooming,
  🎾 play, 🏥 vet …), and color-coded priority indicators (🔴 High / 🟡 Medium /
  🟢 Low). *(see [`main.py`](main.py))*
- **Two front-ends** — a Streamlit UI ([`app.py`](app.py)) and a command-line demo
  ([`main.py`](main.py)), both driven by the same engine, both able to save/load
  `data.json`.

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
| Priority-first sorting | `sort_by_priority_then_time()`, `Task.priority_time_sort_key()`, `Scheduler.sort_by_priority_then_time()` | Priority dominates, time is the tiebreaker |
| Next available slot | `Scheduler.next_available_slot()` | Earliest free start time for a new task of length N |
| Filtering | `Owner.filter_tasks()`, `tasks_for_pet()`, `completed_tasks()`, `pending_tasks()`, `due_tasks()` | By pet, completion status, and/or due date |
| Conflict detection | `Scheduler.detect_overlaps()`, `Owner.find_conflicts()`, `Scheduler.conflict_warning()`, `DailyPlan.conflict_warning()` | Same-pet vs different-pet; warns instead of crashing |
| Recurring tasks | `Task.is_due_on()`, `Task.next_occurrence()`, `Pet.complete_task()`, `Owner.complete_task()` | daily / weekly / once; auto-rolls over on completion |
| Persistence | `Owner.save_to_json()`, `Owner.load_from_json()`, `to_dict()`/`from_dict()` | Save/restore all state to `data.json` |

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

### Priority-first scheduling (priority, then time)

`sort_by_priority_then_time(tasks)` (and the wrapper
`Scheduler.sort_by_priority_then_time()`) is the inverse emphasis of
`sort_by_time`: **priority is the primary key and time is only the tiebreaker.**
The rule, from `Task.priority_time_sort_key()`, is priority high → low, then
anchored-before-flexible, then earliest start, then shortest duration. So a
high-priority task always surfaces above a lower-priority one *even if the
low-priority task is scheduled earlier in the day*:

```text
Sorted by priority, then time (sort_by_priority_then_time)
╭────────┬───────────────────┬─────────┬────────────┬───────────╮
│ Time   │ Task              │ Pet     │ Priority   │ Status    │
├────────┼───────────────────┼─────────┼────────────┼───────────┤
│ 09:00  │ 🍽️ Feeding        │ Biscuit │ 🔴 High     │ ⏳ pending │
│ —      │ 🚶 Morning walk    │ Mochi   │ 🔴 High     │ ⏳ pending │
│ 08:30  │ 🏥 Vet visit       │ Mochi   │ 🟡 Medium   │ ⏳ pending │
│ 09:00  │ 💊 Medication      │ Biscuit │ 🟡 Medium   │ ⏳ pending │
│ —      │ 🎾 Enrichment play │ Biscuit │ 🟡 Medium   │ ⏳ pending │
│ —      │ ✂️ Grooming       │ Mochi   │ 🟢 Low      │ ⏳ pending │
╰────────┴───────────────────┴─────────┴────────────┴───────────╯
```

Note the 08:30 Vet visit sorts **below** the two High-priority tasks even though
it starts earlier — priority wins, then time breaks ties within each band.

### Next available slot

`Scheduler.next_available_slot(duration_minutes)` answers "when could I fit a new
N-minute task today?" It builds today's plan, then reuses the same interval sweep
(`_earliest_free`) the scheduler uses internally to return the earliest free start
time — or `None` when no gap that large remains in the day window:

```text
🔎 Earliest free slot for a 15-min task: 09:30
🔎 Earliest free slot for a 90-min task: no room left today
```

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

## 💾 Data Persistence

PawPal+ remembers your pets and tasks between runs by saving them to a
**`data.json`** file. Rather than pulling in a serialization library like
`marshmallow`, the project uses a small **custom dictionary conversion** — each
class knows how to turn itself into a plain dict and back — which keeps the
engine dependency-free and the on-disk format easy to read.

**The persistence workflow:**

1. **Save** — `Owner.save_to_json("data.json")` walks the object graph
   (`Owner → Pet → Task`), calling each class's `to_dict()`, and writes
   pretty-printed JSON. The two non-JSON-native types are converted at the
   leaves: the `Priority` enum becomes its name (`"HIGH"`) and each `time`
   becomes an `"HH:MM"` string.
2. **Load** — `Owner.load_from_json("data.json")` reads the file and rebuilds a
   fully working `Owner` via `from_dict()` — enums and times are parsed back into
   real objects, and every task's `pet_name` back-reference is restored — so the
   reloaded owner can immediately be scheduled.
3. **In the apps** — the CLI ([`main.py`](main.py)) saves after building the plan
   and reloads to confirm the round-trip. The Streamlit UI ([`app.py`](app.py))
   restores `data.json` on startup if present and offers **Save** / **Load**
   buttons in the sidebar.

```python
owner.save_to_json("data.json")          # persist everything
owner = Owner.load_from_json("data.json")  # restore on the next run
```

**Files modified for persistence:** [`pawpal_system.py`](pawpal_system.py) (added
`to_dict`/`from_dict` on `Task`, `Pet`, `Owner`, plus `Owner.save_to_json` /
`Owner.load_from_json`), [`app.py`](app.py) (load-on-startup + Save/Load buttons),
[`main.py`](main.py) (save/reload demo), and `.gitignore` (ignores the generated
`data.json`).

## 🎨 Output Formatting

The command-line demo ([`main.py`](main.py)) is formatted for readability:

- **Structured tables** — every task list and the final schedule are rendered
  with the [`tabulate`](https://pypi.org/project/tabulate/) library
  (`tablefmt="rounded_grid"`) for clean, boxed columns.
- **Task-type emojis** — `task_emoji()` maps a keyword in each task's description
  to an icon: 🚶 walk, 🍽️ feeding, 💊 meds, ✂️ grooming, 🎾 play, 🧩 enrichment,
  🏥 vet, 🎓 training, 🛁 bath (🐾 as the default).
- **Color-coded priority indicators** — the `PRIORITY_ICON` map shows priority as
  a colored circle (🔴 High / 🟡 Medium / 🟢 Low). Colored circles are used
  instead of raw ANSI color codes so the output stays readable when pasted into
  plain text (like this README).
- **Status glyphs** — ✅ done / ⏳ pending.

`tabulate` is the only added dependency (see [`requirements.txt`](requirements.txt));
the emoji/priority maps and helper functions live in [`main.py`](main.py).

## 🚶 Demo Walkthrough

### The UI at a glance

Launch the app with `streamlit run app.py`. The single-page UI is organized top
to bottom into the actions a user performs:

- **Add a Pet** — enter a name and pick a species (dog / cat / other). Pets you
  add are listed back to you, so you can build a household of several pets.
- **Add a Task** — pick which pet it's for, then set a title, duration (minutes),
  priority (low / medium / high), and an optional preferred time (`HH:MM`). A
  preferred time *anchors* the task to a fixed slot; leaving it blank makes the
  task *flexible* for the scheduler to place.
- **Current tasks table** — every task across all pets, with controls to
  **filter by pet**, **filter by status** (pending / completed), and **sort** by
  "As added", "By time", or "By priority".
- **Plan Settings** — set how many minutes are available in the day.
- **Build Schedule** — generates the day's plan: a success banner and metrics
  (tasks scheduled, minutes used), a table of scheduled slots, an expandable list
  of skipped tasks *with reasons*, and a conflict warning banner when fixed-time
  tasks collide.
- **Sidebar → Data** — **Save** / **Load** buttons persist the whole household to
  `data.json`; the app also auto-restores `data.json` on startup, so your pets and
  tasks survive between runs.

### Example workflow

1. **Add a pet** — create *Mochi* (dog).
2. **Add a fixed-time task** — a *Feeding* at `08:00`, 10 min, high priority
   (anchored to 08:00).
3. **Add a flexible task** — a *Morning walk*, 30 min, high priority, no preferred
   time (the scheduler chooses when).
4. **Filter / sort** — switch the table sort to *By time* to see the 08:00 feeding
   ahead of the unscheduled walk.
5. **Set the day** — 120 minutes available.
6. **Build the schedule** — click *Generate schedule*; the walk is slotted into
   the earliest gap after the feeding, and the plan explains the result.

### Key Scheduler behaviors on display

Running the CLI demo (`python main.py`) exercises the engine end-to-end with two
pets and tasks **added out of order**, so several behaviors are visible at once:

- **Sorting by time** — `tasks_by_time` reorders the shuffled input so anchored
  tasks come first by start time and flexible tasks follow.
- **Filtering** — `tasks_for_pet`, `pending_tasks`, and `completed_tasks` slice
  the same list by pet and completion status.
- **Conflict warnings** — a same-pet clash (Biscuit's *Feeding* and *Medication*
  both at 09:00) is detected and reported as a warning, not a crash.
- **Priority scheduling + skip reasons** — the generated plan places tasks
  highest-priority-first into the earliest fitting gap, and explains why
  *Medication* (time conflict) and *Grooming* (no room left) were skipped.
- **Next available slot & persistence** — after the plan, the demo queries the
  earliest free slot for a new task and saves/reloads `data.json`.

### Sample CLI output

Formatted with `tabulate` tables, task-type emojis, and 🔴/🟡/🟢 priority
indicators. (Several filter tables are trimmed here for brevity — run
`python main.py` to see the full output.)

```text
🐾 PawPal+ demo for Jordan
==================================================

Tasks as added (unsorted)
╭────────┬───────────────────┬─────────┬────────────┬───────────╮
│ Time   │ Task              │ Pet     │ Priority   │ Status    │
├────────┼───────────────────┼─────────┼────────────┼───────────┤
│ 08:00  │ 🍽️ Feeding        │ Mochi   │ 🔴 High     │ ✅ done    │
│ 08:30  │ 🏥 Vet visit       │ Mochi   │ 🟡 Medium   │ ⏳ pending │
│ —      │ 🚶 Morning walk    │ Mochi   │ 🔴 High     │ ⏳ pending │
│ —      │ ✂️ Grooming       │ Mochi   │ 🟢 Low      │ ⏳ pending │
│ 09:00  │ 🍽️ Feeding        │ Biscuit │ 🔴 High     │ ⏳ pending │
│ —      │ 🎾 Enrichment play │ Biscuit │ 🟡 Medium   │ ⏳ pending │
│ 09:00  │ 💊 Medication      │ Biscuit │ 🟡 Medium   │ ⏳ pending │
╰────────┴───────────────────┴─────────┴────────────┴───────────╯

... (Sorted by time, priority-then-time, and filter tables) ...

Conflict check
  ⚠️ 1 time conflict — Feeding & Medication at 09:00 (same pet: Biscuit)
==================================================

Today's schedule (day starts 08:00, 120 min available)
╭─────────────┬───────────────────┬─────────┬────────────┬────────────╮
│ Time        │ Task              │ Pet     │ Duration   │ Priority   │
├─────────────┼───────────────────┼─────────┼────────────┼────────────┤
│ 08:00–08:30 │ 🚶 Morning walk    │ Mochi   │ 30 min     │ 🔴 High     │
│ 08:30–08:50 │ 🏥 Vet visit       │ Mochi   │ 20 min     │ 🟡 Medium   │
│ 09:00–09:10 │ 🍽️ Feeding        │ Biscuit │ 10 min     │ 🔴 High     │
│ 09:10–09:30 │ 🎾 Enrichment play │ Biscuit │ 20 min     │ 🟡 Medium   │
╰─────────────┴───────────────────┴─────────┴────────────┴────────────╯
Total time used: 80 min.

Skipped:
  💊 Medication — preferred time conflicts with another task
  ✂️ Grooming — no free time slot large enough remains in the day window

🔎 Earliest free slot for a 15-min task: 09:30
🔎 Earliest free slot for a 90-min task: no room left today

💾 Saved 2 pets / 7 tasks to data.json; reloaded 2 pets / 7 tasks — data persists between runs.
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

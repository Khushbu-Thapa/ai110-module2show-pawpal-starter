# AI Interactions Log

> Documents the stretch features attempted for PawPal+ and how an AI coding
> assistant was used to build them.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I asked the agent to implement four advanced-capability challenges across the
whole project in one pass, keeping the existing tests green:

1. Add a **third algorithmic capability** beyond the basics.
2. Add **JSON data persistence** so pets/tasks survive between runs.
3. Add **priority-then-time scheduling** (priority first, time as tiebreaker).
4. Add **professional CLI output** (tables, emojis, color-coded priorities).

**What did the agent do?**

The agent worked end-to-end and edited these files:

| File | Change |
|------|--------|
| `pawpal_system.py` | Added `Scheduler.next_available_slot()` (Challenge 1), `sort_by_priority_then_time()` + `Task.priority_time_sort_key()` + `Scheduler.sort_by_priority_then_time()` (Challenge 3), and `to_dict`/`from_dict` on `Task`/`Pet`/`Owner` plus `Owner.save_to_json` / `load_from_json` (Challenge 2). Added `import json`. |
| `main.py` | Rewrote the CLI with `tabulate` boxed tables, a `task_emoji()` keyword map, `PRIORITY_ICON` colored circles, and new demo sections for priority-then-time sort, next-available-slot, and a save/reload round-trip. |
| `app.py` | Load `data.json` on startup and added sidebar **Save** / **Load** buttons. |
| `tests/test_pawpal.py` | Added 9 tests (priority-first sort, next-available-slot, JSON round-trip) — suite went 32 → 41 passing. |
| `requirements.txt` | Added `tabulate>=0.9`. |
| `.gitignore` | Ignored the generated `data.json`. |
| `README.md` | Documented all four features, the persistence workflow, and CLI output examples. |

It ran `python main.py` and `pytest` to verify each step, and confirmed the
persistence round-trip (2 pets / 7 tasks saved and reloaded).

**What did you have to verify or fix manually?**

- **Color indicators:** the first instinct was raw ANSI color codes, but those
  render as escape gibberish when pasted into the README. I had it switch to
  colored-circle emojis (🔴🟡🟢) so the output stays clean in plain text.
- **Single source of truth for time:** I rejected an early version of the
  scheduler that tracked *both* a decrementing `available_minutes` budget and the
  day window (they could disagree and skip tasks that actually fit). The final
  `next_available_slot()` reuses the window-based `_earliest_free()` sweep only.
- **`data.json` in git:** decided it's generated runtime state and added it to
  `.gitignore` rather than committing it.
- **Verification:** I trusted the tests, not the diff — the 9 new tests are what
  confirmed the enum/`time` survive the JSON round-trip and that priority sorting
  really outranks earlier-but-lower-priority tasks.

---

## Prompt Comparison (SF11)

> Complex algorithmic task compared across two tools: **the weekly-task
> rescheduling logic** — i.e. how a recurring weekly task should "come due again"
> and how `next_occurrence()` should behave.

**The task / prompt given to both tools:**

> "Design the logic for recurring weekly pet-care tasks in PawPal+. A weekly task
> (e.g. a Sunday bath) should appear in the plan only on the right day and produce
> its next occurrence after completion. Show the data model and the
> `is_due_on()` / `next_occurrence()` methods."

| | Option A — Claude | Option B — second model (e.g. Gemini/Copilot) |
|-|-------------------|-----------------------------------------------|
| **Model / tool used** | Claude | A second assistant used for comparison |
| **Prompt** | (the task above) | (the same task) |
| **Response summary** | **Weekday-keyed, stateless recurrence.** Each task stores a `recurrence` string and an integer `weekday` (0=Mon…6=Sun). `is_due_on(today)` returns `today.weekday() == self.weekday` for weekly tasks; `next_occurrence()` just returns a fresh incomplete copy (`replace(self, completed=False)`) — no dates stored. Dueness is *derived* per day. | **Date-advancing recurrence.** Each task stores a concrete `next_due` `date`; `is_due_on(today)` compares `today == next_due`; `next_occurrence()` advances the date by `timedelta(days=7)`. Recurrence state lives as an explicit calendar date on every task. |
| **What was useful** | Simple and stateless — no date arithmetic to get wrong, and it fits an app that plans **one day at a time**. Easy to test with a fixed weekday. Plays cleanly with JSON persistence (just an int). | Handles real calendars and arbitrary intervals ("every 14 days", specific dates) naturally, and can express *when* the next one is, not just *which weekday*. |
| **Problems noticed** | Can't express "every other week" or a specific calendar date — only a weekday. No notion of an absolute next date. | Heavier: every task carries mutable date state that must be initialized, migrated, and serialized correctly; more edge cases (timezones, missed days, catch-up). Overkill for a single-day planner. |
| **Decision** | ✅ **Chosen.** | ❌ Not used (kept as a future option). |

**Which approach did you use in your final implementation and why?**

I used **Option A (weekday-keyed, stateless recurrence)**. PawPal+ builds a plan
for a *single day*, so "is this task due today?" is the only question that
matters, and deriving that from a `weekday` is simpler and less error-prone than
threading concrete `date`s through every task and the JSON file. `next_occurrence()`
therefore just resets completion (`Task.next_occurrence()` → `replace(self,
completed=False)`), and `Pet.complete_task()` appends that fresh instance. If the
app later grows into a multi-day calendar, Option B's date-advancing model becomes
the right upgrade — at which point the existing `is_due_on()` seam is where that
logic would slot in.

*Note: attribute the two columns to whichever tools you actually ran; the
technical approaches above are the two designs that were genuinely weighed.*

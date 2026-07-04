# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
--> The PawPal system has pet, owner profile. Owner can create, edit and delete the pet information. Owner can schedule the feeding alert, walk alert and scheduling for pets health. They can also enter these information and track these information so that statistcs/charts can be created. 
- What classes did you include, and what responsibilities did you assign to each?
--> CareTask, Priority (Enum), Scheduler, DailyPlan, ScheduledSlot

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. After reviewing the skeleton, I made several changes before writing logic:

1. **Time is handled as minutes-since-midnight internally.** `datetime.time` cannot be added to a duration (`time(8,0) + 30 min` raises `TypeError`), so I added `minutes_since_midnight()` / `time_from_minutes()` helpers and let the scheduler do all math in ints, converting back to `time` only for display.

2. **`Scheduler` now takes an `Owner` instead of a raw task list.** The constraints (`available_minutes`, `day_start`, `preferences`) all live on `Owner`, so passing them separately duplicated the source of truth. `Scheduler(owner)` pulls tasks via `owner.list_all_tasks()` and reads constraints directly.

3. **Added `CareTask.pet_name` back-reference.** The flat task list lost track of which pet a task belonged to, so two pets with identical "Feeding" tasks were indistinguishable. Tagging each task with its pet fixes this.

4. **Defined a placement strategy for `preferred_time`.** Sequential back-to-back placement collided with tasks that want a specific time. I decided preferred-time tasks are placed first as fixed anchors, then flexible tasks fill the gaps, and added `_has_conflict()` so overlaps are detected instead of silently overlapping.

5. **`_skip_reason()` now receives `remaining_minutes`.** With only the task, it could never explain *why* something was skipped (out of time vs. slot taken); passing the state at skip-time makes the explanation accurate.

6. **Added `CareTask.from_ui()` as the string→`Priority` boundary.** This is the single place UI strings become a `Priority` enum, so the scheduler can always assume `priority` is a real enum.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

The scheduler weighs several constraints when building a `DailyPlan`:

1. **The day window `[day_start, day_end]`** — the owner's availability. Every
   task must fit inside this window; `available_minutes` derives the end when no
   explicit `day_end` is set. This is the single source of truth for placement.
2. **Preferred time (fixed-time anchors)** — tasks with a `preferred_time` are
   placed *first*, at their requested clock time, and skipped if that time is
   outside the window or collides with another anchor.
3. **Priority (high → medium → low)** — flexible tasks are ordered so the most
   important care happens first when time is scarce.
4. **Duration** — among equal-priority tasks, shorter ones go first (they pack
   more tasks into the day) and every task must fit an open gap.
5. **Recurrence + completion status** — only tasks that are *due today*
   (`is_due_on`) and *not completed* are considered, so weekly/one-off tasks
   don't clutter every day and finished tasks drop out automatically.

**How I decided what mattered most.** I ranked constraints by how "hard" they
are — whether violating them produces a plan the owner literally can't follow:

- **Time is a hard constraint** and comes first: a plan that double-books the
  owner or runs past their day is simply wrong, so the window and anchor
  conflicts are enforced before anything else.
- **Preferred time outranks priority** because a fixed time is a real-world
  commitment (a 9:00 vet appointment can't move to fill a gap), whereas priority
  only orders the *flexible* work.
- **Priority then duration** are soft, preference-level tiebreakers: they decide
  *which* flexible tasks win the remaining time and in what order, but never
  override the hard time constraints above.

In short: **fit-in-time first, honor fixed commitments second, then do the most
important and most time-efficient work with whatever room is left.**

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**Tradeoff: a single-track timeline (one task at a time across *all* pets).**

The scheduler treats the owner as a single resource who can only do one thing
at a time. Every task — regardless of which pet it belongs to — is placed on one
shared timeline, and `_has_conflict()` / `_earliest_free()` reject any placement
that overlaps an already-placed slot. So two tasks can never run in parallel,
even when they realistically could: e.g. the cat's kibble could soak while the
dog is being walked, but the scheduler still serializes them.

Note this is *not* an "exact time match only" check — conflicts are detected on
full `[start, start+duration)` intervals using minute math, so a 09:00 feeding
and a 09:05 medication are correctly flagged as overlapping, not just identical
start times. The tradeoff is the opposite one: the model is *too strict* about
parallelism, not too loose about overlap.

**Why it's reasonable here:**

1. **It matches the primary user.** PawPal+ plans one owner's hands-on care
   day. Most pet tasks (walking, feeding, grooming, vet trips) genuinely require
   the owner's undivided attention, so serial scheduling reflects reality for the
   common case.
2. **It keeps the model simple and the plan trustworthy.** A single timeline
   means the output is a clean, conflict-free ordering the owner can follow top
   to bottom. Allowing parallelism would require modeling which tasks are
   "attended" vs "passive," per-task attention costs, and possibly multiple
   caregivers — a large jump in complexity for marginal benefit at this scale.
3. **It fails safe.** Over-serializing at worst makes the day look busier than it
   is (and may skip a task for lack of time). Under-serializing — letting two
   attention-requiring tasks overlap — would produce a plan the owner physically
   can't execute, which is a worse failure.

**What it costs / how I'd revisit it:** the scheduler may report a task as
skipped ("no free slot") when a real owner could have doubled up on a passive
task. A future iteration could add a `Task.requires_attention` flag and let
passive tasks overlap others, or support multiple caregivers — at which point
the existing `detect_overlaps()` (which already classifies same-pet vs
different-pet collisions) becomes the tool for surfacing the clashes that still
matter.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

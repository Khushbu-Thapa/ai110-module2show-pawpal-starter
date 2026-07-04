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

I used my AI coding assistant across every phase, but for different jobs each
time: brainstorming the UML and class responsibilities up front, generating stub
methods from the diagram, then refactoring and debugging the scheduling logic
once real code existed. The most useful prompts were **specific and
constraint-driven** rather than open-ended — "the scheduler needs to place
fixed-time tasks first and fill gaps around them; show me a placement strategy
that detects overlaps" produced far better output than "write a scheduler."
Asking it to *explain tradeoffs* ("what breaks if I store times as
`datetime.time`?") was especially valuable, because it surfaced the arithmetic
problem that led to the minutes-since-midnight design before I wrote any buggy
code.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

I verified suggestions by writing tests against the *behavior* I expected, not
by trusting the code looked right — the 32-test suite is where I caught the
difference between "compiles" and "correct" (e.g. a flexible task should fit a
gap left by a late anchor). When a suggestion and a test disagreed, the test won.

---

## 3.5 AI Strategy

**a. Which AI features were most effective for building the scheduler?**

Three features did the most work:

1. **Whole-file context / attach-the-file prompting.** Once `pawpal_system.py`
   existed, I could attach it and ask questions grounded in *my* code ("based on
   this implementation, what should my UML show?"), so answers referenced my real
   method names and relationships instead of a generic template.
2. **Inline refactoring with explanation.** Asking the assistant to *both* rewrite
   a method *and* explain why — rather than just accept a diff — let me learn the
   reasoning (e.g. keeping `time_sort_key()` on `Task` so a mixed list is
   `None`-safe and never raises) instead of pasting code I didn't understand.
3. **Test generation from described behaviors.** Turning plain-English behaviors
   ("a weekly task is only due on its weekday") into pytest cases was fast and
   caught real edge cases, which made the whole scheduler safe to refactor.

**b. One AI suggestion I rejected or modified to keep the design clean**

The assistant initially had the `Scheduler` track **two** notions of available
time at once: a running `available_minutes` *budget* that it decremented as it
placed tasks, **and** the `[day_start, day_end]` *window*. It looked reasonable,
but I rejected it because it created two sources of truth that could disagree —
the budget could hit zero and skip a task that actually fit an open gap in the
window (double-counting time already accounted for by the placed slots). I
collapsed it to a **single source of truth: the day window**. A flexible task is
placed at the earliest large-enough gap (`_earliest_free()`), and skipped only
when no such gap exists — nothing decrements a separate budget. This removed a
whole class of "skipped but it fit" bugs and made the placement logic much easier
to reason about. (I made the same kind of call on conflict detection, tightening
an exact-start-time check the AI proposed into a full `[start, start+duration)`
interval overlap so a 09:00 and 09:05 task are correctly flagged.)

**c. How separate chat sessions per phase kept me organized**

I used a different chat session for each phase — **design/UML**, **implementation**,
**testing**, and **docs/README** — and this mattered more than I expected. Each
session kept a tight, relevant context: the design chat stayed focused on classes
and responsibilities without implementation noise, while the implementation chat
didn't drag along half-formed diagram ideas. It also made it easy to *revisit* a
phase — when I finalized the UML at the end, I could return to the design session's
framing and simply ask "does this still match my final code?" rather than
untangling one enormous thread. Cleaner context in, cleaner suggestions out.

**d. What I learned about being the "lead architect"**

The biggest lesson: **the AI is an extremely fast implementer, but I own the
architecture and the definition of "correct."** The assistant would happily
produce working-looking code for whatever I asked — including designs with subtle
flaws like the double-counted time budget — so the value I added wasn't typing
speed, it was *judgment*: deciding the single-timeline model, insisting on one
source of truth, ranking the constraints (hard time limits before soft priority
tiebreaks), and writing tests that encoded what "correct" actually meant. I
learned to treat suggestions as **proposals to evaluate against my design intent**,
not answers to accept. The most powerful move was staying in the loop —
understanding every method the AI wrote well enough to explain it — so that when
requirements changed I was refactoring a system I understood, not a black box.

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

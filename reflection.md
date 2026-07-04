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

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

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

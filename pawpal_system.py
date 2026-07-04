"""PawPal+ core system.

Four core classes required by the project:
  - Task      : a single activity (description, time, frequency, completion status)
  - Pet       : pet details + a list of tasks
  - Owner     : manages multiple pets and exposes all their tasks
  - Scheduler : the "brain" that retrieves, organizes, and plans tasks across pets

Supporting types: Priority (enum), ScheduledSlot, DailyPlan.

Design note: times are stored as datetime.time for display, but the scheduler
works internally in "minutes since midnight" (ints) because datetime.time does
not support arithmetic. Use minutes_since_midnight() / time_from_minutes() to
convert at the boundary.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field, replace
from datetime import date, time
from enum import Enum


def minutes_since_midnight(t: time) -> int:
    """Convert a time to an int count of minutes past 00:00."""
    return t.hour * 60 + t.minute


def time_from_minutes(minutes: int) -> time:
    """Convert minutes-past-midnight back to a time (capped at 23:59)."""
    minutes = max(0, min(minutes, 23 * 60 + 59))
    return time(minutes // 60, minutes % 60)


def sort_by_time(tasks: list["Task"]) -> list["Task"]:
    """Order tasks chronologically, using each task's own time_sort_key().

    Anchored tasks (those with a preferred_time) come first, earliest start
    first; flexible tasks (no preferred_time) follow. Ties break by priority
    (high->low) then shortest duration. See Task.time_sort_key for the rule.
    """
    return sorted(tasks, key=Task.time_sort_key)


class Priority(Enum):
    """Task importance. Numeric values let the scheduler sort reliably."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def weight(self) -> int:
        """Return the numeric weight used for sorting."""
        return self.value

    @classmethod
    def from_string(cls, s: str) -> "Priority":
        """Parse UI input ('low'/'medium'/'high') into a Priority."""
        mapping = {"low": cls.LOW, "medium": cls.MEDIUM, "high": cls.HIGH}
        key = (s or "").strip().lower()
        if key not in mapping:
            raise ValueError(f"Unknown priority: {s!r}")
        return mapping[key]


@dataclass
class Task:
    """A single pet-care activity (walk, feed, meds...).

    Required attributes: description, time (preferred_time), frequency
    (recurrence), and completion status (completed). duration_minutes and
    priority are extras the Scheduler uses to organize the day. `pet_name`
    is a back-reference so identical tasks on different pets stay distinct.
    """

    description: str
    duration_minutes: int
    priority: Priority
    pet_name: str = ""
    preferred_time: time | None = None  # the task's "time"
    recurrence: str = "daily"  # the task's "frequency": "daily" | "weekly" | "once"
    weekday: int | None = None  # for weekly tasks: 0=Mon .. 6=Sun (None = any day)
    completed: bool = False  # completion status

    @classmethod
    def from_ui(cls, data: dict) -> "Task":
        """Build a Task from raw UI input, coercing the priority string -> Priority.

        This is the single boundary where strings become a Priority enum, so
        the scheduler can always assume `priority` is a real Priority.
        """
        pref = data.get("preferred_time")
        if isinstance(pref, str) and pref.strip():
            hours, minutes = pref.split(":")
            pref = time(int(hours), int(minutes))
        return cls(
            description=data.get("description") or data.get("title", ""),
            duration_minutes=int(data.get("duration_minutes", 0)),
            priority=Priority.from_string(data.get("priority", "medium")),
            pet_name=data.get("pet_name", ""),
            preferred_time=pref if isinstance(pref, time) else None,
            recurrence=data.get("recurrence", "daily"),
            weekday=data.get("weekday"),
            completed=bool(data.get("completed", False)),
        )

    def is_due_on(self, today: date | None = None) -> bool:
        """True if this task should appear in the plan for `today`.

        Honors the `recurrence` "frequency" field so weekly/one-off tasks
        don't clutter every single day's schedule:
          - "daily"  : always due.
          - "weekly" : due only when today's weekday matches self.weekday
                       (or when we have no date/weekday to check against).
          - "once"   : due until it's been completed.
        Passing today=None (the default) treats every task as due, preserving
        the original "plan everything" behavior for callers that don't care
        about the calendar.
        """
        if self.recurrence == "once":
            return not self.completed
        if self.recurrence == "weekly":
            if today is None or self.weekday is None:
                return True
            return today.weekday() == self.weekday
        return True  # "daily" (and any unknown value) is always due

    def is_higher_priority_than(self, other: "Task") -> bool:
        """True if this task outranks `other` by priority."""
        return self.priority.weight() > other.priority.weight()

    def start_minutes(self) -> int | None:
        """Anchored start as minutes-past-midnight, or None if flexible."""
        if self.preferred_time is None:
            return None
        return minutes_since_midnight(self.preferred_time)

    def end_minutes(self) -> int | None:
        """Anchored end (start + duration) as minutes, or None if flexible."""
        start = self.start_minutes()
        return None if start is None else start + self.duration_minutes

    def time_sort_key(self) -> tuple[int, int, int, int]:
        """Sort key for chronological ordering.

        Ordered by: anchored-before-flexible, then start time, then priority
        (high->low), then shortest duration. Handles preferred_time=None
        safely (flexible tasks sort last) so a mixed list never raises.
        """
        anchored = self.preferred_time is not None
        return (
            0 if anchored else 1,                       # anchored group first
            self.start_minutes() if anchored else 0,    # earliest time first
            -self.priority.weight(),                    # then most important
            self.duration_minutes,                      # then quickest
        )

    def overlaps(self, other: "Task") -> bool:
        """True if this and `other` are both anchored and their times collide.

        Flexible tasks (no preferred_time) never overlap — they have no fixed
        place on the clock yet, so the Scheduler is free to move them.
        """
        s1, e1 = self.start_minutes(), self.end_minutes()
        s2, e2 = other.start_minutes(), other.end_minutes()
        if s1 is None or s2 is None:
            return False
        return s1 < e2 and s2 < e1

    def fits_in(self, remaining_minutes: int) -> bool:
        """True if this task's duration fits in the time left."""
        return self.duration_minutes <= remaining_minutes

    def mark_complete(self) -> None:
        """Mark this task complete so the scheduler stops planning it."""
        self.completed = True

    def mark_undone(self) -> None:
        """Reopen a completed task."""
        self.completed = False

    def is_recurring(self) -> bool:
        """True for tasks that repeat ('daily'/'weekly'), False for 'once'."""
        return self.recurrence in ("daily", "weekly")

    def next_occurrence(self) -> "Task | None":
        """Return a fresh, incomplete copy for this task's next occurrence.

        Recurring tasks (daily/weekly) come due again, so this returns a new
        Task with identical details but completed=False — the next instance to
        schedule. One-off ('once') tasks don't recur, so this returns None.
        The original task is left untouched; callers decide what to do with it.
        """
        if not self.is_recurring():
            return None
        return replace(self, completed=False)


# Backwards-compatible alias for earlier drafts / diagrams that used "CareTask".
CareTask = Task


@dataclass
class Pet:
    """The animal being cared for; stores details and its own task list."""

    name: str
    species: str  # "dog" | "cat" | "other"
    tasks: list[Task] = field(default_factory=list)
    notes: str = ""

    def add_task(self, task: Task) -> None:
        """Add a task and tag it with this pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's list if present."""
        if task in self.tasks:
            self.tasks.remove(task)

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)

    def complete_task(self, task: Task) -> Task | None:
        """Mark `task` complete and auto-create its next occurrence.

        For a recurring (daily/weekly) task, a fresh incomplete instance is
        appended to this pet's list and returned, so the completed one becomes
        history while the next occurrence is ready to schedule. For a one-off
        task, nothing new is created and None is returned.
        """
        task.mark_complete()
        upcoming = task.next_occurrence()
        if upcoming is not None:
            self.add_task(upcoming)
        return upcoming


@dataclass
class Owner:
    """The person using the app; manages pets and the day's constraints.

    Owner is the single source of truth for scheduling constraints
    (available_minutes, day_start, preferences). The Scheduler reads them
    from here rather than taking duplicated copies.
    """

    name: str
    pets: list[Pet] = field(default_factory=list)
    available_minutes: int = 120
    day_start: time = time(8, 0)
    day_end: time | None = None  # explicit end of the availability window
    preferences: dict = field(default_factory=dict)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's roster."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner's roster if present."""
        if pet in self.pets:
            self.pets.remove(pet)

    def add_task(self, pet: Pet, task: Task) -> None:
        """Attach a care task to one of this owner's pets."""
        if pet not in self.pets:
            self.add_pet(pet)
        pet.add_task(task)

    def complete_task(self, task: Task) -> Task | None:
        """Complete a task on whichever pet owns it, rolling over if recurring.

        Delegates to Pet.complete_task, so a daily/weekly task automatically
        gets a fresh next instance. Returns that new instance (or None for a
        one-off, or if the task isn't attached to any pet).
        """
        for pet in self.pets:
            if any(t is task for t in pet.tasks):
                return pet.complete_task(task)
        task.mark_complete()  # not attached to a pet: complete it, no roll-over
        return None

    def list_all_tasks(self) -> list[Task]:
        """Gather tasks across all pets (each already tagged with pet_name)."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks

    def pending_tasks(self) -> list[Task]:
        """All not-yet-completed tasks across every pet."""
        return [t for t in self.list_all_tasks() if not t.completed]

    def filter_tasks(
        self,
        pet: "Pet | str | None" = None,
        completed: bool | None = None,
        due_on: date | None = None,
    ) -> list[Task]:
        """Filter tasks by pet, completion status, and recurrence-due date.

        Every argument is optional; a None argument means "don't filter on
        this". Combine them freely, e.g. `filter_tasks(pet="Mochi",
        completed=False)` for Mochi's open tasks.

          - pet       : a Pet or its name; keeps only that pet's tasks.
          - completed : True/False keeps only done / not-done tasks.
          - due_on    : a date; keeps only tasks due that day (see
                        Task.is_due_on), so weekly/one-off tasks are honored.
        """
        pet_name = pet.name if isinstance(pet, Pet) else pet
        result = self.list_all_tasks()
        if pet_name is not None:
            result = [t for t in result if t.pet_name == pet_name]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        if due_on is not None:
            result = [t for t in result if t.is_due_on(due_on)]
        return result

    def tasks_for_pet(self, pet: "Pet | str") -> list[Task]:
        """All tasks belonging to one pet (by Pet object or name)."""
        return self.filter_tasks(pet=pet)

    def completed_tasks(self) -> list[Task]:
        """All finished tasks across every pet."""
        return self.filter_tasks(completed=True)

    def due_tasks(self, today: date | None = None) -> list[Task]:
        """Open tasks that are actually due on `today` (recurrence-aware)."""
        return self.filter_tasks(completed=False, due_on=today)

    def tasks_by_time(self) -> list[Task]:
        """All tasks ordered chronologically (anchored first, then flexible)."""
        return sort_by_time(self.list_all_tasks())

    def find_conflicts(
        self, today: date | None = None
    ) -> list[tuple[Task, Task]]:
        """Return pairs of open, due, anchored tasks whose fixed times overlap.

        Only tasks with a preferred_time can conflict. Completed tasks and
        tasks not due on `today` are ignored. Runs a sort-then-sweep so it's
        O(n log n) rather than checking every pair.
        """
        anchored = sorted(
            (t for t in self.due_tasks(today) if t.preferred_time is not None),
            key=lambda t: t.start_minutes(),
        )
        conflicts: list[tuple[Task, Task]] = []
        for i, task in enumerate(anchored):
            for later in anchored[i + 1:]:
                # Sorted by start: once a later task starts at/after this one
                # ends, no further task can overlap it — stop early.
                if later.start_minutes() >= task.end_minutes():
                    break
                conflicts.append((task, later))
        return conflicts


@dataclass
class ScheduledSlot:
    """One task placed on the clock."""

    task: Task
    start_time: time
    end_time: time

    def formatted(self) -> str:
        """e.g. '08:00 — Morning walk (30 min) [high]'."""
        who = f" for {self.task.pet_name}" if self.task.pet_name else ""
        return (
            f"{self.start_time.strftime('%H:%M')} — {self.task.description}{who} "
            f"({self.task.duration_minutes} min) [{self.task.priority.name.lower()}]"
        )

    def overlaps(self, other: "ScheduledSlot") -> bool:
        """True if this slot's time range intersects `other`'s (half-open)."""
        s1, e1 = minutes_since_midnight(self.start_time), minutes_since_midnight(self.end_time)
        s2, e2 = minutes_since_midnight(other.start_time), minutes_since_midnight(other.end_time)
        return s1 < e2 and s2 < e1


@dataclass
class DailyPlan:
    """The result the scheduler returns: what got in, what didn't, and why."""

    slots: list[ScheduledSlot] = field(default_factory=list)
    skipped: list[tuple[Task, str]] = field(default_factory=list)
    total_minutes_used: int = 0
    # Overlapping scheduled slots, each tagged same_pet=True/False. Normally
    # empty (the Scheduler avoids overlaps); populated as a validation signal.
    overlaps: list[tuple[ScheduledSlot, ScheduledSlot, bool]] = field(default_factory=list)

    def explain(self) -> str:
        """Human-readable 'why this plan' text."""
        lines: list[str] = []
        if self.slots:
            lines.append("Scheduled (highest priority first, earliest fitting slot):")
            for slot in self.slots:
                lines.append(f"  {slot.formatted()}")
            lines.append(f"Total time used: {self.total_minutes_used} min.")
        else:
            lines.append("No tasks could be scheduled.")
        if self.skipped:
            lines.append("")
            lines.append("Skipped:")
            for task, reason in self.skipped:
                lines.append(f"  {task.description} — {reason}")
        if self.overlaps:
            lines.append("")
            lines.append("⚠️  Time conflicts detected:")
            for a, b, same_pet in self.overlaps:
                scope = (f"same pet ({a.task.pet_name})" if same_pet
                         else f"different pets ({a.task.pet_name} & {b.task.pet_name})")
                lines.append(
                    f"  {a.task.description} and {b.task.description} overlap "
                    f"at {a.start_time.strftime('%H:%M')} — {scope}"
                )
        return "\n".join(lines)

    def conflict_warning(self) -> str:
        """One-line warning summarizing overlapping slots, or '' if none.

        A compact companion to explain(), meant for UIs (st.warning, a banner).
        Guaranteed not to raise — safe to call on any plan, so callers can show
        a warning instead of crashing.
        """
        try:
            if not self.overlaps:
                return ""
            parts = []
            for a, b, same_pet in self.overlaps:
                scope = (f"same pet: {a.task.pet_name}" if same_pet
                         else f"different pets: {a.task.pet_name} & {b.task.pet_name}")
                parts.append(
                    f"{a.task.description} & {b.task.description} "
                    f"at {a.start_time.strftime('%H:%M')} ({scope})"
                )
            count = len(self.overlaps)
            plural = "s" if count != 1 else ""
            return f"⚠️ {count} time conflict{plural} — " + "; ".join(parts)
        except Exception:
            return "⚠️ Could not summarize time conflicts."

    def to_table(self) -> list[dict]:
        """Format slots for Streamlit's st.table."""
        return [
            {
                "Time": f"{s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}",
                "Task": s.task.description,
                "Pet": s.task.pet_name,
                "Duration (min)": s.task.duration_minutes,
                "Priority": s.task.priority.name.lower(),
            }
            for s in self.slots
        ]


class Scheduler:
    """The brain: takes an Owner's tasks + constraints, produces a DailyPlan.

    Placement strategy:
      1. Tasks with a preferred_time are placed FIRST, as fixed anchors.
      2. Remaining flexible tasks fill the gaps, ordered by sort_tasks()
         (priority high -> low, then shortest duration first).
      3. A task is skipped if no free gap large enough remains in the day
         window, or its preferred slot collides with an already-placed
         anchor / falls outside that window.

    The day is modeled as a single availability window [day_start, day_end].
    That window is the one source of truth for placement: a flexible task is
    placed wherever the earliest large-enough gap is, and skipped only when no
    such gap exists. (Earlier drafts also tracked a separate "available_minutes"
    budget, which could double-count and wrongly skip tasks that actually fit a
    gap; the window subsumes it.)
    """

    def __init__(self, owner: Owner, today: date | None = None) -> None:
        """Snapshot the owner's tasks and scheduling constraints.

        `today` (optional) enables recurrence filtering: weekly/one-off tasks
        that aren't due today are left out of the plan. Omit it to plan every
        task regardless of the calendar (the original behavior).
        """
        self.owner = owner
        self.tasks = owner.list_all_tasks()
        self.available_minutes = owner.available_minutes
        self.day_start = owner.day_start
        self.today = today
        # Window end: use the owner's explicit end if given, otherwise derive
        # it from day_start + available_minutes for backwards compatibility.
        if owner.day_end is not None:
            self.day_end = owner.day_end
        else:
            self.day_end = time_from_minutes(
                minutes_since_midnight(owner.day_start) + owner.available_minutes
            )

    def _sorted(self, tasks: list[Task]) -> list[Task]:
        """Priority high->low, then shortest duration first (stable)."""
        return sorted(tasks, key=lambda t: (-t.priority.weight(), t.duration_minutes))

    def sort_tasks(self) -> list[Task]:
        """Order all incomplete, currently-due tasks by priority, then duration."""
        return self._sorted(
            [t for t in self.tasks if not t.completed and t.is_due_on(self.today)]
        )

    def build_plan(self) -> DailyPlan:
        """Place anchored tasks, then fill remaining time with flexible ones."""
        plan = DailyPlan()
        day_start = minutes_since_midnight(self.day_start)
        day_end = minutes_since_midnight(self.day_end)

        pending = [
            t for t in self.tasks if not t.completed and t.is_due_on(self.today)
        ]
        anchored = sorted(
            (t for t in pending if t.preferred_time is not None),
            key=lambda t: minutes_since_midnight(t.preferred_time),
        )
        flexible = self._sorted([t for t in pending if t.preferred_time is None])

        placed: list[ScheduledSlot] = []
        used = 0

        # 1) Fixed-time anchors.
        for task in anchored:
            start = minutes_since_midnight(task.preferred_time)
            end = start + task.duration_minutes
            if start < day_start or end > day_end:
                plan.skipped.append(
                    (task, f"preferred time {task.preferred_time.strftime('%H:%M')} "
                           f"is outside the available window")
                )
                continue
            if self._has_conflict(start, task.duration_minutes, placed):
                plan.skipped.append((task, "preferred time conflicts with another task"))
                continue
            self._insert_sorted(placed, self._place_task(task, start))
            used += task.duration_minutes

        # 2) Flexible tasks fill the earliest free gap in the day window.
        for task in flexible:
            start = self._earliest_free(day_start, day_end, task.duration_minutes, placed)
            if start is None:
                plan.skipped.append((task, self._skip_reason(task, day_start, day_end)))
                continue
            self._insert_sorted(placed, self._place_task(task, start))
            used += task.duration_minutes

        # `placed` is kept in start-time order as slots are inserted, so no
        # final sort is needed here.
        plan.slots = placed
        plan.total_minutes_used = used
        plan.overlaps = self.detect_overlaps(plan)
        return plan

    def detect_overlaps(
        self, plan: DailyPlan
    ) -> list[tuple[ScheduledSlot, ScheduledSlot, bool]]:
        """Find scheduled slots whose times collide, tagged same-pet or not.

        Returns (slot_a, slot_b, same_pet) for every overlapping pair, where
        same_pet is True when both tasks belong to the same pet and False when
        they belong to different pets. Runs a sort-then-sweep (O(n log n)): once
        a later slot starts at/after the current one ends, nothing further can
        overlap it, so the inner loop breaks early.

        The Scheduler places tasks on a single timeline, so a well-formed plan
        has no overlaps; a non-empty result flags a scheduling bug or a plan
        assembled/edited outside build_plan.
        """
        slots = sorted(plan.slots, key=lambda s: minutes_since_midnight(s.start_time))
        overlaps: list[tuple[ScheduledSlot, ScheduledSlot, bool]] = []
        for i, slot in enumerate(slots):
            slot_end = minutes_since_midnight(slot.end_time)
            for other in slots[i + 1:]:
                if minutes_since_midnight(other.start_time) >= slot_end:
                    break  # sorted by start: no later slot can overlap this one
                same_pet = slot.task.pet_name == other.task.pet_name
                overlaps.append((slot, other, same_pet))
        return overlaps

    def conflict_warning(self, today: date | None = None) -> str:
        """Lightweight pre-schedule check: warn about clashing fixed-time tasks.

        Looks at the owner's open, due, anchored tasks (no full plan needed) and
        returns a human-readable warning naming each overlapping pair, tagged
        same-pet / different-pets — or '' when there are no conflicts.

        This is deliberately defensive: it never raises. On any unexpected data
        it returns a generic warning string instead of propagating an exception,
        so a caller can surface a message rather than crash.
        """
        try:
            pairs = self.owner.find_conflicts(today)
        except Exception:
            return "⚠️ Could not check for time conflicts."
        if not pairs:
            return ""
        parts = []
        for a, b in pairs:
            same_pet = a.pet_name == b.pet_name
            scope = (f"same pet: {a.pet_name}" if same_pet
                     else f"different pets: {a.pet_name} & {b.pet_name}")
            when = a.preferred_time.strftime("%H:%M") if a.preferred_time else "?"
            parts.append(f"{a.description} & {b.description} at {when} ({scope})")
        count = len(pairs)
        plural = "s" if count != 1 else ""
        return f"⚠️ {count} time conflict{plural} — " + "; ".join(parts)

    def _place_task(self, task: Task, start_minutes: int) -> ScheduledSlot:
        """Assign a start/end time to a task starting at start_minutes (since midnight)."""
        start = time_from_minutes(start_minutes)
        end = time_from_minutes(start_minutes + task.duration_minutes)
        return ScheduledSlot(task=task, start_time=start, end_time=end)

    @staticmethod
    def _slot_start(slot: ScheduledSlot) -> int:
        """Start of a slot in minutes-past-midnight (the sort key for `placed`)."""
        return minutes_since_midnight(slot.start_time)

    def _insert_sorted(self, placed: list[ScheduledSlot], slot: ScheduledSlot) -> None:
        """Insert `slot` into `placed`, keeping it ordered by start time.

        Maintaining the invariant on insertion (O(n) shift) means _earliest_free
        and _has_conflict can consume `placed` directly instead of re-sorting it
        on every call.
        """
        bisect.insort(placed, slot, key=self._slot_start)

    def _has_conflict(self, start_minutes: int, duration: int, placed: list[ScheduledSlot]) -> bool:
        """True if [start, start+duration) overlaps any already-placed slot.

        Assumes `placed` is sorted by start time (see _insert_sorted): once a
        slot starts at/after our end, no later slot can overlap, so we stop.
        """
        end_minutes = start_minutes + duration
        for slot in placed:
            slot_start = minutes_since_midnight(slot.start_time)
            if slot_start >= end_minutes:
                break  # sorted by start: nothing further can overlap us
            if start_minutes < minutes_since_midnight(slot.end_time):
                return True
        return False

    def _earliest_free(
        self, day_start: int, day_end: int, duration: int, placed: list[ScheduledSlot]
    ) -> int | None:
        """Earliest start (minutes) where `duration` fits without a conflict, else None.

        Expects `placed` already sorted by start time (see _insert_sorted), so no
        sort happens here — this is a single O(n) sweep.
        """
        busy = [
            (minutes_since_midnight(s.start_time), minutes_since_midnight(s.end_time))
            for s in placed
        ]
        cursor = day_start
        for busy_start, busy_end in busy:
            # Is the gap between `cursor` and this busy block big enough?
            if cursor + duration <= busy_start:
                return cursor
            cursor = max(cursor, busy_end)  # otherwise jump past the block
        if cursor + duration <= day_end:
            return cursor
        return None

    def _skip_reason(self, task: Task, day_start: int, day_end: int) -> str:
        """Explain why a flexible task found no home in the day window."""
        window = day_end - day_start
        if task.duration_minutes > window:
            return (
                f"needs {task.duration_minutes} min but the whole day window "
                f"is only {window} min"
            )
        return "no free time slot large enough remains in the day window"

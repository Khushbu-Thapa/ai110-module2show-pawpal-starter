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

from dataclasses import dataclass, field
from datetime import time
from enum import Enum


def minutes_since_midnight(t: time) -> int:
    """Convert a time to an int count of minutes past 00:00."""
    return t.hour * 60 + t.minute


def time_from_minutes(minutes: int) -> time:
    """Convert minutes-past-midnight back to a time (capped at 23:59)."""
    minutes = max(0, min(minutes, 23 * 60 + 59))
    return time(minutes // 60, minutes % 60)


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
            completed=bool(data.get("completed", False)),
        )

    def is_higher_priority_than(self, other: "Task") -> bool:
        """True if this task outranks `other` by priority."""
        return self.priority.weight() > other.priority.weight()

    def fits_in(self, remaining_minutes: int) -> bool:
        """True if this task's duration fits in the time left."""
        return self.duration_minutes <= remaining_minutes

    def mark_complete(self) -> None:
        """Mark this task complete so the scheduler stops planning it."""
        self.completed = True

    def mark_undone(self) -> None:
        """Reopen a completed task."""
        self.completed = False


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

    def list_all_tasks(self) -> list[Task]:
        """Gather tasks across all pets (each already tagged with pet_name)."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks

    def pending_tasks(self) -> list[Task]:
        """All not-yet-completed tasks across every pet."""
        return [t for t in self.list_all_tasks() if not t.completed]


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


@dataclass
class DailyPlan:
    """The result the scheduler returns: what got in, what didn't, and why."""

    slots: list[ScheduledSlot] = field(default_factory=list)
    skipped: list[tuple[Task, str]] = field(default_factory=list)
    total_minutes_used: int = 0

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
        return "\n".join(lines)

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
      3. A task is skipped if it doesn't fit the remaining time OR its
         preferred slot collides with an already-placed anchor / falls
         outside the available window.
    """

    def __init__(self, owner: Owner) -> None:
        """Snapshot the owner's tasks and scheduling constraints."""
        self.owner = owner
        self.tasks = owner.list_all_tasks()
        self.available_minutes = owner.available_minutes
        self.day_start = owner.day_start

    def _sorted(self, tasks: list[Task]) -> list[Task]:
        """Priority high->low, then shortest duration first (stable)."""
        return sorted(tasks, key=lambda t: (-t.priority.weight(), t.duration_minutes))

    def sort_tasks(self) -> list[Task]:
        """Order all incomplete tasks by priority, then duration."""
        return self._sorted([t for t in self.tasks if not t.completed])

    def build_plan(self) -> DailyPlan:
        """Place anchored tasks, then fill remaining time with flexible ones."""
        plan = DailyPlan()
        day_start = minutes_since_midnight(self.day_start)
        day_end = day_start + self.available_minutes

        pending = [t for t in self.tasks if not t.completed]
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
            placed.append(self._place_task(task, start))
            used += task.duration_minutes

        # 2) Flexible tasks fill the earliest free gap.
        for task in flexible:
            remaining = self.available_minutes - used
            start = self._earliest_free(day_start, day_end, task.duration_minutes, placed)
            if start is None or not task.fits_in(remaining):
                plan.skipped.append((task, self._skip_reason(task, remaining)))
                continue
            placed.append(self._place_task(task, start))
            used += task.duration_minutes

        placed.sort(key=lambda s: minutes_since_midnight(s.start_time))
        plan.slots = placed
        plan.total_minutes_used = used
        return plan

    def _place_task(self, task: Task, start_minutes: int) -> ScheduledSlot:
        """Assign a start/end time to a task starting at start_minutes (since midnight)."""
        start = time_from_minutes(start_minutes)
        end = time_from_minutes(start_minutes + task.duration_minutes)
        return ScheduledSlot(task=task, start_time=start, end_time=end)

    def _has_conflict(self, start_minutes: int, duration: int, placed: list[ScheduledSlot]) -> bool:
        """True if [start, start+duration) overlaps any already-placed slot."""
        end_minutes = start_minutes + duration
        for slot in placed:
            slot_start = minutes_since_midnight(slot.start_time)
            slot_end = minutes_since_midnight(slot.end_time)
            if start_minutes < slot_end and slot_start < end_minutes:
                return True
        return False

    def _earliest_free(
        self, day_start: int, day_end: int, duration: int, placed: list[ScheduledSlot]
    ) -> int | None:
        """Earliest start (minutes) where `duration` fits without a conflict, else None."""
        busy = sorted(
            (minutes_since_midnight(s.start_time), minutes_since_midnight(s.end_time))
            for s in placed
        )
        cursor = day_start
        for busy_start, busy_end in busy:
            if cursor + duration <= busy_start:
                return cursor
            cursor = max(cursor, busy_end)
        if cursor + duration <= day_end:
            return cursor
        return None

    def _skip_reason(self, task: Task, remaining_minutes: int) -> str:
        """Explain why a task was left out, given the time remaining when reached."""
        if remaining_minutes < task.duration_minutes:
            return (
                f"not enough time left ({remaining_minutes} min free, "
                f"needs {task.duration_minutes} min)"
            )
        return "no free time slot available in the day window"

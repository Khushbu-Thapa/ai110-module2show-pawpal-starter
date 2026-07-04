"""PawPal+ command-line demo.

Builds an owner with two pets and several care tasks — deliberately added out
of chronological order — then shows off the sorting, filtering, and scheduling
methods before printing today's generated schedule. Run with:  python main.py

Output formatting (Challenge 4) uses:
  - `tabulate` for structured, boxed CLI tables.
  - emojis for different task types (🚶 walk, 🍽️ feeding, 💊 meds ...).
  - color-coded priority indicators (🔴 High / 🟡 Medium / 🟢 Low).
"""

from datetime import time

from tabulate import tabulate

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

DATA_FILE = "data.json"

# --- Challenge 4: output formatting maps ------------------------------------
# Task-type emoji, chosen by a keyword found in the task description.
TASK_EMOJI = {
    "walk": "🚶",
    "feed": "🍽️",
    "med": "💊",
    "groom": "✂️",
    "play": "🎾",
    "enrich": "🧩",
    "vet": "🏥",
    "train": "🎓",
    "bath": "🛁",
}

# Color-coded priority indicators (a colored circle survives in plain text,
# unlike raw ANSI codes, so it reads cleanly in the README too).
PRIORITY_ICON = {
    Priority.HIGH: "🔴 High",
    Priority.MEDIUM: "🟡 Medium",
    Priority.LOW: "🟢 Low",
}


def task_emoji(description: str) -> str:
    """Pick an emoji for a task by matching a keyword in its description."""
    text = description.lower()
    for keyword, emoji in TASK_EMOJI.items():
        if keyword in text:
            return emoji
    return "🐾"  # default paw for anything uncategorized


def build_demo_owner() -> Owner:
    """Create a sample owner with two pets and tasks added OUT OF ORDER.

    The anchored (fixed-time) tasks are intentionally inserted with their
    times shuffled (9:00, then 8:00, then 8:30) so the sorting methods have
    something real to reorder.
    """
    owner = Owner(name="Jordan", available_minutes=120, day_start=time(8, 0))

    mochi = Pet(name="Mochi", species="dog")
    biscuit = Pet(name="Biscuit", species="cat")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    # --- Added out of chronological order on purpose ---
    owner.add_task(
        biscuit,
        Task(description="Feeding", duration_minutes=10, priority=Priority.HIGH,
             preferred_time=time(9, 0)),          # 9:00 added first
    )
    owner.add_task(
        mochi,
        Task(description="Feeding", duration_minutes=10, priority=Priority.HIGH,
             preferred_time=time(8, 0)),          # 8:00 added second
    )
    owner.add_task(
        mochi,
        Task(description="Vet visit", duration_minutes=20, priority=Priority.MEDIUM,
             preferred_time=time(8, 30)),         # 8:30 added third
    )
    # Flexible tasks (no fixed time) — the scheduler slots these into gaps.
    owner.add_task(
        mochi,
        Task(description="Morning walk", duration_minutes=30, priority=Priority.HIGH),
    )
    owner.add_task(
        mochi,
        Task(description="Grooming", duration_minutes=40, priority=Priority.LOW),
    )
    owner.add_task(
        biscuit,
        Task(description="Enrichment play", duration_minutes=20, priority=Priority.MEDIUM),
    )
    # Deliberate clash: two tasks scheduled at the SAME time. Biscuit's meds
    # are set to 09:00 — exactly when its feeding is — so the conflict pre-check
    # has an unambiguous same-time collision to warn about.
    owner.add_task(
        biscuit,
        Task(description="Medication", duration_minutes=10, priority=Priority.MEDIUM,
             preferred_time=time(9, 0)),
    )

    # Mark one task done so the status filters have something to separate.
    mochi.tasks[0].mark_complete()  # Mochi's 8:00 Feeding is already done

    return owner


def task_row(task: Task) -> list[str]:
    """One task as a table row: time, emoji+name, pet, priority icon, status."""
    when = task.preferred_time.strftime("%H:%M") if task.preferred_time else "—"
    status = "✅ done" if task.completed else "⏳ pending"
    return [
        when,
        f"{task_emoji(task.description)} {task.description}",
        task.pet_name,
        PRIORITY_ICON[task.priority],
        status,
    ]


def print_task_table(title: str, tasks: list[Task]) -> None:
    """Print a titled, boxed table of tasks (or a placeholder if empty)."""
    print(f"\n{title}")
    if not tasks:
        print("  (none)")
        return
    print(
        tabulate(
            [task_row(t) for t in tasks],
            headers=["Time", "Task", "Pet", "Priority", "Status"],
            tablefmt="rounded_grid",
        )
    )


def print_schedule(plan, owner: Owner) -> None:
    """Print the generated plan as a boxed schedule table plus skip reasons."""
    print(
        f"\nToday's schedule (day starts {owner.day_start.strftime('%H:%M')}, "
        f"{owner.available_minutes} min available)"
    )
    if plan.slots:
        rows = [
            [
                f"{s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}",
                f"{task_emoji(s.task.description)} {s.task.description}",
                s.task.pet_name,
                f"{s.task.duration_minutes} min",
                PRIORITY_ICON[s.task.priority],
            ]
            for s in plan.slots
        ]
        print(
            tabulate(
                rows,
                headers=["Time", "Task", "Pet", "Duration", "Priority"],
                tablefmt="rounded_grid",
            )
        )
        print(f"Total time used: {plan.total_minutes_used} min.")
    else:
        print("  No tasks could be scheduled.")

    if plan.skipped:
        print("\nSkipped:")
        for task, reason in plan.skipped:
            print(f"  {task_emoji(task.description)} {task.description} — {reason}")


def main() -> None:
    """Show tasks as added, then via sorting/filtering, then the schedule."""
    owner = build_demo_owner()

    print(f"🐾 PawPal+ demo for {owner.name}")
    print("=" * 50)

    # 1) As entered — deliberately out of order.
    print_task_table("Tasks as added (unsorted)", owner.list_all_tasks())

    # 2) Sorting: chronological via tasks_by_time().
    print_task_table("Sorted by time (tasks_by_time)", owner.tasks_by_time())

    # 3) Challenge 3 — priority FIRST, then time.
    scheduler = Scheduler(owner)
    print_task_table(
        "Sorted by priority, then time (sort_by_priority_then_time)",
        scheduler.sort_by_priority_then_time(),
    )

    # 4) Filtering by pet name and by completion status.
    print_task_table("Filtered to Mochi (tasks_for_pet)", owner.tasks_for_pet("Mochi"))
    print_task_table("Pending only (pending_tasks)", owner.pending_tasks())

    # 5) Lightweight conflict pre-check (never crashes; returns a message).
    warning = scheduler.conflict_warning()
    print("\nConflict check")
    print(f"  {warning}" if warning else "  No time conflicts detected.")

    # 6) The generated schedule (completed tasks are excluded automatically).
    print("=" * 50)
    plan = scheduler.build_plan()
    print_schedule(plan, owner)

    # 7) Challenge 1 — "next available slot" query for a hypothetical new task.
    for minutes in (15, 90):
        slot = Scheduler(owner).next_available_slot(minutes)
        when = slot.strftime("%H:%M") if slot else "no room left today"
        print(f"\n🔎 Earliest free slot for a {minutes}-min task: {when}")

    # 8) Challenge 2 — persistence: save to data.json and reload it.
    owner.save_to_json(DATA_FILE)
    reloaded = Owner.load_from_json(DATA_FILE)
    print(
        f"\n💾 Saved {len(owner.pets)} pets / {len(owner.list_all_tasks())} tasks "
        f"to {DATA_FILE}; reloaded {len(reloaded.pets)} pets / "
        f"{len(reloaded.list_all_tasks())} tasks — data persists between runs."
    )


if __name__ == "__main__":
    main()

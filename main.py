"""PawPal+ command-line demo.

Builds an owner with two pets and several care tasks — deliberately added out
of chronological order — then shows off the sorting and filtering methods
before printing today's generated schedule. Run with:  python main.py
"""

from datetime import time

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


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


def format_task(task: Task) -> str:
    """One-line human summary of a task, e.g. '08:00  Feeding (Mochi) [high]'."""
    when = task.preferred_time.strftime("%H:%M") if task.preferred_time else "  —  "
    done = " ✅" if task.completed else ""
    return (f"{when}  {task.description} ({task.pet_name}) "
            f"[{task.priority.name.lower()}]{done}")


def print_section(title: str, tasks: list[Task]) -> None:
    """Print a titled block of task lines (or a placeholder if empty)."""
    print(f"\n{title}")
    print("-" * len(title))
    if not tasks:
        print("  (none)")
        return
    for task in tasks:
        print(f"  {format_task(task)}")


def main() -> None:
    """Show tasks as added, then via sorting/filtering, then the schedule."""
    owner = build_demo_owner()

    print(f"🐾 PawPal+ demo for {owner.name}")
    print("=" * 50)

    # 1) As entered — deliberately out of order.
    print_section("Tasks as added (unsorted)", owner.list_all_tasks())

    # 2) Sorting: chronological via tasks_by_time().
    print_section("Sorted by time (tasks_by_time)", owner.tasks_by_time())

    # 3) Filtering by pet name.
    print_section("Filtered to Mochi (tasks_for_pet)", owner.tasks_for_pet("Mochi"))

    # 4) Filtering by completion status.
    print_section("Pending only (pending_tasks)", owner.pending_tasks())
    print_section("Completed only (completed_tasks)", owner.completed_tasks())

    # 5) Lightweight conflict pre-check (never crashes; returns a message).
    scheduler = Scheduler(owner)
    warning = scheduler.conflict_warning()
    print("\nConflict check")
    print("-" * len("Conflict check"))
    print(f"  {warning}" if warning else "  No time conflicts detected.")

    # 6) The generated schedule (completed tasks are excluded automatically).
    plan = scheduler.build_plan()
    print(f"\nToday's schedule (day starts {owner.day_start.strftime('%H:%M')}, "
          f"{owner.available_minutes} min available)")
    print("=" * 50)
    print(plan.explain())


if __name__ == "__main__":
    main()

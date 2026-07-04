"""Simple unit tests for the PawPal+ core system."""

from datetime import date, time

from pawpal_system import (
    DailyPlan,
    Owner,
    Pet,
    Priority,
    ScheduledSlot,
    Scheduler,
    Task,
    sort_by_priority_then_time,
    sort_by_time,
)


def make_task(description="Walk", duration=30, priority=Priority.MEDIUM):
    """Small helper to build a Task with sensible defaults."""
    return Task(description=description, duration_minutes=duration, priority=priority)


def test_mark_complete_changes_status():
    """Task Completion: marking a task done flips its status to complete."""
    task = make_task()
    assert task.completed is False  # starts incomplete

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Task Addition: adding a task to a Pet grows that pet's task count by one."""
    pet = Pet(name="Rex", species="dog")
    assert len(pet.get_tasks()) == 0  # no tasks yet

    pet.add_task(make_task())

    assert len(pet.get_tasks()) == 1


# --- Window model (#1/#2): the day window is the single source of truth -------

def test_flexible_task_fits_a_gap_left_by_a_late_anchor():
    """A flexible task is placed in a real gap instead of being wrongly skipped.

    Owner has 60 available minutes but an explicit window of 08:00–12:00 (much
    wider). A 30-min flexible task should land in the open morning gap even
    though it exceeds the old available_minutes 'budget'.
    """
    owner = Owner(name="Sam", available_minutes=60, day_start=time(8, 0),
                  day_end=time(12, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    owner.add_task(pet, Task(description="Late feed", duration_minutes=10,
                             priority=Priority.HIGH, preferred_time=time(11, 30)))
    owner.add_task(pet, Task(description="Walk", duration_minutes=30,
                             priority=Priority.MEDIUM))

    plan = Scheduler(owner).build_plan()

    scheduled = {s.task.description for s in plan.slots}
    assert scheduled == {"Late feed", "Walk"}
    assert plan.skipped == []


def test_task_longer_than_window_is_skipped_with_reason():
    """A task that can't fit the whole window is skipped with a clear reason."""
    owner = Owner(name="Sam", available_minutes=30, day_start=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    owner.add_task(pet, Task(description="Long hike", duration_minutes=90,
                             priority=Priority.HIGH))

    plan = Scheduler(owner).build_plan()

    assert plan.slots == []
    assert len(plan.skipped) == 1
    task, reason = plan.skipped[0]
    assert task.description == "Long hike"
    assert "90 min" in reason


# --- Recurrence (#7): due-today filtering ------------------------------------

def test_weekly_task_only_due_on_its_weekday():
    """A weekly task appears only on its configured weekday."""
    task = Task(description="Bath", duration_minutes=20, priority=Priority.LOW,
                recurrence="weekly", weekday=5)  # Saturday
    saturday = date(2026, 7, 4)   # a Saturday
    sunday = date(2026, 7, 5)     # a Sunday
    assert task.is_due_on(saturday) is True
    assert task.is_due_on(sunday) is False


def test_once_task_not_due_after_completion():
    """A one-off task stops being due once completed."""
    task = Task(description="Vet visit", duration_minutes=60,
                priority=Priority.MEDIUM, recurrence="once")
    assert task.is_due_on() is True
    task.mark_complete()
    assert task.is_due_on() is False


def test_scheduler_excludes_tasks_not_due_today():
    """Scheduler(today=...) leaves out weekly tasks that aren't due."""
    owner = Owner(name="Sam", available_minutes=120, day_start=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    owner.add_task(pet, Task(description="Daily walk", duration_minutes=30,
                             priority=Priority.HIGH))
    owner.add_task(pet, Task(description="Weekly bath", duration_minutes=20,
                             priority=Priority.LOW, recurrence="weekly", weekday=5))

    sunday = date(2026, 7, 5)
    plan = Scheduler(owner, today=sunday).build_plan()

    scheduled = {s.task.description for s in plan.slots}
    assert scheduled == {"Daily walk"}


# --- Sorting tasks by time ---------------------------------------------------

def test_sort_by_time_orders_anchored_then_flexible():
    """Anchored tasks come first by start time; flexible ones keep input order."""
    late = Task(description="Late", duration_minutes=10, priority=Priority.LOW,
                preferred_time=time(10, 0))
    early = Task(description="Early", duration_minutes=10, priority=Priority.LOW,
                 preferred_time=time(8, 0))
    flex_a = Task(description="FlexA", duration_minutes=10, priority=Priority.LOW)
    flex_b = Task(description="FlexB", duration_minutes=10, priority=Priority.LOW)

    ordered = [t.description for t in sort_by_time([late, flex_a, early, flex_b])]

    assert ordered == ["Early", "Late", "FlexA", "FlexB"]


def test_sort_by_time_tiebreaks_by_priority_then_duration():
    """Same start time -> higher priority first, then shorter duration."""
    low = Task(description="Low", duration_minutes=10, priority=Priority.LOW,
               preferred_time=time(9, 0))
    high_long = Task(description="HighLong", duration_minutes=40,
                     priority=Priority.HIGH, preferred_time=time(9, 0))
    high_short = Task(description="HighShort", duration_minutes=15,
                      priority=Priority.HIGH, preferred_time=time(9, 0))

    ordered = [t.description for t in sort_by_time([low, high_long, high_short])]

    assert ordered == ["HighShort", "HighLong", "Low"]


# --- Filtering by pet / status -----------------------------------------------

def _owner_with_two_pets():
    owner = Owner(name="Sam")
    dog = Pet(name="Rex", species="dog")
    cat = Pet(name="Milo", species="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    owner.add_task(dog, Task(description="Walk", duration_minutes=30,
                             priority=Priority.HIGH))
    done = Task(description="Feed dog", duration_minutes=10, priority=Priority.HIGH)
    done.mark_complete()
    owner.add_task(dog, done)
    owner.add_task(cat, Task(description="Litter", duration_minutes=10,
                             priority=Priority.MEDIUM))
    return owner, dog, cat


def test_filter_tasks_by_pet():
    """tasks_for_pet returns only that pet's tasks (by object or name)."""
    owner, dog, _cat = _owner_with_two_pets()
    assert {t.description for t in owner.tasks_for_pet(dog)} == {"Walk", "Feed dog"}
    assert {t.description for t in owner.tasks_for_pet("Milo")} == {"Litter"}


def test_filter_tasks_by_status():
    """completed / pending filters split tasks by completion status."""
    owner, _dog, _cat = _owner_with_two_pets()
    assert {t.description for t in owner.completed_tasks()} == {"Feed dog"}
    assert {t.description for t in owner.pending_tasks()} == {"Walk", "Litter"}


def test_filter_tasks_combines_pet_and_status():
    """filter_tasks applies pet and status filters together."""
    owner, dog, _cat = _owner_with_two_pets()
    result = owner.filter_tasks(pet=dog, completed=False)
    assert {t.description for t in result} == {"Walk"}


# --- Basic conflict detection ------------------------------------------------

def test_find_conflicts_detects_overlapping_anchors():
    """Two fixed-time tasks that overlap are reported as a conflict."""
    owner = Owner(name="Sam")
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    a = Task(description="Vet call", duration_minutes=30, priority=Priority.HIGH,
             preferred_time=time(9, 0))     # 09:00–09:30
    b = Task(description="Grooming", duration_minutes=30, priority=Priority.LOW,
             preferred_time=time(9, 15))    # 09:15–09:45 -> overlaps a
    c = Task(description="Walk", duration_minutes=30, priority=Priority.MEDIUM,
             preferred_time=time(10, 0))    # 10:00–10:30 -> no overlap
    for t in (a, b, c):
        owner.add_task(pet, t)

    conflicts = owner.find_conflicts()

    assert len(conflicts) == 1
    descs = {conflicts[0][0].description, conflicts[0][1].description}
    assert descs == {"Vet call", "Grooming"}


def test_find_conflicts_ignores_flexible_and_completed():
    """Flexible tasks and completed tasks never register as conflicts."""
    owner = Owner(name="Sam")
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    anchored = Task(description="Vet call", duration_minutes=30,
                    priority=Priority.HIGH, preferred_time=time(9, 0))
    flexible = Task(description="Play", duration_minutes=30, priority=Priority.LOW)
    done = Task(description="Old appt", duration_minutes=30, priority=Priority.LOW,
                preferred_time=time(9, 10))
    done.mark_complete()
    for t in (anchored, flexible, done):
        owner.add_task(pet, t)

    assert owner.find_conflicts() == []


# --- Recurring roll-over: completing a repeat spawns the next occurrence ------

def test_next_occurrence_recurring_returns_fresh_copy():
    """A daily/weekly task yields a fresh, incomplete copy for next time."""
    daily = Task(description="Walk", duration_minutes=30, priority=Priority.HIGH,
                 preferred_time=time(8, 0), recurrence="daily")
    daily.mark_complete()

    nxt = daily.next_occurrence()

    assert nxt is not None
    assert nxt is not daily            # a new instance, not the same object
    assert nxt.completed is False      # ready to schedule again
    assert nxt.description == "Walk" and nxt.preferred_time == time(8, 0)
    assert daily.completed is True     # original is left untouched


def test_next_occurrence_once_returns_none():
    """A one-off task does not recur."""
    once = Task(description="Vet visit", duration_minutes=60,
                priority=Priority.MEDIUM, recurrence="once")
    assert once.next_occurrence() is None


def test_complete_task_rolls_over_recurring_on_pet():
    """Pet.complete_task marks done AND appends the next occurrence."""
    pet = Pet(name="Rex", species="dog")
    task = Task(description="Feed", duration_minutes=10, priority=Priority.HIGH,
                recurrence="daily")
    pet.add_task(task)
    assert len(pet.get_tasks()) == 1

    upcoming = pet.complete_task(task)

    assert task.completed is True
    assert upcoming is not None and upcoming.completed is False
    assert len(pet.get_tasks()) == 2            # history + next instance
    assert upcoming.pet_name == "Rex"           # tagged to the pet


def test_complete_task_weekly_keeps_weekday():
    """A weekly roll-over preserves its weekday so it recurs on the same day."""
    pet = Pet(name="Rex", species="dog")
    task = Task(description="Bath", duration_minutes=20, priority=Priority.LOW,
                recurrence="weekly", weekday=5)
    pet.add_task(task)

    upcoming = pet.complete_task(task)

    assert upcoming.recurrence == "weekly" and upcoming.weekday == 5


def test_complete_task_once_no_rollover():
    """Completing a one-off task creates no new instance."""
    pet = Pet(name="Rex", species="dog")
    task = Task(description="Microchip", duration_minutes=15,
                priority=Priority.LOW, recurrence="once")
    pet.add_task(task)

    upcoming = pet.complete_task(task)

    assert upcoming is None
    assert len(pet.get_tasks()) == 1
    assert task.completed is True


def test_owner_complete_task_routes_to_owning_pet():
    """Owner.complete_task finds the right pet and rolls the task over."""
    owner = Owner(name="Sam")
    dog = Pet(name="Rex", species="dog")
    owner.add_pet(dog)
    task = Task(description="Walk", duration_minutes=30, priority=Priority.HIGH,
                recurrence="daily")
    owner.add_task(dog, task)

    upcoming = owner.complete_task(task)

    assert upcoming is not None and upcoming.completed is False
    assert len(dog.get_tasks()) == 2
    # The completed original stays as history; only the new one is pending.
    assert owner.pending_tasks() == [upcoming]


# --- Scheduler overlap detection (same pet vs different pets) -----------------

def _slot(desc, pet_name, start, end):
    """Build a ScheduledSlot for a task belonging to `pet_name`."""
    task = Task(description=desc, duration_minutes=(end.hour * 60 + end.minute)
                - (start.hour * 60 + start.minute), priority=Priority.MEDIUM,
                pet_name=pet_name)
    return ScheduledSlot(task=task, start_time=start, end_time=end)


def test_build_plan_produces_no_overlaps():
    """A normally-built plan places tasks on one timeline -> no overlaps."""
    owner = Owner(name="Sam", available_minutes=180, day_start=time(8, 0))
    dog = Pet(name="Rex", species="dog")
    cat = Pet(name="Milo", species="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    owner.add_task(dog, Task("Walk", 30, Priority.HIGH, preferred_time=time(8, 0)))
    owner.add_task(cat, Task("Feed", 20, Priority.HIGH, preferred_time=time(8, 15)))
    owner.add_task(dog, Task("Groom", 30, Priority.LOW))

    plan = Scheduler(owner).build_plan()

    assert plan.overlaps == []


def test_detect_overlaps_same_pet():
    """Two overlapping slots for the SAME pet are tagged same_pet=True."""
    plan = DailyPlan(slots=[
        _slot("Walk", "Rex", time(8, 0), time(8, 30)),   # 08:00–08:30
        _slot("Vet", "Rex", time(8, 15), time(8, 45)),   # 08:15–08:45 overlaps
    ])
    overlaps = Scheduler(Owner(name="Sam")).detect_overlaps(plan)

    assert len(overlaps) == 1
    a, b, same_pet = overlaps[0]
    assert same_pet is True
    assert {a.task.description, b.task.description} == {"Walk", "Vet"}


def test_detect_overlaps_different_pets():
    """Overlapping slots for DIFFERENT pets are tagged same_pet=False."""
    plan = DailyPlan(slots=[
        _slot("Walk dog", "Rex", time(9, 0), time(9, 30)),
        _slot("Bathe cat", "Milo", time(9, 10), time(9, 40)),  # overlaps
    ])
    overlaps = Scheduler(Owner(name="Sam")).detect_overlaps(plan)

    assert len(overlaps) == 1
    _a, _b, same_pet = overlaps[0]
    assert same_pet is False


def test_detect_overlaps_ignores_adjacent_slots():
    """Back-to-back slots (one ends when the next starts) do not overlap."""
    plan = DailyPlan(slots=[
        _slot("A", "Rex", time(8, 0), time(8, 30)),
        _slot("B", "Rex", time(8, 30), time(9, 0)),   # starts exactly at A's end
    ])
    assert Scheduler(Owner(name="Sam")).detect_overlaps(plan) == []


# --- Conflict WARNING messages (graceful, never crash) -----------------------

def test_scheduler_conflict_warning_reports_clash():
    """conflict_warning names overlapping fixed-time tasks (same/diff pets)."""
    owner = Owner(name="Sam")
    dog = Pet(name="Rex", species="dog")
    owner.add_pet(dog)
    owner.add_task(dog, Task("Vet", 30, Priority.HIGH, preferred_time=time(9, 0)))
    owner.add_task(dog, Task("Groom", 30, Priority.LOW, preferred_time=time(9, 15)))

    msg = Scheduler(owner).conflict_warning()

    assert msg.startswith("⚠️")
    assert "Vet" in msg and "Groom" in msg
    assert "same pet: Rex" in msg


def test_scheduler_conflict_warning_empty_when_clean():
    """No clashing fixed-time tasks -> empty string, not an error."""
    owner = Owner(name="Sam")
    dog = Pet(name="Rex", species="dog")
    owner.add_pet(dog)
    owner.add_task(dog, Task("Vet", 30, Priority.HIGH, preferred_time=time(9, 0)))
    owner.add_task(dog, Task("Walk", 30, Priority.HIGH, preferred_time=time(10, 0)))

    assert Scheduler(owner).conflict_warning() == ""


def test_conflict_warning_does_not_crash_on_bad_data():
    """A malformed owner yields a warning string, never an exception."""
    class BrokenOwner:
        def find_conflicts(self, today=None):
            raise RuntimeError("boom")

    sched = Scheduler(Owner(name="Sam"))
    sched.owner = BrokenOwner()  # simulate unexpected/broken data

    msg = sched.conflict_warning()

    assert msg == "⚠️ Could not check for time conflicts."


def test_plan_conflict_warning_from_overlaps():
    """DailyPlan.conflict_warning summarizes detected overlaps in one line."""
    plan = DailyPlan(slots=[
        _slot("Walk", "Rex", time(9, 0), time(9, 30)),
        _slot("Bathe", "Milo", time(9, 10), time(9, 40)),
    ])
    plan.overlaps = Scheduler(Owner(name="Sam")).detect_overlaps(plan)

    msg = plan.conflict_warning()

    assert msg.startswith("⚠️ 1 time conflict")
    assert "different pets: Rex & Milo" in msg


def test_plan_conflict_warning_empty_when_no_overlaps():
    """A clean plan produces no warning string."""
    plan = DailyPlan(slots=[_slot("Walk", "Rex", time(9, 0), time(9, 30))])
    assert plan.conflict_warning() == ""


# --- Rubric-required cases ---------------------------------------------------
# Three tests mapping directly to the assignment's minimum requirements:
#   1. Sorting Correctness   2. Recurrence Logic   3. Conflict Detection


def test_sorting_returns_tasks_in_chronological_order():
    """Sorting Correctness: tasks are returned in chronological (by-time) order.

    Given fixed-time tasks in scrambled input order, sort_by_time should return
    them earliest-start-first.
    """
    evening = Task("Evening walk", 30, Priority.MEDIUM, preferred_time=time(18, 0))
    breakfast = Task("Breakfast", 15, Priority.HIGH, preferred_time=time(7, 30))
    lunch = Task("Lunch", 20, Priority.LOW, preferred_time=time(12, 0))

    ordered = [t.description for t in sort_by_time([evening, breakfast, lunch])]

    assert ordered == ["Breakfast", "Lunch", "Evening walk"]


def test_completing_daily_task_creates_task_for_next_day():
    """Recurrence Logic: completing a daily task spawns the next occurrence.

    Tasks don't carry a calendar date; a daily task's "next day" is represented
    by a fresh, incomplete copy. Completing the task should mark the original as
    history and leave exactly one new incomplete daily instance ready to plan.
    """
    pet = Pet(name="Rex", species="dog")
    walk = Task("Morning walk", 30, Priority.HIGH, preferred_time=time(8, 0),
                recurrence="daily")
    pet.add_task(walk)

    nxt = pet.complete_task(walk)

    # Original becomes completed history.
    assert walk.completed is True
    # A brand-new, incomplete instance stands in for the next day's task.
    assert nxt is not None and nxt is not walk
    assert nxt.completed is False
    assert nxt.recurrence == "daily"
    assert nxt.description == "Morning walk" and nxt.preferred_time == time(8, 0)
    # The pet now holds history + exactly one pending next occurrence.
    tasks = pet.get_tasks()
    assert len(tasks) == 2
    assert [t for t in tasks if not t.completed] == [nxt]


def test_scheduler_flags_duplicate_times():
    """Conflict Detection: two tasks at the SAME fixed time are flagged.

    Both the pre-schedule check (find_conflicts / conflict_warning) and the plan
    itself should surface the clash rather than silently double-booking.
    """
    owner = Owner(name="Sam", available_minutes=120, day_start=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    owner.add_task(pet, Task("Feed", 20, Priority.HIGH, preferred_time=time(9, 0)))
    owner.add_task(pet, Task("Meds", 20, Priority.MEDIUM, preferred_time=time(9, 0)))

    # Reported as a conflict pair.
    conflicts = owner.find_conflicts()
    assert len(conflicts) == 1
    assert {conflicts[0][0].description, conflicts[0][1].description} == {"Feed", "Meds"}

    # Surfaced in the human-readable warning.
    msg = Scheduler(owner).conflict_warning()
    assert msg.startswith("⚠️")
    assert "Feed" in msg and "Meds" in msg

    # And the plan keeps only one of them, skipping the duplicate with a reason.
    plan = Scheduler(owner).build_plan()
    assert len(plan.slots) == 1
    assert len(plan.skipped) == 1
    _task, reason = plan.skipped[0]
    assert "conflicts" in reason


# --------------------------------------------------------------------------- #
# Challenge 3: priority-first sorting (priority then time)                     #
# --------------------------------------------------------------------------- #
def test_sort_by_priority_then_time_orders_priority_first():
    """A high-priority LATER task outranks a low-priority EARLIER one."""
    grooming = Task("Grooming", 40, Priority.LOW, preferred_time=time(8, 0))
    meds = Task("Meds", 10, Priority.HIGH, preferred_time=time(10, 0))
    feed = Task("Feed", 10, Priority.HIGH, preferred_time=time(8, 30))

    ordered = sort_by_priority_then_time([grooming, meds, feed])

    # Both HIGH tasks come before the LOW one, despite grooming being earliest...
    assert [t.description for t in ordered] == ["Feed", "Meds", "Grooming"]
    # ...and within the HIGH band, the earlier time (08:30 Feed) wins.


def test_sort_by_priority_then_time_anchored_before_flexible_in_band():
    """Within a priority band, anchored (timed) tasks precede flexible ones."""
    flexible = Task("Walk", 30, Priority.HIGH)  # no preferred_time
    anchored = Task("Feed", 10, Priority.HIGH, preferred_time=time(9, 0))

    ordered = sort_by_priority_then_time([flexible, anchored])

    assert [t.description for t in ordered] == ["Feed", "Walk"]


def test_scheduler_sort_by_priority_then_time_excludes_done_and_not_due():
    """The Scheduler wrapper only returns incomplete, currently-due tasks."""
    owner = Owner(name="Sam", day_start=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    owner.add_task(pet, Task("Walk", 30, Priority.HIGH))
    done = Task("Feed", 10, Priority.HIGH)
    done.mark_complete()
    owner.add_task(pet, done)
    # Weekly task due only on Wednesday (weekday 2); "today" is a Monday.
    owner.add_task(pet, Task("Vet", 20, Priority.LOW, recurrence="weekly", weekday=2))

    ordered = Scheduler(owner, today=date(2024, 1, 1)).sort_by_priority_then_time()

    assert [t.description for t in ordered] == ["Walk"]


# --------------------------------------------------------------------------- #
# Challenge 1: next available slot                                            #
# --------------------------------------------------------------------------- #
def test_next_available_slot_returns_first_gap_after_scheduled_tasks():
    """next_available_slot finds the earliest free time a new task could take."""
    owner = Owner(name="Sam", available_minutes=120, day_start=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    # A single 30-min anchor at 08:00 fills 08:00-08:30.
    owner.add_task(pet, Task("Walk", 30, Priority.HIGH, preferred_time=time(8, 0)))

    slot = Scheduler(owner).next_available_slot(20)

    assert slot == time(8, 30)


def test_next_available_slot_returns_none_when_no_room():
    """When nothing large enough is left in the window, returns None."""
    owner = Owner(name="Sam", available_minutes=60, day_start=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    owner.add_task(pet, Task("Walk", 30, Priority.HIGH))

    # Window is 08:00-09:00 (60 min); 30 used, so a 45-min task can't fit.
    assert Scheduler(owner).next_available_slot(45) is None


def test_next_available_slot_empty_day_returns_day_start():
    """With no tasks placed, the earliest slot is the start of the day."""
    owner = Owner(name="Sam", available_minutes=120, day_start=time(7, 0))
    owner.add_pet(Pet(name="Rex", species="dog"))

    assert Scheduler(owner).next_available_slot(30) == time(7, 0)


# --------------------------------------------------------------------------- #
# Challenge 2: JSON persistence (round-trip)                                  #
# --------------------------------------------------------------------------- #
def test_task_to_dict_from_dict_round_trip():
    """A Task survives serialization: enum + time restored to real objects."""
    task = Task(
        "Meds", 15, Priority.HIGH, pet_name="Rex",
        preferred_time=time(9, 30), recurrence="weekly", weekday=2, completed=True,
    )

    restored = Task.from_dict(task.to_dict())

    assert restored.description == "Meds"
    assert restored.duration_minutes == 15
    assert restored.priority is Priority.HIGH  # real enum, not the string "HIGH"
    assert restored.pet_name == "Rex"
    assert restored.preferred_time == time(9, 30)  # real time, not "09:30"
    assert restored.recurrence == "weekly"
    assert restored.weekday == 2
    assert restored.completed is True


def test_owner_save_and_load_round_trip(tmp_path):
    """save_to_json + load_from_json rebuild an equivalent Owner from disk."""
    owner = Owner(name="Jordan", available_minutes=90, day_start=time(7, 30))
    mochi = Pet(name="Mochi", species="dog", notes="likes long walks")
    owner.add_pet(mochi)
    owner.add_task(mochi, Task("Walk", 30, Priority.HIGH, preferred_time=time(8, 0)))
    owner.add_task(mochi, Task("Grooming", 40, Priority.LOW))

    path = tmp_path / "data.json"
    owner.save_to_json(str(path))
    loaded = Owner.load_from_json(str(path))

    assert loaded.name == "Jordan"
    assert loaded.available_minutes == 90
    assert loaded.day_start == time(7, 30)
    assert [p.name for p in loaded.pets] == ["Mochi"]
    assert loaded.pets[0].notes == "likes long walks"
    tasks = loaded.pets[0].tasks
    assert [t.description for t in tasks] == ["Walk", "Grooming"]
    assert tasks[0].priority is Priority.HIGH
    assert tasks[0].preferred_time == time(8, 0)
    # pet_name back-reference is preserved on load.
    assert all(t.pet_name == "Mochi" for t in tasks)


def test_loaded_owner_can_still_schedule():
    """A reloaded Owner is a fully working object, not just data."""
    owner = Owner(name="Jordan", available_minutes=120, day_start=time(8, 0))
    pet = Pet(name="Rex", species="dog")
    owner.add_pet(pet)
    owner.add_task(pet, Task("Walk", 30, Priority.HIGH))

    reloaded = Owner.from_dict(owner.to_dict())
    plan = Scheduler(reloaded).build_plan()

    assert len(plan.slots) == 1
    assert plan.slots[0].task.description == "Walk"

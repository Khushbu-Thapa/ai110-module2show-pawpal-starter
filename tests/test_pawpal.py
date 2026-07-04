"""Simple unit tests for the PawPal+ core system."""

from pawpal_system import Pet, Priority, Task


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

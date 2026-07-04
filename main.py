"""PawPal+ command-line demo.

Builds an owner with two pets and several care tasks, then prints today's
generated schedule to the terminal. Run with:  python main.py
"""

from datetime import time

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def build_demo_owner() -> Owner:
    """Create a sample owner with two pets and a handful of tasks."""
    owner = Owner(name="Jordan", available_minutes=120, day_start=time(8, 0))

    mochi = Pet(name="Mochi", species="dog")
    biscuit = Pet(name="Biscuit", species="cat")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    # Three+ tasks with different times/priorities across both pets.
    owner.add_task(mochi, Task("Feeding", 10, Priority.HIGH, preferred_time=time(8, 0)))
    owner.add_task(mochi, Task("Morning walk", 30, Priority.HIGH))
    owner.add_task(mochi, Task("Grooming", 40, Priority.LOW))
    owner.add_task(biscuit, Task("Feeding", 10, Priority.HIGH, preferred_time=time(9, 0)))
    owner.add_task(biscuit, Task("Enrichment play", 20, Priority.MEDIUM))

    return owner


def main() -> None:
    owner = build_demo_owner()
    plan = Scheduler(owner).build_plan()

    print(f"🐾 Today's schedule for {owner.name}")
    print(f"   (day starts {owner.day_start.strftime('%H:%M')}, "
          f"{owner.available_minutes} min available)")
    print("=" * 50)
    print(plan.explain())


if __name__ == "__main__":
    main()

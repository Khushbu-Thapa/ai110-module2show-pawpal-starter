import streamlit as st

import pawpal_system

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
**PawPal+** is a pet care planning assistant. Add your pets and their care tasks,
then generate a daily schedule that orders tasks by priority, time, and preferences.
"""
)

# --- Persistent state -------------------------------------------------------
# Streamlit reruns the whole script on every interaction, so we keep the Owner
# in st.session_state. Create it once; reuse it (with all pets/tasks) after.
if "owner" not in st.session_state:
    st.session_state.owner = pawpal_system.Owner(name="Jordan")
owner = st.session_state.owner

st.divider()

# --- Add a pet --------------------------------------------------------------
st.subheader("Add a Pet")
with st.form("add_pet_form", clear_on_submit=True):
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    if st.form_submit_button("Add pet"):
        if pet_name.strip():
            owner.add_pet(pawpal_system.Pet(name=pet_name.strip(), species=species))
            st.success(f"Added {pet_name.strip()} ({species}).")
        else:
            st.warning("Please enter a pet name.")

if owner.pets:
    st.caption("Your pets: " + ", ".join(f"{p.name} ({p.species})" for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Add a task to a pet ----------------------------------------------------
st.subheader("Add a Task")
if not owner.pets:
    st.info("Add a pet first, then you can give it tasks.")
else:
    with st.form("add_task_form", clear_on_submit=True):
        pet_choice = st.selectbox("For pet", [p.name for p in owner.pets])
        task_title = st.text_input("Task title", value="Morning walk")
        col1, col2, col3 = st.columns(3)
        with col1:
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
        with col2:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        with col3:
            preferred = st.text_input("Preferred time (HH:MM)", value="")
        if st.form_submit_button("Add task"):
            pet = next(p for p in owner.pets if p.name == pet_choice)
            task = pawpal_system.Task.from_ui(
                {
                    "title": task_title,
                    "duration_minutes": int(duration),
                    "priority": priority,
                    "preferred_time": preferred,
                }
            )
            owner.add_task(pet, task)
            st.success(f"Added '{task_title}' for {pet.name}.")

# Show the current tasks across all pets, with sort + filter controls.
all_tasks = owner.list_all_tasks()
if all_tasks:
    st.write("Current tasks:")

    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        pet_filter = st.selectbox(
            "Filter by pet", ["All pets"] + [p.name for p in owner.pets]
        )
    with fcol2:
        status_filter = st.selectbox("Filter by status", ["All", "Pending", "Completed"])
    with fcol3:
        sort_choice = st.selectbox("Sort by", ["As added", "By time"])

    # Apply the filters via Owner.filter_tasks (pet name / completion status).
    completed = {"Pending": False, "Completed": True}.get(status_filter)
    tasks = owner.filter_tasks(
        pet=None if pet_filter == "All pets" else pet_filter,
        completed=completed,
    )

    # Apply the chosen sort.
    if sort_choice == "By time":
        tasks = pawpal_system.sort_by_time(tasks)

    if tasks:
        st.table(
            [
                {
                    "Pet": t.pet_name,
                    "Task": t.description,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority.name.lower(),
                    "Preferred": t.preferred_time.strftime("%H:%M") if t.preferred_time else "—",
                    "Done": "✅" if t.completed else "",
                }
                for t in tasks
            ]
        )
    else:
        st.caption("No tasks match the current filters.")

st.divider()

# --- Owner constraints ------------------------------------------------------
st.subheader("Plan Settings")
owner.available_minutes = st.number_input(
    "Available minutes today", min_value=15, max_value=600, value=owner.available_minutes
)

# --- Generate the schedule --------------------------------------------------
st.subheader("Build Schedule")

# Lightweight, non-crashing pre-check: warn about clashing fixed-time tasks
# before the user even builds a schedule.
pre_warning = pawpal_system.Scheduler(owner).conflict_warning()
if pre_warning:
    st.warning(pre_warning)

if st.button("Generate schedule"):
    if not owner.pending_tasks():
        st.warning("No pending tasks to schedule. Add some tasks first.")
    else:
        plan = pawpal_system.Scheduler(owner).build_plan()
        # Post-schedule validation: surface any overlaps as a warning, never crash.
        plan_warning = plan.conflict_warning()
        if plan_warning:
            st.warning(plan_warning)
        if plan.slots:
            st.table(plan.to_table())
        st.text(plan.explain())

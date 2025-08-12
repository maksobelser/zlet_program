# backend/crud.py

from sqlmodel import Session, select
from sqlalchemy import func
import models
import random

# — Trails & applicants (unchanged) —

def get_applicant_by_user(session: Session, user_id: str) -> models.Applicant | None:
    stmt = select(models.Applicant).where(models.Applicant.user_id == user_id)
    return session.exec(stmt).first()

def create_applicant(session: Session, user_id: str, answers: str) -> models.Applicant:
    appl = models.Applicant(
        user_id=user_id,
        answers=answers,
        status="pending"
    )
    session.add(appl)
    session.commit()
    session.refresh(appl)
    return appl

def list_applicants(session: Session) -> list[models.Applicant]:
    stmt = select(models.Applicant)
    return session.exec(stmt).all()

def get_trails(session: Session) -> list[models.Trail]:
    stmt = select(models.Trail)
    return session.exec(stmt).all()

def create_trail(
    session: Session,
    name: str,
    description: str,
    max_applicants: int
) -> models.Trail:
    trail = models.Trail(
        name=name,
        description=description,
        max_applicants=max_applicants
    )
    session.add(trail)
    session.commit()
    session.refresh(trail)
    return trail

def assign_unapplied_users_randomly(session: Session) -> None:
    # (unchanged)
    leader_ids = session.exec(
        select(models.User.id).where(models.User.leader == True)
    ).all()
    leader_user_ids = [str(uid) for uid in leader_ids]
    applied_user_ids = set(
        str(uid) for uid in session.exec(select(models.Applicant.user_id)).all()
    )
    unapplied_leaders = [uid for uid in leader_user_ids if uid not in applied_user_ids]
    if not unapplied_leaders:
        return

    trails = session.exec(select(models.Trail)).all()
    slots: list[int] = []
    for t in trails:
        taken = session.exec(
            select(func.count())
            .select_from(models.Applicant)
            .where(models.Applicant.answers == str(t.id))
            .where(models.Applicant.status == "accepted")
        ).one()
        free = max(t.max_applicants - taken, 0)
        slots += [t.id] * free

    if not slots:
        return

    random.shuffle(slots)
    for user_id, trail_id in zip(unapplied_leaders, slots):
        session.add(models.Applicant(
            user_id=user_id,
            answers=str(trail_id),
            status="accepted",
        ))

    session.commit()

# — Morning‐activity CRUD — 

def get_morning_application_by_user_and_day(
    session: Session, user_id: str, day: str
) -> models.ApplicationsMorningActivity | None:
    stmt = (
        select(models.ApplicationsMorningActivity)
        .where(models.ApplicationsMorningActivity.user_id == user_id)
        .where(models.ApplicationsMorningActivity.day == day)
    )
    return session.exec(stmt).first()

def get_morning_activities(session: Session) -> list[models.MorningActivity]:
    stmt = select(models.MorningActivity)
    return session.exec(stmt).all()

# — new: Afternoon‐activity CRUD — 

def get_afternoon_application_by_user_and_day(
    session: Session, user_id: str, day: str
) -> models.ApplicationsAfternoonActivity | None:
    """
    Fetch this user's afternoon-activity application for the given day, or None.
    """
    stmt = (
        select(models.ApplicationsAfternoonActivity)
        .where(models.ApplicationsAfternoonActivity.user_id == user_id)
        .where(models.ApplicationsAfternoonActivity.day == day)
    )
    return session.exec(stmt).first()

def get_afternoon_activities(session: Session) -> list[models.AfternoonActivity]:
    """
    Return all AfternoonActivity rows.
    """
    stmt = select(models.AfternoonActivity)
    return session.exec(stmt).all()

def assign_missing_afternoon_activities(session, max_per_user: int = 4) -> None:
    """
    For every non‐leader user, fill in up to `max_per_user` afternoon applications:
      - Never on a seaside day
      - At most one per day, at most `max_per_user` total
      - Never exceed each activity’s capacity
      - Never assign two workshops from the same category (uses ProgramAddlInfo.category)
      - Prefer workshops with the largest remaining free slots
      - Skip any workshops with ProgramAddlInfo.priority == -1
      - Among remaining, prioritise higher ProgramAddlInfo.priority first
      - If there’s a tie on both priority and free slots, pick randomly among them
    """
    from sqlmodel import select
    from sqlalchemy import func
    import models, random

    # 1) load users & activities
    users = session.exec(
        select(models.User).where(models.User.leader == False)
    ).all()
    activities = get_afternoon_activities(session)

    # 1b) load ProgramAddlInfo for category & priority maps
    pinfo_list = session.exec(select(models.ProgramAddlInfo)).all()
    category_by_name = {p.name: p.category for p in pinfo_list if p.name is not None}
    priority_by_name = {p.name: p.priority for p in pinfo_list if p.name is not None}
    category_by_act_id = {
        act.id: category_by_name.get(act.name)
        for act in activities
    }
    priority_by_act_id = {
        act.id: priority_by_name.get(act.name, 0)
        for act in activities
    }

    # 2) compute free slots for each activity
    free_slots: dict[int, int] = {}
    for act in activities:
        taken = session.exec(
            select(func.count())
            .select_from(models.ApplicationsAfternoonActivity)
            .where(models.ApplicationsAfternoonActivity.answers == str(act.id))
            .where(models.ApplicationsAfternoonActivity.status == "accepted")
        ).one()
        free_slots[act.id] = max(act.max_participants - taken, 0)

    # 3) seaside days per user
    user_seaside: dict[str, set[str]] = {}
    for u in users:
        days = []
        if u.group:
            days = session.exec(
                select(models.SeasideDay.day)
                .where(models.SeasideDay.group == u.group)
            ).all()
        user_seaside[u.id] = set(days)

    # 4) track each user’s existing days, categories, slots left
    existing_days: dict[str, set[str]] = {}
    applied_categories: dict[str, set[int]] = {}
    slots_left: dict[str, int] = {}

    for u in users:
        apps = session.exec(
            select(models.ApplicationsAfternoonActivity)
            .where(models.ApplicationsAfternoonActivity.user_id == u.id)
        ).all()
        existing_days[u.id] = {app.day for app in apps}
        cats = {
            category_by_act_id.get(int(app.answers))
            for app in apps
            if category_by_act_id.get(int(app.answers)) is not None
        }
        applied_categories[u.id] = cats
        slots_left[u.id] = max_per_user - len(apps)

    # 5) iterate days in order, one‐per‐day up to max_per_user
    days = sorted({a.day for a in activities if a.day})

    ENGLISH_ONLY = {
        "Bulgaria troop 1", "Bulgaria troop 2", "Bulgaria troop 3",
        "Star Wolves", "Black wolves", "Vampire Foxes", "Scouting for smile",
    }

    new_apps: list[models.ApplicationsAfternoonActivity] = []

    for day in days:
        for u in users:
            if slots_left[u.id] <= 0:
                continue
            if day in user_seaside[u.id]:
                continue
            if day in existing_days[u.id]:
                continue

            # gather viable candidates
            cands = []
            for act in activities:
                if act.day != day:
                    continue
                if free_slots.get(act.id, 0) <= 0:
                    continue
                # skip any with priority == -1
                if priority_by_act_id.get(act.id, 0) == -1:
                    continue
                # group‐specific filter
                if u.group in ENGLISH_ONLY and not act.english_language:
                    continue
                # age filter
                if u.age is not None and u.age < 16 and act.older_participants:
                    continue
                # skip if same category already assigned
                act_cat = category_by_act_id.get(act.id)
                if act_cat is not None and act_cat in applied_categories[u.id]:
                    continue
                cands.append(act)

            if not cands:
                continue

            # ----- new selection logic with entropy -----
            # 1) highest priority
            max_prio = max(priority_by_act_id.get(a.id, 0) for a in cands)
            prio_cands = [a for a in cands if priority_by_act_id.get(a.id, 0) == max_prio]

            # 2) among those, highest free slots
            max_free = max(free_slots[a.id] for a in prio_cands)
            top_cands = [a for a in prio_cands if free_slots[a.id] == max_free]

            # 3) if multiple, pick randomly
            chosen = random.choice(top_cands)

            new_apps.append(models.ApplicationsAfternoonActivity(
                user_id=str(u.id),
                day=day,
                answers=str(chosen.id),
                status="accepted"
            ))

            # update tracking
            free_slots[chosen.id] -= 1
            slots_left[u.id] -= 1
            existing_days[u.id].add(day)
            chosen_cat = category_by_act_id.get(chosen.id)
            if chosen_cat is not None:
                applied_categories[u.id].add(chosen_cat)

    # persist if any new assignments
    if new_apps:
        session.add_all(new_apps)
        session.commit()
# backend/main.py

from datetime import datetime, timedelta
import uuid
from typing import Optional, List
from pydantic   import BaseModel

from fastapi import FastAPI, Depends, HTTPException, status, Form, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from fastapi_users import FastAPIUsers, schemas
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.manager import BaseUserManager
from fastapi_users.exceptions import InvalidPasswordException
from fastapi_users_db_sqlmodel import SQLModelUserDatabase

from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from apscheduler.schedulers.background import BackgroundScheduler
import time

from fastapi import Depends, APIRouter, HTTPException, Header, status
from sqlmodel import Session
import crud

import config, crud, models
from crud import (
    get_applicant_by_user,
    list_applicants,
    get_trails,
    create_applicant,
    assign_unapplied_users_randomly,
    get_morning_activities,
    get_morning_application_by_user_and_day,
    get_afternoon_application_by_user_and_day,
    get_afternoon_activities,
)

from dateutil import tz

# --- App & CORS setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database setup ---
engine = create_engine(
    config.settings.database_url,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600
)
SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# --- User Management (unchanged) ---
async def get_user_db(session: Session = Depends(get_session)):
    yield SQLModelUserDatabase(session, models.User)

SECRET = config.settings.secret

class UserManager(BaseUserManager[models.User, uuid.UUID]):
    user_db_model = models.User

    def parse_id(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)

    async def validate_password(self, password: str, user: models.User) -> None:
        if len(password) < 4:
            raise InvalidPasswordException(reason="Password too short")

    async def on_after_register(self, user: models.User, request=None):
        print(f"User {user.id} has registered.")

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

class UserRead(schemas.BaseUser[uuid.UUID]):
    leader: bool

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass

bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=900)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers(get_user_manager, [auth_backend])

# --- Custom JWT login with time-based access control ---
router = APIRouter()

async def get_user_by_email_dep(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    stmt = select(models.User).where(models.User.email == form_data.username)
    user = session.exec(stmt).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"
        )
    return user, form_data

class AppliedDay(BaseModel):
    day: str

@router.get(
    "/morning_applications",
    response_model=List[AppliedDay],
    tags=["morning"],
    summary="List the days this user has applied for morning activities",
)
def list_my_morning_applications(
    user=Depends(fastapi_users.current_user()),
    session=Depends(get_session),
):
    rows = session.exec(
        select(models.ApplicationsMorningActivity.day)
        .where(models.ApplicationsMorningActivity.user_id == user.id)
    ).all()
    return [{"day": d} for d in rows]

@router.get(
    "/afternoon_applications",
    response_model=List[AppliedDay],
    tags=["afternoon"],
    summary="List the days this user has applied for afternoon activities",
)
def list_my_afternoon_applications(
    user=Depends(fastapi_users.current_user()),
    session=Depends(get_session),
):
    rows = session.exec(
        select(models.ApplicationsAfternoonActivity.day)
        .where(models.ApplicationsAfternoonActivity.user_id == user.id)
    ).all()
    return [{"day": d} for d in rows]

@router.post("/auth/jwt/login", name="jwt_login")
async def custom_login(
    ctx=Depends(get_user_by_email_dep),
    user_manager=Depends(get_user_manager),
    session: Session = Depends(get_session),
):
    user, form_data = ctx

    # 1) verify password (and upgrade hash if needed)
    verified, new_hash = user_manager.password_helper.verify_and_update(
        form_data.password, user.hashed_password
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"
        )
    # if the hash has been upgraded under the hood, persist it
    if new_hash:
        user.hashed_password = new_hash
        session.add(user)
        session.commit()

    # 2) check time windows
    cet = tz.gettz("Europe/Ljubljana")
    now = datetime.now(tz=cet)

    early_open = datetime(2025, 6, 22, 18, 0, tzinfo=cet)
    late_open  = early_open + timedelta(hours=48)

    # — new: also allow early‐access if your group's leader can_apply_early —
    group_leader_early = False
    if user.group:
        leader = session.exec(
            select(models.User)
            .where(
                models.User.group == user.group,
                models.User.leader == True
            )
        ).first()
        if leader and leader.can_apply_early:
            group_leader_early = True

    # combine with the existing per‐user flag
    if user.can_apply_early or group_leader_early:
        if now < early_open:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Login not yet open for early applicants."
            )
    else:
        if now < late_open:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Login not yet open for your group."
            )

    # 3) mint JWT
    jwt_strategy = auth_backend.get_strategy()
    access_token = await jwt_strategy.write_token(user)
    return {"access_token": access_token, "token_type": "bearer"}

# include custom login route
app.include_router(router)

# --- Registration & User endpoints ---
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# --- Trails endpoints ---
from fastapi_users import schemas as _schemas

class TrailOut(_schemas.BaseModel):
    id: int
    name: str
    description: str
    max_applicants: int

class ApplicantOut(_schemas.BaseModel):
    answers: str
    status: str
    created_at: datetime

@app.get(
    "/trails",
    response_model=list[TrailOut],
    tags=["trails"]
)
def read_trails(session: Session = Depends(get_session)):
    return get_trails(session)

@app.get(
    "/application",
    response_model=ApplicantOut,
    tags=["trails"]
)
def get_my_application(
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session)
):
    appl = get_applicant_by_user(session, str(user.id))
    if not appl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trail application not found"
        )
    return appl

@app.post(
    "/apply",
    response_model=ApplicantOut,
    tags=["trails"]
)
def apply_trail(
    answers: str = Form(...),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    if get_applicant_by_user(session, str(user.id)):
        raise HTTPException(400, "Already applied to a trail")
    appl = create_applicant(session, str(user.id), answers)
    return appl

@app.get(
    "/applicants",
    response_model=list[ApplicantOut],
    tags=["trails"]
)
def read_applicants(session: Session = Depends(get_session)):
    return list_applicants(session)

# --- Morning‐activity endpoints
class MorningActivityOut(_schemas.BaseModel):
    id: int
    name: str
    description: str
    max_participants: int
    free_spots: int
    english_language: bool
    older_participants: bool
    day: str

@app.get(
    "/morning_activities",
    response_model=list[MorningActivityOut],
    tags=["morning"]
)
def read_morning_activities(
    day: Optional[str] = Query(None, description="Filter by day"),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    base_activities = get_morning_activities(session)
    if day:
        base_activities = [a for a in base_activities if a.day == day]
    if user.age is not None and user.age < 16:
        base_activities = [a for a in base_activities if not a.older_participants]

    # Get IDs and names of applied activities
    appl_q = (
        select(models.ApplicationsMorningActivity.answers)
        .where(models.ApplicationsMorningActivity.user_id == user.id)
    )
    applied_answers = session.scalars(appl_q).all()
    applied_ids = {int(ans) for ans in applied_answers}

    applied_names = set()
    if applied_ids:
        names_q = (
            select(models.MorningActivity.name)
            .where(models.MorningActivity.id.in_(applied_ids))
        )
        applied_names = set(session.scalars(names_q).all())

    # Get already applied themes
    applied_themes = set()
    if applied_ids:
        themes_q = (
            select(models.MorningActivity.theme)
            .where(models.MorningActivity.id.in_(applied_ids))
            .where(models.MorningActivity.theme.isnot(None))
        )
        applied_themes = set(session.scalars(themes_q).all())

    # First pass: apply theme filtering
    theme_filtered = [a for a in base_activities if a.theme not in applied_themes]

    def with_free_slots_and_filter(activities, exclude_names: bool):
        result = []
        for a in activities:
            count_stmt = (
                select(func.count())
                .select_from(models.ApplicationsMorningActivity)
                .where(models.ApplicationsMorningActivity.answers == str(a.id))
                .where(models.ApplicationsMorningActivity.status == "accepted")
            )
            accepted_count = session.exec(count_stmt).one()
            free = max(a.max_participants - accepted_count, 0)
            # filter out if no slots or name already applied (in fallback mode)
            if free > 0 and (not exclude_names or a.name not in applied_names):
                result.append((a, free))
        return result

    # Try theme-filtered activities first
    filtered_with_slots = with_free_slots_and_filter(theme_filtered, exclude_names=False)

    # Fallback: drop theme filtering, but exclude same-name duplicates
    if not filtered_with_slots:
        filtered_with_slots = with_free_slots_and_filter(base_activities, exclude_names=True)

    # Format response
    return [
        MorningActivityOut(
            id=a.id,
            name=a.name,
            description=a.description,
            max_participants=a.max_participants,
            free_spots=free,
            english_language=a.english_language,
            older_participants=a.older_participants,
            day=a.day or ""
        )
        for a, free in filtered_with_slots
    ]

class MorningApplicationOut(BaseModel):
    answers: str
    status: str
    created_at: datetime
    id: int
    name: str
    description: str
    max_participants: int
    free_spots: int
    english_language: bool
    older_participants: bool
    day: str
    equipment: Optional[str] = None
    location: Optional[str] = None

@app.get(
    "/morning_application",
    tags=["morning"],
    response_model=MorningApplicationOut,
)
def get_my_morning_application(
    day: str = Query(..., description="Day of the activity"),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    # 1) seaside override for groups
    if user.group:
        seaside = session.exec(
            select(models.SeasideDay)
            .where(models.SeasideDay.group == user.group)
            .where(models.SeasideDay.day   == day)
        ).one_or_none()
        if seaside:
            return MorningApplicationOut(
                answers=str(seaside.id),
                status="seaside",
                created_at=datetime.utcnow(),
                id=0,
                name="Izlet na morje",
                description="Na ta dan je za vaš trg organiziran izlet na morje. Odhod na avtobus ob 6:55 z D40, odhod avtobusa ob 7:00. Zajtrk bo na voljo od 6.00 dalje.\n\nS seboj imejte:\n- menažko\n- prvo pomoč\n- pokrivalo, sončno kremo in čutaro vode\n- kakšen evro za sladoled",
                max_participants=0,
                free_spots=0,
                english_language=False,
                older_participants=False,
                day=day,
                equipment=None,
                location=None,
            )

    # 2) fetch the user’s actual application
    appl = crud.get_morning_application_by_user_and_day(session, str(user.id), day)
    if not appl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Morning activity application not found"
        )

    # 3) load the activity details
    activity = session.exec(
        select(models.MorningActivity)
        .where(models.MorningActivity.id == int(appl.answers))
    ).one_or_none()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # 4) compute free spots
    accepted_count = session.exec(
        select(func.count())
        .select_from(models.ApplicationsMorningActivity)
        .where(models.ApplicationsMorningActivity.answers == appl.answers)
        .where(models.ApplicationsMorningActivity.status  == "accepted")
    ).one()
    free_spots = max(activity.max_participants - accepted_count, 0)

    # 5) join in equipment & location
    pinfo = session.exec(
        select(models.MorningProgramInfoApplicants)
        .where(models.MorningProgramInfoApplicants.id == activity.id)
    ).one_or_none()
    equipment = pinfo.equipment if pinfo else None
    location  = pinfo.location  if pinfo else None

    # 6) return enriched payload
    return MorningApplicationOut(
        answers=appl.answers,
        status=appl.status,
        created_at=appl.created_at,
        id=activity.id,
        name=activity.name,
        description=activity.description,
        max_participants=activity.max_participants,
        free_spots=free_spots,
        english_language=activity.english_language,
        older_participants=activity.older_participants,
        day=activity.day or "",
        equipment=equipment,
        location=location,
    )

@app.post(
    "/apply_morning",
    tags=["morning"]
)
def apply_morning(
    answers: str = Form(...),
    day: str = Form(...),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    # only leaders may apply
    if not user.leader:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only leaders can apply for morning activities."
        )

    # ❗️Disallow application if user's group has a SeasideDay
    if user.group:
        seaside = session.exec(
            select(models.SeasideDay)
            .where(models.SeasideDay.group == user.group)
            .where(models.SeasideDay.day == day)
        ).one_or_none()
        if seaside:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have a seaside excursion on this day; morning application is not allowed."
            )

    if get_morning_application_by_user_and_day(session, str(user.id), day):
        raise HTTPException(400, "Already applied for this day")

    try:
        activity_id = int(answers)
        stmt = (
            select(models.MorningActivity)
            .where(models.MorningActivity.id == activity_id)
            .with_for_update()
        )
        activity = session.exec(stmt).one_or_none()
        if not activity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

        count_stmt = (
            select(func.count())
            .select_from(models.ApplicationsMorningActivity)
            .where(models.ApplicationsMorningActivity.answers == str(activity_id))
            .where(models.ApplicationsMorningActivity.status == "accepted")
        )
        accepted_count = session.exec(count_stmt).one()
        if accepted_count >= activity.max_participants:
            raise HTTPException(400, "Activity full")

        appl = models.ApplicationsMorningActivity(
            user_id=str(user.id),
            day=day,
            answers=str(activity_id),
            status="accepted"
        )
        session.add(appl)
        session.commit()
        session.refresh(appl)
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(500, "Internal server error")

    return {"status": appl.status}

# --- Afternoon‐activity endpoints ---
class AfternoonActivityOut(_schemas.BaseModel):
    id: int
    name: str
    description: str
    max_participants: int
    free_spots: int
    english_language: bool
    older_participants: bool
    day: str

@app.get(
    "/afternoon_activities",
    response_model=list[AfternoonActivityOut],
    tags=["afternoon"]
)
def read_afternoon_activities(
    day: Optional[str] = Query(None, description="Filter by day"),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    activities = get_afternoon_activities(session)
    if day:
        activities = [a for a in activities if a.day == day]
    if user.age is not None and user.age < 16:
        activities = [a for a in activities if not a.older_participants]

    appl_q = (
        select(models.ApplicationsAfternoonActivity.answers)
        .where(models.ApplicationsAfternoonActivity.user_id == user.id)
    )
    applied_answers = session.scalars(appl_q).all()
    applied_ids = {int(ans) for ans in applied_answers}
    if applied_ids:
        names_q = (
            select(models.AfternoonActivity.name)
            .where(models.AfternoonActivity.id.in_(applied_ids))
        )
        applied_names = set(session.scalars(names_q).all())
    else:
        applied_names: set[str] = set()

    activities = [a for a in activities if a.name not in applied_names]

    out: list[AfternoonActivityOut] = []
    for a in activities:
        count_stmt = (
            select(func.count())
            .select_from(models.ApplicationsAfternoonActivity)
            .where(models.ApplicationsAfternoonActivity.answers == str(a.id))
            .where(models.ApplicationsAfternoonActivity.status == "accepted")
        )
        accepted_count = session.exec(count_stmt).one()
        free = max(a.max_participants - accepted_count, 0)

        out.append(AfternoonActivityOut(
            id=a.id,
            name=a.name,
            description=a.description,
            max_participants=a.max_participants,
            free_spots=free,
            english_language=a.english_language,
            older_participants=a.older_participants,
            day=a.day or ""
        ))

    return out

@app.get(
    "/afternoon_application",
    tags=["afternoon"]
)
def get_my_afternoon_application(
    day: str = Query(..., description="Day of the activity"),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    # 1) seaside override for groups
    if user.group:
        seaside = session.exec(
            select(models.SeasideDay)
            .where(
                models.SeasideDay.group == user.group,
                models.SeasideDay.day   == day
            )
        ).one_or_none()
        if seaside:
            return {
                "answers":          str(seaside.id),
                "status":           "seaside",
                "created_at":       datetime.utcnow(),
                "id":               0,
                "name":             "Izlet na morje",
                "description":      "Na ta dan je za vaš trg organiziran izlet na morje. Odhod na avtobus ob 6:55 z D40, odhod avtobusa ob 7:00. Zajtrk bo na voljo od 6.00 dalje.\n\nS seboj imejte:\n- menažko\n- prvo pomoč\n- pokrivalo, sončno kremo in čutaro vode\n- kakšen evro za sladoled",
                "max_participants": 0,
                "free_spots":       0,
                "english_language": False,
                "older_participants": False,
                "day":              day,
                "equipment":        None,
                "location":         None,
            }

    # 2) fetch the user’s actual application
    appl = get_afternoon_application_by_user_and_day(session, str(user.id), day)
    if not appl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Afternoon activity application not found"
        )

    # 3) load the activity details
    activity = session.exec(
        select(models.AfternoonActivity)
        .where(models.AfternoonActivity.id == int(appl.answers))
    ).one_or_none()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # 4) compute free spots
    accepted_count = session.exec(
        select(func.count())
        .select_from(models.ApplicationsAfternoonActivity)
        .where(models.ApplicationsAfternoonActivity.answers == appl.answers)
        .where(models.ApplicationsAfternoonActivity.status  == "accepted")
    ).one()
    free_spots = max(activity.max_participants - accepted_count, 0)

    # 5) join in equipment & location
    pinfo = session.exec(
        select(models.AfternoonProgramInfoApplicants)
        .where(models.AfternoonProgramInfoApplicants.id == activity.id)
    ).one_or_none()
    equipment = pinfo.equipment if pinfo else None
    location  = pinfo.location  if pinfo else None

    # 6) return enriched payload
    return {
        "answers":            appl.answers,
        "status":             appl.status,
        "created_at":         appl.created_at,
        "id":                 activity.id,
        "name":               activity.name,
        "description":        activity.description,
        "max_participants":   activity.max_participants,
        "free_spots":         free_spots,
        "english_language":   activity.english_language,
        "older_participants": activity.older_participants,
        "day":                activity.day,
        "equipment":          equipment,
        "location":           location,
    }

@app.post(
    "/apply_afternoon",
    tags=["afternoon"]
)
def apply_afternoon(
    answers: str = Form(...),
    day: str = Form(...),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    # only NOT leaders may apply
    if user.leader:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only leaders can apply for morning activities."
        )

    # ❗️Check if the user has SeasideDay for that day
    if user.group:
        seaside = session.exec(
            select(models.SeasideDay)
            .where(models.SeasideDay.group == user.group)
            .where(models.SeasideDay.day == day)
        ).one_or_none()
        if seaside:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have a seaside excursion on this day; afternoon application is not allowed."
            )

    if get_afternoon_application_by_user_and_day(session, str(user.id), day):
        raise HTTPException(400, "Already applied for this day")

    try:
        activity_id = int(answers)
        stmt = (
            select(models.AfternoonActivity)
            .where(models.AfternoonActivity.id == activity_id)
            .with_for_update()
        )
        activity = session.exec(stmt).one_or_none()
        if not activity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

        count_stmt = (
            select(func.count())
            .select_from(models.ApplicationsAfternoonActivity)
            .where(models.ApplicationsAfternoonActivity.answers == str(activity_id))
            .where(models.ApplicationsAfternoonActivity.status == "accepted")
        )
        accepted_count = session.exec(count_stmt).one()
        if accepted_count >= activity.max_participants:
            raise HTTPException(400, "Activity full")

        appl = models.ApplicationsAfternoonActivity(
            user_id=str(user.id),
            day=day,
            answers=str(activity_id),
            status="accepted"
        )
        session.add(appl)
        session.commit()
        session.refresh(appl)
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(500, "Internal server error")

    return {"status": appl.status}

# --- Delete Morning‐application endpoint ---
@app.delete(
    "/morning_application",
    tags=["morning"],
    summary="Delete your morning activity application for a given day",
)
def delete_morning_application(
    day: str = Query(..., description="Day of the activity to cancel"),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    # only leaders can have a morning application
    if not user.leader:
        raise HTTPException(
            status_code=403, detail="Only leaders can cancel morning applications."
        )

    appl = crud.get_morning_application_by_user_and_day(session, str(user.id), day)
    if not appl:
        raise HTTPException(
            status_code=404, detail="Morning activity application not found."
        )

    try:
        session.delete(appl)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(status_code=500, detail="Could not delete application.")

    return {"detail": f"Morning application for '{day}' deleted."}


# --- Delete Afternoon‐application endpoint ---
@app.delete(
    "/afternoon_application",
    tags=["afternoon"],
    summary="Delete your afternoon activity application for a given day",
)
def delete_afternoon_application(
    day: str = Query(..., description="Day of the activity to cancel"),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    # only non-leaders may have an afternoon application
    if user.leader:
        raise HTTPException(
            status_code=403, detail="Only non-leaders can cancel afternoon applications."
        )

    appl = crud.get_afternoon_application_by_user_and_day(session, str(user.id), day)
    if not appl:
        raise HTTPException(
            status_code=404, detail="Afternoon activity application not found."
        )

    try:
        session.delete(appl)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(status_code=500, detail="Could not delete application.")

    return {"detail": f"Afternoon application for '{day}' deleted."}

# --- define a Pydantic schema for the response ---
class GroupMemberApplicationOut(BaseModel):
    user_id:            uuid.UUID
    first_name:         Optional[str]
    surname:            Optional[str]
    answers:            Optional[str]
    status:             Optional[str]
    id:                  Optional[int]
    name:                Optional[str]
    description:         Optional[str]
    max_participants:    Optional[int]
    free_spots:          Optional[int]
    english_language:    Optional[bool]
    older_participants:  Optional[bool]
    day:                 Optional[str]
    equipment:           Optional[str]   # ← new
    location:            Optional[str]   # ← new

# --- replace your existing get_group_applications with this ---
@app.get(
    "/group_applications",
    response_model=List[GroupMemberApplicationOut],
    tags=["admin"],
    summary="For leaders: list all other group members’ workshop applications on a given day"
)
def get_group_applications(
    day: str = Query(..., description="Day of the activity (e.g. 'Pon', 'Tor', etc.)"),
    user=Depends(fastapi_users.current_user()),
    session: Session = Depends(get_session),
):
    # 1) only leaders may call
    if not user.leader:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group leaders can view group applications."
        )
    # 2) must be in a group
    if not user.group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not assigned to any group."
        )

    # 3) check seaside‐excursion override
    seaside = session.exec(
        select(models.SeasideDay)
        .where(
            models.SeasideDay.group == user.group,
            models.SeasideDay.day   == day
        )
    ).one_or_none()

    # 4) fetch all members in this group except the leader
    members = session.exec(
        select(models.User)
        .where(models.User.group == user.group)
    ).all()
    members = [m for m in members if m.id != user.id]

    result: List[GroupMemberApplicationOut] = []
    for m in members:
        if seaside:
            # Seaside day: everyone is on the trip
            data = {
                "user_id": m.id,
                "first_name": m.name,
                "surname": m.surname,
                "answers": str(seaside.id),
                "status": "seaside",
                "id": 0,
                "name": "Izlet na morje",
                "description": "Na ta dan je za vaš trg organiziran izlet na morje. Odhod na avtobus ob 6:55 z D40, odhod avtobusa ob 7:00. Zajtrk bo na voljo od 6.00 dalje.\n\nS seboj imejte:\n- menažko\n- prvo pomoč\n- pokrivalo, sončno kremo in čutaro vode\n- kakšen evro za sladoled",
                "max_participants": 0,
                "free_spots": 0,
                "english_language": False,
                "older_participants": False,
                "day": day,
                "equipment": None,
                "location": None,
            }
        else:
            appl = crud.get_afternoon_application_by_user_and_day(
                session, str(m.id), day
            )
            if not appl:
                # no application
                data = {
                    "user_id": m.id,
                    "first_name": m.name,
                    "surname": m.surname,
                    "answers": None,
                    "status": None,
                    "id": None,
                    "name": None,
                    "description": None,
                    "max_participants": None,
                    "free_spots": None,
                    "english_language": None,
                    "older_participants": None,
                    "day": None,
                    "equipment": None,
                    "location": None,
                }
            else:
                # fetch the chosen activity
                act = session.exec(
                    select(models.AfternoonActivity)
                    .where(models.AfternoonActivity.id == int(appl.answers))
                ).one_or_none()

                if not act:
                    # fallback if the activity record is missing
                    data = {
                        "user_id": m.id,
                        "first_name": m.name,
                        "surname": m.surname,
                        "answers": appl.answers,
                        "status": appl.status,
                        "id": None,
                        "name": None,
                        "description": None,
                        "max_participants": None,
                        "free_spots": None,
                        "english_language": None,
                        "older_participants": None,
                        "day": None,
                        "equipment": None,
                        "location": None,
                    }
                else:
                    # count accepted spots
                    taken = session.exec(
                        select(func.count())
                        .select_from(models.ApplicationsAfternoonActivity)
                        .where(models.ApplicationsAfternoonActivity.answers == appl.answers)
                        .where(models.ApplicationsAfternoonActivity.status  == "accepted")
                    ).one()
                    free = max(act.max_participants - taken, 0)

                    # join in equipment & location
                    pinfo = session.exec(
                        select(models.AfternoonProgramInfoApplicants)
                        .where(models.AfternoonProgramInfoApplicants.id == act.id)
                    ).one_or_none()
                    equipment = pinfo.equipment if pinfo else None
                    location = pinfo.location if pinfo else None

                    data = {
                        "user_id": m.id,
                        "first_name": m.name,
                        "surname": m.surname,
                        "answers": appl.answers,
                        "status": appl.status,
                        "id": act.id,
                        "name": act.name,
                        "description": act.description,
                        "max_participants": act.max_participants,
                        "free_spots": free,
                        "english_language": act.english_language,
                        "older_participants": act.older_participants,
                        "day": act.day or "",
                        "equipment": equipment,
                        "location": location,
                    }

        result.append(GroupMemberApplicationOut(**data))

    return result

# --- Scheduler for random trail‐assignment ---
scheduler = BackgroundScheduler()
end_dt = datetime.fromisoformat(
    config.settings.application_end.replace("Z", "+00:00")
)

@scheduler.scheduled_job("date", run_date=end_dt)
def do_random_assign():
    with Session(engine) as session:
        assign_unapplied_users_randomly(session)

scheduler.start()
scheduler.print_jobs()

# now for admin:
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# 🎯 Hard-coded one-time token
ADMIN_TOKEN = "e3f1c9b7d5a3e2f4c6b8d0e1f3a5c7b9d2e4f6a8c0b2d4e6f0a1b3c5d7e9f2a4"

@admin_router.post("/fill_afternoon")
def trigger_fill(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
    session: Session = Depends(get_session),
):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid or missing admin token.")
    try:
        crud.assign_missing_afternoon_activities(session)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error running fill: {e}")
    return {"ok": True}

app.include_router(admin_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
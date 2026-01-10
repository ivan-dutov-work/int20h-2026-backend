from fastapi import APIRouter, Depends, HTTPException

from src.domain.models import Form, ParticipationFormat

from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.core import get_session
from src.db.models import Participant, Team

router = APIRouter()


@router.post("/form/")
async def submit_form(form: Form, session: AsyncSession = Depends(get_session)):
    # map domain form fields to DB participant fields (new schema)
    participant = Participant(
        full_name=form.full_name,
        email=form.email,
        telegram=getattr(form, "telegram", None),
        phone=form.phone,
        university_id=getattr(form, "university_id", None),
        preferred_category=(
            str(form.category_id)
            if getattr(form, "category_id", None) is not None
            else None
        ),
        participation_format=form.format,  # type: ignore
        team_leader=bool(form.team_leader),
        wants_job=bool(form.wants_job),
        job_description=getattr(form, "job_description", None),
        cv_url=getattr(form, "cv", None),
        linkedin=getattr(form, "linkedin", None),
        work_consent=bool(form.work_consent),
        source=(form.source or getattr(form, "otherSource", None)),
        comment=getattr(form, "comment", None),
        personal_data_consent=bool(getattr(form, "personal_data_consent", False)),
        photo_consent=bool(getattr(form, "photoConsent", False)),
    )

    # if user has no team, just create participant
    if not form.has_team:
        session.add(participant)
        await session.commit()
        return {"message": "Form submitted successfully", "data": form.dict()}

    # user indicates they have a team -> team_name and team_leader should be present
    team_name = form.team_name
    if not team_name:
        raise HTTPException(status_code=400, detail="Team name must be provided")

    category = (
        str(form.category_id) if getattr(form, "category_id", None) is not None else ""
    )

    # try to find existing team
    result = await session.execute(
        select(Team).where(Team.team_name == team_name, Team.category == category)
    )
    existing = result.scalars().first()

    if existing:
        participant.team_id = existing.id
        session.add(participant)
        await session.commit()
        return {"message": "Joined existing team", "data": form.dict()}

    # If no existing team, only a team leader can create a new one
    if not form.team_leader:
        raise HTTPException(
            status_code=400, detail="Only a team lead can create a new team"
        )

    new_team = Team(team_name=team_name, category=category)
    session.add(new_team)
    try:
        await session.commit()
    except IntegrityError:
        # race: another request created the team concurrently -> fetch it
        await session.rollback()
        result = await session.execute(
            select(Team).where(Team.team_name == team_name, Team.category == category)
        )
        existing = result.scalars().first()
        if existing is None:
            raise HTTPException(status_code=500, detail="Failed to create or find team")
        participant.team_id = existing.id
        session.add(participant)
        await session.commit()
        return {"message": "Joined existing team", "data": form.dict()}

    # success: associate participant with freshly created team
    await session.refresh(new_team)
    participant.team_id = new_team.id
    session.add(participant)
    await session.commit()
    return {"message": "Team created and participant added", "data": form.dict()}

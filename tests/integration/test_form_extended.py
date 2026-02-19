import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from httpx import AsyncClient

from src.db import models as db_models
from tests.builders import FormBuilder


@pytest.mark.asyncio
async def _get_participant(session: AsyncSession, email: str):
    stmt = select(db_models.Participant).where(db_models.Participant.email == email)
    r = await session.execute(stmt)
    return r.scalars().first()


@pytest.mark.asyncio
async def test_store_skills_text_comma_separated(client: AsyncClient, session: AsyncSession, category_factory):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_skills(["Python", "SQL", "Go"])
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.skills_text == "Python,SQL,Go"


@pytest.mark.asyncio
async def test_store_empty_skills_as_empty_string(client: AsyncClient, session: AsyncSession, category_factory):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_skills([])
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.skills_text == ""


@pytest.mark.asyncio
async def test_source_mapping_otherSocial_uses_otherSource(client: AsyncClient, session: AsyncSession, category_factory):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_source("otherSocial", "Reddit")
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.source == "Reddit"


@pytest.mark.asyncio
async def test_store_source_when_not_otherSocial(client: AsyncClient, session: AsyncSession, category_factory):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_source("facebook", "Ignored")
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.source == "facebook"


@pytest.mark.asyncio
async def test_phone_normalized_and_cv_linkedin_stored(client: AsyncClient, session: AsyncSession, category_factory):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_phone("+380 50 123 45 67")
        .seeking_job("https://example.com/cv.pdf", "https://linkedin.com/in/test", work_consent=True)
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    # phone should be normalized to E.164
    assert p.phone == "+380501234567"
    assert p.cv_url == "https://example.com/cv.pdf"
    assert p.linkedin == "https://linkedin.com/in/test"


@pytest.mark.asyncio
async def test_participant_team_fields_after_create(client: AsyncClient, session: AsyncSession, category_factory):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_team("TeamCreateTest", is_leader=True)
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    # Verify team created
    stmt = select(db_models.Team).where(db_models.Team.team_name == "TeamCreateTest")
    tr = await session.execute(stmt)
    team = tr.scalars().first()
    assert team is not None

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.team_id == team.id
    assert p.team_leader is True


@pytest.mark.asyncio
async def test_multi_item_skill_storage_with_special_chars(client: AsyncClient, session: AsyncSession, category_factory):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_skills(["C++", "C#", "Python"])
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.skills_text == "C++,C#,Python"


@pytest.mark.asyncio
async def test_commit_integrityerror_handling_rolls_back_and_returns_400(client: AsyncClient, session: AsyncSession, category_factory, monkeypatch):
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .build()
    )

    # Patch AsyncSession.commit to raise IntegrityError
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
    from sqlalchemy.exc import IntegrityError

    async def _raise_integrity(*args, **kwargs):
        raise IntegrityError("simulated", None, None)

    monkeypatch.setattr(_AsyncSession, "commit", _raise_integrity)

    r = await client.post("/form/", json=payload)
    assert r.status_code == 400
    data = r.json()
    assert "Помилка збереження даних" in data["detail"]

    # Ensure nothing persisted
    p = await _get_participant(session, payload["email"])
    assert p is None


# ========================================
# Error Path Tests: Duplicate User Detection
# ========================================


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client: AsyncClient, session: AsyncSession, category_factory):
    """Duplicate email should be rejected with 400."""
    category = await category_factory()

    payload1 = (
        FormBuilder()
        .with_email("duplicate@example.com")
        .with_telegram("@user1")
        .with_category(category.id)
        .build()
    )

    # First submission succeeds
    r1 = await client.post("/form/", json=payload1)
    assert r1.status_code == 200

    # Second submission with same email but different telegram
    payload2 = (
        FormBuilder()
        .with_email("duplicate@example.com")
        .with_telegram("@user2")
        .with_category(category.id)
        .build()
    )

    r2 = await client.post("/form/", json=payload2)
    assert r2.status_code == 400
    assert "email" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_duplicate_telegram_rejected(client: AsyncClient, session: AsyncSession, category_factory):
    """Duplicate telegram should be rejected with 400."""
    category = await category_factory()

    payload1 = (
        FormBuilder()
        .with_email("user1@example.com")
        .with_telegram("@duplicate")
        .with_category(category.id)
        .build()
    )

    # First submission succeeds
    r1 = await client.post("/form/", json=payload1)
    assert r1.status_code == 200

    # Second submission with same telegram but different email
    payload2 = (
        FormBuilder()
        .with_email("user2@example.com")
        .with_telegram("@duplicate")
        .with_category(category.id)
        .build()
    )

    r2 = await client.post("/form/", json=payload2)
    assert r2.status_code == 400
    assert "telegram" in r2.json()["detail"].lower()


# ========================================
# Error Path Tests: Foreign Key Validation
# ========================================


@pytest.mark.asyncio
async def test_invalid_university_id_rejected(client: AsyncClient, session: AsyncSession, category_factory):
    """Non-existent university_id should be rejected with 400."""
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .as_student(university_id=99999, study_year=3)
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 400
    assert "університет" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_category_id_rejected(client: AsyncClient, session: AsyncSession, category_factory):
    """Non-existent category_id should be rejected with 400."""
    payload = (
        FormBuilder()
        .with_category(99999)
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 400
    assert "категорія" in r.json()["detail"].lower()


# ========================================
# Error Path Tests: Team Validation
# ========================================


@pytest.mark.asyncio
async def test_has_team_without_team_name_rejected(client: AsyncClient, session: AsyncSession, category_factory):
    """has_team=True without team_name should be rejected."""
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .build()
    )
    # Manually set has_team without team_name
    payload["has_team"] = True
    payload["team_name"] = ""

    r = await client.post("/form/", json=payload)
    assert r.status_code == 400
    assert "команди" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_team_without_being_leader_rejected(client: AsyncClient, session: AsyncSession, category_factory):
    """Creating a new team without team_leader=True should be rejected."""
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_category(category.id)
        .with_team("NewTeamNoLeader", is_leader=False)
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 400
    assert "тімлід" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_join_full_team_rejected(client: AsyncClient, session: AsyncSession, category_factory, team_factory):
    """Joining a team with 4 members should be rejected."""
    category = await category_factory()
    team = await team_factory(category_id=category.id, team_name="FullTeam")

    # Add 4 members
    for i in range(4):
        participant = db_models.Participant(
            full_name=f"Member {i+1}",
            email=f"member{i+1}@full.com",
            telegram=f"@member{i+1}",
            phone=f"+38050123456{i}",
            is_student=False,
            category_id=category.id,
            participation_format=db_models.ParticipationFormat.ONLINE,
            team_id=team.id,
            team_leader=(i == 0),
            wants_job=False,
            work_consent=False,
            source="test",
            personal_data_consent=True,
        )
        session.add(participant)
    await session.commit()

    # Try to join as 5th member
    payload = (
        FormBuilder()
        .with_email("member5@full.com")
        .with_telegram("@member5")
        .with_category(category.id)
        .with_team("FullTeam", is_leader=False)
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 400
    assert "повна" in r.json()["detail"].lower()


# ========================================
# Success Path Tests
# ========================================


@pytest.mark.asyncio
async def test_participant_without_team_success(client: AsyncClient, session: AsyncSession, category_factory):
    """Participant without team should be accepted."""
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_email("solo@example.com")
        .with_telegram("@solo")
        .with_category(category.id)
        .without_team()
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.team_id is None
    assert p.team_leader is False


@pytest.mark.asyncio
async def test_participant_as_student_with_university_success(client: AsyncClient, session: AsyncSession, category_factory, university_factory):
    """Student participant with university should be accepted."""
    category = await category_factory()
    university = await university_factory(name="Test University")

    payload = (
        FormBuilder()
        .with_email("student@example.com")
        .with_telegram("@student")
        .with_category(category.id)
        .as_student(university_id=university.id, study_year=3)
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.is_student is True
    assert p.university_id == university.id
    assert p.study_year == 3


@pytest.mark.asyncio
async def test_join_existing_team_forces_non_leader(client: AsyncClient, session: AsyncSession, category_factory, team_factory):
    """Joining existing team should force team_leader=False."""
    category = await category_factory()
    team = await team_factory(category_id=category.id, team_name="ExistingTeam")

    payload = (
        FormBuilder()
        .with_email("joiner@example.com")
        .with_telegram("@joiner")
        .with_category(category.id)
        .with_team("ExistingTeam", is_leader=True)  # Try to join as leader
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200
    assert "приєдналися" in r.json()["message"].lower()

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.team_id == team.id
    assert p.team_leader is False  # Forced to non-leader


@pytest.mark.asyncio
async def test_participant_with_all_optional_fields(client: AsyncClient, session: AsyncSession, category_factory):
    """Participant with all optional fields filled should be stored correctly."""
    category = await category_factory()

    payload = (
        FormBuilder()
        .with_email("complete@example.com")
        .with_telegram("@complete")
        .with_category(category.id)
        .with_skills(["Python", "JavaScript", "Docker"])
        .seeking_job(
            "https://example.com/cv.pdf",
            "https://linkedin.com/in/complete",
            "Looking for backend role",
            work_consent=True
        )
        .with_comment("This is a test comment")
        .build()
    )

    r = await client.post("/form/", json=payload)
    assert r.status_code == 200

    p = await _get_participant(session, payload["email"])
    assert p is not None
    assert p.skills_text == "Python,JavaScript,Docker"
    assert p.wants_job is True
    assert p.cv_url == "https://example.com/cv.pdf"
    assert p.linkedin == "https://linkedin.com/in/complete"
    assert p.job_description == "Looking for backend role"
    assert p.work_consent is True
    assert p.comment == "This is a test comment"

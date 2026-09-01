from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.domain.models import (
    GroupCreate,
    GroupOut,
    MemberAdd,
    MemberOut,
    NextHostOut,
    PersonCreate,
    PersonOut,
    TelegramLinkOut,
)
from app.services import group_service, host_rotation_service

router = APIRouter(tags=["groups"])


@router.post("/people", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, session: Session = Depends(get_session)) -> PersonOut:
    return PersonOut.model_validate(group_service.create_person(session, payload))


@router.get("/people", response_model=list[PersonOut])
def list_people(session: Session = Depends(get_session)) -> list[PersonOut]:
    return [PersonOut.model_validate(person) for person in group_service.list_people(session)]


@router.get(
    "/people/{person_id}/groups",
    response_model=list[GroupOut],
    summary="Groups this person belongs to",
)
def list_groups_for_person(
    person_id: int, session: Session = Depends(get_session)
) -> list[GroupOut]:
    return [
        GroupOut.model_validate(group)
        for group in group_service.list_groups_for_person(session, person_id)
    ]


@router.get(
    "/people/{person_id}/telegram-link",
    response_model=TelegramLinkOut,
    summary="Deep link that binds this person's Telegram account",
)
def telegram_link(person_id: int, session: Session = Depends(get_session)) -> TelegramLinkOut:
    """Hand this URL to the person — as a link or a QR — and /start does the rest."""
    return group_service.build_telegram_link(session, person_id)


@router.post("/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, session: Session = Depends(get_session)) -> GroupOut:
    return GroupOut.model_validate(group_service.create_group(session, payload))


@router.get("/groups", response_model=list[GroupOut])
def list_groups(session: Session = Depends(get_session)) -> list[GroupOut]:
    return [GroupOut.model_validate(group) for group in group_service.list_groups(session)]


@router.get("/groups/{group_id}", response_model=GroupOut)
def get_group(group_id: int, session: Session = Depends(get_session)) -> GroupOut:
    return GroupOut.model_validate(group_service.require_group(session, group_id))


@router.post(
    "/groups/{group_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    group_id: int, payload: MemberAdd, session: Session = Depends(get_session)
) -> MemberOut:
    return group_service.add_member(session, group_id, payload)


@router.get("/groups/{group_id}/members", response_model=list[MemberOut])
def list_members(group_id: int, session: Session = Depends(get_session)) -> list[MemberOut]:
    return group_service.list_members(session, group_id)


@router.get(
    "/groups/{group_id}/next-host",
    response_model=NextHostOut,
    summary="Whose turn is it to host?",
)
def next_host(group_id: int, session: Session = Depends(get_session)) -> NextHostOut:
    """Read-only preview of the rotation decision, with the reason it was made."""
    return host_rotation_service.peek_next_host(session, group_id)

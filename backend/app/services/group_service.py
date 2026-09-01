"""People, groups and membership — the roster the rest of the system is scoped by."""

import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError
from app.domain.models import GroupCreate, MemberAdd, MemberOut, PersonCreate, TelegramLinkOut
from app.domain.tables import Group, Person
from app.repositories import group_repository, person_repository

logger = logging.getLogger(__name__)


def create_person(session: Session, payload: PersonCreate) -> Person:
    return person_repository.create(session, payload.name, payload.telegram_user_id)


def list_people(session: Session) -> list[Person]:
    return person_repository.list_all(session)


def require_person(session: Session, person_id: int) -> Person:
    person = person_repository.get(session, person_id)
    if person is None:
        raise NotFoundError(f"Person {person_id} does not exist.")
    return person


def build_telegram_link(session: Session, person_id: int) -> TelegramLinkOut:
    """The deep link this person scans to bind their Telegram account.

    The token is the person_id, unobscured. That is the same trade already made everywhere
    else: no endpoint authenticates either, and anyone can pass any person_id. Making this
    one spot cryptographic would not buy security the rest of the system does not have.
    """
    person = require_person(session, person_id)
    username = get_settings().telegram_bot_username
    return TelegramLinkOut(
        person_id=person.id,
        name=person.name,
        url=f"https://t.me/{username}?start={person.id}",
        linked=person.telegram_user_id is not None,
    )


def link_telegram_account(session: Session, person_id: int, telegram_user_id: int) -> Person:
    """Bind a Telegram account to a person, moving it if it was bound to someone else.

    telegram_user_id is UNIQUE, so re-scanning someone else's link has to release the old
    binding rather than fail. Re-scanning is the normal way to fix a mis-scan in a demo.
    """
    person = require_person(session, person_id)
    holder = person_repository.get_by_telegram_user_id(session, telegram_user_id)
    if holder is not None and holder.id != person.id:
        logger.info("Moving Telegram binding from person %s to person %s", holder.id, person.id)
        person_repository.clear_telegram_user_id(session, holder)
    return person_repository.set_telegram_user_id(session, person, telegram_user_id)


def create_group(session: Session, payload: GroupCreate) -> Group:
    return group_repository.create(session, payload.name)


def list_groups(session: Session) -> list[Group]:
    return group_repository.list_all(session)


def list_groups_for_person(session: Session, person_id: int) -> list[Group]:
    if person_repository.get(session, person_id) is None:
        raise NotFoundError(f"Person {person_id} does not exist.")
    return group_repository.list_for_person(session, person_id)


def require_group(session: Session, group_id: int) -> Group:
    group = group_repository.get(session, group_id)
    if group is None:
        raise NotFoundError(f"Group {group_id} does not exist.")
    return group


def add_member(session: Session, group_id: int, payload: MemberAdd) -> MemberOut:
    require_group(session, group_id)
    person = person_repository.get(session, payload.person_id)
    if person is None:
        raise NotFoundError(f"Person {payload.person_id} does not exist.")
    if group_repository.get_membership(session, group_id, payload.person_id) is not None:
        raise ConflictError(f"Person {payload.person_id} is already in group {group_id}.")

    member = group_repository.add_member(
        session, group_id, payload.person_id, payload.last_hosted_at
    )
    return MemberOut(
        person_id=member.person_id,
        name=person.name,
        is_active=member.is_active,
        last_hosted_at=member.last_hosted_at,
    )


def list_members(session: Session, group_id: int) -> list[MemberOut]:
    require_group(session, group_id)
    return [
        MemberOut(
            person_id=member.person_id,
            name=person.name,
            is_active=member.is_active,
            last_hosted_at=member.last_hosted_at,
        )
        for member, person in group_repository.list_members(session, group_id)
    ]

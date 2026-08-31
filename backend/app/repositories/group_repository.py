from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import Group, GroupMember, Person


def create(session: Session, name: str) -> Group:
    group = Group(name=name)
    session.add(group)
    session.flush()
    return group


def get(session: Session, group_id: int) -> Group | None:
    return session.get(Group, group_id)


def list_all(session: Session) -> list[Group]:
    return list(session.scalars(select(Group).order_by(Group.name)))


def list_for_person(session: Session, person_id: int) -> list[Group]:
    """Groups this person is an active member of — the home screen's roster."""
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.person_id == person_id, GroupMember.is_active.is_(True))
        .order_by(Group.name)
    )
    return list(session.scalars(stmt))


def add_member(
    session: Session, group_id: int, person_id: int, last_hosted_at: date | None
) -> GroupMember:
    member = GroupMember(
        group_id=group_id,
        person_id=person_id,
        is_active=True,
        last_hosted_at=last_hosted_at,
    )
    session.add(member)
    session.flush()
    return member


def get_membership(session: Session, group_id: int, person_id: int) -> GroupMember | None:
    stmt = select(GroupMember).where(
        GroupMember.group_id == group_id, GroupMember.person_id == person_id
    )
    return session.scalars(stmt).first()


def list_members(
    session: Session, group_id: int, active_only: bool = False
) -> list[tuple[GroupMember, Person]]:
    """Members with their person row, oldest membership first.

    The rotation order is deliberately *not* applied here — picking the next host is a
    decision, and decisions live in the service layer where they can be unit tested.
    """
    stmt = (
        select(GroupMember, Person)
        .join(Person, Person.id == GroupMember.person_id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at, GroupMember.id)
    )
    if active_only:
        stmt = stmt.where(GroupMember.is_active.is_(True))
    return [(member, person) for member, person in session.execute(stmt)]


def set_last_hosted_at(session: Session, group_id: int, person_id: int, hosted_on: date) -> None:
    membership = get_membership(session, group_id, person_id)
    if membership is not None:
        membership.last_hosted_at = hosted_on
        session.flush()

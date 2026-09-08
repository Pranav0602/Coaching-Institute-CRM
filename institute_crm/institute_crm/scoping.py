"""
Multi-tenant scoping primitives.

This institute runs several branches out of one database, so *every* read and write has to
be constrained to the branches the caller may see. Getting that wrong is the highest-impact
class of bug in the codebase, and it has a recognisable failure mode: a scope filter that
is applied *conditionally* - skipped when a query parameter is present, or skipped when the
caller happens to have no branch assigned - lets a caller read another branch's data simply
by passing the right parameter.

The helpers here exist so that scoping is applied unconditionally and fails **closed**:

* :func:`is_global` - is this caller allowed to see every branch?
* :func:`scope_to_branch` - AND a branch filter onto a queryset; a non-global caller with
  no branch gets ``.none()``, never the whole table.
* :func:`narrow` - apply *optional* filters. Because it only ever narrows, a caller-supplied
  filter can never widen a scope that was already applied.
* :func:`assert_same_branch` - the write-side counterpart, for guarding a create/update
  against a target that lives in another branch.

Rule for service authors: call :func:`scope_to_branch` **first**, then :func:`narrow`. Never
put an optional filter inside the same ``if`` that decides whether to scope.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from institute_crm.exceptions import PermissionDeniedError


def _role_code(actor) -> str | None:
    return getattr(actor, "role_code", None)


def is_global(actor) -> bool:
    """True when the caller may operate across every branch."""
    from accounts.models import Role

    if actor is None or not getattr(actor, "is_authenticated", False):
        return False
    return bool(getattr(actor, "is_superuser", False)) or _role_code(actor) == Role.SUPER_ADMIN


def actor_branch_id(actor):
    return getattr(actor, "branch_id", None)


def scope_to_branch(queryset, actor, *, branch_path: str = "branch"):
    """Restrict ``queryset`` to the branches ``actor`` may see.

    ``branch_path`` is the ORM path from the queryset's model to :class:`accounts.Branch` -
    ``"branch"`` for a directly-owned model, ``"batch__branch"`` or
    ``"lecture__timetable__batch__branch"`` for models that reach it through a relation.

    Fails closed: a non-global caller with no branch assigned sees nothing. That is
    deliberate. Returning the unfiltered table in this case (the previous behaviour) turned
    an incomplete user record into a cross-branch data leak.
    """
    if is_global(actor):
        return queryset

    branch_id = actor_branch_id(actor)
    if not branch_id:
        return queryset.none()
    return queryset.filter(**{f"{branch_path}_id": branch_id})


def scope_to_own_rows(queryset, actor, *, path: str):
    """Restrict ``queryset`` to rows belonging to ``actor`` (e.g. a student's own records)."""
    if actor is None or not getattr(actor, "is_authenticated", False):
        return queryset.none()
    return queryset.filter(**{f"{path}_id": actor.pk})


def child_student_user_ids(parent_user) -> list:
    """The ``User`` ids of the students linked to a parent account.

    Parents are granted read access to their children's records, and the relation is two
    hops (``ParentProfile`` -> ``StudentParent`` -> ``StudentProfile``). Centralised here so
    every app resolves it the same way and a parent with no linked child gets an empty list
    - which, combined with ``__in=[]``, correctly yields no rows.
    """
    if parent_user is None or not getattr(parent_user, "is_authenticated", False):
        return []

    from users_profiles.models import StudentProfile

    return list(
        StudentProfile.objects.filter(
            is_deleted=False, parent_links__parent__user_id=parent_user.pk
        ).values_list("user_id", flat=True)
    )



def narrow(queryset, filters: Mapping[str, Any]):
    """Apply optional filters, skipping empty values.

    Only ever *narrows*, so it is safe to call after :func:`scope_to_branch`::

        qs = scope_to_branch(qs, actor)
        qs = narrow(qs, {"course_id": course_id, "batch_id": batch_id})
    """
    clean = {key: value for key, value in filters.items() if value not in (None, "", [])}
    return queryset.filter(**clean) if clean else queryset


def assert_same_branch(actor, branch_id, *, message: str = "That record belongs to another branch.") -> None:
    """Write-side guard: refuse to touch a record outside the caller's branch."""
    if is_global(actor):
        return
    own = actor_branch_id(actor)
    if not own:
        raise PermissionDeniedError(
            "Your account is not assigned to a branch yet, so it cannot create or modify "
            "branch records.",
            code="no_branch_assigned",
        )
    if branch_id and str(branch_id) != str(own):
        raise PermissionDeniedError(message, code="cross_branch_denied")


def assert_role(actor, allowed: Iterable[str], *, message: str | None = None) -> None:
    """Guard an operation on the caller's role. Super admins always pass."""
    if is_global(actor):
        return
    allowed = tuple(allowed)
    if _role_code(actor) not in allowed:
        raise PermissionDeniedError(
            message or "You do not have permission to perform this action.",
            code="role_not_permitted",
        )


def resolve_write_branch(actor, requested_branch):
    """Decide which branch a newly created record belongs to.

    A non-global caller always writes into their own branch - a supplied value is not
    trusted, it is overridden. A global caller must name a branch explicitly, because
    guessing one for them would silently file records in the wrong place.
    """
    if not is_global(actor):
        own_id = actor_branch_id(actor)
        if not own_id:
            raise PermissionDeniedError(
                "Your account must be assigned to a branch before you can create this record.",
                code="no_branch_assigned",
            )
        if requested_branch is not None and str(getattr(requested_branch, "pk", requested_branch)) != str(own_id):
            raise PermissionDeniedError(
                "You can only create records for your own branch.",
                code="cross_branch_denied",
            )
        from accounts.models import Branch

        return requested_branch or Branch.objects.get(pk=own_id)

    if requested_branch is None:
        from institute_crm.exceptions import ValidationFailed

        raise ValidationFailed(
            "Branch is required.", field_errors={"branch": ["Branch is required."]}
        )
    return requested_branch

"""
Dashboard aggregation.

Rewritten from scratch. The previous version had two problems that mattered more than any
inefficiency:

1. It computed a ``branch_filter`` and then **never applied it**, so a branch admin's
   dashboard showed institute-wide student counts, revenue and attendance. Every figure
   crossed the tenant boundary.
2. Roughly half the response was hard-coded demo data - a fixed monthly growth series, a
   fixed branch league table, a fixed course popularity list - and the real aggregates were
   wrapped in ``or <plausible number>`` fallbacks. So an empty database reported
   "452,000 collected" and a real day with no attendance reported 92.5%. A dashboard that
   invents numbers is worse than one that shows zero, because nobody can tell which they are
   looking at.

Everything below is derived from the database and scoped through
:mod:`institute_crm.scoping`. Zero means zero.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from academics.models import Attendance, Course, CourseEnrolment, Lecture
from academics.services import BatchService
from accounts.models import Role, User
from assignments_exams.models import Exam, Result
from crm_leads.models import Admission, Lead
from finance.models import Installment, Payment
from institute_crm.scoping import is_global, scope_to_branch
from institute_crm.utils import active

ZERO = Decimal("0.00")

#: Roles that may see money. A teacher's dashboard has no revenue panel.
FINANCE_VIEWERS = (Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.RECEPTIONIST)

#: Roles that see institute- or branch-wide operational counts rather than their own slice.
OPERATIONS_VIEWERS = (
    Role.SUPER_ADMIN,
    Role.BRANCH_ADMIN,
    Role.RECEPTIONIST,
    Role.ADMISSION_COUNSELOR,
)

_MONEY = DecimalField(max_digits=14, decimal_places=2)


def _money_sum(queryset, field: str = "amount") -> Decimal:
    """``Sum`` that returns ``Decimal("0.00")`` rather than ``None`` for an empty set."""
    return queryset.aggregate(
        total=Coalesce(Sum(field), Value(ZERO, output_field=_MONEY), output_field=_MONEY)
    )["total"]


def _month_starts(count: int, *, ending: date) -> list[date]:
    """The first day of each of the last ``count`` months, oldest first."""
    year, month = ending.year, ending.month
    months: list[date] = []
    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


def _has_role(actor, allowed) -> bool:
    return is_global(actor) or getattr(actor, "role_code", None) in allowed


class DashboardAnalyticsService:
    """Read-only cross-app aggregation for the dashboard.

    Reuses each app's scoping rather than re-deriving it: the batch anchor comes from
    :meth:`academics.services.BatchService.visible_batches`, so a teacher's dashboard
    automatically covers the batches they teach and nothing else.
    """

    @staticmethod
    def dashboard(actor: User, *, months: int = 6) -> dict:
        today = timezone.localdate()
        months = max(1, min(int(months or 6), 24))

        batches = BatchService.visible_batches(actor)
        batch_ids = list(batches.values_list("id", flat=True))

        payload = {
            "generated_at": timezone.now(),
            "scope": DashboardAnalyticsService._scope(actor, batch_count=len(batch_ids)),
            "cards": DashboardAnalyticsService._cards(actor, batch_ids=batch_ids, today=today),
            "charts": DashboardAnalyticsService._charts(
                actor, batch_ids=batch_ids, today=today, months=months
            ),
        }
        return payload

    # ------------------------------------------------------------------- parts

    @staticmethod
    def _scope(actor: User, *, batch_count: int) -> dict:
        branch = getattr(actor, "branch", None)
        return {
            "role": getattr(actor, "role_code", None),
            "branch_id": str(branch.pk) if branch else None,
            "branch_name": branch.name if branch else None,
            "all_branches": is_global(actor),
            "visible_batches": batch_count,
            "shows_finance": _has_role(actor, FINANCE_VIEWERS),
        }

    @staticmethod
    def _cards(actor: User, *, batch_ids: list, today: date) -> dict:
        cards = {
            "total_students": scope_to_branch(
                active(User).filter(role__code=Role.STUDENT, is_active=True), actor
            ).count(),
            "total_teachers": scope_to_branch(
                active(User).filter(role__code=Role.TEACHER, is_active=True), actor
            ).count(),
            "active_batches": BatchService.filter_batches(actor, status="running").count(),
            "active_courses": (
                active(Course).count()
                if is_global(actor)
                else active(Course).filter(batches__id__in=batch_ids).distinct().count()
            ),
            "upcoming_exams": active(Exam)
            .filter(batch_id__in=batch_ids, exam_date__gte=timezone.now())
            .count(),
        }
        cards.update(DashboardAnalyticsService._attendance_card(batch_ids=batch_ids, today=today))

        if _has_role(actor, OPERATIONS_VIEWERS):
            leads = scope_to_branch(active(Lead), actor)
            cards["open_leads"] = leads.exclude(
                stage__in=[Lead.STAGE_ADMITTED, Lead.STAGE_LOST]
            ).count()
            cards["admissions_this_month"] = (
                scope_to_branch(active(Admission), actor, branch_path="batch__branch")
                .filter(admission_date__gte=today.replace(day=1))
                .count()
            )

        if _has_role(actor, FINANCE_VIEWERS):
            payments = scope_to_branch(active(Payment), actor, branch_path="student__branch")
            installments = scope_to_branch(
                active(Installment), actor, branch_path="student__branch"
            )
            collected_total = _money_sum(payments)
            collected_month = _money_sum(
                payments.filter(payment_date__date__gte=today.replace(day=1))
            )
            outstanding = _money_sum(
                installments.filter(status__in=["PENDING", "OVERDUE"])
            )
            # Anything unpaid whose due date has passed, whether or not a nightly job has
            # got round to re-flagging it as OVERDUE.
            overdue = _money_sum(
                installments.filter(
                    status__in=["PENDING", "OVERDUE"], due_date__lt=today
                )
            )
            cards.update(
                {
                    "total_fee_collection": collected_total,
                    "collection_this_month": collected_month,
                    "pending_fees": outstanding,
                    "overdue_fees": overdue,
                }
            )

        return cards

    @staticmethod
    def _attendance_card(*, batch_ids: list, today: date) -> dict:
        """Today's attendance percentage, or ``None`` when nothing has been marked yet.

        ``None`` is the honest answer for "no sessions marked today" and the UI renders it as
        a dash. The previous code returned 92.5 here.
        """
        marks = active(Attendance).filter(
            lecture__date=today, lecture__timetable__batch_id__in=batch_ids
        )
        totals = marks.aggregate(
            total=Count("id"),
            attended=Count("id", filter=Q(status__in=["PRESENT", "LATE"])),
            excused=Count("id", filter=Q(status="EXCUSED")),
        )
        countable = (totals["total"] or 0) - (totals["excused"] or 0)
        percentage = (
            round((totals["attended"] or 0) / countable * 100, 1) if countable else None
        )
        return {
            "todays_attendance_pct": percentage,
            "todays_sessions": active(Lecture)
            .filter(date=today, timetable__batch_id__in=batch_ids)
            .count(),
            "todays_marks_recorded": totals["total"] or 0,
        }

    @staticmethod
    def _charts(actor: User, *, batch_ids: list, today: date, months: int) -> dict:
        charts = {
            "course_popularity": DashboardAnalyticsService._course_popularity(batch_ids),
            "attendance_trend": DashboardAnalyticsService._attendance_trend(
                batch_ids=batch_ids, today=today, months=months
            ),
        }

        if _has_role(actor, OPERATIONS_VIEWERS):
            charts["lead_funnel"] = DashboardAnalyticsService._lead_funnel(actor)
            charts["growth_and_revenue"] = DashboardAnalyticsService._growth_and_revenue(
                actor, today=today, months=months
            )

        if is_global(actor):
            charts["branch_performance"] = DashboardAnalyticsService._branch_performance()

        if _has_role(actor, (Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.TEACHER)):
            charts["exam_performance"] = DashboardAnalyticsService._exam_performance(batch_ids)

        return charts

    # ------------------------------------------------------------------ series

    @staticmethod
    def _lead_funnel(actor: User) -> list[dict]:
        """Every stage in pipeline order, including the empty ones.

        Stages with no leads have to appear or the funnel chart silently changes shape from
        one day to the next.
        """
        counts = dict(
            scope_to_branch(active(Lead), actor)
            .values_list("stage")
            .annotate(count=Count("id"))
        )
        return [
            {"stage": label, "count": counts.get(code, 0)}
            for code, label in Lead.STAGE_CHOICES
        ]

    @staticmethod
    def _growth_and_revenue(actor: User, *, today: date, months: int) -> list[dict]:
        """Admissions and collections per month, in two grouped queries."""
        window = _month_starts(months, ending=today)
        start = window[0]

        admissions = dict(
            scope_to_branch(active(Admission), actor, branch_path="batch__branch")
            .filter(admission_date__gte=start)
            .annotate(bucket=TruncMonth("admission_date"))
            .values_list("bucket")
            .annotate(count=Count("id"))
        )

        shows_money = _has_role(actor, FINANCE_VIEWERS)
        revenue: dict[date, Decimal] = {}
        if shows_money:
            buckets = (
                scope_to_branch(active(Payment), actor, branch_path="student__branch")
                .filter(payment_date__date__gte=start)
                .annotate(bucket=TruncMonth("payment_date"))
                .values_list("bucket")
                .annotate(total=Sum("amount"))
            )
            # ``payment_date`` is a DateTimeField, so TruncMonth hands back a datetime while
            # the admissions series (a DateField) hands back a date. Normalise on the way in
            # rather than comparing mixed types at lookup time.
            for bucket, total in buckets:
                key = bucket.date() if isinstance(bucket, datetime) else bucket
                revenue[key] = revenue.get(key, ZERO) + (total or ZERO)

        series = []
        for month_start in window:
            row = {
                "month": month_start.strftime("%b %Y"),
                "month_start": month_start,
                "admissions": admissions.get(month_start, 0),
            }
            if shows_money:
                row["revenue"] = revenue.get(month_start, ZERO)
            series.append(row)
        return series

    @staticmethod
    def _course_popularity(batch_ids: list) -> list[dict]:
        rows = (
            active(CourseEnrolment)
            .filter(batch_id__in=batch_ids, status="ACTIVE")
            .values("course__title")
            .annotate(enrolments=Count("id"))
            .order_by("-enrolments")[:10]
        )
        return [
            {"course": row["course__title"], "enrolments": row["enrolments"]} for row in rows
        ]

    @staticmethod
    def _attendance_trend(*, batch_ids: list, today: date, months: int) -> list[dict]:
        window = _month_starts(months, ending=today)
        rows = (
            active(Attendance)
            .filter(
                lecture__timetable__batch_id__in=batch_ids,
                lecture__date__gte=window[0],
            )
            .annotate(bucket=TruncMonth("lecture__date"))
            .values("bucket")
            .annotate(
                total=Count("id"),
                attended=Count("id", filter=Q(status__in=["PRESENT", "LATE"])),
                excused=Count("id", filter=Q(status="EXCUSED")),
            )
        )
        by_month = {row["bucket"]: row for row in rows}

        series = []
        for month_start in window:
            row = by_month.get(month_start)
            countable = (row["total"] - row["excused"]) if row else 0
            series.append(
                {
                    "month": month_start.strftime("%b %Y"),
                    "month_start": month_start,
                    "percentage": round(row["attended"] / countable * 100, 1)
                    if countable
                    else None,
                    "sessions_marked": row["total"] if row else 0,
                }
            )
        return series

    @staticmethod
    def _branch_performance() -> list[dict]:
        """Super-admin only: the branch league table, built from real rows.

        Three separate aggregates rather than one join-heavy query, because joining students,
        payments and enrolments in a single statement multiplies the rows and inflates every
        sum.
        """
        from accounts.models import Branch

        students = dict(
            active(User)
            .filter(role__code=Role.STUDENT, is_active=True, branch__isnull=False)
            .values_list("branch_id")
            .annotate(count=Count("id"))
        )
        revenue = dict(
            active(Payment)
            .filter(student__branch__isnull=False)
            .values_list("student__branch_id")
            .annotate(total=Sum("amount"))
        )
        enrolments = dict(
            active(CourseEnrolment)
            .filter(status="ACTIVE")
            .values_list("batch__branch_id")
            .annotate(count=Count("id"))
        )

        table = [
            {
                "branch_id": str(branch.pk),
                "branch": branch.name,
                "students": students.get(branch.pk, 0),
                "active_enrolments": enrolments.get(branch.pk, 0),
                "revenue": revenue.get(branch.pk, ZERO),
            }
            for branch in active(Branch).order_by("name")
        ]
        table.sort(key=lambda row: row["revenue"], reverse=True)
        return table

    @staticmethod
    def _exam_performance(batch_ids: list) -> list[dict]:
        """Average score and pass rate per recent exam."""
        rows = (
            active(Result)
            .filter(exam__batch_id__in=batch_ids)
            .values("exam_id", "exam__title", "exam__total_marks", "exam__exam_date")
            .annotate(
                candidates=Count("id"),
                average=Avg("marks_obtained"),
                passed=Count("id", filter=Q(marks_obtained__gte=F("exam__passing_marks"))),
            )
            .order_by("-exam__exam_date")[:12]
        )
        return [
            {
                "exam_id": str(row["exam_id"]),
                "exam": row["exam__title"],
                "total_marks": row["exam__total_marks"],
                "exam_date": row["exam__exam_date"],
                "candidates": row["candidates"],
                "average_marks": round(float(row["average"]), 2) if row["average"] else 0.0,
                "pass_rate": round(row["passed"] / row["candidates"] * 100, 1)
                if row["candidates"]
                else None,
            }
            for row in rows
        ]

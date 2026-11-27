"""Seed the fee-sheet catalog and its Shivajinagar batches without duplicates."""
from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date

from accounts.models import Branch, Role, User
from accounts.services.branch_service import BranchService
from academics.models import Batch, Course, CourseEnrolment
from academics.services.batch_service import BatchService
from academics.services.course_service import CourseService
from users_profiles.models import StudentProfile


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "shivajinagar_fee_catalog.json"


def _load_data() -> dict:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CommandError(f"Unable to read fee catalog data at {DATA_PATH}: {exc}") from exc

    if data.get("source_offerings") != 60 or len(data.get("courses", [])) != 58:
        raise CommandError("Fee catalog data must contain 60 source entries and 58 unique courses.")

    course_codes = [item.get("code") for item in data["courses"]]
    batch_codes = [item.get("batch", {}).get("code") for item in data["courses"]]
    if len(course_codes) != len(set(course_codes)) or len(batch_codes) != len(set(batch_codes)):
        raise CommandError("Course and batch codes in the fee catalog must be unique.")

    for item in data["courses"]:
        batch = item["batch"]
        batch["start_date"] = parse_date(batch["start_date"])
        batch["end_date"] = parse_date(batch["end_date"])
        if not batch["start_date"] or not batch["end_date"] or batch["end_date"] < batch["start_date"]:
            raise CommandError(f"Invalid batch date range for course {item['code']}.")
        item["total_fee"] = Decimal(item["total_fee"])
    return data


def _course_defaults(item: dict) -> dict:
    return {
        "title": item["title"],
        "description": item["description"],
        "duration_months": item["duration_months"],
        "total_fee": item["total_fee"],
        "field_of_engineering": item["field_of_engineering"],
    }


def _course_matches(course: Course, defaults: dict) -> bool:
    return all(getattr(course, field) == value for field, value in defaults.items())


def _batch_matches(batch: Batch, course: Course, branch: Branch, expected: dict) -> bool:
    return (
        batch.course_id == course.pk
        and batch.branch_id == branch.pk
        and batch.name == expected["name"]
        and batch.start_date == expected["start_date"]
        and batch.end_date == expected["end_date"]
        and batch.max_capacity == expected["max_capacity"]
    )


class Command(BaseCommand):
    help = "Preview or seed the 58 fee-sheet courses and one batch per course at Shivajinagar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write missing or safe-to-refresh records (default is a preview).",
        )

    def handle(self, *args, **options):
        data = _load_data()
        branch_data = data["branch"]

        branch = Branch.objects.filter(code=branch_data["code"]).first()
        if branch and branch.is_deleted:
            raise CommandError(f"Branch code {branch_data['code']} belongs to a deleted branch.")
        if branch and branch.name != branch_data["name"]:
            raise CommandError(f"Branch code {branch_data['code']} is already used by another branch.")
        name_match = Branch.objects.filter(name__iexact=branch_data["name"], is_deleted=False).first()
        if name_match and branch and name_match.pk != branch.pk:
            raise CommandError("Shivajinagar exists under a different branch code.")
        if not branch and name_match:
            raise CommandError("A Shivajinagar branch exists under a different code; review it before seeding.")

        creates_course = 0
        updates_course = 0
        existing_course = 0
        creates_batch = 0
        existing_batch = 0
        prepared = []

        for item in data["courses"]:
            defaults = _course_defaults(item)
            course = Course.objects.filter(code=item["code"]).first()
            if course and course.is_deleted:
                raise CommandError(f"Course code {item['code']} belongs to a deleted course.")
            if course is None:
                creates_course += 1
            elif not _course_matches(course, defaults):
                external_batches = Batch.objects.filter(course=course, is_deleted=False)
                if branch:
                    external_batches = external_batches.exclude(branch=branch)
                has_enrolments = CourseEnrolment.objects.filter(course=course, is_deleted=False).exists()
                has_direct_students = StudentProfile.objects.filter(course=course, is_deleted=False).exists()
                if external_batches.exists() or has_enrolments or has_direct_students:
                    raise CommandError(
                        f"Course {item['code']} differs from the fee sheet and is already used; "
                        "refusing to change its fee or title."
                    )
                updates_course += 1
            else:
                existing_course += 1
            prepared.append((item, defaults, course))

        if branch:
            for item, defaults, course in prepared:
                if course is None:
                    continue
                expected = item["batch"]
                by_code = Batch.objects.filter(code=expected["code"]).first()
                if by_code:
                    if by_code.is_deleted or not _batch_matches(by_code, course, branch, expected):
                        raise CommandError(f"Batch code {expected['code']} is already used by different data.")
                    existing_batch += 1
                    continue
                if Batch.objects.filter(course=course, branch=branch, is_deleted=False).exists():
                    raise CommandError(
                        f"Course {course.code} already has a Shivajinagar batch with a different code."
                    )
                creates_batch += 1
            creates_batch += sum(1 for _, _, course in prepared if course is None)
        else:
            creates_batch = len(prepared)

        self.stdout.write(f"Fee-sheet rows: {data['source_offerings']}")
        self.stdout.write(f"Unique courses: {len(data['courses'])}")
        self.stdout.write(
            f"Branch: {'already present' if branch else 'will create'} "
            f"{branch_data['name']} ({branch_data['code']})"
        )
        self.stdout.write(
            f"Courses: {creates_course} to create, {updates_course} to refresh, "
            f"{existing_course} already matched"
        )
        self.stdout.write(
            f"Batches: {creates_batch} to create, {existing_batch} already matched"
        )
        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Preview only; no database changes were made."))
            return

        actor = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(role__code=Role.SUPER_ADMIN).first()
        )
        if actor is None:
            raise CommandError("A super administrator account is required to seed this catalog.")

        course_created = 0
        course_updated = 0
        batch_created = 0
        with transaction.atomic():
            if branch is None:
                branch = BranchService.create_branch(actor=actor, data=branch_data)

            for item, defaults, observed_course in prepared:
                course = Course.objects.filter(code=item["code"]).first()
                if course is None:
                    course = CourseService.create_course(
                        actor=actor,
                        data={"code": item["code"], **defaults},
                    )
                    course_created += 1
                elif not _course_matches(course, defaults):
                    CourseService.update_course(actor=actor, course=course, data=defaults)
                    course_updated += 1

                expected = item["batch"]
                batch = Batch.objects.filter(code=expected["code"]).first()
                if batch:
                    if batch.is_deleted or not _batch_matches(batch, course, branch, expected):
                        raise CommandError(f"Batch code {expected['code']} is already used by different data.")
                    continue
                if Batch.objects.filter(course=course, branch=branch, is_deleted=False).exists():
                    raise CommandError(
                        f"Course {course.code} already has a Shivajinagar batch with a different code."
                    )
                BatchService.create_batch(
                    actor=actor,
                    data={
                        "course": course,
                        "branch": branch,
                        **expected,
                    },
                )
                batch_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {course_created} courses created, {course_updated} refreshed, "
            f"{batch_created} batches created."
        ))

"""Import student roster rows from an .xlsx workbook into the CRM."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import posixpath
import re
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REQUIRED_COLUMNS = (
    "BRANCH",
    "REG NO",
    "STUDENT NAME",
    "MOB.NO",
    "COURSE",
    "SOFTWARES",
)


@dataclass(frozen=True)
class RosterRow:
    sheet: str
    row_number: int
    values: dict[str, str]


def _column_index(cell_reference: str) -> int:
    column = 0
    for character in re.sub(r"\d", "", cell_reference).upper():
        column = column * 26 + ord(character) - ord("A") + 1
    return column - 1


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", NS)).strip()

    value = cell.find("a:v", NS)
    if value is None or value.text is None:
        return ""
    raw = value.text
    if cell_type == "s":
        return shared_strings[int(raw)].strip()
    if cell_type == "n":
        # Phone numbers stored as Excel numbers should become text without a
        # trailing decimal; text-formatted numbers keep their original spelling.
        try:
            number = Decimal(raw)
            if number == number.to_integral_value():
                return str(int(number))
        except (InvalidOperation, ValueError):
            pass
    return raw.strip()


def _read_workbook(path: Path) -> list[RosterRow]:
    try:
        with ZipFile(path) as archive:
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relationship_targets = {
                relationship.attrib["Id"]: relationship.attrib["Target"]
                for relationship in relationships
            }

            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared_strings = [
                    "".join(text.text or "" for text in item.findall(".//a:t", NS))
                    for item in shared_root.findall("a:si", NS)
                ]

            imported: list[RosterRow] = []
            for sheet in workbook.findall("a:sheets/a:sheet", NS):
                relationship_id = sheet.attrib[f'{{{NS["r"]}}}id']
                target = relationship_targets[relationship_id]
                if target.startswith("/"):
                    worksheet_path = target.lstrip("/")
                else:
                    worksheet_path = posixpath.normpath(posixpath.join("xl", target))
                worksheet = ET.fromstring(archive.read(worksheet_path))
                sheet_data = worksheet.find("a:sheetData", NS)
                if sheet_data is None:
                    continue

                rows = []
                for row in sheet_data.findall("a:row", NS):
                    values = {
                        _column_index(cell.attrib["r"]): _cell_text(cell, shared_strings)
                        for cell in row.findall("a:c", NS)
                    }
                    if values:
                        rows.append((int(row.attrib.get("r", len(rows) + 1)), values))

                header_position = next(
                    (index for index, (_, values) in enumerate(rows) if any(values.values())),
                    None,
                )
                if header_position is None:
                    continue

                _, header_cells = rows[header_position]
                headers = [header_cells.get(index, "").strip() for index in range(max(header_cells) + 1)]
                missing_headers = [name for name in REQUIRED_COLUMNS if name not in headers]
                if missing_headers:
                    raise CommandError(
                        f"Sheet {sheet.attrib['name']!r} is missing required columns: "
                        f"{', '.join(missing_headers)}"
                    )

                for row_number, cells in rows[header_position + 1 :]:
                    values = {
                        header: cells.get(index, "").strip()
                        for index, header in enumerate(headers)
                        if header
                    }
                    if not any(values.values()):
                        continue
                    missing_values = [name for name in REQUIRED_COLUMNS if not values.get(name)]
                    if missing_values:
                        raise CommandError(
                            f"Sheet {sheet.attrib['name']!r}, row {row_number} has empty "
                            f"required cells: {', '.join(missing_values)}"
                        )
                    imported.append(
                        RosterRow(sheet.attrib["name"], row_number, values)
                    )
            return imported
    except CommandError:
        raise
    except (OSError, KeyError, ValueError, ET.ParseError, BadZipFile) as exc:
        raise CommandError(f"Could not read workbook {path.name!r}: {exc}") from exc


def _username_for(reg_no: str, used_usernames: set[str]) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", reg_no).strip("_").lower() or "student"
    base = f"roster_{slug}"[:140]
    candidate = base
    suffix = 2
    while candidate.casefold() in used_usernames:
        ending = f"_{suffix}"
        candidate = f"{base[:150 - len(ending)]}{ending}"
        suffix += 1
    used_usernames.add(candidate.casefold())
    return candidate


def _phone_parts(raw_phone: str) -> tuple[str, str | None]:
    parts = re.findall(r"\d+", raw_phone)
    if not 1 <= len(parts) <= 2:
        raise CommandError("Each MOB.NO cell must contain one or two phone numbers.")
    if any(len(part) > 20 for part in parts):
        raise CommandError("A phone number exceeds the CRM field limit of 20 characters.")
    return parts[0], parts[1] if len(parts) == 2 else None


class Command(BaseCommand):
    help = "Import student roster records from an Excel workbook. Defaults to a dry run."

    def add_arguments(self, parser):
        parser.add_argument("workbook", type=Path, help="Path to the .xlsx workbook")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Create student accounts and profiles (otherwise only preview)",
        )

    def handle(self, *args, **options):
        from accounts.models import Role, User
        from institute_crm import audit
        from users_profiles.models import StudentProfile

        workbook_path: Path = options["workbook"]
        if not workbook_path.is_file() or workbook_path.suffix.lower() != ".xlsx":
            raise CommandError("Provide an existing .xlsx workbook.")

        rows = _read_workbook(workbook_path)
        if not rows:
            raise CommandError("No student rows were found in the workbook.")

        seen_registrations: set[str] = set()
        for row in rows:
            values = row.values
            reg_no = values["REG NO"]
            normalized_reg_no = reg_no.casefold()
            if normalized_reg_no in seen_registrations:
                raise CommandError(
                    f"Duplicate registration number in workbook at "
                    f"{row.sheet!r}, row {row.row_number}."
                )
            seen_registrations.add(normalized_reg_no)
            limits = {
                "REG NO": (reg_no, 50),
                "STUDENT NAME": (values["STUDENT NAME"], 150),
                "BRANCH": (values["BRANCH"], 20),
                "COURSE": (values["COURSE"], 150),
            }
            for label, (value, maximum) in limits.items():
                if len(value) > maximum:
                    raise CommandError(
                        f"{label} is longer than {maximum} characters at "
                        f"{row.sheet!r}, row {row.row_number}."
                    )
            _phone_parts(values["MOB.NO"])

        student_role = Role.objects.filter(code=Role.STUDENT).first()
        if student_role is None:
            raise CommandError("The STUDENT role is not configured in this database.")

        existing_registrations = {
            value.casefold() for value in StudentProfile.objects.values_list("reg_no", flat=True)
        }
        new_rows = [
            row for row in rows if row.values["REG NO"].casefold() not in existing_registrations
        ]
        skipped = len(rows) - len(new_rows)
        existing_usernames = {
            value.casefold() for value in User.objects.values_list("username", flat=True)
        }
        existing_phones = {
            value for value in User.objects.exclude(phone__isnull=True).values_list("phone", flat=True)
            if value
        }
        phone_matches = sum(
            any(phone in existing_phones for phone in _phone_parts(row.values["MOB.NO"]) if phone)
            for row in new_rows
        )
        secondary_phone_count = sum(
            _phone_parts(row.values["MOB.NO"])[1] is not None for row in new_rows
        )

        self.stdout.write(f"Workbook rows: {len(rows)}")
        self.stdout.write(f"Already imported (same REG NO): {skipped}")
        self.stdout.write(f"New student records: {len(new_rows)}")
        self.stdout.write(f"New records with a secondary phone: {secondary_phone_count}")
        self.stdout.write(f"Phone values also used by existing accounts: {phone_matches}")
        self.stdout.write(
            "Study-area counts among new records: "
            + (", ".join(
                f"{branch}={count}"
                for branch, count in sorted(Counter(row.values["BRANCH"] for row in new_rows).items())
            ) or "none")
        )

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry run only; no records were written."))
            return
        if not new_rows:
            self.stdout.write(self.style.SUCCESS("Nothing to import."))
            return

        actor = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(role__code=Role.SUPER_ADMIN).first()
            or User.objects.filter(role__code=Role.BRANCH_ADMIN).first()
        )
        if actor is None:
            raise CommandError("An administrator account is required to audit this import.")

        created = 0
        with transaction.atomic():
            for row in new_rows:
                values = row.values
                reg_no = values["REG NO"]
                if StudentProfile.objects.filter(reg_no__iexact=reg_no).exists():
                    continue
                primary_phone, secondary_phone = _phone_parts(values["MOB.NO"])

                user = User(
                    username=_username_for(reg_no, existing_usernames),
                    email="",
                    # The workbook provides one full name, not reliable given/family
                    # name parts; keep it intact in first_name.
                    first_name=values["STUDENT NAME"],
                    last_name="",
                    phone=primary_phone,
                    role=student_role,
                    # The workbook's BRANCH column is an academic area, not a campus.
                    branch=None,
                )
                user.set_unusable_password()
                user.save(force_insert=True)
                audit.record_audit(
                    actor=actor,
                    action=audit.CREATE,
                    instance=user,
                    changes={
                        "role": Role.STUDENT,
                        "import_source": workbook_path.name,
                    },
                )

                profile = StudentProfile.objects.create(
                    user=user,
                    reg_no=reg_no,
                    secondary_phone=secondary_phone,
                    academic_branch=values["BRANCH"],
                    source_course_label=values["COURSE"],
                    source_softwares=values["SOFTWARES"],
                )
                audit.record_audit(
                    actor=actor,
                    action=audit.CREATE,
                    instance=profile,
                    changes={
                        "reg_no": reg_no,
                        "academic_branch": values["BRANCH"],
                        "source_course_label": values["COURSE"],
                        "source_file": workbook_path.name,
                        "source_sheet": row.sheet,
                        "source_row": row.row_number,
                    },
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {created} student records."))

# Coaching-Institute-CRM

## Shivajinagar fee catalog

The 58 unique courses and their Shivajinagar batches are defined in
`institute_crm/academics/data/shivajinagar_fee_catalog.json`. This data represents 60
entries from the Mechanical, Civil, and Electrical fee sheets; the identical Navisworks
and BIM 360 Design offerings are shared between the Civil and Electrical lists.

Preview the seed operation from the Django project directory:

```powershell
python manage.py seed_shivajinagar_catalog
```

Apply missing records with:

```powershell
python manage.py seed_shivajinagar_catalog --apply
```

The command is idempotent. It creates the Shivajinagar branch if needed, creates or
refreshes safe-to-update course catalog rows, and creates one batch per course. It stops
if a course is already used by another branch, an enrolment, or a directly linked student
and its fee-sheet values differ.

## Student cancellations & removal (Reception)

`StudentProfile.admission_status` tracks the admission lifecycle: `PENDING`, `ACTIVE`,
`ENROLLED`, `CANCELLED`. The reception desk (`RECEPTIONIST`, plus admins) can:

* `POST /api/v1/profiles/students/{reg_no}/cancel-admission/` `{reason}` — mark a
  non-enrolled admission cancelled (records `cancellation_reason`, `cancelled_at`;
  audited). A cancelled student cannot then be enrolled until reinstated.
* `DELETE /api/v1/profiles/students/{reg_no}/` `{confirm: true, reason}` — remove an
  **eligible cancelled-admission** record from active views. Requires explicit
  confirmation; only cancelled-admission records with no live enrolment/batch are
  eligible; active or enrolled students are rejected (`409`); non-reception/unauthorized
  callers are rejected (`403`); cross-branch records are hidden (`404`).

Removal is a **soft delete** (`is_deleted`, `deleted_at`, `deletion_reason`,
`deleted_by`) — history, related records and the `AuditLog` trail are retained; nothing
is hard-erased. `GET .../deletion-eligibility/` reports current eligibility.

## Branch filters

Super Admin can filter students and staff by branch:

* `GET /api/v1/profiles/students/?branch_id=<id>` or repeated/comma `branch_ids=`
* `GET /api/v1/profiles/teachers/?branch_id=...&branch_ids=...`
* `GET /api/v1/accounts/users/?branch_id=...&branch_ids=...`

Filters only **narrow**. Branch-level scoping is applied unconditionally first; a
non-global caller cannot read another branch's records by changing a URL, request, or
filter value. Other roles remain limited to their authorized branch. The student
directory adds a "Clear filters" reset; summary counts and pagination respect the filter.

## Teacher assignments

`academics.TeacherAssignment` binds a **teacher + branch + course** (one row per triple;
partial-unique; soft-deleted; audited). Branch Admins manage assignments in their own
branch; Super Admins have system-wide access. Existing batch-level assignment
(`Batch.teachers`) and per-slot `Timetable.teacher` are preserved; teacher visibility is
the union; teachers with no course assignment still work.

Endpoints under `/api/v1/academics/teacher-assignments/`:

* `GET` list (scoped; `teacher_id`/`branch_id`/`course_id` narrow; `my` own)
* `POST` `{teacher, branch, course | course_ids[], notes}` — assign teacher to branch +
  course(s). Validates active TEACHER role; teacher not in another branch (an unassigned
  teacher is moved into the branch); **selected courses must belong to that branch**
  (offered by an active batch); rejects invalid and duplicate assignments (`400`/`409`);
  cross-branch denied (`403`).
* `PATCH` change teacher/branch/course/notes with full re-validation + duplicate check.
* `DELETE` soft-delete (course lists stay accurate).
* `GET available-courses/?branch_id=` — courses offered at a branch (branch-scoped).

## Student profile editing

Authorized staff (`RECEPTIONIST`, `ADMISSION_COUNSELOR`, `BRANCH_ADMIN`,
`SUPER_ADMIN`) can `PATCH /api/v1/profiles/students/{reg_no}/`. **Every supported
profile field is editable**: personal (`dob`, `gender`, `blood_group`, `address`,
`emergency_contact`, `secondary_phone`), guardian (`guardian_name`,
`guardian_phone`, `guardian_relationship`), academic (`course`, `academic_branch`,
`source_course_label`, `source_softwares`, `documents_url`), and fee terms
(`agreed_fee`, `discount_amount`, `concession_amount`, `scholarship_amount`,
`fee_notes`). Contact (`first_name`, `last_name`, `email`, `phone`) is updated
through `/api/v1/accounts/users/{id}/`. **System-managed fields are protected**:
`reg_no`, `id`, `user`, `created_at`, `updated_at`, `deleted_at`, `version`,
`is_deleted`, `deleted_by`, `admission_status`, `cancellation_*`, `deletion_*`,
and computed read-only values cannot be set. Validation + existing permission
rules are re-applied; non-authorized callers are rejected (`403`); saved changes
are reflected everywhere. The "Edit Student Profile" dialog exposes all fields
with loading / success / error feedback.

## Assign batch to unassigned student

`POST /api/v1/profiles/students/{reg_no}/assign-batch/` `{batch}` (or clear with
`null`). Staff-only. Validates the student isn't already assigned that batch,
**batch is active and in the student's branch**, **batch course matches the
student's course** when set, student is active, no duplicate live enrolment,
and batch capacity. Syncs `StudentProfile.batch`, creates a `CourseEnrolment`,
updates `admission_status`, audited. The student dialog offers a batch picker
(valid batches only; empty/loading/success/error states). Missing/incomplete
course & batch assignments are handled safely.

## User Access & Roles filters (Super Admin)

`GET /api/v1/accounts/users/` accepts combined `name`, `email`, `reg_no`,
`course_id`, `batch_id`, `branch_id` (+ `role`, `search`, `is_active`). Filters
are applied server-side **after** the actor's visibility scope; results,
pagination (`page`/`page_size`) and counts reflect active filters; non-global
callers can't widen scope. User Management page exposes all filters + Clear
filters + pagination.

### Teacher dashboard

`GET /api/v1/academics/teacher-dashboard/` (teachers only; own scope) returns assigned
courses + branch, batches, **students enrolled per assigned course**, weekly/today
**schedule**, **attendance/progress**, **notices** (announcements), notifications,
**upcoming activities**, and **tasks** (submissions to grade) — all restricted to the
teacher's own assignments and branch.

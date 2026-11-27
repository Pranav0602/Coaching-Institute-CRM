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

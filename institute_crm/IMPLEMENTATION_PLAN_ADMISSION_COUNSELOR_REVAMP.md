# Implementation Plan — Admission Counselor Revamp

**Status:** Proposed | **Owner:** Frontend + Backend (Django REST / React MUI) | **Target release:** Next sprint

---

## 1. Objective

Revamp the Admission Counselor experience so that:

1. **The 8-stage lead pipeline moves out of the main dashboard and into the Sidebar.** Each pipeline stage becomes a sidebar menu item with a live count badge. The counselor lands on a lightweight *Counselling Desk overview* and drills into an individual stage board by clicking a stage in the sidebar.
2. **Every lead card displays Course, Batch, and Branch** alongside the student/customer identity, giving the counselor full context without opening the lead.

> Note: "Revoke the design" has been interpreted as **"Revamp the design"** (re-design / rework of the existing UI). Scope is limited to the Admission Counselor role; other roles are untouched.

---

## 2. Current State Analysis

| Area | File | Current Behaviour |
|---|---|---|
| Counselor dashboard | `frontend/src/pages/dashboards/AdmissionCounselorDashboard.jsx` | Renders the entire 8-stage pipeline as a single horizontal Kanban (`STAGES` array, 8 `<Paper>` columns, horizontally scrollable). Dense; stage columns get deep lists; main page is the pipeline itself. |
| Sidebar | `frontend/src/components/layout/Sidebar.jsx` | `getRoleMenuItems()` for `ROLES.ADMISSION_COUNSELOR` returns only 4 coarse links: *Counselling Desk, Lead Pipeline (8 Stages), Scheduled Follow-ups, Lead Conversion*. Two of these routes (`/followups`, `/convert`) do not exist in `App.jsx` and fall through to `Navigate to /`. |
| Routing | `frontend/src/App.jsx` | Single dashboard switch (`DashboardRouter`) with no per-stage route. |
| Lead model | `crm_leads/models.py` | `Lead` has `branch` (FK), `target_course` (free-text CharField), `stage`, `source`, `lead_owner`. **No `batch` FK and no structured `course` FK.** |
| API | `crm_leads/serializers.py` + `crm_leads/views/counselor_views.py` | `LeadSerializer` exposes `branch`, `branch_name`, `target_course`, `stage`. `LeadViewSet.get_queryset()` already supports `?stage=` and `?branch_id=` filters. No per-stage count endpoint. |
| Batch/Course source | `academics/models.py` | `Batch` has `course` (FK) and `branch` (FK). `Course` has `code/title/total_fee`. Available via `/academics/courses/` and `/academics/batches/`. |

### Gaps identified
- **Pipeline noise:** 8 horizontally-scrolling columns overload the landing page; no way to focus one stage.
- **Sidebar dead links:** `/followups` and `/convert` are not registered routes.
- **Missing context:** Lead cards show only course; branch/batch are not visible. Batch currently only exists on `Admission` after conversion, so leads can never surface a batch.
- **No count visibility:** Sidebar cannot show per-stage counts without an API call.

---

## 3. Target Design

### 3.1 Sidebar (Admission Counselor role)

```
ADMISSION COUNSELOR MODE
────────────────────────────
Counselling Desk            ( /            )
── Lead Pipeline ──────────────────────────
  New                  [badge n]
  Contacted            [badge n]
  Interested           [badge n]
  Demo Scheduled       [badge n]
  Demo Attended        [badge n]
  Admission Pending    [badge n]
  Admitted             [badge n]
  Lost                 [badge n]
── ───────────────────────────────────────
Scheduled Follow-ups     ( /followups  )
Lead Conversion          ( /convert    )
────────────────────────────
```

- Each stage is a first-class nav item (icon + live count `Chip` badge).
- "Lead Pipeline (8 Stages)" coarse link is **removed**; stages become a grouped sub-section.
- Active stage highlighted via `location.pathname` (same pattern already used by the sidebar's `.Mui-selected`).

### 3.2 Counselling Desk — landing page (`/`)

Slim replacement of the current Kanban. Contains:
- **Pipeline summary card:** horizontal funnel/progress chips — each stage with count, click-through to `/pipeline/<stage>`.
- **Quick actions:** *New Enquiry Lead*, *Refresh* (reuse existing handlers).
- **Today's follow-ups** list (from `FollowUp` API, optional phase).
- No full 8-column pipeline.

### 3.3 Stage board — `/pipeline/:stage`

Single-stage view; the "same page the counselor used to see, minus the other 7 columns":
- Header: stage name + description + count + filters (branch selector, optional course selector).
- Responsive grid of lead cards (`Grid`) instead of narrow Kanban columns.
- Each card (shared component) shows:

```
┌─────────────────────────────────────────────┐
│ Aarav Sharma                      ┃ phone   │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│ │ Course  │ │ Batch   │ │ Branch  │        │
│ │ FSW (…) │ │ B1/A1   │ │ Mumbai  │        │
│ └─────────┘ └─────────┘ └─────────┘        │
│ [Move Stage ▼]            [Convert ▸]      │
└─────────────────────────────────────────────┘
```

---

## 4. Design Decisions & Trade-offs

| # | Decision | Rationale |
|---|---|---|
| D1 | Add **nullable `batch` FK** (+ structured `course` FK) to `Lead`. | Batch/branch/course must be visible before admission. `target_course` is kept for backwards compat and free-text enquiries. |
| D2 | Sidebar counts come from a **new `GET /crm/leads/stage-counts/`** endpoint. | Avoids 8 separate list calls; one lightweight aggregate. Honors the counselor scoping already in `get_queryset` (`lead_owner = user OR null`). |
| D3 | New routes **`/pipeline/:stage`**; `/` becomes Counselling Desk. | Clean URL-per-stage, deep-linkable, and matches sidebar highlighting. |
| D4 | Extract a **shared `LeadCard`** component. | Reused by stage board + counsellor desk; single source for Course/Batch/Branch chips. |
| D5 | Counselor assigns **batch at "Demo Scheduled" or later** via card (PATCH), and confirm during Convert. | Batch is irrelevant at New/Contacted; prevents empty dropdowns and premature assignment. |
| D6 | Keep `FollowUp`/`Conversion` as separate pages (`/followups`, `/convert`) and register them. | Fixes the existing dead sidebar links; avoids scope creep. |

---

## 5. Implementation Phases

### Phase A — Backend (Django)

**A1. Model change** — `crm_leads/models.py`
```python
course = models.ForeignKey(
    'academics.Course', on_delete=models.SET_NULL, null=True, blank=True,
    related_name='leads')
batch = models.ForeignKey(
    'academics.Batch', on_delete=models.SET_NULL, null=True, blank=True,
    related_name='leads')
```
- Keep `target_course` (migration/back-compat path).
- Migration: `python manage.py makemigrations crm_leads && python manage.py migrate`.

**A2. Serializer** — `crm_leads/serializers.py`
- Add read-only fields: `course_id`, `course_title`, `batch_id`, `batch_name`, `batch_code`.
- `branch` / `branch_name` already present.
- Allow `batch` and `course` (write) in `fields` so `PATCH /crm/leads/:id/` can assign them.

**A3. Stage-count endpoint** — `crm_leads/views/counselor_views.py`
- Add `@action(detail=False, methods=['get'], url_path='stage-counts')` on `LeadViewSet`.
- Return `{ "New": n, "Contacted": n, ..., "Lost": n }` using the same scoped queryset (honors `?branch_id=` too).
- Must be registered **before** the router's `{pk}` catch so `/crm/leads/stage-counts/` resolves (DRF router handles `detail=False` actions correctly).

**A4. Optional filters**
- Extend `get_queryset` with optional `?course_id=` filter (parallels existing `stage`/`branch_id`).

**A5. Backend tests** — `crm_leads/tests.py` (new)
- Stage-count returns correct totals and respects counselor scoping.
- `PATCH` assigning `batch`/`course` persists and serializer emits `batch_name`.
- `?stage=` + `?branch_id=` filters still work after model change.

### Phase B — Frontend routing

**B1. `frontend/src/App.jsx`**
- Import new `PipelineStagePage`.
- Add:
  ```jsx
  <Route path="/pipeline/:stage" element={<PipelineStagePage />} />
  ```
- Register real routes for `/followups` and `/convert` (Phase D), removing the current `* → /` fallback for these.

### Phase C — Frontend sidebar

**C1. `frontend/src/components/layout/Sidebar.jsx`**
- Add a shared `PIPELINE_STAGES` constant (imported from one place — see C2).
- For `ROLES.ADMISSION_COUNSELOR`, render the pipeline stages as grouped `List` items under a *Lead Pipeline* section header, each with:
  - icon (e.g., `FiberManualRecord`/`Circle`, color-coded by stage),
  - count `Chip` badge populated from `/crm/leads/stage-counts/`,
  - active highlight when `location.pathname === /pipeline/<stage>`.
- Remove the coarse `Lead Pipeline (8 Stages)` item; keep `Counselling Desk`, `Scheduled Follow-ups`, `Lead Conversion`.
- Fetch stage counts once per mount (and refetch on route change into a pipeline page, or via a lightweight context).
- Add navigation: navigate to `/pipeline/${encodeURIComponent(stage)}`.

**C2. Shared constants** — new `frontend/src/constants/pipeline.js`
- Export `PIPELINE_STAGES = ['New','Contacted','Interested','Demo Scheduled','Demo Attended','Admission Pending','Admitted','Lost']` and stage→color map. Import from the dashboard + sidebar (single source of truth; currently duplicated inline in the dashboard).

### Phase D — Frontend pages

**D1. New `frontend/src/pages/pipeline/PipelineStagePage.jsx`**
- Reads `stage` from `useParams()`.
- Fetches `/crm/leads/?stage=<stage>` (reuse existing data-shaping logic from `AdmissionCounselorDashboard.fetchLeads`).
- Renders header (stage, count, description), branch filter dropdown (from `/accounts/branches/` or current-user branch), and a responsive `Grid` of `LeadCard`s.
- Batch assignment: when stage ≥ "Demo Scheduled", each card's menu includes "Assign Batch" which PATCHes `{ batch_id }` and refreshes.

**D2. New shared `frontend/src/components/leads/LeadCard.jsx`**
- Props: `lead`, `courses`, `batches`, `onStageChange`, `onConvert`, `onAssignBatch`.
- Displays name, phone, email, and three chips: **Course** (`lead.course_title || lead.target_course`), **Batch** (`lead.batch_name || 'Unassigned'`), **Branch** (`lead.branch_name`).
- Reuses the existing stage-move `Select` and Convert button markup from the current dashboard (moved verbatim).

**D3. Rework `frontend/src/pages/dashboards/AdmissionCounselorDashboard.jsx` → Counselling Desk**
- Remove the 8-column Kanban render.
- Replace with: pipeline summary chips (counts + click-through), quick actions (New Enquiry / Refresh), recent leads or today's follow-ups.
- Keep existing dialogs: New Lead (add **Branch** + **Course** selectors), Convert Lead (batch required — already present; show branch read-only).
- Rename file to `CounsellingOverview.jsx` (optional but clearer) and update the import in `App.jsx`.

**D4. Fix `/followups` and `/convert`** (small scope)
- Either register lightweight placeholder pages that reuse existing lead data, or route them to stage boards filtered to relevant stages (Follow-ups → stages with demo/follow-up data; Conversion → `Admission Pending`/`Admitted`). Full implementation out of scope; minimum is to remove the 404 fallback.

### Phase E — Verification & QA

| Check | Command / Action |
|---|---|
| Backend migrations applied | `python manage.py makemigrations crm_leads` → `python manage.py migrate` |
| Backend tests | `python manage.py test crm_leads` |
| Lint (frontend) | `npm run lint` (`.oxlintrc.json` present; add script if missing) |
| Build | `npm run build` |
| Manual smoke | Login as `ADMISSION_COUNSELOR`: sidebar shows 8 stage items + counts; click each stage → single-stage board; card shows Course + Batch + Branch; assign batch; convert a lead; counsellor desk has no kanban. |

---

## 6. File Change Summary

| File | Action | Detail |
|---|---|---|
| `crm_leads/models.py` | Edit | Add `Lead.course`, `Lead.batch` FKs (nullable). |
| `crm_leads/migrations/0002_lead_course_batch.py` | New (generated) | Schema migration. |
| `crm_leads/serializers.py` | Edit | `LeadSerializer`: add `course_id`, `course_title`, `batch_id`, `batch_name`, `batch_code`. |
| `crm_leads/views/counselor_views.py` | Edit | Add `stage-counts` action; optional `course_id` filter. |
| `crm_leads/tests.py` | New | Stage-count + batch/course PATCH + filter tests. |
| `frontend/src/constants/pipeline.js` | New | `PIPELINE_STAGES` + colour map. |
| `frontend/src/App.jsx` | Edit | Add `/pipeline/:stage` route; fix `/followups`, `/convert`. |
| `frontend/src/components/layout/Sidebar.jsx` | Edit | Pipeline stage sub-menu with count badges. |
| `frontend/src/components/leads/LeadCard.jsx` | New | Shared card with Course/Batch/Branch chips. |
| `frontend/src/pages/pipeline/PipelineStagePage.jsx` | New | Single-stage board. |
| `frontend/src/pages/dashboards/AdmissionCounselorDashboard.jsx` | Rework | → Counselling Desk overview (no kanban). |

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Adding FKs to `Lead` affects other writers (`PublicEnquiry`, `Register`, bulk-import) | All new fields nullable with `SET_NULL`; `target_course` retained; existing POST payloads keep working. |
| Counselor data scope (`lead_owner = user OR null`) breaks on new aggregate endpoint | Stage-count reuses the exact same `get_queryset` scoping so counts match lists. |
| `/pipeline/:stage` param with spaces (`Demo Scheduled`) | `encodeURIComponent` on nav, `decodeURIComponent`/default on read; keep a `* → /pipeline/New` guard for invalid stage. |
| Stale sidebar counts after stage move | Refetch counts on every pipeline page mount and after stage PATCH (single shared `usePipelineCounts` hook). |
| Dead `/followups`, `/convert` links | Register minimal pages (Phase D4) so no nav item 404s. |
| Horizontal scroll regression | Stage boards are responsive `Grid`; single stage never exceeds viewport. |

---

## 8. Definition of Done

- [ ] `Lead` model has nullable `course` + `batch` FKs; migration committed and applied.
- [ ] `LeadSerializer` returns `course_title`, `batch_name`, `batch_code`, `branch_name`.
- [ ] `GET /crm/leads/stage-counts/` returns per-stage totals respecting counselor scope.
- [ ] Sidebar shows all 8 pipeline stages with live count badges; active stage highlighted.
- [ ] `/pipeline/:stage` renders a single-stage board; invalid stage redirects safely.
- [ ] Lead cards display **Course, Batch, Branch** chips; batch assignable from `Demo Scheduled` onward.
- [ ] Counselling Desk (`/`) no longer shows the 8-column kanban.
- [ ] `/followups` and `/convert` no longer 404.
- [ ] Backend tests pass; frontend builds; manual smoke passes.

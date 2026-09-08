# Enterprise Coaching CRM — Mobile Product Implementation Plan

**Working title:** *CoachOS* (placeholder — see [§16 Open decisions](#16-open-decisions--user-review-required))
**Document owner:** Lead Developer
**Status:** Draft for approval — revision 2
**Created:** 2026-09-03
**Sibling documents:** `institute_crm/RAG_IMPLEMENTATION_PLAN.md` (historical design doc, not current state), `institute_crm/AWS_DEPLOYMENT_GUIDE.md` (reusable).

> **Revision note.** Revision 1 of this plan was reviewed against the actual `institute_crm/`
> codebase and three of its premises turned out to be wrong. Those corrections are folded in here and
> flagged with **📌 CORRECTED** so you can see what changed and why. The short version: the RAG
> retrieval service is a Python full-table scan with no vector index at all; `institute_crm/scoping.py`
> already implements the branch-scoping layer this plan's identity redesign would delete; and the web
> frontend's axios interceptor does *not* normalise the response envelope. All three change scope.

---

## 0. How to read this document

Sections 1–4 are the *what and why*. Sections 5–11 are the architecture the whole build hangs off.
Sections 12–15 are execution. Section 16 lists decisions I could not make for you.

Three markers are used throughout:

- **⚠️ CONTRADICTION** — this plan disagrees with a decision already recorded in the Graphix repo.
  Each needs an explicit ruling, not a silent override.
- **📌 CORRECTED** — revision 1 asserted something about the existing codebase that verification
  disproved. Read these; they are where the estimate moved.
- **🔍 USER REVIEW** — a product or commercial judgement rather than an engineering one.

---

## 1. Executive summary

We are building a **multi-tenant, mobile-first CRM and academic operations platform for coaching
institutes**, sold as a product rather than delivered as a project to one client.

The existing Graphix Technology CRM is a **single-tenant web application**: 38 models across 8 Django
apps, working and well-factored, but with the institute's identity living in configuration rather than
in the schema. It is an excellent *domain model* and a poor *product foundation*.

The plan: **new backend repository, ported domain, tenancy in from the first migration; one React
Native (Expo) app whose navigation forks by role; and a guided setup wizard that turns a fresh install
into a usable CRM in under ten minutes.**

### Decisions already ratified

| # | Decision | Chosen | Rejected |
|---|---|---|---|
| D1 | Backend lineage | New repo, port the proven domain from `institute_crm` | Retrofitting tenancy into the live Graphix repo; full greenfield re-modelling |
| D2 | Tenant isolation | Shared schema, `institute_id` on every tenant-owned row, hard-scoped by a default manager | Schema-per-tenant (`django-tenants`); Postgres RLS in v1 |
| D3 | v1 app scope | One binary, role-based navigation for all **eight** personas | Two apps (staff / learner); staff-only v1 |
| D4 | Commercial model | Self-serve onboarding + trial in v1; subscription billing deferred to v2 | Full billing in v1; admin-provisioned tenants only |

### What "done" means for v1

Three pilot institutes running their **daily** operations on the app — enquiry capture, follow-ups,
admissions, attendance, fee collection, parent communication — with zero data leakage between them,
and with an owner able to onboard without a call from us.

### Headline estimate

**40 engineering-weeks** of work (§12 breaks this down). At 2–3 engineers with realistic
parallelisation efficiency of roughly 65%, that is **24–30 calendar weeks**. Solo, budget **46 weeks**.

Revision 1 said 29 engineering-weeks and also, incoherently, "18–26 engineering weeks" in one place
and "18–26 calendar weeks" in another. That was wrong on both units and arithmetic. The increase to 40
comes almost entirely from four things verification exposed: the branch-scoping rewrite (§6.4), the
response-envelope/OpenAPI incompatibility (§7), the RAG retrieval rebuild (§6.6), and honest sizing of
the onboarding phase (§12).

---

## 2. Why this is a new product, not a reskin

"Make the Graphix CRM generic" sounds like a configuration exercise. It is not, and the reasons shape
every phase below.

**Identity stops being local.** In a single-tenant system a user belongs to the institute by
definition. In a product, one human legitimately belongs to several: a parent with children at two
coaching centres, a teacher taking evening batches at a competitor, a franchise owner running three
brands. Tenant-scoped user accounts force duplicate identities and duplicate passwords, and every
support ticket afterwards is about the wrong one. Identity becomes global; membership becomes
tenant-scoped. This is the most consequential schema change in the plan.

**`Branch` is not the tenant.** The existing schema already scopes nearly everything to `Branch`,
which is why this port is cheap — but `Branch` is an operating unit *within* an institute. The new
hierarchy is `Institute → Branch → data`, and `Branch.code`, currently globally unique, becomes unique
per institute.

**Roles stop being a fixed enum.** `Role.code` is a globally unique field over eight hard-coded
choices. Institutes want their own vocabulary ("Centre Head", not "Branch Admin") and their own
permission mixes — some let counsellors approve discounts, most do not. The eight canonical roles stay
as the permission substrate; names and grants become tenant data (§6.5).

**Configuration becomes a product surface.** Fee heads, receipt series, academic year boundaries,
attendance granularity, working days, grading scales, currency, tax treatment, timezone, and language
are all currently implicit or hard-coded. Each becomes a tenant setting with a sane default, because
"any coaching institute" spans a JEE factory in Kota, a spoken-English centre in Coimbatore, and a
UPSC academy in Delhi.

**Mobile is not a smaller web app.** The web CRM assumes a desk, a mouse, and a spreadsheet. The
mobile app is used standing in a corridor between lectures, on two bars of signal, one-handed. That
inverts priorities: the counsellor's twenty-second enquiry capture matters more than the report
builder; the teacher's offline attendance marking matters more than the timetable grid editor.

---

## 3. Scope: what belongs on mobile, and what does not

> **Mobile owns the daily loop. Web owns setup, bulk work, and analysis.**

| Work | Home | Reasoning |
|---|---|---|
| Enquiry capture, follow-ups, calls, WhatsApp | **Mobile** | Happens away from a desk; needs the dialler and camera |
| Attendance marking | **Mobile** | Happens in a classroom, often without signal |
| Fee collection + receipt sharing | **Mobile** | Happens at a counter or doorstep; receipt goes out over WhatsApp |
| Study material upload, assignment grading | **Mobile** | The teacher's phone *is* the scanner |
| Student and parent everything | **Mobile only** | They will never open a web app |
| KPI dashboards, approvals | **Both** | Owner checks on mobile, analyses on web |
| Timetable grid construction | **Web** | Two-dimensional drag-and-drop is hostile on a phone |
| Bulk CSV import of students | **Web** | File pickers and error-row correction need a keyboard |
| Fee structure and installment design | **Web** (mobile read-only) | Complex, infrequent, high-consequence |
| Reports, reconciliation, payroll | **Web** | Spreadsheet-adjacent by nature |

**Consequence:** the existing Vite/MUI frontend becomes the **institute back-office**, and porting it
onto the tenancy layer is a real line item (§12, Phase 10).

🔍 **USER REVIEW:** confirm you want to keep and port the web app. My recommendation is to keep it;
the alternative is a phone app with a settings menu forty screens deep.

### Explicitly out of scope for v1

Subscription billing with gateway-backed plan enforcement (D4 defers this). Full bidirectional offline
sync (§9). Live video classes. In-app chat threads — announcements and push only. Payroll and HR.
Franchise hierarchies above `Institute`. Custom report builder. Public marketing site. Each is a
defensible v2 candidate; none is needed to prove the product.

---

## 4. Technology stack

You proposed React Native + Django. I agree, and the sharpened version of that choice differs
meaningfully from the default one.

### 4.1 Backend — Django 5 + DRF (keep)

Keeping Django is right, and not merely the path of least resistance: the ported domain comes for free,
`django-admin` is a real internal back-office, migrations can be trusted with a shared-schema
multi-tenant database, and `drf-spectacular` gives us a schema we can compile into a typed mobile
client. A Node rewrite would buy nothing and cost 38 models.

| Concern | Choice | Notes |
|---|---|---|
| Framework | Django 5.x + DRF | Pin exact versions in Phase 0 |
| Database | **PostgreSQL 16+ with `pgvector`** | Hard requirement, no SQLite path — carried over from the Graphix ruling |
| Auth | `simplejwt` with rotation, **`token_blacklist` installed**, short access tokens | See §6.3; the existing config does *not* blacklist |
| API schema | `drf-spectacular`, **non-optional**, `OAS_VERSION` pinned | See §7 — this needs real work, not a checkbox |
| Async work | **Celery + Redis + `django-celery-beat`** | ⚠️ Contradiction below |
| Files | Presigned **direct-to-S3**, per-tenant key prefixes | See §10.4; not `django-storages` |
| Push | Provider-abstracted; Expo Push behind it in v1 | Swap to direct FCM/APNs without touching callers |
| Observability | Sentry + structured JSON logs carrying `institute_id` | Per-tenant error grouping |
| Hosting | AWS `ap-south-1`: ECS Fargate, RDS Postgres Multi-AZ, ElastiCache, S3 + CloudFront | `AWS_DEPLOYMENT_GUIDE.md` is a usable starting point |

> ⚠️ **CONTRADICTION — Celery and Redis.** `institute_crm/requirements.txt` records celery and redis
> as *"Deliberately NOT added — adding a broker before there is any task to run would be dead
> configuration."* That was correct for a single-tenant web app. It is not survivable here: push
> fan-out to thousands of devices, scheduled fee reminders, WhatsApp/SMS dispatch, receipt PDF
> generation, tenant provisioning, demo-data seeding, storage reconciliation, and document ingestion
> are all work that must not happen inside a request. **Recommendation: adopt Celery + Redis in the new
> repo** and treat the Graphix rule as scoped to Graphix. Needs your explicit ruling.

> ⚠️ **CONTRADICTION — test database.** The Postgres-only rule (`ImproperlyConfigured` on any other
> engine, no `USE_SQLITE`) is right for correctness and wrong for test speed — we flagged at the time
> that this would need resolving. Resolution: **keep Postgres-only, buy speed elsewhere** — a Postgres
> service container in CI, `--reuse-db`, `pytest-xdist`, transaction-wrapped tests, `factory_boy`
> instead of fixtures. No SQLite branch, not even for tests.

📌 **CORRECTED — `aws_services` is not reusable as a storage backend.** Revision 1 said we would
"reuse `aws_services/s3` helpers" with `django-storages`. In fact `aws_services/s3_service.py` is a
hand-rolled boto3 wrapper (`S3StorageService.upload_fileobj / generate_upload_url /
generate_download_url`) and `aws_services` is not even in `INSTALLED_APPS`. Adopting `django-storages`
would mean *replacing* it. Better call: keep the hand-rolled approach and build on
`generate_upload_url`, because §10.4 wants presigned direct-to-S3 uploads, which is what that helper
already does and which `django-storages` makes harder, not easier.

### 4.2 Mobile — React Native via Expo

Use **Expo with EAS**, not bare React Native. The decisive argument is **EAS Update**: a coaching CRM
in its first year ships fixes weekly, and waiting two days for App Store review to correct a fee
calculation is unacceptable. OTA JavaScript updates make that a ten-minute operation. Continuous Native
Generation keeps full native control via config plugins, so "managed" costs nothing in capability.

| Concern | Choice | Why over the obvious alternative |
|---|---|---|
| Runtime | Expo SDK (stable at kickoff) + EAS Build/Submit/Update | OTA updates; managed native modules; one CI story |
| Language | TypeScript, `strict: true` | 38 domain models is far past where JS is viable |
| Navigation | **Expo Router** (file-based, typed routes) | Role shells map to route groups — all eight of them |
| Server state | **TanStack Query** + persisted cache | Delivers the offline read layer almost free; Redux would be ceremony |
| Client state | **Zustand** (session, active institute, UI prefs only) | Small surface; no reducers for server data |
| Forms | `react-hook-form` + **Zod** | Zod schemas double as runtime validation of API responses |
| API client | **Generated from OpenAPI** | Only viable once §7 is fixed — currently the generated types would be wrong for every endpoint |
| UI primitives | **React Native Paper (MD3)** wrapped in our own `design-system/` | Continuity with the MUI web app; tenant branding drives theme tokens; a11y handled |
| Lists | `FlashList` | §13's 60fps-at-1000-rows budget is not reachable with `FlatList` |
| Secure storage | `expo-secure-store` (Keychain/Keystore) for tokens | Never `AsyncStorage` for credentials |
| Fast KV | `react-native-mmkv` for cache and prefs | Synchronous reads make cold start feel instant |
| Local DB | `expo-sqlite` — **only** the mutation outbox | Not a replica; see §9 |
| Notifications | `expo-notifications` + deep links into Expo Router | One registration path, both platforms |
| i18n | `i18next`, English-only at pilot, **structured for Hindi** | See R10; translation is deferred, extraction is not |
| Analytics | PostHog or Amplitude, **behind a consent gate** | Minors' data — §14.2 |
| E2E | **Maestro** | Cheaper and far less flaky than Detox at our flow count |

**On version numbers.** My reliable knowledge ends around May 2025 and this authoring environment has
no network egress, so I have deliberately written no Expo SDK or React Native version numbers. Phase 0
carries an explicit spike to pin current stable versions and confirm two things that materially affect
the plan: that Expo Router's typed-routes API is stable, and that `openapi-typescript` handles whatever
OAS version we pin. Do not let me assert a version from memory.

🔍 **USER REVIEW — UI library.** Paper gives consistency with the MUI web app and solid accessibility,
at the cost of looking somewhat stock. Tamagui or NativeWind would be more distinctive and mean
building more primitives ourselves. Recommendation: Paper primitives with our own composites on top,
because the requirement that actually matters is *white-labelling per institute*, not novelty — and
token-driven theming is easier over Paper.

---

## 5. What the port actually inherits

Precise numbers, because Phase 1's scope and the CI guard in §6.2 are both sized off them.

| App | Models | Notes |
|---|---|---|
| `accounts` | 4 | `Role`, `Branch`, `User`, `AuditLog` |
| `users_profiles` | 4 | Student / Teacher / Parent profiles, `StudentParent` |
| `crm_leads` | 5 | `Lead`, `FollowUp`, `CounsellingNote`, `Admission`, `Visitor` |
| `academics` | 8 | Course, Subject, Batch, CourseEnrolment, Timetable, Lecture, Attendance, StudyMaterial |
| `assignments_exams` | 5 | Assignment, Submission, Exam, ExamQuestionPaper, Result |
| `finance` | 6 | FeeStructure, FeeDiscount, Installment, Payment, Receipt, Refund |
| `communications` | 2 | Announcement, Notification |
| `rag` | 4 | KnowledgeDocument, DocumentChunk, IngestionJob, RagQueryAudit |
| **Total** | **38** | **32 inherit `BaseModel`; 6 do not** |

📌 **CORRECTED.** Revision 1 said "34 models" in three places and "30 domain models" in a fourth. The
real figure is 38. More importantly, **six models inherit `models.Model` or `AbstractUser` directly**,
not `BaseModel`: `Role`, `User`, `AuditLog`, `StudentParent`, `IngestionJob`, `RagQueryAudit`. That
detail is not trivia — it is the hole in revision 1's flagship isolation guard, fixed in §6.2 layer 7.
`StudentParent` matters most: it is the parent↔student join, i.e. the row that decides which children
a parent account can see, and it would have been invisible to a `BaseModel`-based check.

### 5.1 Assets worth preserving unchanged

- **`BaseModel`** — UUID pk, `created_at`/`updated_at`, `is_deleted` + `deleted_at` soft delete,
  `version` counter. `TenantModel` extends it.
- **The service layer convention** — `<app>/services/<domain>_service.py`, one `XxxService` of
  `@staticmethod`s, `@transaction.atomic` stacked below `@staticmethod`, module logger, domain
  exceptions from `institute_crm/exceptions.py` (`DomainError` and its eight subclasses) rather than
  DRF `ValidationError`, acting user passed explicitly as `actor=`, services never touch `request`,
  serialisation left to serializers. Views authenticate, validate, call one service, serialise. This is
  a genuine asset; the new repo inherits it intact.
- **`institute_crm/scoping.py`** — 11 helpers (`is_global`, `scope_to_branch`, `scope_to_own_rows`,
  `child_student_user_ids`, `narrow`, `assert_same_branch`, `assert_role`, `resolve_write_branch`, …)
  that constitute the *entire* current isolation story. See §6.4 — this module is the single biggest
  piece of rework in the port, and revision 1 did not mention it at all.

### 5.2 Things not to port

- **The hardcoded embedding dimension.** `rag/services/embedding_service.py` sets
  `EMBEDDING_DIM = 1536` as a class constant and reads `os.environ` directly, while
  `RAG_EMBEDDING_MODEL` and `RAG_EMBEDDING_DIMENSIONS` sit in settings *unread*. Changing embedding
  model later requires a coordinated re-index; a hardcoded constant hides that dependency.
- **The retrieval implementation.** See §6.6. It needs replacing, not porting.
- **`cognito_sub`.** Replace with a generic `external_idp_sub` for future SSO. Per-tenant Cognito user
  pools add real complexity for no gain at this scale (R6).
- **`version` as if it were a lock.** `BaseModel.save()` increments it and nothing ever compares it.
  The docstring calls it "optimistic-locking"; it is a change counter. §9 depends on making it real.
- **The absence of pagination.** There is no `DEFAULT_PAGINATION_CLASS` and no `pagination_class`
  anywhere in the backend — every list endpoint returns the whole table. See §7.3.

---

## 6. Tenancy architecture

This section is the foundation. Everything else is replaceable; this is not.

### 6.1 Identity and membership

```
  User  (global identity)                    Institute  (the tenant)
  ────────────────────────                   ───────────────────────
  phone  (E.164, unique)                     slug, display_name, branding
  email  (unique, nullable)                  locale / currency / timezone
  credentials, external_idp_sub              plan, status, limits
  token_generation  (int)                    onboarding_state, onboarding_data
  NO institute FK — ever                     academic_years  →  AcademicYear
            │                                          │
            └──────────────  Membership  ──────────────┘
                     user × institute
                     primary_role  (FK Role)
                     capabilities  (resolved from InstituteRole)
                     status: INVITED | ACTIVE | SUSPENDED | LEFT
                     membership_generation  (int)
                     employee_id, joined_at
                             │
                     BranchAssignment  (effective-dated)
                     membership × branch × valid_from × valid_to
```

`User` carries **no** tenant foreign key. All tenant association flows through `Membership`. The
consequences are all good: one login for a parent with children at two institutes; a teacher
moonlighting at a second centre keeps one account; deactivating someone at one institute cannot affect
another; and "claim your pre-created account" becomes possible because phone is a global lookup key.

**One `Membership` per `(user, institute)`, enforced by a partial unique constraint.** Revision 1 left
this ambiguous and suggested `extra_roles` as an M2M — which was a design bug, because §6.3's token
carries a single scalar role, so extra roles would be invisible to any check trusting the claim.
Corrected design: **one membership, one `primary_role`, and a resolved `capabilities` set** (§6.5). The
multi-hat senior teacher who also counsels walk-ins is expressed by granting counselling capabilities
to their membership, not by giving them two roles.

**Branch is effective-dated, not a column on the membership.** A student who transfers branches mid-year
is a real and common event, and both naive answers are wrong: mutating `Membership.branch` makes every
historical branch-scoped `Attendance` and `Payment` row inconsistent with the membership that explains
it, while creating a second membership splits their fee ledger mid-installment-plan. So:
`BranchAssignment(membership, branch, valid_from, valid_to)`, historical rows are read at **the row's
own** `branch_id` rather than the actor's current one, and a mid-plan installment collects into the
branch that was effective on the installment's due date. This needs to be decided now because it is a
schema shape, not a feature.

### 6.2 Isolation enforcement — eight layers

Shared-schema tenancy (D2) is the right economic choice; its weakness is that isolation depends on
every query being correct. We do not rely on discipline. We make the wrong thing hard to write and
impossible to merge.

1. **`TenantModel(BaseModel)`** — abstract base adding
   `institute = FK(Institute, on_delete=PROTECT, db_index=True)`. Note `PROTECT`, not `CASCADE`; see
   §6.8 for why cascading a tenant delete is unacceptable.
2. **Scope acquisition, from more than one source.** `InstituteScopeMiddleware` sets a
   `contextvars.ContextVar` (not a thread-local, so it survives ASGI). The scope comes from the JWT
   claim for API callers — but a JWT is not the only caller, which revision 1 missed entirely. See
   §6.7.
3. **`TenantManager` as the default manager** — `get_queryset()` filters on the ambient institute, and
   raises `TenantScopeMissing` if a tenant-model query runs with no scope set, rather than returning
   everything.
4. **Scope is entered explicitly, never bypassed.** The only escape is a
   `with institute_scope(institute_id):` context manager. There is **no public `.unscoped()`**.
   Revision 1 described both mechanisms in different sections and they are not the same thing — one
   sets ambient scope and queries normally, the other bypasses scoping and filters by hand. The second
   is the one that leaks, so it does not exist. Cross-tenant reads live in exactly one audited module
   (§6.7).
5. **Write stamping** — `save()` stamps `institute` from ambient scope and raises if an explicitly-set
   value disagrees.
6. **Cross-tenant FK validation** — a service-layer assertion plus a test that walks every FK between
   two `TenantModel`s and proves a mismatched pair is rejected. Postgres cannot express this as a
   single-row check constraint, so it is enforced in code and *proven by test*.
7. **The isolation matrix test and the CI guard — enumerated from `django.apps`, not from a base
   class.** This is the most important correction in the document. Revision 1 said the matrix test
   "enumerates every model inheriting `TenantModel`" and the CI guard "fails if a model inherits
   `BaseModel` instead of `TenantModel`". Both miss a model inheriting `models.Model` **directly** —
   which is precisely what six models in the existing repo do (§5). A forgotten model would be
   invisible to the test (not a `TenantModel`) and pass the guard (not a `BaseModel`). Corrected: the
   guard asserts that **every concrete model in a tenant app is a `TenantModel` unless explicitly
   allow-listed**, walking `django.apps.apps.get_models()`. The matrix test then creates two institutes
   with parallel data and asserts every list, retrieve, update, and delete path denies cross-tenant
   access — covering new models the moment they are added.
8. **Performance as part of correctness** — composite indexes led by `institute_id` on every hot path,
   tenant-prefixed cache keys, and a partial-unique-index strategy (§6.8).

**Deferred but designed-for:** Postgres Row-Level Security as v2 hardening. We rejected it for v1 (D2)
because it complicates every migration and all reporting paths, but if an institute's security review
ever demands database-level isolation, RLS over these same `institute_id` columns is additive rather
than a re-architecture.

### 6.3 The token, and making revocation actually work

```
access claims: { user_id, membership_id, institute_id, role, capabilities_hash,
                 branch_id, token_generation, membership_generation, jti, exp }
```

Switching institutes is an explicit server operation — `POST /api/v1/auth/switch-institute/` — which
verifies an `ACTIVE` membership in the target and mints a new pair scoped to it. There is no
`X-Institute-Id` header and no query parameter, because any such mechanism is one missing check away
from a cross-tenant read.

**Revocation is the hard part, and revision 1 had no answer.** It baked `institute_id`, `role`, and
`branch_id` into the token while `Membership.status` supported `SUSPENDED`, and connected the two
nowhere. With the existing default of `JWT_ACCESS_MINUTES=480`, sacking a counsellor at 10:00 leaves
their token valid until 18:00. The same gap covers role demotion, branch transfer, a student dropping
out, and suspending the institute itself.

Fix, in three parts:

- **Access tokens drop to 10–15 minutes**, with rotating refresh tokens. This alone bounds the exposure
  window.
- **Two generation counters** — `User.token_generation` and `Membership.membership_generation` — are
  carried as claims and compared against a Redis-cached value on each request. Bumping either
  invalidates every outstanding token for that user or membership *immediately*. The cache read is a
  single keyspace hit, which fits the §13 latency budget; a cache miss falls through to the database.
- **`token_blacklist` actually installed.** The existing config sets `ROTATE_REFRESH_TOKENS: True` but
  `BLACKLIST_AFTER_ROTATION: False`, and `rest_framework_simplejwt.token_blacklist` is not in
  `INSTALLED_APPS` — so today nothing is blacklisted. Both change.

📌 **CORRECTED — "reuse detection" is not a simplejwt feature.** Revision 1 promised "rotating refresh
tokens with reuse detection". simplejwt gives blacklisting; detecting replay of an already-rotated
token and revoking the whole token *family* is custom work. It is worth building — replay of a stolen
refresh token is the realistic mobile attack — but it is a line item, not a setting, and Phase 1 now
budgets for it.

### 6.4 Branch scoping — the layer revision 1 deleted by accident

📌 **CORRECTED, and this is the largest scope change in the document.**

`institute_crm/scoping.py` is a 165-line module implementing the entire current isolation story:
`is_global(actor)`, `scope_to_branch(qs, actor)`, `scope_to_own_rows`, `child_student_user_ids`,
`assert_same_branch`, `assert_role`, `resolve_write_branch`. Every one of these reads
`actor.role_code` and `actor.branch_id` **off the `User` model** — and §5.2's identity redesign moves
both of those onto `Membership`. So do all nine permission classes in `accounts/permissions.py`, and
`rag/services/retrieval_service.py` reads `actor.branch` and `actor.role` too.

Revision 1 rated the `BaseModel → TenantModel` migration "Low risk" across 30 models. That rating was
wrong. The mechanical re-basing is indeed low risk; **the scoping rewrite that necessarily accompanies
it is not**, because it touches every permission class, every service that calls `scope_to_branch`, and
every caller of `actor.role_code`.

The corrected design, which the plan needs to state explicitly because two scope levels must compose:

- **`TenantManager` filters `institute_id` only.** Branch is a second, *narrower* scope and is applied
  deliberately, not ambiently — because plenty of legitimate queries are institute-wide (an owner's
  cross-branch dashboard) and an ambient branch filter would silently break them.
- **`scoping.py` is rewritten to read from the request's `Membership`**, not from `User`. The function
  signatures survive; their internals and their `actor` contract change. Keeping the signatures is
  deliberate — it means the ~dozens of existing call sites port mechanically.
- **Branch-less tenant models exist** (institute-wide settings, fee structures, announcements) and
  `scope_to_branch` must no-op safely on them rather than filtering on a null column.
- **The isolation matrix test covers branch isolation as well as institute isolation.** A Branch Admin
  at branch A must be denied branch B's rows, and that is a different test axis from tenant isolation.

### 6.5 Roles and capabilities

Revision 1 said "display names and permission grants become tenant data" and specified nothing further.
That is not a design. Concretely:

- **`Role`** stays as the canonical substrate: the same eight codes, globally unique, not tenant data.
  It is what the permission code reasons about.
- **`Capability`** is the atom of authorisation: a bespoke string like `finance.discount.approve` or
  `leads.reassign`, deliberately *not* a Django `Permission` (which is model-and-CRUD shaped, while
  half of what institutes want to toggle is action-shaped).
- **`InstituteRole(institute, role, display_name, capabilities)`** holds the tenant's vocabulary and its
  grant set, seeded from a per-role default at institute creation so a tenant that never touches it
  behaves exactly like the Graphix defaults.
- **Resolution is cached, not queried per request.** The membership's resolved capability set is
  computed on login and on any `InstituteRole` change, stored in Redis, and summarised in the token as
  `capabilities_hash` so a stale token is detectable. A per-request DB read of grants would sit
  directly under the §13 p95 budget.
- **Two guardrails.** A tenant cannot grant a capability its plan tier does not include, and a tenant
  admin cannot grant themselves a capability they do not already hold — otherwise the grant system is
  a privilege-escalation surface rather than a permission system.
- **The nine existing `BasePermission` classes become one** capability-checking permission class
  parameterised by required capability. That is a simplification, but it is also a rewrite of every
  view's `permission_classes`.

### 6.6 RAG multi-tenancy — the premise was wrong, and the real problem is worse

📌 **CORRECTED.** Revision 1 warned at length that "the tenant filter must be applied to the ANN search
itself, not to its results", and advised filtering "in the same statement as the `<=>` distance
operator" while expecting "degraded HNSW recall under selective filters".

There is no ANN search. `rag/services/retrieval_service.py` loads every matching chunk into Python and
scores in a loop:

```python
chunks_qs = DocumentChunk.objects.filter(doc_filter).select_related('document')
...
for chunk in chunks_qs:
    dot_product = sum(a * b for a, b in zip(chunk.embedding, query_embedding))
```

There is no `<=>` operator, no distance ordering in SQL, and **no `hnsw` or `ivfflat` index in
`rag/migrations/`** — verified by grep. So the warning was about the wrong failure mode. The actual one
is worse: an unbounded full-table scan that pulls every 1536-float embedding into the web process and
scores it in interpreted Python. That does not survive one busy tenant, let alone §13's target of 1,000
institutes.

The corrected requirement is **replace the retrieval implementation**, not move a `WHERE` clause:

- Real `pgvector` ANN search with a distance operator in SQL and an `hnsw` index created in a migration.
- `institute_id` on `KnowledgeDocument` and `DocumentChunk`, filtered **inside** the same statement as
  the distance ordering — so the original warning still applies, it just applies to code that does not
  exist yet.
- Expect and measure recall degradation under a selective tenant filter; if it bites, partition
  `DocumentChunk` by `institute_id`.
- **The embedding dimension comes from settings**, not a class constant (§5.2).
- **A cross-tenant retrieval leakage test as a release gate**: ingest distinctive documents into two
  institutes, assert neither institute's retrieval ever surfaces the other's chunks. A misordered
  filter here surfaces one institute's internal documents inside another's answer, which is
  product-ending.

This is why RAG gets its own phase in §12 rather than sharing one with assessments.

### 6.7 Non-JWT callers, and platform support access

Two gaps revision 1 left, both of which would have been discovered painfully.

**Callers with no JWT.** §4.1 sells `django-admin` as a day-one back-office, while §6.2 layer 3 raises
`TenantScopeMissing` when there is no institute in scope. Django admin is session-authenticated, so
every changelist would raise. The same hole swallows the DRF browsable API, `manage.py` commands, health
checks, and schema generation. Each needs a stated answer: admin gets an institute selector that sets
scope per request (and platform staff see a tenant picker); management commands take an explicit
`--institute` or wrap themselves in `institute_scope`; health checks and schema generation touch no
tenant models and are asserted not to.

**Platform support access.** The words "superadmin" and "impersonate" appeared nowhere in revision 1,
and `Role.SUPER_ADMIN` is an *institute*-level role, not us. Without a design, support will reach for a
shell and a raw cross-tenant query — exactly the practice layer 4 exists to prevent. So:

- **`PlatformStaff`** is a separate concept from `Role.SUPER_ADMIN`, living outside `Membership`.
- **Impersonation is a grant, not a capability**: `POST /platform/impersonate/{institute}` mints a
  time-boxed token carrying `impersonated_by`, and every write made under it is audited with that
  attribution.
- **Impersonated sessions are read-only by default**, with write access requiring a second explicit
  step and a reason string.
- **The access log is visible to the tenant.** "Our staff can silently read your students' data" fails
  the first institute security review, and coaching institutes hold minors' data.
- **Cross-tenant support search** ("a parent phoned, which institute are they in?") lives in one
  audited module with `PlatformStaff` authorisation, because it is the single operation most likely to
  be implemented as an ad-hoc unscoped query.

### 6.8 Deletion, uniqueness, and retention

Three collisions between soft delete and the rest of the design, none of which revision 1 examined.

**Soft delete versus per-tenant unique constraints.** `utils.py` states rows are never removed by the
application. A plain `unique_together(institute, code)` on `Branch` therefore means that soft-deleting
branch `MAIN` permanently prevents recreating `MAIN`, with an error message about a row the user cannot
see. The same trap applies to receipt series, `Membership.employee_id`, student roll numbers,
`InstituteRole` names, and `Institute.slug`. Every per-tenant uniqueness rule must be a **partial
index**: `UniqueConstraint(fields=[...], condition=Q(is_deleted=False))`.

**Tenant deletion versus financial retention.** §14.2 commits to hard delete on offboarding; `utils.py`
requires that financial records survive. `on_delete=CASCADE` on the tenant FK would resolve that
conflict in the wrong direction, silently, which is why §6.2 layer 1 specifies `PROTECT`. The actual
resolution is a policy: offboarding triggers export, then anonymisation of personal data, then a
retention hold on financial rows for the statutory period, then hard delete. Indian statutory retention
on financial records and DPDP erasure rights genuinely conflict here, and the resolution is legal, not
technical (R11).

**Gapless receipt numbering.** Financial receipt numbers must be gapless and per-institute, which means
`SELECT ... FOR UPDATE` on a per-tenant counter row inside the payment transaction, not `max(number)+1`.
Getting this wrong produces duplicate receipt numbers under concurrent collection — an audit problem,
not a bug report.

### 6.9 Time, and the academic year

**Timezone.** `settings.py` has one global `TIME_ZONE = "Asia/Kolkata"`. Revision 1 collected a
timezone on `Institute` and then never used it. But every headline feature is a *local-day* computation:
"today's follow-ups", "today's collections", day close, attendance for a date, quiet hours, fee due
dates. Each needs `timezone.override(institute.timezone)` wrapped around request handling **and** inside
every Celery task — which is exactly where it will be forgotten, since a worker has no request to
inherit from. A Dubai or Kathmandu tenant otherwise gets a day-close at the wrong hour and an attendance
date boundary off by hours. Push recipients may also sit in a different zone than the institute, so
quiet hours resolve against the *recipient*.

**`AcademicYear` is a first-class model, not two settings fields.** Revision 1 collected "academic year
start/end" as scalars, which makes the year a mutable pair of dates. That fails the most predictable
annual operation a coaching institute performs: prior-year data cannot be partitioned or archived, fee
structures and batches cannot be versioned per year, "attendance % this year" becomes unanswerable once
the dates move, and the promotion event — students advance a level, batches close, new fee structures
issue, alumni separate from actives — has no home. It lands on all three pilots simultaneously and it is
a schema change if discovered late. So: `AcademicYear(institute, name, starts_on, ends_on, status)`, and
every year-scoped model carries an `academic_year` FK.

---

## 7. The API contract — the largest execution risk after tenancy

📌 **CORRECTED, and this one silently invalidated two of revision 1's named CI gates.**

### 7.1 The envelope versus the generated client

`StandardResponseRenderer` wraps payloads **at render time** into `{success, message, data}`, and
`custom_exception_handler` produces `{success, message, errors, status_code}`. `drf-spectacular`, by
contrast, derives response schemas from `serializer_class` — so **the generated OpenAPI describes the
bare object while the wire format is the envelope**. Two consequences:

- Revision 1's claim that a generated client means "backend and app cannot drift; renaming a field
  breaks the build, not production" is false as stated. The generated types would be wrong for *every*
  endpoint from day one, so they could not detect drift at all.
- Revision 1's CI gate "`schemathesis` against the schema | schema drift fails CI" would fail response
  validation on 100% of endpoints, go permanently red, and be switched off in week two.

The fix is real work and Phase 0 spikes it before anything depends on it: a custom `AutoSchema` or
`POSTPROCESSING_HOOKS` that wraps every response component in the envelope, a declared error-response
component for the exception-handler shape, and a `204` handling decision (the renderer currently returns
`b""`, which most generated clients treat as a parse error against a JSON-typed response).

📌 **CORRECTED — the web interceptor does not unwrap.** Revision 1 asserted that
`frontend/src/services/api.js` "already unwraps the envelope, so the API contract is compatible" and
that "the mobile client unwraps this in one place, exactly as the web axios interceptor does." It
returns the *whole* envelope (`return response.data;`), and unwrapping happens per call site through two
exported helpers, `unwrapData` and `unwrapList` — the latter trying **five** different shapes
(`[...]`, `d.data`, `d.results`, `d.data.results`, and a paginated envelope) precisely because the
contract is not uniform in practice. So Phase 10's web port is *not* a drop-in, and the mobile client
should unwrap in exactly one generated layer rather than inheriting five-way shape-sniffing.

### 7.2 `drf-spectacular` must stop being optional

`settings.py` gates it behind `HAS_SPECTACULAR = importlib.util.find_spec(...)` and only registers
`DEFAULT_SCHEMA_CLASS` if the package happens to be installed. A schema that is the load-bearing
contract for the mobile client cannot be a conditional feature. It becomes a hard dependency, with
`OAS_VERSION` pinned explicitly (the default emits 3.0.3, not the 3.1 revision 1 claimed) and schema
generation running in CI so a drift is a red build.

### 7.3 Pagination — absent, and entangled with three other decisions

There is no `DEFAULT_PAGINATION_CLASS` and no `pagination_class` anywhere in the backend; every list
endpoint returns the entire table. Meanwhile §13 promises 60fps at 1,000 rows, zero unbounded queries,
and 500k students. This is a Phase 1 decision, not an omission, because it entangles with:

- **Cursor, not page numbers.** Mobile infinite scroll with page numbers shifts rows under the user as
  records are created — and in a CRM, records are created constantly.
- **The envelope nests it one level deeper.** DRF's `{count, next, previous, results}` inside
  `{success, message, data}` is exactly why `unwrapList` has five branches. The generated client must
  model this once.
- **`next`/`previous` are absolute URLs**, which break behind CloudFront and ECS unless
  `SECURE_PROXY_SSL_HEADER` and host handling are right.

---

## 8. Onboarding: from install to a working CRM

You suggested that on install we ask the user to set up their coaching institute. That is right for the
*owner* and wrong for everyone else — and everyone else is the overwhelming majority of installs. A
student must never see "name your institute". So the first screen **forks rather than assumes**.

### 8.1 The four entry paths

```
                       Fresh install
                             │
                  "How will you use this?"
                             │
   ┌──────────────┬──────────┴───────────┬──────────────────┐
   │              │                      │                  │
I run an     I'm joining an        Already have      Phone already
institute    institute             an account       known to us
   │              │                      │                  │
Create       Invite code /          Sign in →        Auto-discover
tenant →     QR / slug link →       institute        memberships
wizard →     join with the          picker if        after OTP —
role OWNER   pre-assigned role      >1 membership    no code needed
```

**Path 4 is the one to optimise for.** When an owner imports their student list, every student and
parent phone already exists as an `INVITED` membership. That person installs, enters their phone,
verifies an OTP — and the server hands back their memberships with no code and no institute name typed.
Two screens to inside. This should carry the majority of installs; it is the difference between an app
parents adopt and one that dies at the invite-code screen.

> **Security condition on path 4, which is not optional.** Memberships must be returned **only after
> OTP verification**. Returning them on phone entry alone makes the endpoint a membership enumeration
> oracle — anyone could learn which coaching institutes a given phone number attends. That is minors'
> data, and it is the kind of design error that is trivial to introduce and hard to walk back.

**Invitations must be WhatsApp-native.** Indian coaching institutes run on WhatsApp groups. Every invite
is a deep link (`https://app.<domain>/join/<slug>?t=<token>`) registered as an iOS Universal Link and
Android App Link, so tapping it in a group opens the app at the right institute — falling back to the
store listing and resuming the join after install. Deferred deep linking is a small piece of work with
outsized adoption impact, and it carries its own vendor decision (R12).

### 8.2 Pre-auth tenant resolution

All four paths need an `Institute` resolved *before* a token exists, which §6.2 layer 3 would reject.
So there is a **named, narrow, individually rate-limited set of unauthenticated tenant-resolving
endpoints**: resolve slug → institute branding, validate invite token → institute, request OTP, verify
OTP. Nothing else. Each is audited, and each has its own throttle scope, because §14.1's "per-tenant
rate limits" cannot apply to a request that has no tenant yet.

**OTP abuse is a financial attack, not just a security one.** SMS-pumping fraud against a pre-auth,
per-message-cost endpoint is a direct drain on our bill. Mitigations: per-phone and per-IP throttles,
exponential backoff on repeat requests, a daily spend cap with alerting, device attestation (Play
Integrity / App Attest) on the OTP request, and country allow-listing.

### 8.3 The owner setup wizard

**Server-side state machine, not client-side.** `Institute.onboarding_state` plus `onboarding_data`
live on the server, so the wizard resumes on another device, survives a reinstall, and can be finished
partly on mobile and partly on web. A client-side wizard loses everything when the owner's phone rings
mid-signup, which it will.

| Step | Collected | Blocking? | Notes |
|---|---|---|---|
| 1. Identity | Name, logo, **institute type**, city, country, timezone, currency, language | **Yes** | Type drives every template below |
| 2. Academic frame | First `AcademicYear`, target exams or boards, class levels | No | Defaults per type and country |
| 3. Branches | "Main Branch" auto-created; add more | No | Single-branch institutes never see this again |
| 4. Courses & batches | Seeded from the **template library**, then edited | No | The step that makes the app non-empty |
| 5. Fees | Fee heads, installment template, tax treatment, receipt series prefix | No | Summary on mobile; deep editing on web |
| 6. Team | Invite staff by phone with roles; bulk paste | No | Each invite produces a WhatsApp-ready link |
| 7. Students | Add first student, share a self-enrol QR, or CSV on web | No | Three routes because institute sizes vary wildly |
| 8. Preferences | Attendance mode, working days, notification defaults, sender identity | No | All defaulted |
| 9. Go live | Completion checklist with percentage | — | Never a wall; always dismissible |

**Only step 1 blocks.** Everything else is skippable and resumable, and the app is usable at roughly 40%
completion with contextual nudges ("You have no batches yet — add one to start marking attendance")
appearing in the relevant screen rather than as a launch modal. Wizards that block lose trials;
checklists that nudge convert them.

**The template library is a competitive feature and gets its own budget.** `institute_type` selects a
starter pack — *JEE Main + Advanced (2-year)*, *NEET Dropper*, *Foundation VIII–X*, *UPSC Prelims +
Mains*, *CBSE Class 10*, *Spoken English (3-month)*, *CA Foundation*, *Skill/vocational* — each
pre-creating courses, subjects, a plausible batch structure, a fee-head skeleton, and an exam pattern.
An owner who picks "NEET Dropper" and taps through has a configured CRM in about four minutes; an owner
facing an empty database has an evening of data entry ahead and will not finish it. Packs are versioned
seed data so we can improve them without migrating existing tenants. Revision 1 called this "a
competitive feature, not a nicety" and then gave it no separate budget; §12 corrects that.

**Demo mode.** "Explore with sample data" produces a fully populated fake institute — students, batches,
attendance history, leads at every funnel stage, fee records — with a single-tap irreversible wipe when
they go live. This lets an owner evaluate before committing a real record, and it doubles as the demo
tenant we hand to App Store reviewers, who reject apps they cannot log into.

### 8.4 Trial and plan scaffolding without a gateway

D4 defers billing; the *schema* must not defer it. `Institute` carries `plan`, `status`
(`PENDING_SETUP / TRIALING / ACTIVE / SUSPENDED / CANCELLED`), `trial_ends_at`, and `limits`
(`max_students`, `max_staff`, `max_branches`, `max_storage_mb`). Limits are enforced from day one with
friendly messaging; only *charging* is absent. Retrofitting enforcement after tenants exist means
backfilling limits onto live data and telling paying customers their usage is now capped.

Which usage counters Phase 1 must record depends on the pricing *shape* — per-student, per-seat, or flat
tier. That is why R8 asks for the shape now even though the number can wait.

> **App-store billing, for v2.** Selling a subscription *inside* the app triggers in-app-purchase rules
> and their revenue share; selling the SaaS plan on the **web** is the standard way this is handled.
> Note the distinction: an institute collecting **tuition fees from a parent** through the app is
> payment for a real-world service, not digital content, so a normal gateway is appropriate and IAP does
> not apply. Those two money flows stay architecturally separate for exactly this reason.

---

## 9. Role-based application shells

One binary (D3), **eight** shells — matching `Role.ROLE_CHOICES` exactly. Revision 1 said "seven" twice,
listed eight in one table, and listed five route groups in another; the number is eight.

| Persona | Home screen | Daily loop |
|---|---|---|
| **Owner / Super Admin** | KPIs: admissions vs target, collected vs outstanding, attendance %, funnel, batch occupancy | Scan numbers, compare branches, clear approvals, review staff activity |
| **Branch Admin** | Same, branch-scoped, plus today's operations | Staffing gaps, substitutions, escalations, day close |
| **Admission Counsellor** ⭐ | My follow-ups today, overdue highlighted | Quick-add enquiry in **under 20 seconds**; one-tap call/WhatsApp with the activity auto-logged; move stage; convert |
| **Teacher** ⭐ | Today's timetable | Mark attendance (offline); upload material from camera; set and grade assignments; enter marks; message a batch |
| **Accountant** | Today's collections and aging dues | Collect, generate receipt, share as PDF over WhatsApp; refunds; close the day book |
| **Receptionist** | Walk-in capture | Visitor log, call log, front-desk announcements |
| **Student** | Next class and what's due | Timetable, attendance %, assignments, material, results, dues + pay, announcements, AI doubt assistant |
| **Parent** | Child switcher, then that child's status | Attendance alerts, results, dues + pay, teacher messages, PTM booking |

⭐ The counsellor and teacher shells are where mobile earns its keep and deserve the most design
attention — they are used dozens of times a day, and their adoption determines renewal.

**Cross-cutting shell elements:** global search (§11.3), notification centre, an offline banner that
states *what is queued* rather than just "offline", tenant logo and primary colour in the header, and an
institute switcher for the multi-membership case.

**Permission enforcement is server-side, always.** Role-based navigation hides screens for usability,
never for security. Every endpoint independently verifies the membership's capabilities. A hidden tab is
a UX decision; an unprotected endpoint is a breach.

---

## 10. Offline strategy — tiered, deliberately

Full bidirectional offline sync is where mobile CRM projects die. It is a distributed-systems problem —
conflict resolution, tombstones, clock skew, migrating the local replica's schema — and it routinely
consumes more engineering than the rest of the app combined. We are not doing it in v1, and that is a
stated decision rather than something we drift into.

| Tier | Scope | Mechanism | v1? |
|---|---|---|---|
| **0 — Read cache** | Every read screen shows last-known data offline | TanStack Query cache persisted to MMKV, with visible staleness indicators | **Yes** |
| **1 — Write outbox** | The few writes that genuinely happen with no signal | Durable queue in `expo-sqlite`; idempotency keys; replay on reconnect; per-item conflict UI | **Yes, narrow** |
| **2 — Full replica sync** | Everything bidirectional | WatermelonDB or similar with a real sync protocol | **No — v2 at earliest, and only on evidence** |

Tier 1 covers exactly three flows, chosen because they happen in basements and corridors: **attendance
marking**, **lead follow-up notes**, and **fee receipt capture**.

**Conflict detection needs real optimistic concurrency, which does not currently exist.**
`BaseModel.save()` increments `version` and nothing ever compares it — the docstring calls it
"optimistic-locking" but it is a change counter. Idempotency keys (which revision 1 did specify) prevent
*duplicate* replay; they do not detect that someone else edited the row while the phone was offline.
Attendance is both the flagship offline flow and the one most likely to be double-marked by a teacher and
a branch admin. So Tier 1 requires `UPDATE ... WHERE id = %s AND version = %s` with a rowcount check, a
`409 Conflict` carrying the server's current state, and a per-item resolution screen. That is a change to
`BaseModel`'s write path, and it is a Phase 1 item because everything built after it assumes the
semantics.

Tier 0 plus a narrow Tier 1 delivers most of the perceived benefit for a fraction of the cost. Revisit
Tier 2 only with pilot telemetry showing real connectivity failures on flows we did not cover.

---

## 11. Communications, uploads, and search

### 11.1 Notifications

Notifications are the retention mechanism for parents and students, and the most common source of
"please make it stop". Both facts shape the design.

**Transport** is provider-abstracted with Expo Push behind it in v1, so moving to direct FCM/APNs later
is an infrastructure change rather than a caller change. Device tokens live on a `Device` model (user,
institute, platform, token, app version, last_seen) so we can revoke per device and diagnose per
platform. Note that this revokes *push*, not *auth* — auth revocation is §6.3.

**Fan-out is always a Celery task.** Announcing to 3,000 parents cannot happen in a request. Tasks enter
scope explicitly via `with institute_scope(institute_id):` rather than inheriting ambient context,
because a worker has no request to inherit from — and per §6.2 layer 4 there is no `.unscoped()` to reach
for instead.

**Templates and channels.** `NotificationTemplate` per tenant, per event (fee due, fee overdue, absence,
result published, announcement, PTM scheduled), with channel selection across push, SMS, and WhatsApp and
per-locale variants. WhatsApp is the channel institutes actually want; it needs pre-approved message
templates through the official Cloud API or a BSP, with a lead time measured in days — start this in
Phase 0, not Phase 7.

**Restraint by default.** Per-tenant quiet hours resolved against the *recipient's* timezone (§6.9),
digests rather than per-event for low-urgency categories, per-user category preferences, and rate-limited
fee nudges. An app that pushes six times a day gets its notifications disabled in week one, after which
the retention mechanism is gone permanently.

### 11.2 File upload — under-designed in revision 1 for its own flagship flow

§3 says the teacher's phone *is* the scanner. The inherited config says
`MAX_UPLOAD_SIZE_BYTES = 5 MB` and `ALLOWED_IMAGE_EXTENSIONS = jpg,jpeg,png,webp`. A modern phone photo
is routinely 4–12 MB and a multi-page scanned worksheet more, so **the inherited limit rejects the
headline flow**. Required:

- **Client-side downscale and compress before upload** — the single highest-leverage fix, and it also
  protects the user's data plan.
- **Presigned direct-to-S3 `PUT`** so multi-megabyte bodies never traverse ECS. The existing
  `generate_upload_url` already supports this; revision 1 mentioned signed URLs only for reads.
- **MIME sniffing rather than extension trust**, plus PDF in the allow-list for scanned material.
- **Per-request and per-membership upload throttles.**
- **Storage accounting that actually works.** `limits.max_storage_mb` is unenforceable against a
  presigned direct upload unless we either put a `Content-Length` condition in the policy or reconcile
  asynchronously from S3 events. Without one of those it is a column, not a control.

### 11.3 Global search

Revision 1 listed "global search" as a shell bullet and said nothing else, which understates a genuinely
hard problem. The design needs to state: what is searched (students, leads, payments, materials — each a
different table with different scoping); how it is indexed (Postgres FTS plus **`pg_trgm` for fuzzy
Indian-name matching**, which is essential when the same student is "Aakash", "Akash", and "आकाश"); how
the institute filter composes with the text index — the same ordering hazard §6.6 describes for vectors;
and how results are permission-filtered **per row** rather than per query, so a counsellor's search never
surfaces another branch's fee records. Cross-tenant support search is separate and lives in §6.7.

---

## 12. Delivery plan

Effort is **engineering-weeks**. The calendar column assumes 2–3 engineers at roughly 65%
parallelisation efficiency, which is what mixed backend/mobile work realistically achieves.

| Phase | Name | Effort | Exit criteria |
|---|---|---|---|
| 0 | Foundations & spikes | 2 wks | Repos, CI, environments, versions pinned, ADRs; **the §7 envelope/OpenAPI spike proven**; WhatsApp template approval started |
| **1** | **Tenancy, identity & scoping core** | **5 wks** | **HARD GATE** — isolation matrix test green across institute *and* branch axes; `scoping.py` and `permissions.py` rewritten; revocation working; pagination and optimistic concurrency decided and built |
| 2 | Auth, onboarding & wizard | 5 wks | Owner installs, creates an institute, reaches a usable home screen unaided; template packs authored; demo mode; deep links; in-app account deletion |
| 3 | Mobile shell & design system | 3 wks | Eight role shells routing, tenant theming, offline read cache, push registration, telemetry |
| 4 | Academics wave | 4 wks | Courses, subjects, batches, enrolment, timetable, attendance (offline) — teacher and student shells usable |
| 5 | CRM wave | 3 wks | Leads, follow-ups, notes, admissions, visitors — counsellor shell usable; the 20-second capture measured |
| 6 | Finance wave | 4 wks | Fee structures, installments, payments, gapless receipts, refunds, online collection, reconciliation |
| 7 | Communications & notifications | 2 wks | Templated push/SMS/WhatsApp with quiet hours and per-user preferences |
| 8 | Assessments wave | 2 wks | Assignments, submissions, exams, question papers, results |
| 9 | RAG assistant rebuild | 3 wks | Real `pgvector` ANN retrieval with an `hnsw` index; tenant-scoped; leakage test as a release gate |
| 10 | Web back-office alignment | 3 wks | Vite/MUI app ported onto tenancy for setup, bulk import, reporting — including the envelope rework §7 exposed |
| 11 | Hardening, compliance & release | 4 wks | Store approval, DPDP compliance, budgets met, three pilots live |
| | **Total** | **40 wks** | ≈ **24–30 calendar weeks** at 2–3 engineers; **≈46 weeks solo** |

### Sequencing notes

**Phase 1 is a hard gate and nothing parallelises against it.** Building domain features on a tenancy
layer that later needs reshaping means re-migrating every model and re-auditing every queryset. It grew
from 3 weeks to 5 because verification added the `scoping.py`/`permissions.py` rewrite (§6.4), token
revocation (§6.3), the capability model (§6.5), pagination (§7.3), partial unique indexes (§6.8), and
real optimistic concurrency (§10) — all of which are load-bearing for everything after.

**Phase 2 grew from 3 weeks to 5** because its stated scope was never 3 weeks of work: OTP with
anti-abuse, a nine-step resumable server-side state machine, eight authored template packs, demo-data
generation with a wipe, Universal Links plus App Links plus *deferred* deep linking, the invite/claim
flow, the institute picker, and in-app account deletion.

**Phases 4–8 are the parallelisation window.** Each wave is backend endpoints plus matching mobile
screens, so a two-person split roughly halves the calendar. Each ships end-to-end rather than
backend-then-frontend, because a wave that cannot be demoed cannot be validated.

**RAG is its own phase now.** Revision 1 had it sharing three weeks with all of assessments, while also
rating it catastrophic-if-wrong. Given §6.6 requires replacing the retrieval implementation and adding a
vector index, that allocation was inverted against its own risk register.

**Phase 11 contains items outside our control** — Apple review is unbounded, a first submission for an
app handling minors' data with account creation invites a rejection cycle, the privacy review is an
external dependency, and pilots move at customer pace. Four weeks is a planning figure, not a promise.

---

## 13. Non-functional requirements and budgets

Budgets that are not measured are aspirations, so each gets an automated check or a synthetic monitor.

| Dimension | Target | Enforcement |
|---|---|---|
| Cold start (mid-range Android) | < 2.5 s to first usable screen | Measured in CI on a real device profile; regressions fail the build |
| API latency | p95 < 400 ms, p99 < 1 s | APM alerting per endpoint, per tenant |
| Attendance marking | < 1 s perceived, fully offline | Optimistic local write; measured in the Maestro flow |
| Enquiry capture | < 20 s tap-to-saved | Explicit timed acceptance test |
| List scrolling | 60 fps at 1,000 rows | `FlashList` + cursor pagination; virtualisation mandatory |
| Bundle size | < 25 MB Android download | Size budget check in CI |
| Crash-free sessions | > 99.5% | Sentry release health; blocks staged-rollout promotion |
| Availability | 99.9% monthly | Multi-AZ RDS, ECS across two AZs, synthetic checks |
| Tenant scale | 1,000 institutes / 500k students, one shared schema | Load test in Phase 11 with a realistic tenant *size distribution*, not uniform tenants |
| Query hygiene | Zero unbounded queries on tenant tables | Pagination mandatory by default; CI check on hot-path query plans |

---

## 14. Security, privacy and compliance

### 14.1 Application security

Token discipline: 10–15 minute access tokens, rotating refresh tokens with `token_blacklist` installed,
generation counters for immediate revocation (§6.3), custom refresh-reuse detection, tokens only in
Keychain/Keystore via `expo-secure-store`, per-device push revocation via `Device`. Biometric unlock for
staff roles, per-tenant session timeout, and screenshot suppression on fee and PII screens where the
tenant enables it.

Server side: per-tenant, per-endpoint, and — for pre-auth routes (§8.2) — per-phone and per-IP rate
limits; strict serializer validation; presigned short-lived S3 URLs with no public buckets and per-tenant
key prefixes; `bandit` and dependency scanning in CI; secrets exclusively in AWS Secrets Manager, never
in the app bundle, which is trivially extractable and must be treated as public.

Audit: the existing `AuditLogMiddleware` writes a coarse row per authenticated mutation — keep it, add
`institute_id`. Fine-grained entries remain the service layer's job. Impersonated writes carry
`impersonated_by` (§6.7).

### 14.2 Privacy — the part that is easy to get wrong

**This product processes the personal data of minors at scale.** That is not a footnote; under India's
Digital Personal Data Protection Act 2023 it is the single most consequential compliance fact about the
system. Processing a child's data requires verifiable parental consent, and the Act restricts behavioural
advertising and tracking directed at children.

Practical consequences, which must be designed in rather than bolted on:

- **Consent is a data model, not a checkbox** — recorded per student with timestamp, consenting guardian,
  scope, and the version of the notice consented to, and revocable.
- **This constrains the analytics choice.** Any product analytics on student-facing screens must be
  consent-gated and must not build behavioural profiles of minors. That is why §4.2 lists analytics
  behind a consent gate rather than as a default-on SDK.
- **Data-principal rights need endpoints.** Access, correction, erasure, and export must be
  near-self-service per tenant; doing them by hand across a thousand institutes does not scale.
- **The institute is a Data Fiduciary and we are a Data Processor**, which needs a written DPA defining
  who answers a parent's request. Draft it before the first paying customer.
- **Residency and retention:** `ap-south-1`, documented retention per data category, tenant export and
  deletion on offboarding — subject to the financial-retention conflict in §6.8.

GDPR applies additionally if any institute operates in the EU; this design largely satisfies it, but
lawful basis and transfer language would need review.

> 🔍 **USER REVIEW.** The DPA, privacy notice, and consent copy are legal documents and I am not a
> lawyer — this section describes engineering obligations, not legal advice. Budget a privacy lawyer's
> review before pilot launch. It is small relative to processing minors' data without a defensible
> consent record.

### 14.3 App store compliance

Both stores require **in-app account deletion** for any app with account creation — built in Phase 2
rather than discovered at review. Apple's data-collection disclosures and Google Play's Data Safety form
must match what the app actually does, which is easier when analytics is minimal and consent-gated.
Reviewers must be able to log in, which the demo tenant provides. And per §8.4, keep SaaS subscription
selling on the web and tuition collection in the app.

---

## 15. Testing, CI/CD and release

| Layer | Tooling | Non-negotiables |
|---|---|---|
| Backend unit | `pytest` + `pytest-django` + `factory_boy` | Services tested directly; no ORM writes in views to test |
| **Tenant isolation** | Matrix test enumerated from `django.apps` | **Release gate.** Covers institute *and* branch axes. Plus the CI guard that every concrete model in a tenant app is a `TenantModel` unless allow-listed |
| **RAG leakage** | Two-institute retrieval test | **Release gate** (§6.6) |
| API contract | `schemathesis` against the schema | Only meaningful once §7's envelope wrapping is done — sequenced after the Phase 0 spike |
| Mobile unit | Jest + React Native Testing Library | Services, hooks, and outbox replay/conflict logic |
| Mobile E2E | **Maestro** | Five flows: owner onboarding, claim-account join, offline attendance, enquiry-to-admission, fee collection with receipt |
| Load | Locust or k6 | Realistic tenant size distribution |
| Security | `bandit`, dependency audit, manual two-tenant penetration attempt | Phase 1 gate and Phase 11 gate |

**CI/CD.** GitHub Actions with Postgres and Redis service containers (no SQLite shortcut). Backend runs
`ruff`, `mypy`, `bandit`, then tests with `--reuse-db` and `pytest-xdist`. Mobile runs typecheck, lint,
unit tests, then an **EAS preview build per pull request** so any change is installable on a real device
before merge — this single practice catches more than any amount of simulator testing.

**Release.** EAS Build on merge to main; staged rollout 10% → 50% → 100% gated on Sentry release health;
**EAS Update for JavaScript-only fixes** so a regression is a ten-minute rollback rather than a two-day
review cycle. Native changes bump `runtimeVersion`, JS-only changes do not. A written policy on
acceptable OTA content — bug fixes yes, feature changes no — because stores care about that distinction.

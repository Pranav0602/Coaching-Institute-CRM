# Implementation Plan: Enable Admission Counselors to View Course Syllabus Documents

## Problem Summary

Admission counselors at Graphix Techno Services guide prospective students, handle enquiries, answer detailed questions regarding curriculum, software versions, course duration, fees, eligibility, and projects, and convert leads into admissions. 

Currently, all master and individual course syllabus documents (seeded or uploaded by administrators) are stored as `KnowledgeDocument` records (categories `STUDY_GUIDE` and `COURSE_CATALOGUE`) in the `rag` app. However:
1. **API Authorization Barrier**: `KnowledgeDocumentViewSet` in [`institute_crm/rag/views.py`](file:///d:/CRM%20project/CRM/institute_crm/rag/views.py) requires `IsBranchAdmin`, completely blocking Admission Counselors (`403 Forbidden`).
2. **Route Authorization Barrier**: In [`frontend/src/App.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/App.jsx), `/knowledge-base` is restricted to `[ROLES.SUPER_ADMIN, ROLES.BRANCH_ADMIN]`.
3. **Missing Navigation**: In [`frontend/src/components/layout/Sidebar.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/components/layout/Sidebar.jsx), Admission Counselors only have links for Counselling Desk, Follow-ups, and Conversion, with no link to view courses or syllabi.
4. **No Counselor-Friendly Syllabus Interface**: Counselors have no clean syllabus viewer with module breakdown, tools covered, industrial projects, copy-to-clipboard for WhatsApp/email lead counseling, or contextual preview drawers inside their lead management workflows.

---

## User Review Required

> [!IMPORTANT]
> **Read-Only Scope for Counselors**: Admission counselors will be granted read access exclusively to **published** documents (`is_published=True`). Administrative editorial rights (create, edit, delete, unpublish, and catalogue re-indexing) remain strictly restricted to `SUPER_ADMIN` and `BRANCH_ADMIN`.

> [!NOTE]
> **Syllabus Ingestion Alignment**: The 29 industry-standardized course syllabuses ingested by [`scripts/seed_graphix_courses.py`](file:///d:/CRM%20project/CRM/institute_crm/scripts/seed_graphix_courses.py) and new syllabi created in [`KnowledgeBasePage.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/pages/KnowledgeBasePage.jsx) (via category `STUDY_GUIDE` or `COURSE_CATALOGUE`) will be automatically available to counselors both in the dedicated hub and contextually on lead cards.

---

## Proposed Changes

Grouped logically by architectural layers:

### 1. Backend Security & API Layer

#### [MODIFY] [`accounts/permissions.py`](file:///d:/CRM%20project/CRM/institute_crm/accounts/permissions.py)
- Create `IsAdminOrCounselorReadOnly(BasePermission)`:
  - Grants full access (CRUD) to `SUPER_ADMIN` and `BRANCH_ADMIN` (and superusers).
  - Grants read-only access (`SAFE_METHODS`: `GET`, `HEAD`, `OPTIONS`) to `ADMISSION_COUNSELOR`.
  - Rejects other unauthorized roles and unauthenticated requests.

#### [MODIFY] [`rag/views.py`](file:///d:/CRM%20project/CRM/institute_crm/rag/views.py)
- Update `KnowledgeDocumentViewSet`:
  - Change `permission_classes` to `[IsAuthenticated, IsAdminOrCounselorReadOnly]`.
  - Override `get_queryset()`:
    - Automatically enforce `is_published=True` for non-admin callers (such as Admission Counselors).
    - Support query parameters:
      - `category`: Filter by category (e.g. `?category=STUDY_GUIDE` or `?category=COURSE_CATALOGUE`).
      - `course_id`: Filter by `metadata_json__course_id`.
      - `search`: Filter by title or content keywords.
    - Order by `-updated_at`.

#### [MODIFY] [`academics/views/admin_views.py`](file:///d:/CRM%20project/CRM/institute_crm/academics/views/admin_views.py)
- In `CourseViewSet`:
  - Add detail action `@action(detail=True, methods=["get"], url_path="syllabus")`:
    - Allows direct retrieval of the syllabus document linked to a course by its ID or code.
    - Returns serialized `KnowledgeDocument` with complete module details, or HTTP 404 if no syllabus has been uploaded yet.

---

### 2. Frontend Components & Pages Layer

#### [NEW] [`frontend/src/components/syllabus/SyllabusViewerDrawer.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/components/syllabus/SyllabusViewerDrawer.jsx)
- Slide-out drawer / modal accessible from any page.
- Features:
  - Renders course details: Title, Code, Duration, Total Fee, Engineering Discipline.
  - Software & Tools Badges (e.g. AutoCAD, CATIA V5, SolidWorks, Revit, Spring Boot, etc.).
  - Structured sections:
    - Course Overview & Objectives
    - Prerequisites & Eligibility
    - Detailed Module-by-Module curriculum with topic bullets
    - Industrial Projects & Capstone work
    - Certification & Placement Highlights
  - "Copy Prospect Summary" button: Copies a clean message formatted for WhatsApp / Email with key course points so the counselor can send it to the prospective student during the call.
  - External link / PDF download button if `source_url` is provided.

#### [NEW] [`frontend/src/pages/CourseSyllabiPage.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/pages/CourseSyllabiPage.jsx)
- Dedicated Course Syllabi Hub for Admission Counselors and Admins.
- Features:
  - **Toolbar**: Search bar (search by course name, code, software tool, topics) + Engineering Discipline filter dropdown (`Mechanical CAD`, `Civil CAD`, `IT & Software`, etc.).
  - **Tabs**:
    - **Course Syllabuses**: Cards / table listing all courses with attached syllabus status, duration, fees, tools covered, and "View Full Syllabus" action.
    - **Master Catalogue**: Displays the full enriched Master Syllabus & Curriculum Catalogue (`GRAPHIX_TECHNO_SERVICES_COURSE_SYLLABUS_CATALOGUE.md` / `COURSE_CATALOGUE` document).
  - Quick action to open `SyllabusViewerDrawer` for any selected course.

#### [MODIFY] [`frontend/src/components/layout/Sidebar.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/components/layout/Sidebar.jsx)
- In `getRoleMenuItems()`:
  - Add `{ text: 'Course Syllabi', icon: <MenuBook />, path: '/course-syllabi' }` for `ROLES.ADMISSION_COUNSELOR`.
  - Also add `{ text: 'Course Syllabi', icon: <MenuBook />, path: '/course-syllabi' }` for `ROLES.SUPER_ADMIN` and `ROLES.BRANCH_ADMIN` for convenient direct syllabus exploration.

#### [MODIFY] [`frontend/src/App.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/App.jsx)
- Register new route:
  ```jsx
  <Route
    path="/course-syllabi"
    element={
      <RequireRole allowed={[ROLES.SUPER_ADMIN, ROLES.BRANCH_ADMIN, ROLES.ADMISSION_COUNSELOR]}>
        <CourseSyllabiPage />
      </RequireRole>
    }
  />
  ```

#### [MODIFY] [`frontend/src/pages/dashboards/CounsellingOverview.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/pages/dashboards/CounsellingOverview.jsx)
- Add a "Course Syllabi Reference" banner / quick card on the Counselling Desk.
- Allows admission counselors to search courses or quickly jump to syllabus documents while reviewing daily enquiries and stage metrics.

#### [MODIFY] [`frontend/src/components/leads/LeadCard.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/components/leads/LeadCard.jsx)
- Add a "View Syllabus" trigger next to the course badge on lead cards.
- Clicking opens the `SyllabusViewerDrawer` with that specific course syllabus loaded, enabling quick answers during counseling calls.

#### [MODIFY] [`frontend/src/pages/CoursesPage.jsx`](file:///d:/CRM%20project/CRM/institute_crm/frontend/src/pages/CoursesPage.jsx)
- Add a "Syllabus" column to the course catalogue table with a "View Syllabus" button opening the syllabus preview.

---

## Verification Plan

### Automated Tests
1. **Backend Permission & Scoping Tests**:
   - Create test cases in [`institute_crm/rag/tests.py`](file:///d:/CRM%20project/CRM/institute_crm/rag/tests.py):
     - `test_admission_counselor_can_list_published_documents`: Verify 200 OK and only published documents returned.
     - `test_admission_counselor_cannot_create_document`: Verify POST returns 403 Forbidden.
     - `test_admission_counselor_cannot_edit_or_delete_document`: Verify PATCH and DELETE return 403 Forbidden.
     - `test_counselor_can_filter_documents_by_category_and_course`: Verify query params work as expected.
     - `test_admin_retains_full_crud`: Verify Super Admin / Branch Admin can still create, edit, delete.
   - Run tests via PowerShell:
     ```powershell
     python manage.py test rag academics
     ```
2. **Frontend Build Verification**:
   - Verify Vite frontend builds without JSX / import errors:
     ```powershell
     cd frontend; npm run build
     ```

### Manual Verification
1. **Admission Counselor Flow**:
   - Log in as an Admission Counselor.
   - Verify that "Course Syllabi" is present in the left sidebar.
   - Click "Course Syllabi" and verify the list of 29 courses with their software tools, fees, duration, and disciplines.
   - Search for a specific software/course (e.g. "Creo", "CATIA", "Full Stack", "Salesforce").
   - Click "View Syllabus" to open the detailed drawer and verify modules, projects, and prerequisites.
   - Click "Copy Prospect Summary" and verify clipboard content.
   - Switch to "Master Catalogue" tab and verify master document rendering.
   - Navigate to the Counselling Desk and Lead Pipeline, verify clicking the course chip on a lead opens the syllabus drawer seamlessly.
2. **Access Control Verification**:
   - Verify that an Admission Counselor does not see "Edit", "Delete", "Add Document", or "Sync Catalogue" administrative controls.

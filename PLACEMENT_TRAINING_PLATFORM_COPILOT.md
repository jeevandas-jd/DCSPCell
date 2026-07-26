# Placement Training Engagement Platform

## Copilot + VS Code Development Specification

This file is the primary instruction document for building a secure Python web application that engages students in placement preparation through aptitude quizzes, coding tests, performance analytics, leaderboards, student search, and downloadable reports.

Use this document with **GitHub Copilot Chat in VS Code**. Complete one phase at a time. Do not generate the entire system in a single response.

---

## 1. Product Vision

Build a multi-role placement training platform for an educational institution. Students are organized into cohorts. Each cohort has one faculty coordinator and multiple student coordinators. Authorized coordinators publish aptitude and coding assessments within a defined time window. Students attempt them, receive results after release, review explanations, and track their progress through leaderboards and analytics.

The platform must also help faculty identify students matching placement-related criteria and generate reports from all significant lists, dashboards, and result pages.

### Suggested product name

**PlacePrep Hub** — Learn, Practise, Compete, Improve.

---

## 2. Recommended Technology Stack

- Backend: Python 3.12+, Django 5+, Django REST Framework
- Database: PostgreSQL
- Frontend: Django templates, Bootstrap 5, HTMX, Alpine.js
- Charts: Chart.js
- Background jobs: Celery and Redis
- Reports: Pandas/OpenPyXL for Excel, WeasyPrint for PDF, CSV export
- Authentication: Django authentication with email/username login
- Testing: Pytest, pytest-django, Factory Boy, Playwright
- Code quality: Ruff, Black, mypy, pre-commit
- Deployment: Docker Compose for development; Gunicorn, Nginx, PostgreSQL, Redis in production
- Coding evaluation: isolated external judge such as Judge0; never execute untrusted student code directly in the Django process or application container

Keep business logic in service modules rather than views. Use environment variables for secrets and deployment-specific configuration.

---

## 3. Roles and Permissions

Use role-based access control and object-level authorization. A user may hold more than one role, but only within authorized scopes.

### Admin

- Manage institutions/departments, academic years, programs, batches, users, roles, cohorts, categories, tags, and system settings.
- Assign one faculty coordinator and multiple student coordinators to a cohort.
- Import and export students in bulk.
- View all assessments, attempts, reports, leaderboards, and audit logs.
- Activate, deactivate, archive, or transfer users and cohorts.
- Configure leaderboard rules, report branding, notification settings, and result-release policies.

### Faculty Coordinator

- Access only assigned cohorts unless additional permission is granted.
- Create, review, publish, reschedule, cancel, and archive assessments for assigned cohorts.
- Create aptitude and coding questions with answers, explanations, difficulty, topic, tags, and marks.
- Maintain question banks and reuse questions.
- View students, attempts, analytics, reports, and leaderboards for assigned cohorts.
- Search students using placement-related criteria.
- Approve, edit, or remove content created by student coordinators.
- Grant limited assessment-author privileges to designated student coordinators.

### Student Coordinator

- Access only cohorts to which the user belongs and is assigned as a coordinator.
- Create draft questions and assessments when authorized.
- Publish only if explicitly designated; otherwise submit content for faculty approval.
- View participation summaries but not confidential student information, private notes, or answers before an assessment closes.
- Never modify another student's attempt, marks, or profile.

### Student

- View eligible upcoming, active, and completed assessments.
- Attempt an assessment only during its allowed time window and within attempt limits.
- View results and explanations only after the configured release condition.
- View personal dashboard, progress, topic strengths/weaknesses, badges, rank, and attempt history.
- Maintain permitted placement-profile fields.

### Permission rule

Never rely only on hidden buttons. Enforce every permission on the server and test it.

---

## 4. Cohort Model

A cohort represents a group of students receiving a shared placement-training plan.

Suggested fields:

- Name, code, department, program, admission year, graduation year, section, academic year
- Start date, end date, status: draft/active/completed/archived
- One faculty coordinator
- Multiple student coordinators
- Multiple students

Maintain assignment history so coordinator changes are auditable. A student may belong to one primary cohort and optionally multiple training groups. Do not hard-delete cohorts with historical attempts.

---

## 5. Functional Modules

### 5.1 Authentication and User Management

- Login, logout, password reset, password change, account activation, and optional email verification.
- Optional institutional SSO can be added later.
- User status: invited, active, suspended, graduated, archived.
- Bulk CSV/XLSX import with preview, validation, duplicate detection, downloadable error report, and transaction-safe commit.
- Profile photograph, student register number, contact fields, program data, and placement attributes.
- Record last login and important security events.

### 5.2 Question Bank

Support these initial question types:

1. Single-answer MCQ
2. Multiple-answer MCQ
3. Numerical answer
4. Short answer with manual or exact-match evaluation
5. Coding problem

Common fields:

- Title, question statement, type, topic, subtopic, tags, difficulty
- Positive marks, negative marks, default time estimate
- Correct answer/evaluation rule and detailed explanation
- Author, reviewer, approval status, version, visibility, created/updated timestamps
- Optional image, formula, attachment, hint, reference link

Coding problem fields:

- Problem statement, input/output format, constraints, examples
- Supported languages
- Public sample tests and private evaluation tests
- Time and memory limits
- Scoring strategy: all-or-nothing or weighted test cases
- Starter code and reference solution stored securely

Requirements:

- Search, filter, sort, preview, duplicate, archive, import, export, and version questions.
- Sanitize rich text and uploads.
- Do not reveal correct answers, private tests, or explanations through page source or APIs before release.

### 5.3 Assessment Builder

An assessment may contain aptitude questions, coding questions, or both.

Fields and settings:

- Title, description, instructions, cohort(s), creator, approver
- Start datetime, end datetime, optional duration per student
- Total marks, pass mark, maximum attempts
- Question order and optional answer-option randomization
- Navigation policy, autosave, late-entry policy, negative marking
- Result release: immediately after closure, scheduled datetime, or manual release
- Explanation release policy
- Leaderboard inclusion and tie-break rule
- Status: draft, pending approval, scheduled, active, closed, evaluated, released, cancelled, archived

Validate that the end time follows the start time, assigned questions are valid, totals are consistent, and publication permissions are satisfied.

Once an assessment receives attempts, preserve a versioned snapshot of its questions, answers, marks, settings, and test cases.

### 5.4 Student Assessment Experience

- Show server-authoritative countdown and clear start/end information.
- Create the attempt atomically and prevent unauthorized duplicate attempts.
- Autosave answers and code periodically and on navigation.
- Allow manual submission with confirmation.
- Auto-submit when duration or assessment window expires.
- Recover safely after network interruption without extending authorized time.
- Mark questions for review and show answered/unanswered status.
- Provide accessible keyboard navigation and mobile-responsive layout.
- Record relevant attempt events without intrusive surveillance.
- Use the server clock for all eligibility and submission decisions.

### 5.5 Evaluation and Results

- Auto-evaluate objective questions.
- Queue coding submissions for isolated evaluation.
- Support manual evaluation for short answers and authorized mark adjustments with reason and audit trail.
- Calculate raw marks, penalties, final score, percentage, pass status, rank, accuracy, time taken, and topic-level performance.
- Release results and explanations only according to assessment policy.
- Show correct answer, student's answer, explanation, marks, and coding test summary after release.
- Permit re-evaluation and publish a new result version without silently overwriting history.

### 5.6 Leaderboard

Provide overall and filtered leaderboards.

Filters:

- Cohort, assessment, date range, topic, difficulty, question type, program, batch, section
- Weekly, monthly, semester, and all-time views

Metrics:

- Total points, average percentage, best score, participation rate, accuracy, coding problems solved, current streak, improvement score

Default ranking formula must be configurable. Suggested first version:

`leaderboard_score = 0.60 * normalized_average + 0.25 * normalized_participation + 0.15 * normalized_improvement`

Tie-break order: higher accuracy, lower valid completion time, earlier final submission. Display the active rule near the leaderboard. Allow students to opt out of public display if institutional policy requires it, while faculty retains authorized reporting access.

### 5.7 Faculty Student Search

Create a general student finder for authorized faculty. Filters must be combinable and saved as reusable search views.

Suggested filters:

- Name, register number, email
- Cohort, program, batch, section, graduation year
- CGPA range, active backlogs, placement status
- Skills, preferred role/domain, certifications
- Aptitude average/range, coding average/range, topic score
- Assessment participation, tests attempted/missed, pass rate
- Rank range, improvement trend, coding languages, problems solved
- Training attendance, profile completeness, last activity

Support AND/OR criteria groups, sorting, pagination, selected-student export, and privacy-aware column selection. Search results must obey cohort/data access permissions.

### 5.8 Dashboards and Analytics

Admin dashboard:

- Active users/cohorts, scheduled assessments, participation, platform activity, evaluation queue, and system alerts.

Faculty dashboard:

- Assigned cohorts, upcoming assessments, completion rate, cohort average, pass rate, missed tests, topic gaps, top improvers, and students needing support.

Student coordinator dashboard:

- Authorized content workflow, upcoming tests, cohort participation summary, and pending faculty approvals.

Student dashboard:

- Upcoming/active tests, recent scores, rank, streak, topic profile, progress trend, recommendations, badges, and missed assessments.

### 5.9 Reports and Exports

Every major dashboard, list, result, leaderboard, and search page must expose a **Generate Report** or **Export** action when the user has permission.

Formats:

- PDF for presentation/printing
- XLSX for analysis
- CSV for raw tabular export
- Printable HTML where appropriate

Report options:

- Respect active filters and sorting.
- Allow current page, selected rows, or all filtered rows.
- Include institution name/logo, report title, generation timestamp, generated-by user, filter summary, page numbers, and confidentiality notice.
- Large reports run asynchronously and notify the requester when ready.
- Save report-job status and expiry; do not store downloadable files indefinitely.
- Record report generation/download in the audit log.
- Prevent spreadsheet-formula injection in CSV/XLSX exports.

Initial reports:

- Cohort roster and profile report
- Assessment participation and absentee report
- Assessment result and rank report
- Individual student performance report
- Topic-wise strength/gap report
- Coding performance report
- Leaderboard report
- Placement-readiness/custom student search report

### 5.10 Notifications

- In-app notifications for invitations, assessment publication, reminders, rescheduling, result release, approval requests, and report completion.
- Email notifications are configurable and queued.
- Avoid duplicate reminders and respect user preferences.

### 5.11 Audit and Administration

- Audit role changes, cohort assignments, question publication, assessment changes, result adjustments, report exports, and critical settings.
- Store actor, action, target, timestamp, request metadata, and safe before/after summaries.
- Admin configuration for time zone, scoring defaults, leaderboard policy, branding, upload limits, and retention.

---

## 6. Suggested Data Model

Create normalized Django models with UUID primary keys, timestamps, constraints, useful indexes, and soft-archive behavior where history matters.

Core models:

- `User`, `RoleAssignment`, `StudentProfile`, `FacultyProfile`
- `Department`, `Program`, `AcademicYear`
- `Cohort`, `CohortMembership`, `CoordinatorAssignment`
- `Topic`, `Tag`, `Question`, `QuestionVersion`, `QuestionOption`, `CodingProblem`, `TestCase`
- `Assessment`, `AssessmentCohort`, `AssessmentQuestion`, `AssessmentSnapshot`
- `Attempt`, `AttemptAnswer`, `CodeSubmission`, `EvaluationJob`, `ResultVersion`
- `LeaderboardRule`, `LeaderboardEntry`, `Badge`, `StudentBadge`
- `SavedStudentSearch`, `Notification`, `ReportJob`, `AuditEvent`

Important constraints:

- Only one active faculty coordinator assignment per cohort.
- Unique active student membership per cohort.
- An attempt belongs to an eligible student and assessment snapshot.
- One active/final attempt per student and assessment unless multiple attempts are enabled.
- Marks cannot exceed configured bounds without an audited override.
- Private test cases and unreleased answers must use restricted serializers/services.

Add indexes for cohort membership, assessment windows/status, attempts by student/assessment, common student filters, tags/topics, and leaderboard queries.

---

## 7. Key Workflows

### Publish an assessment

1. Coordinator creates or selects approved questions.
2. Coordinator configures cohort, window, duration, release, and scoring.
3. System validates content and permissions.
4. Student coordinator content goes to faculty approval unless publishing permission exists.
5. System creates an immutable assessment snapshot.
6. Assessment is scheduled and eligible students are notified.

### Attend an assessment

1. System verifies user, cohort eligibility, time window, and attempt limit.
2. Attempt begins with authoritative timestamps.
3. Answers autosave; coding submissions are queued to the judge.
4. Student submits or system auto-submits on expiry.
5. Objective evaluation runs; pending manual/coding evaluation is tracked.
6. Result is finalized and later released according to policy.

### Generate a report

1. User selects format, scope, columns, and current filters.
2. Server rechecks access and builds an immutable report request.
3. Small report downloads immediately; large report becomes a queued job.
4. System creates the file, stores it temporarily, and notifies the user.
5. Download is authorized, audited, and expires after the retention period.

---

## 8. Non-Functional Requirements

### Security

- Follow OWASP guidance, Django security defaults, CSRF protection, secure cookies, HTTPS, Content Security Policy, rate limiting, and strict upload validation.
- Apply least privilege and object-level authorization to all pages, APIs, exports, and background jobs.
- Never execute untrusted code locally; use an isolated judge with CPU, memory, time, network, process, and filesystem restrictions.
- Encrypt sensitive data in transit and protect secrets with environment configuration.
- Prevent IDOR, mass assignment, XSS, SQL injection, CSV injection, answer leakage, and report data leakage.
- Add throttling and idempotency controls to assessment start, autosave, submission, and code-evaluation endpoints.

### Reliability and Concurrency

- Store datetimes in UTC and display them in the configured institutional time zone.
- Use transactions and row locking where duplicate attempts or final submission races are possible.
- Make autosave, final submission, evaluation callbacks, notifications, and report jobs idempotent.
- Back up PostgreSQL and document restore procedures.

### Performance

- Paginate large tables and use database-side filtering.
- Prevent N+1 queries with `select_related`/`prefetch_related`.
- Cache safe aggregate analytics and invalidate appropriately.
- Target ordinary page responses below two seconds under expected institutional load.

### Accessibility and UX

- Responsive from mobile to desktop.
- Aim for WCAG 2.1 AA: keyboard support, labels, contrast, focus states, and screen-reader-friendly feedback.
- Use consistent status badges, empty states, confirmation prompts, validation messages, and breadcrumbs.

### Privacy

- Define which student-profile fields are visible to each role.
- Limit student coordinators to minimum necessary information.
- Record consent/notice where required and define retention/export/deletion policies according to institutional rules.

---

## 9. Repository Structure

```text
placeprep-hub/
├── .github/
│   ├── copilot-instructions.md
│   └── workflows/ci.yml
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── test.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── academics/
│   ├── cohorts/
│   ├── question_bank/
│   ├── assessments/
│   ├── evaluation/
│   ├── analytics/
│   ├── reports/
│   ├── notifications/
│   └── audit/
├── templates/
├── static/
├── tests/
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   ├── permissions.md
│   ├── api.md
│   └── deployment.md
├── docker/
├── manage.py
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── README.md
└── PLACEMENT_TRAINING_PLATFORM_COPILOT.md
```

---

## 10. Copilot Global Instructions

Copy the following block into `.github/copilot-instructions.md` after scaffolding:

```md
You are contributing to PlacePrep Hub, a Django placement-training platform.

- Read PLACEMENT_TRAINING_PLATFORM_COPILOT.md before implementing a feature.
- Use Python 3.12+, Django 5+, PostgreSQL, Bootstrap 5, HTMX, Celery, and Redis.
- Keep views thin; place business workflows in services and complex queries in selectors.
- Enforce role and object-level authorization on the server for every request.
- Use UUID keys, database constraints, transactions, and UTC-aware datetimes.
- Never expose unreleased answers, explanations, reference solutions, or private test cases.
- Never run student code inside the web application or worker container.
- Validate and sanitize all input, rich text, uploads, filters, and exported cells.
- Avoid N+1 queries and paginate all potentially large lists.
- Add type hints, docstrings for public interfaces, migrations, tests, and concise documentation.
- For each feature, implement models/migrations, permissions, services/selectors, views/APIs, templates, tests, and documentation as applicable.
- Use accessible, mobile-responsive templates and clear error/empty/loading states.
- Do not add a dependency without explaining why and updating pyproject.toml.
- Do not invent missing business rules silently. Add a documented assumption or ask for a decision.
- Before finishing, run formatting, linting, type checking, tests, and Django system checks; report failures honestly.
```

---

## 11. Phased Implementation Plan

### Phase 0 — Architecture and setup

- Create an architecture decision record for core stack and coding judge.
- Scaffold project, settings, Docker Compose, PostgreSQL, Redis, Celery, lint/test tools, CI, base templates, health checks, and `.env.example`.
- Create README setup instructions and seed-development command.

### Phase 1 — Accounts, roles, and cohorts

- Custom user model, profiles, role assignments, academic structures, cohorts, memberships, coordinator history, bulk import, permissions, and dashboards.

### Phase 2 — Question bank

- Question types, versioning, choices, explanations, coding problems, protected test cases, approval workflow, filters, import/export, and tests.

### Phase 3 — Assessment authoring

- Assessment builder, cohort assignment, scheduling, snapshots, validation, approval, publication, and notifications.

### Phase 4 — Quiz engine

- Eligibility, attempt lifecycle, countdown, autosave, navigation, submission, expiry, objective evaluation, and concurrency tests.

### Phase 5 — Coding judge integration

- Judge adapter interface, queued submissions, webhook/polling result handling, retry/idempotency, language configuration, and security documentation.

### Phase 6 — Results and explanations

- Manual evaluation, result calculation/versioning, release policies, student review, faculty result pages, and audit trail.

### Phase 7 — Leaderboards and analytics

- Configurable ranking, scheduled aggregation, filters, dashboards, charts, topic gaps, participation, improvement, and privacy options.

### Phase 8 — Student finder

- Search criteria, AND/OR builder, saved filters, authorized columns, database indexes, selected rows, and exports.

### Phase 9 — Reporting

- Common report service, synchronous/asynchronous generation, PDF/XLSX/CSV, branded templates, filter summaries, temporary secure downloads, and audit.

### Phase 10 — Hardening and release

- Accessibility review, authorization matrix tests, load tests, security tests, backup/restore, monitoring, production Docker/deployment, and user documentation.

Do not move to a later phase while critical tests in the current phase fail.

---

## 12. Reusable Prompt for Each Copilot Phase

Use this prompt in Copilot Chat and replace the placeholders:

```text
Read #file:PLACEMENT_TRAINING_PLATFORM_COPILOT.md and the current repository.

Implement Phase [NUMBER]: [NAME] only.

Before writing code:
1. Summarize the relevant requirements.
2. Inspect existing models, migrations, URLs, services, templates, tests, and project conventions.
3. List the files you will create or change.
4. State assumptions and security/authorization risks.

Then implement the phase in small, reviewable steps. For every step:
- produce complete production-oriented code, not pseudocode;
- add migrations and database constraints when required;
- enforce server-side role and object permissions;
- add unit, integration, authorization, and edge-case tests;
- update documentation;
- do not expose protected assessment content.

After implementation, run or provide commands for:
- ruff check .
- ruff format --check .
- mypy .
- pytest
- python manage.py check
- python manage.py makemigrations --check --dry-run

Finish with:
- implemented features;
- changed files;
- tests and results;
- assumptions or unresolved decisions;
- the next smallest recommended step.
```

---

## 13. Feature-Level Prompt Template

```text
Read #file:PLACEMENT_TRAINING_PLATFORM_COPILOT.md.

Implement this feature: [FEATURE].
Actors: [ROLES].
Scope: [COHORT/ASSESSMENT/GLOBAL].
Acceptance criteria:
- [CRITERION 1]
- [CRITERION 2]
- [CRITERION 3]

First inspect the repository and propose a minimal file-level plan. Reuse existing patterns. Include server-side authorization, validation, transactions where needed, accessible UI, audit events, pagination/filtering, report integration where applicable, and automated tests. Do not change unrelated behavior.
```

---

## 14. Definition of Done

A feature is complete only when:

- Acceptance criteria are demonstrably satisfied.
- Permissions work for allowed and forbidden roles and cohorts.
- Models include required constraints, indexes, migrations, and admin support.
- UI is responsive, accessible, and includes validation/empty/error states.
- Relevant pages support report/export integration.
- Audit events exist for sensitive actions.
- Tests cover happy paths, validation, unauthorized access, boundary time conditions, and concurrency where relevant.
- Lint, formatting, types, tests, migrations check, and Django system check pass.
- Documentation and sample/seed data are updated.
- No answer, explanation, reference solution, private test case, secret, or cross-cohort data leaks before authorization/release.

---

## 15. Minimum Acceptance Scenarios

1. Admin creates a cohort, assigns one faculty coordinator, assigns two student coordinators, and imports students.
2. Unauthorized faculty cannot view or export another cohort's students.
3. A student coordinator creates a draft quiz and submits it for faculty approval.
4. A designated student coordinator publishes only when explicitly granted that permission.
5. A student cannot start before the window, after the window, or outside the assigned cohort.
6. An active attempt autosaves and is submitted exactly once when time expires.
7. Correct answers and explanations are unavailable until the configured release.
8. Coding code runs only through the isolated judge and private tests remain hidden.
9. Leaderboard changes correctly when cohort, assessment, topic, or date filters change.
10. Faculty searches for students using combined academic, aptitude, coding, participation, and skill criteria.
11. A PDF/XLSX/CSV report reflects the same authorized filters as the page.
12. A manual mark adjustment requires a reason and creates an audit record and result version.

---

## 16. Decisions to Confirm Before Production

Development can begin with the defaults below, but confirm these before finalizing business rules:

| Decision | Default assumption |
|---|---|
| Institution scope | One institution, multiple departments/programs |
| Student identifiers | Register number is unique within the institution |
| Cohort membership | One primary cohort per student; optional training groups later |
| Coordinator publishing | Faculty publishes; designated student coordinators may be granted publish permission |
| Attempts | One attempt unless explicitly configured otherwise |
| Result release | After assessment closes and all required evaluation finishes |
| Explanations | Released with results |
| Negative marks | Configurable per question/assessment |
| Ranking | Configurable composite score described above |
| Coding languages | Python, C, C++, and Java initially |
| Code judge | Judge0-compatible isolated service |
| Time zone | Asia/Kolkata for display; UTC in database |
| Reports | PDF, XLSX, CSV; filtered data only |
| Notifications | In-app plus optional email |
| Placement fields | CGPA, backlogs, skills, certifications, placement status, preferred roles |

---

## 17. First Copilot Command

Start a new repository, open it in VS Code, save this file at the repository root, and send Copilot Chat:

```text
Read #file:PLACEMENT_TRAINING_PLATFORM_COPILOT.md. Begin Phase 0 only. First propose the architecture decisions, repository scaffold, dependencies, environment variables, Docker services, and test strategy. Wait for my approval before generating files.
```


# CLAUDE.md — Resolve_Hub Implementation Contract

You are implementing **Resolve_Hub**, an Integrated Command Centre for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus and Cells (Smart India Hackathon 2026, problem statement SIH26264). Read `README.md`, `ARCHITECTURE.md`, and `IMPLEMENTATION.md` before changing code. Treat them as the product and engineering specification.

## Non-negotiable stack
- Backend: Python + Django 5.x
- Web UI: Django Templates + Bootstrap 5 + vanilla JS
- Database: PostgreSQL (Supabase/production) via Django ORM (SQLite for local dev via `DB_ENGINE`)
- Authentication: Django authentication/session framework
- Attachments: private storage with access validation
- Spam engine: Python rules + TF-IDF similarity
- Charts: Chart.js

Never access PostgreSQL directly from browser code. Never expose DB credentials or service-role keys.

## Roles
`STUDENT` (Complainant), `FACULTY`, `PUBLIC`, `SECTION_HEAD`, `BUREAU_HEAD`, `MEMBER_SECRETARY`, `DIRECTOR`, `ADMIN`.

Public registration may create **Complainant-type accounts only** (`STUDENT`, `FACULTY`, `PUBLIC`). Officer accounts (`SECTION_HEAD`, `BUREAU_HEAD`, `MEMBER_SECRETARY`, `DIRECTOR`) are provisioned administratively. `is_staff` alone is not officer/director authorization.

## Critical security rules
1. Enforce authorization server-side on every protected endpoint.
2. Complainants may view only complaints where `student=request.user`.
3. Officers in cells/bureaus see only complaints scoped to their Cell/Bureau; Member Secretary, Director, and Admin have overall oversight.
4. Officers never see complainant personal identity (name, email, mobile, roll number) - identity is never passed to officer templates/contexts. Only Director/Admin can see identity (respecting `is_confidential`).
5. Keep CSRF enabled; use Django password hashing and secure sessions.
6. Never trust user-supplied owner IDs, roles, status, priority, cell, filenames, MIME types, or complaint IDs.
7. Keep `.env` out of Git. Do not log passwords, OTPs, DB passwords, service keys, or attachment contents.
8. Private attachments require an ownership/role check before access.
9. Internal remarks/notes must never render in complainant responses or public tracker.
10. Spam scoring must never automatically delete a complaint.
11. Add tests for authorization before considering a feature complete.

## Engineering rules
- Use custom User model (`AUTH_USER_MODEL = 'accounts.User'`).
- Keep views thin; place status changes, intake, routing, spam scoring, SLA, and risk logic in services.
- Use `transaction.atomic()` for complaint creation, status updates, and escalations.
- Stay on Django + templates + PostgreSQL. No React/FastAPI/Celery/Redis/OpenSearch; scheduled work runs as Django management commands triggered by cron or a platform scheduler.
- Keep the app runnable after each implementation phase.

## Required apps
`accounts`, `institutions`, `complaints`, `officer_portal`, `director_portal`, `triage`, `spam_detection`, `audit`.

## Required core models
- User (complainant_type, cell, bureau)
- Institution, Bureau, Cell, SLAPolicy
- CategoryCellRoute, ComplaintCategory, Complaint, Attachment, ComplaintStatusHistory, EscalationEvent
- SpamAnalysis, InstitutionRiskScore, AuditLog

## Complaint lifecycle
Logged -> Triaged -> Assigned -> Action -> Closed
Mapped backwards-compatibly to: `SUBMITTED -> UNDER_REVIEW -> IN_PROGRESS -> RESOLVED -> CLOSED`.
Administrative outcomes: `REJECTED`, `SPAM`, and pause state: `AWAITING_COMPLAINANT`.

## Spam and triage behavior
Return explainable scores and reasons. Triage combines Hindi/English language detection, ML category prediction, rule-based priority and cell routing, and institutional duplicate linking.

## Implementation workflow
Keep all existing and new tests green: `python manage.py test tests`.

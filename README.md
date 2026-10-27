# Resolve Hub
### Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells

**Resolve Hub** is a centralized institutional grievance monitoring and case management platform designed to help administrators monitor complaints, track resolution progress, oversee institutional performance, and identify cases requiring escalation across AICTE bureaus, cells, and affiliated institutions.

The platform presents an administrative command centre for institutional oversight, case tracking, workload monitoring, and data-driven decision-making.

---

## Overview

Managing institution-related grievances across multiple departments and institutions requires clear visibility into case status, resolution timelines, accountability, and escalation priorities.

Resolve Hub aims to bring these workflows together in a unified dashboard. Instead of functioning as a student-facing complaint submission portal, it focuses on the administrative perspective: monitoring grievance volumes, reviewing case progress, tracking institutional workloads, and supporting timely resolution.

## Key Features

### 1. Administrative Command Centre
- Centralized overview of institutional grievance activity.
- KPI cards and dashboard metrics for quick operational assessment.
- Case summaries, status indicators, and priority visibility.
- Navigation across major administrative monitoring modules.

### 2. Case Registry and Tracking
- Centralized case listing and case-detail views.
- Search, filtering, and case-status monitoring.
- Visibility into complaint priorities, assignments, and resolution progress.
- Case history and activity tracking where supported by the application.

### 3. Bureau and Cell Monitoring
- Organize grievance oversight around administrative bureaus and cells.
- Review workload distribution and case handling activity.
- Identify pending cases and potential bottlenecks.

### 4. Institution Directory
- Maintain an organized view of institutions associated with grievance monitoring.
- Support institution-level oversight and comparison.
- Provide an institutional perspective on complaint volumes and case progress.

### 5. Risk and Escalation Monitoring
- Highlight cases that may require administrative attention.
- Support SLA-oriented monitoring and escalation workflows where configured.
- Help administrators identify delayed or high-priority cases.

### 6. Reports and Analytics
- Present grievance statistics and operational trends.
- Support analysis of case status, workload, and resolution activity.
- Provide CSV export functionality where available.

### 7. Demonstration Data
- Includes a mock-data layer for demonstrating dashboard workflows.
- Sample institutions, bureaus, cells, cases, case histories, and dashboard metrics can be used for demonstrations.
- The demonstration interface is designed to operate without requiring a live external database for its mock-data views.

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend framework | Python, Django |
| Frontend | HTML, CSS, JavaScript |
| Data visualization | Chart.js, where configured |
| Development server | Django development server |
| Demonstration data | Local JavaScript mock-data modules |
| Version control | Git and GitHub |

*The table describes the project's known technology stack. Specific integrations and runtime dependencies may vary with the current implementation.*

---

## Project Structure

The repository contains a Django application with separate modules for complaint management, administrative dashboards, authentication, and supporting services.

```text
Resolve_Hub/
├── Resolve_hub/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── command_centre/
│   │   ├── complaints/
│   │   ├── director_portal/
│   │   ├── hod_portal/
│   │   └── officer_portal/
│   ├── config/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   │       └── mockData/
│   ├── templates/
│   │   ├── command_centre/
│   │   ├── complaints/
│   │   ├── director_portal/
│   │   └── officer_portal/
│   ├── manage.py
│   └── requirements.txt
└── README.md
```

The exact directory contents may evolve as the project develops.

---

## Getting Started

### Prerequisites

Install the following before running the application:

- Python 3.10 or a compatible version supported by the project's dependencies.
- Git.
- PowerShell, Command Prompt, or a terminal.

### 1. Clone the repository

```bash
git clone https://github.com/GORAANG69/Resolve_Hub.git
cd Resolve_Hub
```

### 2. Navigate to the Django project

```bash
cd Resolve_hub
```

### 3. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you already have a working `.venv`, you can activate that environment instead.

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Apply database migrations

```powershell
python manage.py migrate
```

This prepares the configured Django database for application components that require it. The mock-data dashboard views are intended for demonstration and should not be assumed to use a live external database.

### 6. Start the development server

```powershell
python manage.py runserver
```

Open the following address in your browser:

**http://127.0.0.1:8000/**

If a page requires authentication, follow the application's configured login workflow. Create a local administrator account only if required by the current configuration:

```powershell
python manage.py createsuperuser
```

---

## Demonstration Mode

Resolve Hub includes a local mock-data layer for showcasing the administrative dashboard without depending on Supabase, MongoDB, or another external database for those demonstration views.

The mock-data modules are located in:

```text
static/js/mockData/
```

They provide demonstration data for dashboard entities and metrics. These records are illustrative and must not be interpreted as real AICTE grievance records or official institutional statistics.

**Important:** Demonstration data is not a substitute for a production data integration. Before operational deployment, database usage, access controls, data retention, and institutional data sources must be reviewed and configured appropriately.

---

## Intended Users

Resolve Hub is designed around administrative and institutional monitoring workflows, including:

- Regulatory and administrative oversight teams.
- Bureau and cell coordinators.
- Institutional grievance officers.
- Authorized case reviewers and administrators.
- Decision-makers monitoring grievance resolution performance.

The actual roles and permissions available depend on the application's current configuration.

---

## Project Objectives

- Centralize institution-related grievance monitoring.
- Improve visibility into case status and resolution progress.
- Support accountability across bureaus, cells, and institutions.
- Identify cases that need timely intervention.
- Enable data-informed administrative oversight.
- Demonstrate a scalable approach to institutional grievance management.

---

## Security and Responsible Use

- Use synthetic data for demonstrations and presentations.
- Never commit passwords, secret keys, tokens, or production credentials.
- Restrict access to case details according to authorized roles.
- Review authentication, authorization, logging, and data-protection controls before production deployment.
- Do not treat demonstration records or simulated risk scores as official findings.

---

## Current Status

Resolve Hub is a development project demonstrating a centralized administrative approach to institutional grievance monitoring and case management.

Feature availability depends on the current implementation. Production readiness, integrations, and deployment requirements should be verified before use with real institutional data.

---

## Repository

**GitHub:** https://github.com/GORAANG69/Resolve_Hub

---

*Resolve Hub — Bringing institutional grievance monitoring, accountability, and administrative oversight into one centralized command centre.*

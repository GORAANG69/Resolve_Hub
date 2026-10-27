# Resolve_Hub — AICTE Institutional Grievance Monitoring System

**Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells**  
*Smart India Hackathon 2026 &bull; Problem Statement SIH26264*

---

## 1. Overview & Product Identity

**Resolve_Hub** is an enterprise-grade administrative case management and regulatory monitoring system designed for the **All India Council for Technical Education (AICTE)**. It provides executive leadership, bureau heads, cell coordinators, and investigating officers with real-time operational visibility into complaints filed against technical institutions across India.

### Core Objectives
- **Centralized Institutional Triage:** Monitor grievances originating from multiple channels (Web Portal, CPGRAMS, Letter OCR, RTI/Court) in a single operational dashboard.
- **Bureau & Cell Routing:** Track workload distribution across AICTE Bureaus (*Approval, PGRC, Regional Offices, Legal*) and Cells (*Anti-Ragging, Grievance Redressal, Faculty Welfare, Infrastructure, SC/ST/OBC Cell*).
- **SLA & Escalation Autopilot:** Enforce strict resolution turnaround windows with automatic multi-tier escalation (L1 Section Officer &rarr; L2 Bureau Head &rarr; L3 Member Secretary &rarr; L4 Director General).
- **Institutional Risk Radar:** Dynamically score institutions based on active violations, pending show-cause notices, repeat grievances, and SLA breaches.

> **Demonstration Notice:** This deployment operates in a **Simulated Demo Environment** backed by a deterministic local data layer. All institution profiles, case records, officer assignments, and allegations are fictional illustrative representations for evaluation purposes.

---

## 2. Architecture & Data Layer

Resolve_Hub features a **zero-database, fully local demonstration architecture**. It does not require Supabase, PostgreSQL, MongoDB, or any external database credentials to run out of the box.

### Mock Data Engine (`static/js/mockData/`)
The frontend is driven by an in-memory & `localStorage`-synced service (`mockDataService.js`) providing deterministic state management:
- **`mockInstitutions.js`**: 25 realistic technical institutes across Indian states/UTs with permanent AICTE IDs, categories (Engineering, Pharmacy, Architecture, Management), and baseline risk ratings.
- **`mockBureaus.js`**: 4 AICTE Bureaus, 8 Specialized Cells, and illustrative case officers.
- **`mockCases.js`**: 54 comprehensive case records across categories (*Regulatory Compliance, Faculty & Staffing, Approval & Accreditation, Infrastructure & Facilities, Academic Administration, Financial Irregularities, etc.*) with SLA deadlines, priorities (*Critical, High, Medium, Low*), and statuses (*Received, Under Investigation, Awaiting Institutional Response, Escalated, Resolved*).
- **`mockCaseHistory.js`**: Detailed chronological investigation notes, show-cause notices, compliance orders, and document attachment metadata.
- **`mockDashboardMetrics.js`**: Dynamic calculation of KPI counters, SLA compliance rates, monthly intake/resolution trends, and bureau workloads from underlying records.
- **`mockDataService.js`**: High-performance client-side service handling search, multi-field filtering, sorting, pagination, CRUD mutations, audit logging, and CSV export.

---

## 3. Key Administrative Features & Workflows

### A. Main Command Center (`#overview`)
- **Real-Time KPI Counters:** Total Cases Received, Awaiting Assignment, Under Investigation, Awaiting Institutional Response, Resolved, Overdue (Breached), and Approaching SLA Deadlines.
- **Interactive Visualizations (Chart.js):**
  - Monthly Case Intake vs. Resolution Performance.
  - Workload Distribution by AICTE Bureau & Cell.
  - Complaints Breakdown by Category & Source Channel.
  - Geographic Spread by State/UT.
- **Active Escalation Alerts Feed:** Highlighting L1–L3 escalated matters requiring immediate executive review.

### B. Institutional Case Registry (`#registry`)
- High-density data grid displaying Case ID, Monitored Institution, Cell, Category, Priority, Lifecycle Stage, SLA Status, and Channel.
- Real-time instant search (by ID, subject, institution name, or AICTE code).
- Multi-dimensional filters: Bureau, Cell, Priority, Status, State, SLA State (*Breached / At-Risk*), and Source Channel.
- Paginated table with instant client-side updates.

### C. Case Investigation Workspace Modal
Clicking any case opens a comprehensive case workspace:
- **Overview Tab:** Complete grievance dossier, complainant type (confidential), institution details, elapsed time vs. SLA countdown.
- **Investigation Notes Tab:** Interactive form to record time-stamped investigation remarks, officer directives, and findings.
- **Administrative Actions:** Reassign case officer, update status, change priority, trigger executive escalation (L1–L3), update deadlines, or mark case resolved with a resolution summary.
- **Audit & Timeline Tab:** Full chronological history of actions, status transitions, and communications.

### D. Bureau & Cell Workload Monitoring (`#bureaus`)
- Operational workload dashboard comparing case volume, pending actions, resolution velocity, and breach rates across administrative units.
- Interactive filter to inspect individual bureau rosters and case queues.

### E. Institutions Directory (`#institutions`)
- Directory of technical institutes monitored by AICTE with risk level indicators (*Critical, High, Medium, Low*).
- Profile drawer showing institutional compliance history and linked active cases.

### F. Reports & Analytics (`#reports`)
- Comprehensive resolution turnaround times and SLA compliance analysis.
- One-click **Export Filtered CSV** to download case reports directly in the browser.

### G. Audit & Activity Log (`#activity`)
- Immutable chronological record of regulatory actions taken during the demonstration session.

---

## 4. Local Quickstart (Zero External Configuration)

### Prerequisites
- Python 3.10+ (tested with Python 3.12 / 3.14 on Windows, macOS, Linux)
- Modern Web Browser (Chrome, Edge, Firefox, Safari)

### Setup Steps
```bash
# 1. Clone repository
git clone https://github.com/GORAANG69/Resolve_Hub.git
cd Resolve_Hub/Resolve_hub

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# 3. Install core dependencies
pip install -r requirements.txt

# 4. Collect static assets
python manage.py collectstatic --noinput

# 5. Launch the local development server
python manage.py runserver
```

Open your browser and navigate to:
```
http://127.0.0.1:8000/
```
The application will launch directly into the **AICTE Integrated Command Center** with zero login friction.

---

## 5. Demonstration Controls

- **Simulated Role Selector:** Switch between leadership and regulatory roles in the top banner:
  - *Dr. A. K. Mittal* — Director General / Member Secretary
  - *Smt. Sunita Rao* — Bureau Head (Approval & Licensing)
  - *Dr. Ramesh Verma* — Section Head (PGRC Cell)
  - *Adv. Rajesh Kumar* — Legal & Compliance Officer
  - *Sh. Vikramaditya Sen* — Senior Anti-Ragging Coordinator
- **Reset Demo Data:** Click the **Reset Demo Data** button in the top navigation bar at any time to clear local mutations and restore the seed dataset of 54 cases and 25 institutions.

---

## 6. Automated Test Suite

Run the full automated test suite (68 tests passing):
```bash
python manage.py test tests
```

---

## 7. License & Credits
Developed for **Smart India Hackathon 2026** under Problem Statement **SIH26264** (*All India Council for Technical Education - AICTE*).

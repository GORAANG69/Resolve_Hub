/**
 * mockDataService.js - Centralized in-memory & localStorage mock service for Resolve_Hub
 * Provides deterministic state, CRUD updates, filtering, sorting, pagination, and CSV export.
 */

import { mockBureaus, mockOfficers } from "./mockBureaus.js";
import { mockInstitutions } from "./mockInstitutions.js";
import { mockCases } from "./mockCases.js";
import { mockCaseHistory } from "./mockCaseHistory.js";
import { calculateDashboardMetrics } from "./mockDashboardMetrics.js";

const STORAGE_KEY_CASES = "resolve_hub_mock_cases_v2";
const STORAGE_KEY_HISTORY = "resolve_hub_mock_history_v2";
const STORAGE_KEY_ROLE = "resolve_hub_active_role_v2";

class MockDataService {
  constructor() {
    this.bureaus = [...mockBureaus];
    this.officers = [...mockOfficers];
    this.institutions = [...mockInstitutions];
    this.activityLog = [];
    this.loadState();
  }

  loadState() {
    try {
      const savedCases = localStorage.getItem(STORAGE_KEY_CASES);
      const savedHistory = localStorage.getItem(STORAGE_KEY_HISTORY);

      if (savedCases) {
        this.cases = JSON.parse(savedCases);
      } else {
        this.cases = JSON.parse(JSON.stringify(mockCases));
      }

      if (savedHistory) {
        this.caseHistory = JSON.parse(savedHistory);
      } else {
        this.caseHistory = JSON.parse(JSON.stringify(mockCaseHistory));
      }
    } catch (e) {
      console.warn("Storage fallback to memory:", e);
      this.cases = JSON.parse(JSON.stringify(mockCases));
      this.caseHistory = JSON.parse(JSON.stringify(mockCaseHistory));
    }

    this.activeRole = this.getActiveRole();
    this.generateRecentActivity();
  }

  saveState() {
    try {
      localStorage.setItem(STORAGE_KEY_CASES, JSON.stringify(this.cases));
      localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(this.caseHistory));
    } catch (e) {
      console.warn("Unable to persist to localStorage:", e);
    }
  }

  resetDemoData() {
    try {
      localStorage.removeItem(STORAGE_KEY_CASES);
      localStorage.removeItem(STORAGE_KEY_HISTORY);
    } catch (e) {}
    this.cases = JSON.parse(JSON.stringify(mockCases));
    this.caseHistory = JSON.parse(JSON.stringify(mockCaseHistory));
    this.generateRecentActivity();
    return true;
  }

  getActiveRole() {
    try {
      return localStorage.getItem(STORAGE_KEY_ROLE) || "Director General";
    } catch (e) {
      return "Director General";
    }
  }

  setActiveRole(roleName) {
    try {
      localStorage.setItem(STORAGE_KEY_ROLE, roleName);
    } catch (e) {}
    this.activeRole = roleName;
  }

  generateRecentActivity() {
    this.activityLog = [
      { timestamp: "2026-10-26 11:20", caseId: "AICTE-2026-REG-0106", officer: "Sh. Vikramaditya Sen", action: "Escalated to Level 3", details: "Emergency Hearing with Director General convened regarding anti-ragging non-compliance." },
      { timestamp: "2026-10-26 10:15", caseId: "AICTE-2026-REG-0104", officer: "Dr. Priya Sundaram", action: "Investigation Note Added", details: "Aadhaar cross-check verification completed for ghost faculty investigation." },
      { timestamp: "2026-10-25 16:40", caseId: "AICTE-2026-REG-0102", officer: "Smt. Sunita Rao", action: "Status Updated", details: "Moved to 'Awaiting Institutional Response' following Show Cause Notice." },
      { timestamp: "2026-10-25 14:10", caseId: "AICTE-2026-REG-0129", officer: "Smt. Sunita Rao", action: "Case Reassigned", details: "Assigned to Institutional Approval Cell for site plan verification." },
      { timestamp: "2026-10-25 09:30", caseId: "AICTE-2026-REG-0101", officer: "Dr. Ramesh Verma", action: "Priority Upgraded", details: "Upgraded from High to Critical due to repeated fee extortion complaints." }
    ];
  }

  getDashboardMetrics() {
    return calculateDashboardMetrics(this.cases, this.institutions, this.bureaus);
  }

  getBureaus() {
    return this.bureaus;
  }

  getOfficers() {
    return this.officers;
  }

  getInstitutions() {
    return this.institutions.map(inst => {
      const instCases = this.cases.filter(c => c.institutionId === inst.id);
      const openCount = instCases.filter(c => c.status !== "Resolved" && c.status !== "Closed").length;
      const overdueCount = instCases.filter(c => c.slaStatus === "Overdue" && c.status !== "Resolved" && c.status !== "Closed").length;
      const resolvedCount = instCases.filter(c => c.status === "Resolved" || c.status === "Closed").length;

      return {
        ...inst,
        totalCases: instCases.length,
        openCases: openCount,
        overdueCases: overdueCount,
        resolvedCases: resolvedCount
      };
    });
  }

  getInstitutionById(id) {
    const inst = this.institutions.find(i => i.id === id || i.aicteId === id);
    if (!inst) return null;
    const instCases = this.cases.filter(c => c.institutionId === inst.id);
    return {
      ...inst,
      cases: instCases,
      openCases: instCases.filter(c => c.status !== "Resolved" && c.status !== "Closed").length,
      overdueCases: instCases.filter(c => c.slaStatus === "Overdue" && c.status !== "Resolved" && c.status !== "Closed").length,
      resolvedCases: instCases.filter(c => c.status === "Resolved" || c.status === "Closed").length
    };
  }

  getCases(filters = {}, search = "", sortBy = "dateReceived", sortOrder = "desc", page = 1, pageSize = 15) {
    let result = [...this.cases];

    // Search query across ID, institution name, AICTE ID, subject, or external ref
    if (search && search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(c =>
        c.id.toLowerCase().includes(q) ||
        c.institutionName.toLowerCase().includes(q) ||
        (c.aicteId && c.aicteId.toLowerCase().includes(q)) ||
        c.subject.toLowerCase().includes(q) ||
        (c.externalRef && c.externalRef.toLowerCase().includes(q))
      );
    }

    // Role-based scoping simulation
    if (this.activeRole.includes("Approval")) {
      // Prioritize or show Approval bureau
      if (!filters.bureau) {
        // Can filter or view all with a note
      }
    } else if (this.activeRole.includes("PGRC")) {
      // Grievance bureau
    }

    // Explicit filters
    if (filters.bureau && filters.bureau !== "ALL") {
      result = result.filter(c => c.bureauId === filters.bureau);
    }
    if (filters.cell && filters.cell !== "ALL") {
      result = result.filter(c => c.cellId === filters.cell);
    }
    if (filters.category && filters.category !== "ALL") {
      result = result.filter(c => c.category === filters.category);
    }
    if (filters.priority && filters.priority !== "ALL") {
      result = result.filter(c => c.priority === filters.priority);
    }
    if (filters.status && filters.status !== "ALL") {
      result = result.filter(c => c.status === filters.status);
    }
    if (filters.slaStatus && filters.slaStatus !== "ALL") {
      result = result.filter(c => c.slaStatus === filters.slaStatus);
    }
    if (filters.state && filters.state !== "ALL") {
      const stateInstIds = this.institutions.filter(i => i.state === filters.state).map(i => i.id);
      result = result.filter(c => stateInstIds.includes(c.institutionId));
    }
    if (filters.institutionCategory && filters.institutionCategory !== "ALL") {
      const catInstIds = this.institutions.filter(i => i.category === filters.institutionCategory).map(i => i.id);
      result = result.filter(c => catInstIds.includes(c.institutionId));
    }

    // Sorting
    result.sort((a, b) => {
      let valA = a[sortBy];
      let valB = b[sortBy];

      if (sortBy === "priority") {
        const order = { Critical: 4, High: 3, Medium: 2, Low: 1 };
        valA = order[a.priority] || 0;
        valB = order[b.priority] || 0;
      }

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });

    const totalCount = result.length;
    const totalPages = Math.ceil(totalCount / pageSize) || 1;
    const startIndex = (page - 1) * pageSize;
    const paginatedItems = result.slice(startIndex, startIndex + pageSize);

    return {
      items: paginatedItems,
      totalCount,
      totalPages,
      currentPage: page,
      pageSize
    };
  }

  getCaseById(id) {
    const caseItem = this.cases.find(c => c.id === id);
    if (!caseItem) return null;

    const history = this.caseHistory[id] || { notes: [], timeline: [] };
    const institution = this.institutions.find(i => i.id === caseItem.institutionId);

    return {
      ...caseItem,
      institution,
      notes: history.notes || [],
      timeline: history.timeline || []
    };
  }

  assignCase(caseId, bureauId, cellId, officerName, assignedBy = "System") {
    const c = this.cases.find(item => item.id === caseId);
    if (!c) return false;

    const bureau = this.bureaus.find(b => b.id === bureauId);
    const cell = bureau ? bureau.cells.find(cl => cl.id === cellId) : null;

    c.bureauId = bureauId;
    c.bureauName = bureau ? bureau.name : c.bureauName;
    c.cellId = cellId;
    c.cellName = cell ? cell.name : c.cellName;
    c.assignedOfficer = officerName;
    c.lastUpdated = new Date().toISOString().split("T")[0];

    if (c.status === "Awaiting Assignment") {
      c.status = "Under Preliminary Review";
    }

    this.recordActivity(caseId, assignedBy, "Case Assigned", `Assigned to ${officerName} (${c.cellName})`);
    this.saveState();
    return true;
  }

  updateCaseStatus(caseId, newStatus, remarks, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (!c) return false;

    const oldStatus = c.status;
    c.status = newStatus;
    c.lastUpdated = new Date().toISOString().split("T")[0];

    if (newStatus === "Resolved") {
      c.slaStatus = "Resolved Within SLA";
      c.resolutionSummary = remarks || "Resolution formally accepted and recorded.";
    }

    this.recordActivity(caseId, officerName, "Status Updated", `Changed from '${oldStatus}' to '${newStatus}'. Remarks: ${remarks || "None"}`);
    this.saveState();
    return true;
  }

  updateCasePriority(caseId, newPriority, remarks, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (!c) return false;

    const old = c.priority;
    c.priority = newPriority;
    c.lastUpdated = new Date().toISOString().split("T")[0];

    this.recordActivity(caseId, officerName, "Priority Changed", `Priority re-evaluated from '${old}' to '${newPriority}'. Reason: ${remarks}`);
    this.saveState();
    return true;
  }

  addInvestigationNote(caseId, noteText, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (!c) return false;

    if (!this.caseHistory[caseId]) {
      this.caseHistory[caseId] = { notes: [], timeline: [] };
    }

    const now = new Date();
    const dateStr = now.toISOString().replace("T", " ").substring(0, 16);

    const newNote = {
      id: `NOTE-${Date.now()}`,
      author: officerName,
      date: dateStr,
      content: noteText
    };

    this.caseHistory[caseId].notes.unshift(newNote);
    c.lastUpdated = now.toISOString().split("T")[0];

    this.recordActivity(caseId, officerName, "Investigation Note Added", noteText.substring(0, 100) + (noteText.length > 100 ? "..." : ""));
    this.saveState();
    return true;
  }

  escalateCase(caseId, targetLevel, justification, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (!c) return false;

    c.escalationLevel = targetLevel;
    c.status = "Escalated";
    c.lastUpdated = new Date().toISOString().split("T")[0];

    const levelDescriptions = {
      1: "Level 1: Section Head Priority Review",
      2: "Level 2: Bureau Head Inter-Departmental Escalation",
      3: "Level 3: Member Secretary & Director General Alert"
    };

    this.recordActivity(caseId, officerName, `Case Escalated (L${targetLevel})`, `${levelDescriptions[targetLevel] || "Escalation"}. Justification: ${justification}`);
    this.saveState();
    return true;
  }

  recordActivity(caseId, officer, action, details) {
    const now = new Date();
    const dateStr = now.toISOString().replace("T", " ").substring(0, 16);

    // Add to global activity log
    this.activityLog.unshift({
      timestamp: dateStr,
      caseId,
      officer,
      action,
      details
    });
    if (this.activityLog.length > 50) this.activityLog.pop();

    // Add to specific case timeline
    if (!this.caseHistory[caseId]) {
      this.caseHistory[caseId] = { notes: [], timeline: [] };
    }

    this.caseHistory[caseId].timeline.unshift({
      date: dateStr,
      title: action,
      actor: officer,
      description: details
    });
  }

  getActivityLog() {
    return this.activityLog;
  }

  exportCasesCSV(filters = {}, search = "") {
    const { items } = this.getCases(filters, search, "dateReceived", "desc", 1, 1000);
    const headers = [
      "Case ID",
      "Institution Name",
      "AICTE ID",
      "Category",
      "Assigned Bureau",
      "Assigned Cell",
      "Officer",
      "Priority",
      "Status",
      "Date Received",
      "Deadline",
      "SLA Status",
      "Escalation Level"
    ];

    const rows = items.map(c => [
      `"${c.id}"`,
      `"${c.institutionName}"`,
      `"${c.aicteId}"`,
      `"${c.category}"`,
      `"${c.bureauName}"`,
      `"${c.cellName}"`,
      `"${c.assignedOfficer}"`,
      `"${c.priority}"`,
      `"${c.status}"`,
      `"${c.dateReceived}"`,
      `"${c.resolutionDeadline}"`,
      `"${c.slaStatus}"`,
      `"L${c.escalationLevel}"`
    ]);

    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `AICTE_Grievance_Case_Registry_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async fetchRealDatasetsAnalytics() {
    try {
      const response = await fetch("/command-centre/api/datasets/analytics/");
      if (response.ok) {
        return await response.json();
      }
    } catch (e) {
      console.warn("Real datasets analytics fetch failed:", e);
    }
    return null;
  }

  async fetchCitizenGrievances(page = 1, pageSize = 20, category = "", search = "") {
    try {
      const params = new URLSearchParams({ page, page_size: pageSize });
      if (category) params.append("category", category);
      if (search) params.append("search", search);
      const response = await fetch(`/command-centre/api/datasets/citizen-grievances/?${params.toString()}`);
      if (response.ok) {
        return await response.json();
      }
    } catch (e) {
      console.warn("Citizen grievances API fetch failed:", e);
    }
    return null;
  }

  async fetchStudentFeedback(page = 1, pageSize = 20, category = "", sentiment = "") {
    try {
      const params = new URLSearchParams({ page, page_size: pageSize });
      if (category) params.append("category", category);
      if (sentiment) params.append("sentiment", sentiment);
      const response = await fetch(`/command-centre/api/datasets/student-feedback/?${params.toString()}`);
      if (response.ok) {
        return await response.json();
      }
    } catch (e) {
      console.warn("Student feedback API fetch failed:", e);
    }
    return null;
  }
}

export const mockDataService = new MockDataService();

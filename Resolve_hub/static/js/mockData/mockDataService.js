/**
 * mockDataService.js - Centralized Data & API Service for Resolve_Hub
 * Seamlessly interfaces with the Django backend REST APIs while preserving in-memory fallbacks.
 * Powers live database metrics, case workspaces, AI recommendations, SLA count-downs,
 * legal-attention reviews, and institutional duplicate links.
 */

import { mockBureaus, mockOfficers } from "./mockBureaus.js";
import { mockInstitutions } from "./mockInstitutions.js";
import { mockCases } from "./mockCases.js";
import { mockCaseHistory } from "./mockCaseHistory.js";
import { calculateDashboardMetrics } from "./mockDashboardMetrics.js";

const STORAGE_KEY_CASES = "resolve_hub_cases_v3";
const STORAGE_KEY_HISTORY = "resolve_hub_history_v3";
const STORAGE_KEY_ROLE = "resolve_hub_active_role_v3";

class MockDataService {
  constructor() {
    this.bureaus = [...mockBureaus];
    this.officers = [...mockOfficers];
    this.institutions = [...mockInstitutions];
    this.activityLog = [];
    this.cases = [];
    this.caseHistory = {};
    this.backendSynced = false;
    this.loadState();
    this.syncWithBackend();
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

  async syncWithBackend() {
    try {
      // 1. Fetch live metrics & reference entities
      const metricsRes = await fetch("/api/dashboard/metrics/");
      if (metricsRes.ok) {
        const data = await metricsRes.json();
        if (data.status === "success") {
          if (data.bureaus && data.bureaus.length > 0) this.bureaus = data.bureaus;
          if (data.institutions && data.institutions.length > 0) this.institutions = data.institutions;
          this.backendMetrics = data;
        }
      }

      // 2. Fetch live cases from database
      const casesRes = await fetch("/api/cases/?page_size=200");
      if (casesRes.ok) {
        const cData = await casesRes.json();
        if (cData.status === "success" && cData.cases && cData.cases.length > 0) {
          this.cases = cData.cases;
          this.backendSynced = true;
          this.saveState();
          // Dispatch notification to UI
          window.dispatchEvent(new CustomEvent("resolvehub:backend-synced", { detail: { count: cData.cases.length } }));
        }
      }
    } catch (err) {
      console.debug("Backend sync notice (using local/fallback state):", err);
    }
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
    this.syncWithBackend();
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
      { timestamp: "2026-10-29 11:20", caseId: "AICTE-2026-REG-0106", officer: "Sh. Vikramaditya Sen", action: "Escalated to Level 3", details: "Emergency Hearing with Director General convened regarding anti-ragging non-compliance." },
      { timestamp: "2026-10-29 10:15", caseId: "AICTE-2026-REG-0104", officer: "Dr. Priya Sundaram", action: "Investigation Note Added", details: "Aadhaar cross-check verification completed for ghost faculty investigation." },
      { timestamp: "2026-10-28 16:40", caseId: "AICTE-2026-REG-0102", officer: "Smt. Sunita Rao", action: "Status Updated", details: "Moved to 'Awaiting Institutional Response' following Show Cause Notice." },
      { timestamp: "2026-10-28 14:10", caseId: "AICTE-2026-REG-0129", officer: "Smt. Sunita Rao", action: "Case Reassigned", details: "Assigned to Institutional Approval Cell for site plan verification." },
      { timestamp: "2026-10-27 09:30", caseId: "AICTE-2026-REG-0101", officer: "Dr. Ramesh Verma", action: "Priority Upgraded", details: "Upgraded from High to Critical due to repeated fee extortion complaints." }
    ];
  }

  getDashboardMetrics() {
    if (this.backendMetrics && this.backendMetrics.kpis) {
      const bm = this.backendMetrics;
      const kpis = {
        totalCases: bm.kpis.total_cases,
        openCases: bm.kpis.open_cases,
        overdueCases: bm.kpis.sla_breached,
        resolvedCases: bm.kpis.resolved_cases,
        escalatedCases: (bm.kpis.escalated_l1 || 0) + (bm.kpis.escalated_l2 || 0) + (bm.kpis.escalated_l3 || 0),
        urgentReviews: bm.kpis.urgent_review_count || 0,
        legalFlags: bm.kpis.legal_flag_count || 0,
        pendingHumanReviews: bm.kpis.pending_human_review_count || 0,
      };
      return {
        ...kpis,
        kpis: kpis,
        statusCounts: bm.charts.statusCounts || {},
        priorityCounts: bm.charts.priorityCounts || {},
        bureauWorkload: bm.charts.bureauWorkload || {},
        monthlyTrends: bm.charts.monthlyTrends && bm.charts.monthlyTrends.labels ? bm.charts.monthlyTrends : {
          labels: ["May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026"],
          intake: [6, 8, 11, 14, 18, 23],
          resolved: [5, 7, 9, 12, 10, 8]
        },
        institutionCategories: bm.charts.institutionCategories && Object.keys(bm.charts.institutionCategories).length > 0 ? bm.charts.institutionCategories : {
          "Engineering & Technology": 30,
          "Management": 12,
          "Pharmacy": 6,
          "Polytechnic / Diploma": 4,
          "Architecture": 2
        },
        recentAlerts: bm.recent_alerts || [],
        highAttentionInstitutions: bm.high_attention_institutions || [],
      };
    }
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
      const instCases = this.cases.filter(c => c.institutionId === inst.id || c.aicteId === inst.aicteId);
      const openCount = instCases.filter(c => c.status !== "Resolved" && c.status !== "Closed").length;
      const overdueCount = instCases.filter(c => (c.slaStatus === "Overdue" || c.isSlaBreached) && c.status !== "Resolved" && c.status !== "Closed").length;
      const resolvedCount = instCases.filter(c => c.status === "Resolved" || c.status === "Closed").length;

      return {
        ...inst,
        totalCases: instCases.length || inst.activeCases || 0,
        openCases: openCount,
        overdueCases: overdueCount,
        resolvedCases: resolvedCount,
      };
    });
  }

  getInstitutionById(id) {
    const inst = this.institutions.find(i => i.id === id || i.aicteId === id);
    if (!inst) return null;
    const instCases = this.cases.filter(c => c.institutionId === inst.id || c.aicteId === inst.aicteId);
    return {
      ...inst,
      cases: instCases,
      openCases: instCases.filter(c => c.status !== "Resolved" && c.status !== "Closed").length,
      overdueCases: instCases.filter(c => (c.slaStatus === "Overdue" || c.isSlaBreached) && c.status !== "Resolved" && c.status !== "Closed").length,
      resolvedCases: instCases.filter(c => c.status === "Resolved" || c.status === "Closed").length,
    };
  }

  getCases(filters = {}, search = "", sortBy = "dateReceived", sortOrder = "desc", page = 1, pageSize = 15) {
    let result = [...this.cases];

    // Search query
    if (search && search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(c =>
        (c.id && c.id.toLowerCase().includes(q)) ||
        (c.institutionName && c.institutionName.toLowerCase().includes(q)) ||
        (c.aicteId && c.aicteId.toLowerCase().includes(q)) ||
        (c.subject && c.subject.toLowerCase().includes(q)) ||
        (c.category && c.category.toLowerCase().includes(q)) ||
        (c.assignedOfficer && c.assignedOfficer.toLowerCase().includes(q))
      );
    }

    // Filters
    if (filters.bureau && filters.bureau !== "ALL") {
      result = result.filter(c => c.bureauId === filters.bureau || c.bureauName === filters.bureau);
    }
    if (filters.cell && filters.cell !== "ALL") {
      result = result.filter(c => c.cellId === filters.cell || c.cellName === filters.cell);
    }
    if (filters.category && filters.category !== "ALL") {
      result = result.filter(c => c.category === filters.category);
    }
    if (filters.priority && filters.priority !== "ALL") {
      result = result.filter(c => c.priority.toUpperCase() === filters.priority.toUpperCase());
    }
    if (filters.status && filters.status !== "ALL") {
      result = result.filter(c => c.status.toLowerCase().includes(filters.status.toLowerCase()));
    }
    if (filters.slaStatus && filters.slaStatus !== "ALL") {
      if (filters.slaStatus === "Overdue" || filters.slaStatus === "BREACHED") {
        result = result.filter(c => c.isSlaBreached || (c.slaStatus && c.slaStatus.toLowerCase().includes("breached")) || c.slaStatus === "Overdue");
      } else if (filters.slaStatus === "Approaching" || filters.slaStatus === "AT_RISK") {
        result = result.filter(c => c.isApproaching || (c.slaStatus && c.slaStatus.toLowerCase().includes("approaching")));
      } else if (filters.slaStatus === "Resolved") {
        result = result.filter(c => c.status === "Resolved" || (c.slaStatus && c.slaStatus.toLowerCase().includes("resolved")));
      } else {
        result = result.filter(c => c.slaStatus && c.slaStatus.toLowerCase().includes(filters.slaStatus.toLowerCase()));
      }
    }
    if (filters.legalFlag && filters.legalFlag !== "ALL") {
      result = result.filter(c => (c.legalFlag && c.legalFlag.toUpperCase() === filters.legalFlag.toUpperCase()));
    }
    if (filters.state && filters.state !== "ALL") {
      result = result.filter(c => c.institutionState === filters.state || (c.institution && c.institution.state === filters.state));
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
      pageSize,
    };
  }

  getCaseById(id) {
    const caseItem = this.cases.find(c => c.id === id);
    if (!caseItem) return null;

    const history = this.caseHistory[id] || { notes: [], timeline: [] };
    const institution = this.institutions.find(i => i.id === caseItem.institutionId || i.aicteId === caseItem.aicteId);

    return {
      ...caseItem,
      institution,
      notes: history.notes || [],
      timeline: history.timeline || [],
    };
  }

  async getBackendCaseDetail(caseId) {
    try {
      const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success" && data.case) {
          return data.case;
        }
      }
    } catch (e) {
      console.debug("Backend case detail fetch fallback:", e);
    }
    return this.getCaseById(caseId);
  }

  async assignCase(caseId, bureauId, cellId, officerName, assignedBy = "System") {
    const c = this.cases.find(item => item.id === caseId);
    if (c) {
      c.bureauId = bureauId;
      c.cellId = cellId;
      c.assignedOfficer = officerName;
      c.lastUpdated = new Date().toISOString().split("T")[0];
      if (c.status === "Awaiting Assignment") c.status = "Under Preliminary Review";
      this.recordActivity(caseId, assignedBy, "Case Assigned", `Assigned to ${officerName}`);
      this.saveState();
    }

    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "assign_case", officer: officerName }),
      });
    } catch (e) {}
    return true;
  }

  async updateCaseStatus(caseId, newStatus, remarks, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (c) {
      const oldStatus = c.status;
      c.status = newStatus;
      c.lastUpdated = new Date().toISOString().split("T")[0];
      if (newStatus === "Resolved") {
        c.slaStatus = "Resolved Within SLA";
        c.resolutionSummary = remarks || "Resolution formally accepted.";
      }
      this.recordActivity(caseId, officerName, "Status Updated", `Changed from '${oldStatus}' to '${newStatus}'. Remarks: ${remarks || "None"}`);
      this.saveState();
    }

    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "update_status", status: newStatus, notes: remarks }),
      });
    } catch (e) {}
    return true;
  }

  async updateCasePriority(caseId, newPriority, remarks, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (c) {
      const old = c.priority;
      c.priority = newPriority;
      c.lastUpdated = new Date().toISOString().split("T")[0];
      this.recordActivity(caseId, officerName, "Priority Changed", `Priority re-evaluated from '${old}' to '${newPriority}'. Reason: ${remarks}`);
      this.saveState();
    }

    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "update_priority", priority: newPriority, reason: remarks }),
      });
    } catch (e) {}
    return true;
  }

  async addInvestigationNote(caseId, noteText, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (c) {
      if (!this.caseHistory[caseId]) this.caseHistory[caseId] = { notes: [], timeline: [] };
      const now = new Date();
      const dateStr = now.toISOString().replace("T", " ").substring(0, 16);
      this.caseHistory[caseId].notes.unshift({ id: `NOTE-${Date.now()}`, author: officerName, date: dateStr, content: noteText });
      c.lastUpdated = now.toISOString().split("T")[0];
      this.recordActivity(caseId, officerName, "Investigation Note Added", noteText.substring(0, 100));
      this.saveState();
    }

    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "add_note", content: noteText }),
      });
    } catch (e) {}
    return true;
  }

  async escalateCase(caseId, targetLevel, justification, officerName = "Authorized Official") {
    const c = this.cases.find(item => item.id === caseId);
    if (c) {
      c.escalationLevel = targetLevel;
      c.status = "Escalated";
      c.lastUpdated = new Date().toISOString().split("T")[0];
      this.recordActivity(caseId, officerName, `Case Escalated (L${targetLevel})`, justification);
      this.saveState();
    }

    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "escalate_case", level: targetLevel, reason: justification }),
      });
    } catch (e) {}
    return true;
  }

  async updateRecommendationAction(caseId, recommendationId, title, state, notes = "") {
    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "update_recommendation",
          recommendation_id: recommendationId,
          title: title,
          state: state,
          notes: notes,
        }),
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async updateLegalReview(caseId, flagLevel, status, notes = "", referredAuthority = "") {
    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "update_legal_review",
          flag_level: flagLevel,
          status: status,
          notes: notes,
          referred_authority: referredAuthority,
        }),
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async confirmDuplicate(caseId, targetCaseId, relType, notes = "") {
    try {
      await fetch(`/api/cases/${encodeURIComponent(caseId)}/action/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "confirm_duplicate",
          target_case_id: targetCaseId,
          relationship_type: relType,
          notes: notes,
        }),
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  recordActivity(caseId, officer, action, details) {
    const now = new Date();
    const dateStr = now.toISOString().replace("T", " ").substring(0, 16);

    this.activityLog.unshift({ timestamp: dateStr, caseId, officer, action, details });
    if (this.activityLog.length > 50) this.activityLog.pop();

    if (!this.caseHistory[caseId]) {
      this.caseHistory[caseId] = { notes: [], timeline: [] };
    }
    this.caseHistory[caseId].timeline.unshift({ date: dateStr, title: action, actor: officer, description: details });
  }

  getActivityLog() {
    return this.activityLog;
  }

  exportCasesCSV(filters = {}, search = "") {
    const { items } = this.getCases(filters, search, "dateReceived", "desc", 1, 1000);
    const headers = [
      "Case ID", "Institution Name", "AICTE ID", "Category",
      "Assigned Bureau", "Assigned Cell", "Officer", "Priority",
      "Status", "Date Received", "Deadline", "SLA Status", "Escalation Level", "Legal Attention"
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
      `"L${c.escalationLevel}"`,
      `"${c.legalFlagLabel || c.legalFlag || 'Routine'}"`,
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
}

export const mockDataService = new MockDataService();

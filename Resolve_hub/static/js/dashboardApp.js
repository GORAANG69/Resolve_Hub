/**
 * dashboardApp.js - Main Application Controller for Resolve_Hub Administrative Console
 * Seamlessly manages views, interactive charts, filtering, search, pagination, and case actions.
 */

import { mockDataService } from "./mockData/mockDataService.js";

class DashboardApp {
  constructor() {
    this.currentView = "overview";
    this.filters = {
      bureau: "ALL",
      cell: "ALL",
      category: "ALL",
      priority: "ALL",
      status: "ALL",
      slaStatus: "ALL",
      legalFlag: "ALL",
      state: "ALL",
      institutionCategory: "ALL"
    };
    this.searchQuery = "";
    this.currentPage = 1;
    this.pageSize = 12;
    this.sortBy = "dateReceived";
    this.sortOrder = "desc";
    this.chartInstances = {};
    this.activeCaseId = null;

    this.init();
  }

  init() {
    this.setupNavigation();
    this.setupGlobalControls();
    this.renderCurrentView();
  }

  setupNavigation() {
    document.querySelectorAll(".rh-nav-link").forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const targetView = link.getAttribute("data-view");
        this.switchView(targetView);
      });
    });

    // Support browser back/forward and direct hash routing
    window.addEventListener("hashchange", () => {
      const hash = window.location.hash.replace("#", "").trim();
      const validViews = ["overview", "registry", "bureaus", "institutions", "reports", "activity", "settings"];
      if (hash && validViews.includes(hash) && this.currentView !== hash) {
        this.switchView(hash, false);
      }
    });

    // Brand title click to return to overview
    const brand = document.querySelector(".rh-brand-title");
    if (brand) {
      brand.style.cursor = "pointer";
      brand.addEventListener("click", () => this.switchView("overview"));
    }
  }

  switchView(viewName, updateHash = true) {
    this.currentView = viewName;
    if (updateHash && window.location.hash !== `#${viewName}`) {
      window.history.pushState(null, "", `#${viewName}`);
    }
    document.querySelectorAll(".rh-nav-link").forEach(link => {
      if (link.getAttribute("data-view") === viewName) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });
    this.renderCurrentView();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  setupGlobalControls() {
    // Role selector
    const roleSelect = document.getElementById("activeRoleSelector");
    if (roleSelect) {
      roleSelect.value = mockDataService.getActiveRole();
      roleSelect.addEventListener("change", (e) => {
        mockDataService.setActiveRole(e.target.value);
        this.showNotification(`Active role switched to: ${e.target.value}`, "info");
        this.renderCurrentView();
      });
    }

    // Reset demo data button
    const resetBtn = document.getElementById("btnResetDemoData");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        if (confirm("Reset all simulated cases and investigation notes to initial seed dataset?")) {
          mockDataService.resetDemoData();
          this.showNotification("Simulated dataset successfully restored to original seed state.", "success");
          this.renderCurrentView();
        }
      });
    }

    // Phase 8: Theme Controls (Light, Dark, System)
    this.setupThemeControls();

    // Live SLA countdown background ticker
    this.startSlaTickers();

    // Listen for backend database synchronization
    window.addEventListener("resolvehub:backend-synced", () => {
      if (this.currentView === "overview" || this.currentView === "registry" || this.currentView === "bureaus") {
        this.renderCurrentView();
      }
    });
  }

  setupThemeControls() {
    const currentTheme = (localStorage.getItem("rh_theme_preference") || "system").toLowerCase();
    this.applyTheme(currentTheme, false);

    document.querySelectorAll(".theme-choice-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const chosen = btn.getAttribute("data-theme");
        this.applyTheme(chosen, true);
      });
    });

    // Listen for OS scheme change if in system mode
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      const active = (localStorage.getItem("rh_theme_preference") || "system").toLowerCase();
      if (active === "system") {
        this.applyTheme("system", false);
      }
    });
  }

  applyTheme(theme, notify = true) {
    theme = (theme || "system").toLowerCase();
    this.currentTheme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("rh_theme_preference", theme);

    const labelEl = document.getElementById("themeLabelCurrent");
    const iconEl = document.getElementById("themeIconCurrent");
    if (labelEl && iconEl) {
      if (theme === "dark") {
        labelEl.textContent = "Theme: Dark";
        iconEl.className = "bi bi-moon-stars me-1 text-info";
      } else if (theme === "light") {
        labelEl.textContent = "Theme: Light";
        iconEl.className = "bi bi-sun me-1 text-warning";
      } else {
        labelEl.textContent = "Theme: System";
        iconEl.className = "bi bi-display me-1 text-secondary";
      }
    }

    // Persist to backend session / user profile
    fetch("/api/theme/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme: theme.toUpperCase() }),
    }).catch(() => {});

    if (notify) {
      this.showNotification(`Theme set to ${theme.charAt(0).toUpperCase() + theme.slice(1)} Mode.`, "info");
    }
  }

  startSlaTickers() {
    if (this.slaInterval) clearInterval(this.slaInterval);
    this.slaInterval = setInterval(() => {
      this.tickSlaTimers();
    }, 30000);
  }

  tickSlaTimers() {
    document.querySelectorAll(".sla-timer-badge[data-deadline]").forEach(el => {
      const deadlineStr = el.getAttribute("data-deadline");
      if (!deadlineStr || el.getAttribute("data-completed") === "true") return;

      const deadline = new Date(deadlineStr);
      const now = new Date();
      const diffSec = (deadline - now) / 1000;

      if (diffSec < 0) {
        const sec = Math.abs(diffSec);
        const days = Math.floor(sec / 86400);
        const hours = Math.floor((sec % 86400) / 3600);
        el.innerHTML = `<i class="bi bi-exclamation-octagon-fill me-1"></i>SLA breached by ${days > 0 ? `${days}d ` : ''}${hours}h`;
        el.className = "sla-timer-badge sla-badge-breached";
      } else {
        const days = Math.floor(diffSec / 86400);
        const hours = Math.floor((diffSec % 86400) / 3600);
        const mins = Math.floor((diffSec % 3600) / 60);
        if (days > 0) {
          el.innerHTML = `<i class="bi bi-clock-history me-1"></i>${days}d ${hours}h remaining`;
          el.className = "sla-timer-badge sla-badge-on-track";
        } else if (hours > 0) {
          el.innerHTML = `<i class="bi bi-hourglass-split me-1"></i>Due in ${hours}h ${mins}m`;
          el.className = "sla-timer-badge sla-badge-approaching";
        } else {
          el.innerHTML = `<i class="bi bi-alarm-fill me-1"></i>Due in ${Math.max(1, mins)}m`;
          el.className = "sla-timer-badge sla-badge-breached";
        }
      }
    });
  }

  renderCurrentView() {
    const container = document.getElementById("mainContentArea");
    if (!container) return;

    this.destroyCharts();

    try {
      switch (this.currentView) {
        case "overview":
          this.renderOverview(container);
          break;
        case "registry":
          this.renderRegistry(container);
          break;
        case "bureaus":
          this.renderBureaus(container);
          break;
        case "institutions":
          this.renderInstitutions(container);
          break;
        case "reports":
          this.renderReports(container);
          break;
        case "activity":
          this.renderActivity(container);
          break;
        case "settings":
          this.renderSettings(container);
          break;
        default:
          this.renderOverview(container);
      }
    } catch (err) {
      console.error("Dashboard render error on view:", this.currentView, err);
      container.innerHTML = `
        <div class="alert alert-warning border-0 shadow-sm m-4 p-4 text-center" style="border-left: 4px solid #F59E0B !important;">
          <h5 class="fw-bold text-dark"><i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Unable to Display Dashboard View</h5>
          <p class="text-muted small mb-3">A temporary error occurred while rendering the ${this.currentView} console. Please retry loading.</p>
          <button class="btn btn-primary btn-sm px-4" id="btnRetryRender">
            <i class="bi bi-arrow-clockwise me-1"></i> Retry Loading Dashboard
          </button>
        </div>
      `;
      const retryBtn = container.querySelector("#btnRetryRender");
      if (retryBtn) {
        retryBtn.addEventListener("click", () => {
          this.renderCurrentView();
        });
      }
    }
  }

  destroyCharts() {
    Object.values(this.chartInstances).forEach(chart => {
      if (chart && typeof chart.destroy === "function") {
        try { chart.destroy(); } catch (e) {}
      }
    });
    this.chartInstances = {};

    if (typeof Chart !== "undefined" && typeof Chart.getChart === "function") {
      ["chartIntakeResolved", "chartStatusDistribution", "chartBureauWorkload", "chartInstitutionCategory", "chartReportsResolutionRate", "chartReportsAging"].forEach(id => {
        const existing = Chart.getChart(id);
        if (existing) {
          try { existing.destroy(); } catch (e) {}
        }
      });
    }
  }

  showNotification(message, type = "info") {
    const alertBox = document.createElement("div");
    alertBox.className = `alert alert-${type === "error" ? "danger" : type} alert-dismissible fade show shadow-sm position-fixed top-0 end-0 m-3`;
    alertBox.style.zIndex = "9999";
    alertBox.innerHTML = `
      <strong>${type === "success" ? "✓ Success" : "Notice"}:</strong> ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertBox);
    setTimeout(() => {
      if (alertBox.parentElement) alertBox.remove();
    }, 4000);
  }

  /* =========================================================================
     VIEW 1: OVERVIEW / COMMAND CENTER
     ========================================================================= */
  renderOverview(container) {
    const metrics = mockDataService.getDashboardMetrics();
    const { kpis, monthlyTrends, priorityCounts, statusCounts, highAttentionInstitutions } = metrics;
    const bureaus = mockDataService.getBureaus();
    const urgentCases = mockDataService.getCases({ status: "ALL" }, "", "priority", "desc", 1, 6).items;
    const overdueCases = mockDataService.getCases({ slaStatus: "Overdue" }, "", "dateReceived", "asc", 1, 5).items;

    container.innerHTML = `
      <!-- Command Center Header -->
      <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
        <div>
          <h4 class="fw-bold mb-1" style="color: var(--rh-navy-dark);">AICTE Executive Command Center</h4>
          <p class="text-muted small mb-0">Cross-Bureau Institutional Grievance Monitoring, Case Triage & Regulatory Turnaround Analysis</p>
        </div>
        <div class="d-flex gap-2 mt-2 mt-md-0">
          <button class="btn btn-rh-secondary btn-sm" id="btnExportOverviewCSV">
            <i class="bi bi-download me-1"></i> Export Cases CSV
          </button>
          <button class="btn btn-rh-primary btn-sm" id="btnGoToRegistry">
            <i class="bi bi-table me-1"></i> Open Case Registry
          </button>
        </div>
      </div>

      <!-- KPI Cards Row -->
      <div class="row g-3 mb-4">
        <div class="col-xl-3 col-md-6">
          <div class="rh-kpi-card border-accent-primary">
            <div class="rh-kpi-title">Total Institutional Cases</div>
            <div class="rh-kpi-value">${kpis.totalCases}</div>
            <div class="rh-kpi-sub"><span class="text-primary fw-bold">${kpis.openCases}</span> active cases under tracking</div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="rh-kpi-card border-accent-warning">
            <div class="rh-kpi-title">Under Investigation</div>
            <div class="rh-kpi-value text-warning">${kpis.underInvestigation}</div>
            <div class="rh-kpi-sub">${kpis.awaitingAssignment} pending bureau assignment</div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="rh-kpi-card border-accent-danger">
            <div class="rh-kpi-title">Overdue Cases (SLA Breached)</div>
            <div class="rh-kpi-value text-danger">${kpis.overdueCases}</div>
            <div class="rh-kpi-sub text-danger fw-bold"><i class="bi bi-exclamation-triangle-fill"></i> ${kpis.escalatedL2 + kpis.escalatedL3} cases escalated</div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="rh-kpi-card border-accent-success">
            <div class="rh-kpi-title">Cases Resolved</div>
            <div class="rh-kpi-value text-success">${kpis.resolvedCases}</div>
            <div class="rh-kpi-sub"><span class="text-success fw-bold">${kpis.resolutionRate}%</span> overall resolution rate</div>
          </div>
        </div>
      </div>

      <!-- Secondary Metrics Row -->
      <div class="row g-3 mb-4">
        <div class="col-md-3 col-sm-6">
          <div class="p-3 bg-white rounded border shadow-sm text-center">
            <div class="small text-muted fw-bold">PENDING WITH INSTITUTION</div>
            <h4 class="mb-0 fw-bold mt-1 text-secondary">${kpis.pendingInstitution}</h4>
            <div class="small text-muted">Awaiting Show-Cause replies</div>
          </div>
        </div>
        <div class="col-md-3 col-sm-6">
          <div class="p-3 bg-white rounded border shadow-sm text-center">
            <div class="small text-muted fw-bold">APPROACHING DEADLINE</div>
            <h4 class="mb-0 fw-bold mt-1 text-warning">${kpis.approachingDeadline}</h4>
            <div class="small text-muted">&lt; 48 hours remaining</div>
          </div>
        </div>
        <div class="col-md-3 col-sm-6">
          <div class="p-3 bg-white rounded border shadow-sm text-center">
            <div class="small text-muted fw-bold">SLA COMPLIANCE RATE</div>
            <h4 class="mb-0 fw-bold mt-1 text-primary">${kpis.slaComplianceRate}%</h4>
            <div class="small text-muted">Cases within statutory window</div>
          </div>
        </div>
        <div class="col-md-3 col-sm-6">
          <div class="p-3 bg-white rounded border shadow-sm text-center">
            <div class="small text-muted fw-bold">AVG RESOLUTION TIME</div>
            <h4 class="mb-0 fw-bold mt-1 text-dark">${kpis.avgTurnaroundDays} Days</h4>
            <div class="small text-muted">Turnaround across bureaus</div>
          </div>
        </div>
      </div>

      <!-- Interactive Charts Row -->
      <div class="row g-3 mb-4">
        <div class="col-lg-8">
          <div class="rh-card h-100 mb-0">
            <div class="rh-card-header">
              <h6 class="rh-card-title">Case Intake vs. Resolution Performance (Monthly)</h6>
              <span class="badge bg-light text-dark border">May - Oct 2026</span>
            </div>
            <div class="rh-card-body">
              <canvas id="chartIntakeResolved" height="220"></canvas>
            </div>
          </div>
        </div>
        <div class="col-lg-4">
          <div class="rh-card h-100 mb-0">
            <div class="rh-card-header">
              <h6 class="rh-card-title">Case Distribution by Status</h6>
            </div>
            <div class="rh-card-body">
              <canvas id="chartStatusDistribution" height="220"></canvas>
            </div>
          </div>
        </div>
      </div>

      <!-- Bureau Workload & Categories Row -->
      <div class="row g-3 mb-4">
        <div class="col-lg-6">
          <div class="rh-card h-100 mb-0">
            <div class="rh-card-header">
              <h6 class="rh-card-title">Active Workload by Administrative Bureau</h6>
            </div>
            <div class="rh-card-body">
              <canvas id="chartBureauWorkload" height="200"></canvas>
            </div>
          </div>
        </div>
        <div class="col-lg-6">
          <div class="rh-card h-100 mb-0">
            <div class="rh-card-header">
              <h6 class="rh-card-title">Cases by Institution Category</h6>
            </div>
            <div class="rh-card-body">
              <canvas id="chartInstitutionCategory" height="200"></canvas>
            </div>
          </div>
        </div>
      </div>

      <!-- Priority & Attention Section -->
      <div class="row g-3 mb-4">
        <!-- Critical & High Priority Attention -->
        <div class="col-lg-7">
          <div class="rh-card h-100 mb-0">
            <div class="rh-card-header bg-white">
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-danger">Critical Attention</span>
                <h6 class="rh-card-title">High Priority Cases Requiring Regulatory Action</h6>
              </div>
              <button class="btn btn-sm btn-outline-primary" id="btnViewAllCritical">View All</button>
            </div>
            <div class="rh-card-body p-0">
              <div class="table-responsive">
                <table class="rh-table mb-0">
                  <thead>
                    <tr>
                      <th>Case ID</th>
                      <th>Institution</th>
                      <th>Category</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${urgentCases.map(c => `
                      <tr>
                        <td><a href="#" class="btn-open-workspace text-primary fw-bold" data-id="${c.id}">${c.id}</a></td>
                        <td>
                          <div class="fw-semibold text-truncate" style="max-width: 180px;" title="${c.institutionName}">${c.institutionName}</div>
                          <small class="text-muted">${c.aicteId}</small>
                        </td>
                        <td><small class="text-muted">${c.category}</small></td>
                        <td><span class="rh-badge priority-${c.priority.toLowerCase()}">${c.priority}</span></td>
                        <td><span class="rh-badge status-${c.status.toLowerCase().replace(/\s+/g, '-')}">${c.status}</span></td>
                        <td>
                          <button class="btn btn-sm btn-outline-secondary btn-open-workspace py-0 px-2" data-id="${c.id}">Workspace</button>
                        </td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Overdue Escalation Feed & High-Risk Institutions -->
        <div class="col-lg-5">
          <div class="rh-card h-100 mb-0">
            <div class="rh-card-header">
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-warning text-dark">Watchlist</span>
                <h6 class="rh-card-title">Institutions with Multiple Grievances</h6>
              </div>
            </div>
            <div class="rh-card-body p-0">
              <ul class="list-group list-group-flush small">
                ${highAttentionInstitutions.slice(0, 5).map(item => `
                  <li class="list-group-item d-flex justify-content-between align-items-center py-2 px-3">
                    <div>
                      <div class="fw-bold">${item.name}</div>
                      <span class="text-danger fw-semibold">${item.openCount} Open Active Grievances</span>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary btn-filter-inst" data-name="${item.name}">Filter Cases</button>
                  </li>
                `).join("")}
              </ul>
              <div class="p-3 bg-light border-top text-center">
                <small class="text-muted d-block mb-2">Automated SLA escalation triggers on L1 (80% SLA) and L2 (Breach).</small>
                <button class="btn btn-sm btn-outline-dark" id="btnGoToBureaus">View Bureau Workload Breakdown</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Init charts
    this.initOverviewCharts(monthlyTrends, statusCounts, metrics.bureauWorkload, metrics.institutionCategories);

    // Event listeners
    container.querySelector("#btnGoToRegistry").addEventListener("click", () => this.switchView("registry"));
    container.querySelector("#btnViewAllCritical").addEventListener("click", () => {
      this.filters.priority = "Critical";
      this.switchView("registry");
    });
    container.querySelector("#btnGoToBureaus").addEventListener("click", () => this.switchView("bureaus"));
    container.querySelector("#btnExportOverviewCSV").addEventListener("click", () => mockDataService.exportCasesCSV());

    container.querySelectorAll(".btn-open-workspace").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const caseId = btn.getAttribute("data-id");
        this.openCaseWorkspace(caseId);
      });
    });

    container.querySelectorAll(".btn-filter-inst").forEach(btn => {
      btn.addEventListener("click", () => {
        this.searchQuery = btn.getAttribute("data-name");
        this.switchView("registry");
      });
    });
  }

  initOverviewCharts(monthlyTrends, statusCounts, bureauWorkload, institutionCategories) {
    if (typeof Chart === "undefined") return;

    this.destroyCharts();

    const isDark = document.documentElement.getAttribute("data-theme") === "dark" ||
      (document.documentElement.getAttribute("data-theme") === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const gridColor = isDark ? "#334155" : "#F1F5F9";
    const textColor = isDark ? "#CBD5E1" : "#64748B";

    // Safe fallbacks for chart data
    const mTrends = monthlyTrends && Array.isArray(monthlyTrends.labels) && monthlyTrends.labels.length > 0 ? monthlyTrends : {
      labels: ["May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026"],
      intake: [6, 8, 11, 14, 18, 23],
      resolved: [5, 7, 9, 12, 10, 8]
    };
    const sCounts = statusCounts && Object.keys(statusCounts).length > 0 ? statusCounts : {
      "Under Investigation": 18,
      "Awaiting Institutional Response": 12,
      "Preliminary Review": 8,
      "Resolved Within SLA": 16
    };
    const bWorkload = bureauWorkload && Object.keys(bureauWorkload).length > 0 ? bureauWorkload : {
      "Approval Bureau": { code: "AB", open: 12, overdue: 2 },
      "Grievance Redressal Bureau": { code: "GRB", open: 14, overdue: 3 },
      "Compliance & Legal Affairs Bureau": { code: "CLAB", open: 8, overdue: 1 },
      "Regional Coordination Bureau": { code: "RCB", open: 4, overdue: 0 }
    };
    const instCats = institutionCategories && Object.keys(institutionCategories).length > 0 ? institutionCategories : {
      "Engineering & Technology": 30,
      "Management": 12,
      "Pharmacy": 6,
      "Polytechnic": 4,
      "Architecture": 2
    };

    // 1. Monthly Intake vs Resolved
    const ctxIntake = document.getElementById("chartIntakeResolved")?.getContext("2d");
    if (ctxIntake) {
      this.chartInstances.intake = new Chart(ctxIntake, {
        type: "bar",
        data: {
          labels: mTrends.labels,
          datasets: [
            {
              label: "New Grievances Received",
              data: mTrends.intake,
              backgroundColor: "#0284C7",
              borderRadius: 4
            },
            {
              label: "Cases Formally Resolved",
              data: mTrends.resolved,
              backgroundColor: "#10B981",
              borderRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "top", labels: { boxWidth: 12, color: textColor } }
          },
          scales: {
            y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } },
            x: { grid: { display: false }, ticks: { color: textColor } }
          }
        }
      });
    }

    // 2. Status Doughnut Chart
    const ctxStatus = document.getElementById("chartStatusDistribution")?.getContext("2d");
    if (ctxStatus) {
      const labels = Object.keys(sCounts);
      const data = Object.values(sCounts);
      const colors = ["#94A3B8", "#F59E0B", "#0284C7", "#EA580C", "#8B5CF6", "#DC2626", "#10B981", "#64748B"];

      this.chartInstances.status = new Chart(ctxStatus, {
        type: "doughnut",
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: colors.slice(0, labels.length)
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 }, color: textColor } }
          },
          cutout: "65%"
        }
      });
    }

    // 3. Bureau Workload
    const ctxBureau = document.getElementById("chartBureauWorkload")?.getContext("2d");
    if (ctxBureau) {
      const bLabels = Object.values(bWorkload).map(b => b.code || b.name || "BUR");
      const bOpen = Object.values(bWorkload).map(b => b.open ?? b.total ?? 0);
      const bOverdue = Object.values(bWorkload).map(b => b.overdue ?? 0);

      this.chartInstances.bureau = new Chart(ctxBureau, {
        type: "bar",
        data: {
          labels: bLabels,
          datasets: [
            { label: "Active Open Cases", data: bOpen, backgroundColor: "#3B82F6", borderRadius: 4 },
            { label: "Overdue Cases", data: bOverdue, backgroundColor: "#EF4444", borderRadius: 4 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: textColor } }
          },
          scales: {
            x: { stacked: true, grid: { display: false }, ticks: { color: textColor } },
            y: { stacked: true, beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } }
          }
        }
      });
    }

    // 4. Institution Category
    const ctxCat = document.getElementById("chartInstitutionCategory")?.getContext("2d");
    if (ctxCat) {
      const cLabels = Object.keys(instCats).map(k => k.split(" ")[0]);
      const cData = Object.values(instCats);

      this.chartInstances.cat = new Chart(ctxCat, {
        type: "polarArea",
        data: {
          labels: cLabels,
          datasets: [{
            data: cData,
            backgroundColor: [
              "rgba(2, 132, 199, 0.7)",
              "rgba(245, 158, 11, 0.7)",
              "rgba(16, 185, 129, 0.7)",
              "rgba(139, 92, 246, 0.7)",
              "rgba(100, 116, 139, 0.7)"
            ]
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "right", labels: { boxWidth: 10, font: { size: 10 }, color: textColor } } },
          scales: {
            r: { grid: { color: gridColor }, ticks: { color: textColor, backdropColor: "transparent" } }
          }
        }
      });
    }
  }

  /* =========================================================================
     VIEW 2: INSTITUTIONAL CASE REGISTRY
     ========================================================================= */
  renderRegistry(container) {
    const { items, totalCount, totalPages, currentPage } = mockDataService.getCases(
      this.filters,
      this.searchQuery,
      this.sortBy,
      this.sortOrder,
      this.currentPage,
      this.pageSize
    );

    const bureaus = mockDataService.getBureaus();
    const categories = [
      "Regulatory Compliance",
      "Approval and Accreditation",
      "Institutional Governance",
      "Infrastructure and Facilities",
      "Faculty and Staffing",
      "Academic Administration",
      "Financial and Administrative Irregularities",
      "Policy Implementation",
      "Student Welfare & Anti-Ragging",
      "Institutional Reporting & Disclosure"
    ];

    container.innerHTML = `
      <div class="d-flex flex-wrap justify-content-between align-items-center mb-3">
        <div>
          <h4 class="fw-bold mb-1" style="color: var(--rh-navy-dark);">Institutional Case Registry</h4>
          <p class="text-muted small mb-0">Active repository of regulatory and institutional complaint cases across AICTE Bureaus</p>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-rh-secondary btn-sm" id="btnExportCSV">
            <i class="bi bi-download me-1"></i> Export Filtered CSV
          </button>
          <button class="btn btn-outline-danger btn-sm" id="btnResetFilters">
            <i class="bi bi-arrow-counterclockwise me-1"></i> Reset Filters
          </button>
        </div>
      </div>

      <!-- Filter Controls Bar -->
      <div class="filter-bar shadow-sm">
        <div class="row g-2 align-items-center">
          <div class="col-lg-3 col-md-6">
            <div class="input-group input-group-sm">
              <span class="input-group-text bg-white"><i class="bi bi-search"></i></span>
              <input type="text" class="form-control" id="inputCaseSearch" placeholder="Search Case ID, Institution, AICTE ID..." value="${this.searchQuery}">
            </div>
          </div>
          <div class="col-lg-2 col-md-3 col-sm-6">
            <select class="form-select form-select-sm" id="filterBureau">
              <option value="ALL">All Bureaus</option>
              ${bureaus.map(b => `<option value="${b.id}" ${this.filters.bureau === b.id ? "selected" : ""}>${b.code || b.name.split(" ")[0]} (${b.name.split(" ")[0]})</option>`).join("")}
            </select>
          </div>
          <div class="col-lg-1 col-md-3 col-sm-6">
            <select class="form-select form-select-sm" id="filterPriority">
              <option value="ALL">Priority</option>
              <option value="Critical" ${this.filters.priority === "Critical" ? "selected" : ""}>Critical</option>
              <option value="High" ${this.filters.priority === "High" ? "selected" : ""}>High</option>
              <option value="Medium" ${this.filters.priority === "Medium" ? "selected" : ""}>Medium</option>
              <option value="Low" ${this.filters.priority === "Low" ? "selected" : ""}>Low</option>
            </select>
          </div>
          <div class="col-lg-2 col-md-3 col-sm-6">
            <select class="form-select form-select-sm" id="filterStatus">
              <option value="ALL">All Statuses</option>
              <option value="Received" ${this.filters.status === "Received" ? "selected" : ""}>Received</option>
              <option value="Under Investigation" ${this.filters.status === "Under Investigation" ? "selected" : ""}>Under Investigation</option>
              <option value="Awaiting Institutional Response" ${this.filters.status === "Awaiting Institutional Response" ? "selected" : ""}>Awaiting Institutional Response</option>
              <option value="Awaiting Bureau Review" ${this.filters.status === "Awaiting Bureau Review" ? "selected" : ""}>Awaiting Bureau Review</option>
              <option value="Escalated" ${this.filters.status === "Escalated" ? "selected" : ""}>Escalated</option>
              <option value="Resolved" ${this.filters.status === "Resolved" ? "selected" : ""}>Resolved</option>
            </select>
          </div>
          <div class="col-lg-2 col-md-3 col-sm-6">
            <select class="form-select form-select-sm" id="filterSla">
              <option value="ALL">All SLA Statuses</option>
              <option value="On Track" ${this.filters.slaStatus === "On Track" ? "selected" : ""}>On Track</option>
              <option value="Approaching Deadline" ${this.filters.slaStatus === "Approaching Deadline" ? "selected" : ""}>Approaching Deadline</option>
              <option value="Overdue" ${this.filters.slaStatus === "Overdue" ? "selected" : ""}>Overdue / Breached</option>
            </select>
          </div>
          <div class="col-lg-1 col-md-3 col-sm-6">
            <select class="form-select form-select-sm" id="filterLegal">
              <option value="ALL">Review</option>
              <option value="URGENT" ${this.filters.legalFlag === "URGENT" ? "selected" : ""}>Urgent</option>
              <option value="LEGAL" ${this.filters.legalFlag === "LEGAL" ? "selected" : ""}>Legal</option>
              <option value="PRIORITY" ${this.filters.legalFlag === "PRIORITY" ? "selected" : ""}>Priority</option>
              <option value="ROUTINE" ${this.filters.legalFlag === "ROUTINE" ? "selected" : ""}>Routine</option>
            </select>
          </div>
          <div class="col-lg-1 col-md-2 col-sm-6">
            <button class="btn btn-rh-primary btn-sm w-100" id="btnApplySearch">Apply</button>
          </div>
        </div>
      </div>

      <!-- Case Registry Table -->
      <div class="rh-card shadow-sm">
        <div class="rh-card-header bg-white py-2">
          <span class="small text-muted fw-bold">Showing ${items.length} of ${totalCount} records (Page ${currentPage} of ${totalPages})</span>
          <div class="d-flex align-items-center gap-2">
            <span class="small text-muted">Sort by:</span>
            <select class="form-select form-select-sm py-0" style="width: auto;" id="selectSortBy">
              <option value="dateReceived" ${this.sortBy === "dateReceived" ? "selected" : ""}>Date Received</option>
              <option value="priority" ${this.sortBy === "priority" ? "selected" : ""}>Priority Level</option>
              <option value="resolutionDeadline" ${this.sortBy === "resolutionDeadline" ? "selected" : ""}>Deadline</option>
            </select>
          </div>
        </div>
        <div class="rh-card-body p-0">
          <div class="table-responsive">
            <table class="rh-table">
              <thead>
                <tr>
                  <th>Case Reference</th>
                  <th>Institution &amp; AICTE ID</th>
                  <th>Complaint Category</th>
                  <th>Assigned Unit</th>
                  <th>Officer</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>SLA Countdown &amp; Deadline</th>
                  <th>Legal Attention</th>
                  <th class="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${items.length === 0 ? `
                  <tr>
                    <td colspan="10" class="text-center py-5 text-muted">
                      <i class="bi bi-folder2-open display-6 d-block mb-2 text-secondary"></i>
                      No institutional cases match the current filter criteria.
                    </td>
                  </tr>
                ` : items.map(c => `
                  <tr>
                    <td>
                      <a href="#" class="btn-open-workspace fw-bold text-primary text-decoration-none" data-id="${c.id}">${c.id}</a>
                      ${c.escalationLevel > 0 ? `<span class="badge bg-danger ms-1">L${c.escalationLevel}</span>` : ""}
                    </td>
                    <td>
                      <div class="fw-bold text-dark text-truncate" style="max-width: 220px;" title="${c.institutionName}">${c.institutionName}</div>
                      <span class="badge bg-light text-muted border py-0">${c.aicteId}</span>
                    </td>
                    <td>
                      <div class="small text-truncate" style="max-width: 170px;" title="${c.category}">${c.category}</div>
                    </td>
                    <td>
                      <div class="small fw-semibold">${c.bureauName ? c.bureauName.split(" ")[0] : '-'}</div>
                      <small class="text-muted">${c.cellName ? c.cellName.split(" ")[0] : '-'}</small>
                    </td>
                    <td><small class="text-muted">${c.assignedOfficer || "Unassigned"}</small></td>
                    <td><span class="rh-badge priority-${c.priority.toLowerCase()}">${c.priority}</span></td>
                    <td><span class="rh-badge status-${c.status.toLowerCase().replace(/\s+/g, '-')}">${c.status}</span></td>
                    <td>
                      <div class="small fw-semibold mb-1">${c.resolutionDeadline || 'Not defined'}</div>
                      <span class="sla-timer-badge ${c.slaBadgeClass || (c.slaStatus === 'Overdue' || c.isSlaBreached ? 'sla-badge-breached' : (c.slaStatus === 'Approaching Deadline' || c.isApproaching ? 'sla-badge-approaching' : 'sla-badge-on-track'))}" data-deadline="${c.resolutionDeadline}" data-completed="${c.status === 'Resolved' || c.status === 'Closed'}">
                        <i class="bi bi-clock-history me-1"></i>${c.slaStatus || 'On Track'}
                      </span>
                    </td>
                    <td>
                      <span class="badge ${c.legalFlag === 'URGENT' ? 'legal-flag-urgent' : (c.legalFlag === 'LEGAL' ? 'legal-flag-legal' : (c.legalFlag === 'PRIORITY' ? 'legal-flag-priority' : 'legal-flag-routine'))}">
                        ${c.legalFlagLabel || c.legalFlag || 'Routine Review'}
                      </span>
                    </td>
                    <td class="text-end">
                      <button class="btn btn-sm btn-outline-primary py-0 px-2 btn-open-workspace" data-id="${c.id}">
                        Workspace
                      </button>
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Pagination -->
        ${totalPages > 1 ? `
          <div class="d-flex justify-content-between align-items-center p-3 border-top bg-light">
            <span class="small text-muted">Showing page ${currentPage} of ${totalPages}</span>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-secondary" id="btnPrevPage" ${currentPage === 1 ? "disabled" : ""}>Previous</button>
              <button class="btn btn-outline-secondary" id="btnNextPage" ${currentPage === totalPages ? "disabled" : ""}>Next</button>
            </div>
          </div>
        ` : ""}
      </div>
    `;

    // Filter Listeners
    container.querySelector("#inputCaseSearch").addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.searchQuery = e.target.value;
        this.currentPage = 1;
        this.renderRegistry(container);
      }
    });

    container.querySelector("#btnApplySearch").addEventListener("click", () => {
      this.searchQuery = container.querySelector("#inputCaseSearch").value;
      this.filters.bureau = container.querySelector("#filterBureau").value;
      this.filters.priority = container.querySelector("#filterPriority").value;
      this.filters.status = container.querySelector("#filterStatus").value;
      this.filters.slaStatus = container.querySelector("#filterSla").value;
      if (container.querySelector("#filterLegal")) {
        this.filters.legalFlag = container.querySelector("#filterLegal").value;
      }
      this.currentPage = 1;
      this.renderRegistry(container);
    });

    container.querySelector("#btnResetFilters").addEventListener("click", () => {
      this.filters = { bureau: "ALL", cell: "ALL", category: "ALL", priority: "ALL", status: "ALL", slaStatus: "ALL", legalFlag: "ALL", state: "ALL", institutionCategory: "ALL" };
      this.searchQuery = "";
      this.currentPage = 1;
      this.renderRegistry(container);
    });

    container.querySelector("#selectSortBy").addEventListener("change", (e) => {
      this.sortBy = e.target.value;
      this.renderRegistry(container);
    });

    container.querySelector("#btnExportCSV").addEventListener("click", () => {
      mockDataService.exportCasesCSV(this.filters, this.searchQuery);
    });

    if (container.querySelector("#btnPrevPage")) {
      container.querySelector("#btnPrevPage").addEventListener("click", () => {
        if (this.currentPage > 1) {
          this.currentPage--;
          this.renderRegistry(container);
        }
      });
    }

    if (container.querySelector("#btnNextPage")) {
      container.querySelector("#btnNextPage").addEventListener("click", () => {
        if (this.currentPage < totalPages) {
          this.currentPage++;
          this.renderRegistry(container);
        }
      });
    }

    container.querySelectorAll(".btn-open-workspace").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const caseId = btn.getAttribute("data-id");
        this.openCaseWorkspace(caseId);
      });
    });
  }

  /* =========================================================================
     VIEW 3: CASE DETAILS & INVESTIGATION WORKSPACE (MODAL)
     ========================================================================= */
  async openCaseWorkspace(caseId) {
    let c = await mockDataService.getBackendCaseDetail(caseId);
    if (!c) c = mockDataService.getCaseById(caseId);
    if (!c) return;

    this.activeCaseId = caseId;
    const bureaus = mockDataService.getBureaus();
    const officers = mockDataService.getOfficers();

    let modalEl = document.getElementById("caseWorkspaceModal");
    if (!modalEl) {
      modalEl = document.createElement("div");
      modalEl.id = "caseWorkspaceModal";
      modalEl.className = "modal fade";
      modalEl.tabIndex = -1;
      document.body.appendChild(modalEl);
    }

    const sla = c.sla || {
      label: c.slaStatus || "On Track",
      state: c.isSlaBreached ? "BREACHED" : "ON_TRACK",
      badge_class: c.slaBadgeClass || (c.isSlaBreached ? "sla-badge-breached" : "sla-badge-on-track"),
      mismatch_flag: false,
      mismatch_reason: ""
    };

    const legal = c.legal_review || {
      flag_level: c.legalFlag || "ROUTINE",
      flag_label: c.legalFlagLabel || "Routine Review",
      suggested_reason: "Standard regulatory review applies.",
      status: "PENDING",
      status_label: "Pending",
      evidence_excerpt: "",
      review_notes: "",
      referred_authority: ""
    };

    const intel = c.ai_intelligence || {
      summary: c.summary || "Complaint under official regulatory review.",
      main_issue: c.subject || "",
      important_facts: ["Referenced in institutional registry."],
      missing_evidence: ["Pending institutional response."],
      regulatory_concerns: ["AICTE Approval Process Handbook"],
      recommended_action: "Review case dossier and proceed with cell inquiry.",
      recommended_action_rationale: "Standard compliance verification required.",
      suggested_responsible_role: "Assigned Cell Officer",
      action_checklist: ["Review merits", "Verify institution records", "Prepare inquiry findings"],
      recommendation_actions: [],
      followup_escalation: "Routine monthly review.",
      confidence_score: 75,
      is_rule_fallback: false,
      model_name: "AICTE-Triage-v1"
    };

    const relatedComplaints = c.related_complaints || [];

    modalEl.innerHTML = `
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header modal-header-rh py-3">
            <div>
              <div class="d-flex align-items-center gap-2">
                <h5 class="modal-title fw-bold mb-0">${c.id}</h5>
                <span class="rh-badge priority-${(c.priority || 'medium').toLowerCase()}">${c.priority}</span>
                <span class="rh-badge status-${(c.status || 'received').toLowerCase().replace(/[\s()]+/g, '-')}">${c.status}</span>
                ${c.escalationLevel > 0 ? `<span class="badge bg-danger">Escalation L${c.escalationLevel}</span>` : ""}
                <span class="badge ${legal.flag_level === 'URGENT' ? 'legal-flag-urgent' : (legal.flag_level === 'LEGAL' ? 'legal-flag-legal' : (legal.flag_level === 'PRIORITY' ? 'legal-flag-priority' : 'legal-flag-routine'))}">
                  ${legal.flag_label}
                </span>
              </div>
              <small class="text-light opacity-75">${c.institutionName} (${c.aicteId}) &bull; Category: ${c.category}</small>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>

          <div class="modal-body p-4 bg-light">
            <!-- Action Toolbar -->
            <div class="p-3 bg-white border rounded shadow-sm mb-4">
              <div class="small fw-bold text-uppercase text-muted mb-2">Administrative Actions</div>
              <div class="d-flex flex-wrap gap-2">
                <button class="btn btn-sm btn-outline-primary" id="btnModalAssign">
                  <i class="bi bi-person-check me-1"></i> Assign / Reassign
                </button>
                <button class="btn btn-sm btn-outline-secondary" id="btnModalStatus">
                  <i class="bi bi-arrow-repeat me-1"></i> Update Status
                </button>
                <button class="btn btn-sm btn-outline-warning text-dark" id="btnModalPriority">
                  <i class="bi bi-flag me-1"></i> Change Priority
                </button>
                <button class="btn btn-sm btn-outline-danger" id="btnModalEscalate">
                  <i class="bi bi-arrow-up-circle me-1"></i> Escalate Case
                </button>
                <button class="btn btn-sm btn-outline-success" id="btnModalResolve">
                  <i class="bi bi-check-circle me-1"></i> Mark Resolved
                </button>
                <button class="btn btn-sm btn-outline-dark" id="btnModalAddNote">
                  <i class="bi bi-journal-plus me-1"></i> Add Note
                </button>
              </div>
            </div>

            <!-- Live SLA & Legal Attention Banner Row -->
            <div class="row g-3 mb-4">
              <!-- SLA Countdown Monitor -->
              <div class="col-md-6">
                <div class="card shadow-sm border-0 h-100">
                  <div class="card-header bg-white fw-bold py-2 d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-stopwatch text-primary me-2"></i>SLA Countdown &amp; Breach Monitor</span>
                    <span class="sla-timer-badge ${sla.badge_class || (c.isSlaBreached ? 'sla-badge-breached' : 'sla-badge-on-track')}" data-deadline="${c.resolutionDeadline}" data-completed="${c.status === 'Resolved' || c.status === 'Closed'}">
                      <i class="bi bi-clock-history me-1"></i>${sla.label}
                    </span>
                  </div>
                  <div class="card-body small">
                    <div class="d-flex justify-content-between mb-1">
                      <span class="text-muted">Statutory Deadline:</span>
                      <strong>${c.resolutionDeadline || "Not specified"}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                      <span class="text-muted">Current State:</span>
                      <strong class="${c.isSlaBreached ? 'text-danger' : 'text-success'}">${sla.state}</strong>
                    </div>
                    ${sla.mismatch_flag ? `
                      <div class="alert alert-warning py-1 px-2 mt-2 mb-0 small">
                        <i class="bi bi-exclamation-triangle-fill me-1"></i><strong>Reconciled:</strong> ${sla.mismatch_reason}
                      </div>
                    ` : ''}
                  </div>
                </div>
              </div>

              <!-- Legal Attention & Human Review -->
              <div class="col-md-6">
                <div class="card shadow-sm border-0 h-100">
                  <div class="card-header bg-white fw-bold py-2 d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-shield-exclamation text-warning me-2"></i>Legal Attention &amp; Human Review</span>
                    <span class="badge ${legal.flag_level === 'URGENT' ? 'legal-flag-urgent' : (legal.flag_level === 'LEGAL' ? 'legal-flag-legal' : (legal.flag_level === 'PRIORITY' ? 'legal-flag-priority' : 'legal-flag-routine'))}">
                      ${legal.flag_label}
                    </span>
                  </div>
                  <div class="card-body small">
                    <div class="mb-1">
                      <span class="text-muted">Assessment Reason:</span>
                      <div class="mt-1">${legal.suggested_reason}</div>
                    </div>
                    ${legal.evidence_excerpt ? `
                      <div class="p-2 rounded bg-light border-start border-3 border-warning my-2">
                        <em>"${legal.evidence_excerpt}"</em>
                      </div>
                    ` : ''}
                    <div class="d-flex justify-content-between align-items-center pt-1 border-top mt-2">
                      <span class="text-muted">Status: <strong>${legal.status_label || legal.status}</strong></span>
                      <div class="d-flex gap-1">
                        <button class="btn btn-xs btn-outline-danger btn-legal-action" data-action="confirm_flag" data-case="${c.id}">Confirm</button>
                        <button class="btn btn-xs btn-outline-primary btn-legal-action" data-action="refer_legal" data-case="${c.id}">Refer Legal</button>
                        <button class="btn btn-xs btn-outline-secondary btn-legal-action" data-action="dismiss_flag" data-case="${c.id}">Dismiss</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Case Information Grids -->
            <div class="row g-3 mb-4">
              <!-- Left Details Column -->
              <div class="col-lg-7">
                <div class="card shadow-sm border-0 mb-3">
                  <div class="card-header bg-white fw-bold py-2">Allegation Summary &amp; Narrative</div>
                  <div class="card-body">
                    <h6 class="fw-bold text-dark">${c.subject}</h6>
                    <p class="text-muted small">${c.summary}</p>
                    <hr class="my-2">
                    <div class="row g-2 small">
                      <div class="col-6"><strong>Intake Channel:</strong> ${c.sourceChannel || 'Portal'}</div>
                      <div class="col-6"><strong>Reference No:</strong> ${c.externalRef || c.id}</div>
                      <div class="col-6"><strong>Date Received:</strong> ${c.dateReceived}</div>
                      <div class="col-6"><strong>Resolution Deadline:</strong> ${c.resolutionDeadline || 'Not specified'}</div>
                    </div>
                  </div>
                </div>

                <!-- DEDICATED SECTION 1: AI Case Intelligence & Recommended Next Steps -->
                <div class="card shadow-sm border-0 mb-3">
                  <div class="card-header bg-white fw-bold py-2 d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-cpu text-primary me-2"></i>AI Case Intelligence &amp; Recommended Next Steps</span>
                    <span class="badge bg-primary-subtle text-primary border">${intel.model_name || 'AICTE-Triage-v1'} (${intel.confidence_score}% confidence)</span>
                  </div>
                  <div class="card-body small">
                    <h6 class="fw-bold text-dark mb-1">Issue Analysis:</h6>
                    <p class="text-muted mb-2">${intel.summary}</p>

                    <!-- Important Facts Extracted -->
                    <div class="mb-2">
                      <strong class="d-block text-dark">Important Facts Extracted:</strong>
                      <ul class="mb-2 ps-3 text-secondary">
                        ${intel.important_facts && intel.important_facts.length > 0 ? intel.important_facts.map(f => `<li>${f}</li>`).join('') : '<li>Facts corroborated with institutional registry intake.</li>'}
                      </ul>
                    </div>

                    <!-- Missing Evidence -->
                    <div class="mb-2">
                      <strong class="d-block text-dark">Missing Information / Evidence:</strong>
                      <ul class="mb-2 ps-3 text-danger">
                        ${intel.missing_evidence && intel.missing_evidence.length > 0 ? intel.missing_evidence.map(m => `<li>${m}</li>`).join('') : '<li>Awaiting institutional response affidavit.</li>'}
                      </ul>
                    </div>

                    <!-- Regulatory Framework Concerns -->
                    <div class="mb-3">
                      <strong class="d-block text-dark">Regulatory Framework Concerns:</strong>
                      <div class="d-flex flex-wrap gap-1 mt-1">
                        ${intel.regulatory_concerns && intel.regulatory_concerns.length > 0 ? intel.regulatory_concerns.map(rc => `<span class="badge bg-light text-dark border">${rc}</span>`).join('') : '<span class="badge bg-light text-dark border">AICTE Approval Process Handbook</span>'}
                      </div>
                    </div>

                    <!-- Recommended Action Box -->
                    <div class="p-3 mb-3 bg-primary-subtle border border-primary-subtle rounded">
                      <div class="fw-bold text-primary mb-1"><i class="bi bi-lightbulb-fill me-1"></i>Recommended Next Action:</div>
                      <div class="fw-semibold text-dark">${intel.recommended_action}</div>
                      <div class="text-muted mt-1 small"><em>${intel.recommended_action_rationale}</em></div>
                      <div class="mt-2 text-secondary"><strong>Responsible Authority:</strong> ${intel.suggested_responsible_role || 'Assigned Cell'}</div>
                    </div>

                    <!-- Ordered Action Checklist -->
                    <div class="mb-3">
                      <strong class="d-block text-dark mb-2">Ordered Action Checklist:</strong>
                      <div class="list-group list-group-flush border rounded">
                        ${intel.recommendation_actions && intel.recommendation_actions.length > 0 ? intel.recommendation_actions.map(act => `
                          <div class="list-group-item d-flex justify-content-between align-items-center py-2 px-3">
                            <div>
                              <span class="badge ${act.state === 'COMPLETED' ? 'bg-success' : (act.state === 'DISMISSED' ? 'bg-secondary' : (act.state === 'NOT_APPLICABLE' ? 'bg-dark' : 'bg-warning text-dark'))} me-2">${act.state}</span>
                              <span class="${act.state === 'COMPLETED' ? 'text-decoration-line-through text-muted' : 'text-dark'}">${act.title}</span>
                              ${act.decided_by ? `<small class="text-muted d-block ms-4">Recorded by ${act.decided_by}</small>` : ''}
                            </div>
                            <div class="btn-group btn-group-sm">
                              <button class="btn btn-xs btn-outline-success btn-rec-state" data-case="${c.id}" data-id="${act.id}" data-title="${act.title}" data-state="COMPLETED" title="Mark Completed"><i class="bi bi-check"></i></button>
                              <button class="btn btn-xs btn-outline-secondary btn-rec-state" data-case="${c.id}" data-id="${act.id}" data-title="${act.title}" data-state="DISMISSED" title="Dismiss"><i class="bi bi-x"></i></button>
                              <button class="btn btn-xs btn-outline-dark btn-rec-state" data-case="${c.id}" data-id="${act.id}" data-title="${act.title}" data-state="NOT_APPLICABLE" title="Not Applicable">N/A</button>
                            </div>
                          </div>
                        `).join('') : (intel.action_checklist ? intel.action_checklist.map((item, idx) => `
                          <div class="list-group-item d-flex justify-content-between align-items-center py-2 px-3">
                            <span class="text-dark">${idx + 1}. ${item}</span>
                            <div class="btn-group btn-group-sm">
                              <button class="btn btn-xs btn-outline-success btn-rec-state" data-case="${c.id}" data-title="${item}" data-state="COMPLETED">Done</button>
                              <button class="btn btn-xs btn-outline-secondary btn-rec-state" data-case="${c.id}" data-title="${item}" data-state="DISMISSED">Dismiss</button>
                            </div>
                          </div>
                        `).join('') : '<div class="list-group-item text-muted">No pending checklist items.</div>')}
                      </div>
                    </div>

                    <!-- Follow-up Recommendation -->
                    <div class="small text-secondary">
                      <strong>Escalation / Follow-up Path:</strong>
                      ${intel.followup_escalation}
                    </div>
                  </div>
                </div>

                <!-- DEDICATED SECTION 2: Related Complaints from This Institution -->
                <div class="card shadow-sm border-0 mb-3">
                  <div class="card-header bg-white fw-bold py-2 d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-diagram-2 text-info me-2"></i>Related Complaints from This Institution</span>
                    <span class="badge bg-light text-dark border">${relatedComplaints.length} Related Cases</span>
                  </div>
                  <div class="card-body p-0">
                    ${relatedComplaints.length === 0 ? `
                      <div class="p-3 text-center text-muted small">
                        No other complaints from ${c.institutionName} currently recorded in the registry.
                      </div>
                    ` : `
                      <div class="table-responsive">
                        <table class="table table-hover table-sm mb-0 small">
                          <thead class="table-light">
                            <tr>
                              <th>Case ID</th>
                              <th>Category</th>
                              <th>Priority</th>
                              <th>Status</th>
                              <th>Relationship</th>
                              <th class="text-end">Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${relatedComplaints.map(rc => `
                              <tr>
                                <td>
                                  <a href="#" class="fw-bold text-primary btn-switch-related" data-id="${rc.case_id}">${rc.case_id}</a>
                                </td>
                                <td><div class="text-truncate" style="max-width: 140px;" title="${rc.summary}">${rc.category}</div></td>
                                <td><span class="rh-badge priority-${(rc.priority || 'medium').toLowerCase()}">${rc.priority}</span></td>
                                <td><span class="badge bg-light text-dark border">${rc.status}</span></td>
                                <td>
                                  <span class="badge ${rc.relationship_type.includes('DUPLICATE') ? 'bg-danger-subtle text-danger border-danger' : 'bg-info-subtle text-info border-info'}">
                                    ${rc.relationship_label} (${rc.similarity_score}%)
                                  </span>
                                </td>
                                <td class="text-end">
                                  ${rc.is_confirmed ? `
                                    <span class="badge bg-success-subtle text-success">Confirmed</span>
                                  ` : `
                                    <button class="btn btn-xs btn-outline-danger btn-confirm-dup-link" data-source="${c.id}" data-target="${rc.case_id}" title="Confirm Duplicate">Link</button>
                                  `}
                                </td>
                              </tr>
                            `).join('')}
                          </tbody>
                        </table>
                      </div>
                    `}
                  </div>
                </div>

                <!-- Evidence & Supporting Documents -->
                <div class="card shadow-sm border-0 mb-3">
                  <div class="card-header bg-white fw-bold py-2 d-flex justify-content-between align-items-center">
                    <span>Evidence &amp; Audit Documents</span>
                    <span class="badge bg-light text-dark border">${c.evidenceDocuments ? c.evidenceDocuments.length : 0} Files</span>
                  </div>
                  <div class="card-body p-0">
                    <ul class="list-group list-group-flush small">
                      ${(c.evidenceDocuments && c.evidenceDocuments.length > 0) ? c.evidenceDocuments.map(doc => `
                        <li class="list-group-item d-flex justify-content-between align-items-center py-2 px-3">
                          <div>
                            <i class="bi bi-file-earmark-pdf text-danger me-2"></i>
                            <span class="fw-semibold">${doc.name}</span>
                            <small class="text-muted ms-2">(${doc.size})</small>
                          </div>
                          <button class="btn btn-sm btn-link text-primary p-0 text-decoration-none" onclick="alert('Viewing document: ${doc.name}')">Download</button>
                        </li>
                      `).join("") : `<li class="list-group-item text-muted py-2">No documents attached to this case record.</li>`}
                    </ul>
                  </div>
                </div>

                <!-- Investigation Notes Log -->
                <div class="card shadow-sm border-0">
                  <div class="card-header bg-white fw-bold py-2 d-flex justify-content-between align-items-center">
                    <span>Official Investigation Notes</span>
                    <button class="btn btn-sm btn-link text-primary p-0 text-decoration-none" id="btnCardAddNote">+ Add Note</button>
                  </div>
                  <div class="card-body">
                    ${(!c.notes || c.notes.length === 0) ? `<p class="text-muted small mb-0">No investigation notes recorded yet.</p>` : c.notes.map(n => `
                      <div class="p-2 mb-2 rounded bg-light border-start border-primary border-3">
                        <div class="d-flex justify-content-between small text-muted mb-1">
                          <span class="fw-bold text-dark">${n.author}</span>
                          <span>${n.date}</span>
                        </div>
                        <div class="small">${n.content}</div>
                      </div>
                    `).join("")}
                  </div>
                </div>
              </div>

              <!-- Right Metadata & Timeline Column -->
              <div class="col-lg-5">
                <!-- Institution Profile Mini-Card -->
                <div class="card shadow-sm border-0 mb-3">
                  <div class="card-header bg-white fw-bold py-2">Target Institution Profile</div>
                  <div class="card-body small">
                    <div class="fw-bold text-dark mb-1">${c.institutionName}</div>
                    <div><strong>AICTE Permanent ID:</strong> ${c.aicteId}</div>
                    <div><strong>Category:</strong> ${c.institution ? c.institution.category : "Technical"}</div>
                    <div><strong>Location:</strong> ${c.institution ? `${c.institution.district || 'Capital'}, ${c.institution.state || 'National'}` : "-"}</div>
                    <div><strong>Risk Level:</strong> <span class="badge bg-warning text-dark">${c.institution ? c.institution.riskBand : "Normal"}</span></div>
                  </div>
                </div>

                <!-- Assigned Unit -->
                <div class="card shadow-sm border-0 mb-3">
                  <div class="card-header bg-white fw-bold py-2">Assigned Unit &amp; Officer</div>
                  <div class="card-body small">
                    <div><strong>Bureau:</strong> ${c.bureauName}</div>
                    <div><strong>Cell:</strong> ${c.cellName}</div>
                    <div><strong>Investigating Officer:</strong> <span class="fw-bold text-primary">${c.assignedOfficer || "Unassigned"}</span></div>
                    <div><strong>SLA Standard:</strong> ${c.slaHours || 168} Hours statutory window</div>
                  </div>
                </div>

                <!-- Chronological Timeline -->
                <div class="card shadow-sm border-0">
                  <div class="card-header bg-white fw-bold py-2">Activity &amp; Audit Timeline</div>
                  <div class="card-body">
                    <div class="case-timeline">
                      ${c.timeline ? c.timeline.map(t => `
                        <div class="timeline-item small">
                          <div class="fw-bold text-dark">${t.title}</div>
                          <div class="text-muted" style="font-size: 0.75rem;">${t.date} &bull; ${t.actor}</div>
                          <div class="text-secondary mt-1">${t.description}</div>
                        </div>
                      `).join("") : '<div class="text-muted small">No recorded activity timeline.</div>'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer bg-white py-2">
            <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close Workspace</button>
          </div>
        </div>
      </div>
    `;

    // Hook modal action buttons
    const bsModal = new bootstrap.Modal(modalEl);
    bsModal.show();

    modalEl.querySelector("#btnModalAssign").addEventListener("click", () => this.actionAssignCase(c, bsModal));
    modalEl.querySelector("#btnModalStatus").addEventListener("click", () => this.actionUpdateStatus(c, bsModal));
    modalEl.querySelector("#btnModalPriority").addEventListener("click", () => this.actionUpdatePriority(c, bsModal));
    modalEl.querySelector("#btnModalEscalate").addEventListener("click", () => this.actionEscalateCase(c, bsModal));
    modalEl.querySelector("#btnModalResolve").addEventListener("click", () => this.actionResolveCase(c, bsModal));
    modalEl.querySelector("#btnModalAddNote").addEventListener("click", () => this.actionAddNote(c, bsModal));
    modalEl.querySelector("#btnCardAddNote").addEventListener("click", () => this.actionAddNote(c, bsModal));

    // Hook recommendation actions
    modalEl.querySelectorAll(".btn-rec-state").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const cid = btn.getAttribute("data-case");
        const actId = btn.getAttribute("data-id");
        const title = btn.getAttribute("data-title");
        const state = btn.getAttribute("data-state");
        const notes = prompt(`Enter officer notes for marking action as ${state}:`, "");
        await mockDataService.updateRecommendationAction(cid, actId, title, state, notes || "");
        this.showNotification(`Recommendation marked as ${state}.`, "success");
        this.openCaseWorkspace(cid);
      });
    });

    // Hook legal review actions
    modalEl.querySelectorAll(".btn-legal-action").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const cid = btn.getAttribute("data-case");
        const act = btn.getAttribute("data-action");
        if (act === "confirm_flag") {
          const notes = prompt("Enter human review confirmation remarks:", "Verified against complaint merits.");
          await mockDataService.updateLegalReview(cid, legal.flag_level, "CONFIRMED", notes || "");
          this.showNotification("Legal review flag confirmed.", "success");
        } else if (act === "refer_legal") {
          const auth = prompt("Enter designated referral authority / bureau:", "Legal Affairs & RTI Cell");
          const notes = prompt("Enter referral instructions:", "Referred for legal review and compliance advisory.");
          await mockDataService.updateLegalReview(cid, "LEGAL", "REFERRED_LEGAL", notes || "", auth || "Legal Cell");
          this.showNotification("Case formally referred to Legal Bureau.", "success");
        } else if (act === "dismiss_flag") {
          const notes = prompt("Enter rationale for dismissing flag to routine:", "No actionable regulatory breach found upon preliminary inspection.");
          await mockDataService.updateLegalReview(cid, "ROUTINE", "DISMISSED", notes || "");
          this.showNotification("Flag dismissed to Routine Review.", "info");
        }
        this.openCaseWorkspace(cid);
      });
    });

    // Hook switch related case
    modalEl.querySelectorAll(".btn-switch-related").forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const targetId = link.getAttribute("data-id");
        bsModal.hide();
        setTimeout(() => this.openCaseWorkspace(targetId), 300);
      });
    });

    // Hook confirm duplicate link
    modalEl.querySelectorAll(".btn-confirm-dup-link").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const sId = btn.getAttribute("data-source");
        const tId = btn.getAttribute("data-target");
        if (confirm(`Confirm linking Case ${sId} as duplicate of Case ${tId}?`)) {
          await mockDataService.confirmDuplicate(sId, tId, "CONFIRMED_DUPLICATE", "Officer verified duplicate submission.");
          this.showNotification(`Case ${sId} linked as confirmed duplicate of ${tId}.`, "success");
          this.openCaseWorkspace(sId);
        }
      });
    });
  }

  actionAssignCase(c, parentModal) {
    const bureaus = mockDataService.getBureaus();
    const officers = mockDataService.getOfficers();

    const newBureau = prompt(
      `Select Bureau for Case ${c.id}:\n1: Approval & Licensing Bureau\n2: Grievance Redressal Bureau\n3: Compliance & Legal Affairs Bureau\n4: Regional Coordination Bureau\n(Enter 1, 2, 3, or 4):`,
      "2"
    );
    if (!newBureau) return;

    const bMap = { "1": bureaus[0], "2": bureaus[1], "3": bureaus[2], "4": bureaus[3] };
    const chosenBureau = bMap[newBureau] || bureaus[1];
    const chosenCell = chosenBureau.cells[0];
    const chosenOfficer = officers.find(o => o.bureau.includes(chosenBureau.name.split(" ")[0])) || officers[0];

    mockDataService.assignCase(c.id, chosenBureau.id, chosenCell.id, chosenOfficer.name, mockDataService.getActiveRole());
    this.showNotification(`Case ${c.id} successfully assigned to ${chosenOfficer.name} (${chosenCell.name}).`, "success");
    parentModal.hide();
    this.renderCurrentView();
  }

  actionUpdateStatus(c, parentModal) {
    const statusOptions = [
      "Under Investigation",
      "Awaiting Institutional Response",
      "Awaiting Bureau Review",
      "Escalated",
      "Resolved",
      "Closed"
    ];
    const promptText = `Select New Status for Case ${c.id}:\n` + statusOptions.map((s, idx) => `${idx + 1}: ${s}`).join("\n") + "\n(Enter number):";
    const choice = prompt(promptText, "1");
    if (!choice) return;

    const chosenStatus = statusOptions[parseInt(choice, 10) - 1];
    if (!chosenStatus) return;

    const remarks = prompt(`Enter internal administrative remarks for status update to '${chosenStatus}':`, "Proceeding with regulatory verification.");
    mockDataService.updateCaseStatus(c.id, chosenStatus, remarks, mockDataService.getActiveRole());
    this.showNotification(`Status for ${c.id} updated to '${chosenStatus}'.`, "success");
    parentModal.hide();
    this.renderCurrentView();
  }

  actionUpdatePriority(c, parentModal) {
    const pChoice = prompt(`Change Priority for Case ${c.id}:\n1: Critical\n2: High\n3: Medium\n4: Low\n(Enter 1, 2, 3, or 4):`, "1");
    if (!pChoice) return;
    const pMap = { "1": "Critical", "2": "High", "3": "Medium", "4": "Low" };
    const chosenPriority = pMap[pChoice];
    if (!chosenPriority) return;

    const reason = prompt("Enter justification for priority modification:", "Re-evaluated based on institutional risk impact.");
    mockDataService.updateCasePriority(c.id, chosenPriority, reason, mockDataService.getActiveRole());
    this.showNotification(`Priority for ${c.id} updated to ${chosenPriority}.`, "success");
    parentModal.hide();
    this.renderCurrentView();
  }

  actionAddNote(c, parentModal) {
    const note = prompt(`Add Official Investigation Note for Case ${c.id}:`, "");
    if (!note || !note.trim()) return;

    mockDataService.addInvestigationNote(c.id, note.trim(), mockDataService.getActiveRole());
    this.showNotification(`Investigation note added to Case ${c.id}.`, "success");
    parentModal.hide();
    this.renderCurrentView();
  }

  actionEscalateCase(c, parentModal) {
    const level = prompt(`Select Escalation Level for Case ${c.id}:\n1: Level 1 (Section Head)\n2: Level 2 (Bureau Head)\n3: Level 3 (Member Secretary & Director General)\n(Enter 1, 2, or 3):`, "2");
    if (!level) return;
    const lNum = parseInt(level, 10);
    if (![1, 2, 3].includes(lNum)) return;

    const justification = prompt("Enter statutory justification for escalation:", "SLA breach / urgent regulatory intervention mandated.");
    mockDataService.escalateCase(c.id, lNum, justification, mockDataService.getActiveRole());
    this.showNotification(`Case ${c.id} escalated to Level ${lNum}.`, "success");
    parentModal.hide();
    this.renderCurrentView();
  }

  actionResolveCase(c, parentModal) {
    const summary = prompt(`Enter formal Resolution Summary for Case ${c.id}:`, "Compliance verified through regional inspection; necessary corrective actions implemented by institution.");
    if (!summary || !summary.trim()) return;

    mockDataService.updateCaseStatus(c.id, "Resolved", summary.trim(), mockDataService.getActiveRole());
    this.showNotification(`Case ${c.id} has been formally recorded as RESOLVED.`, "success");
    parentModal.hide();
    this.renderCurrentView();
  }

  /* =========================================================================
     VIEW 4: BUREAU / CELL WORKLOAD MONITORING
     ========================================================================= */
  renderBureaus(container) {
    const metrics = mockDataService.getDashboardMetrics();
    const bureaus = mockDataService.getBureaus();
    const { bureauWorkload } = metrics;

    container.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h4 class="fw-bold mb-1" style="color: var(--rh-navy-dark);">Administrative Bureau & Cell Monitoring</h4>
          <p class="text-muted small mb-0">Cross-departmental case distribution, SLA compliance, and investigational workload tracking</p>
        </div>
      </div>

      <div class="row g-3 mb-4">
        ${bureaus.map(b => {
          const w = bureauWorkload[b.name] || { total: 0, open: 0, overdue: 0, resolved: 0, avgResolutionDays: 10 };
          return `
            <div class="col-lg-6">
              <div class="rh-card h-100 shadow-sm">
                <div class="rh-card-header bg-light">
                  <div>
                    <span class="badge bg-primary me-2">${b.code}</span>
                    <strong class="text-dark">${b.name}</strong>
                  </div>
                  <button class="btn btn-sm btn-outline-primary py-0 btn-filter-bureau" data-id="${b.id}">Filter Registry</button>
                </div>
                <div class="rh-card-body">
                  <p class="small text-muted mb-3">${b.description}</p>
                  
                  <div class="row g-2 mb-3 text-center">
                    <div class="col-3">
                      <div class="p-2 border rounded bg-white">
                        <small class="text-muted text-uppercase d-block" style="font-size:0.7rem;">Total</small>
                        <span class="fw-bold fs-5">${w.total}</span>
                      </div>
                    </div>
                    <div class="col-3">
                      <div class="p-2 border rounded bg-white">
                        <small class="text-muted text-uppercase d-block" style="font-size:0.7rem;">Open</small>
                        <span class="fw-bold fs-5 text-warning">${w.open}</span>
                      </div>
                    </div>
                    <div class="col-3">
                      <div class="p-2 border rounded bg-white">
                        <small class="text-muted text-uppercase d-block" style="font-size:0.7rem;">Overdue</small>
                        <span class="fw-bold fs-5 text-danger">${w.overdue}</span>
                      </div>
                    </div>
                    <div class="col-3">
                      <div class="p-2 border rounded bg-white">
                        <small class="text-muted text-uppercase d-block" style="font-size:0.7rem;">Resolved</small>
                        <span class="fw-bold fs-5 text-success">${w.resolved}</span>
                      </div>
                    </div>
                  </div>

                  <div class="small fw-bold text-muted mb-2">Assigned Cells in this Bureau:</div>
                  <ul class="list-group list-group-flush small border rounded">
                    ${b.cells.map(cell => {
                      const cellCases = mockDataService.getCases({ cell: cell.id }).items;
                      return `
                        <li class="list-group-item d-flex justify-content-between align-items-center py-2 px-3">
                          <div>
                            <strong>${cell.name}</strong>
                            <div class="text-muted" style="font-size:0.75rem;">Lead: ${cell.leadOfficer} &bull; Default SLA: ${cell.defaultSlaHours}h</div>
                          </div>
                          <span class="badge bg-light text-dark border">${cellCases.length} Cases</span>
                        </li>
                      `;
                    }).join("")}
                  </ul>
                </div>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;

    container.querySelectorAll(".btn-filter-bureau").forEach(btn => {
      btn.addEventListener("click", () => {
        this.filters.bureau = btn.getAttribute("data-id");
        this.switchView("registry");
      });
    });
  }

  /* =========================================================================
     VIEW 5: INSTITUTION DIRECTORY
     ========================================================================= */
  renderInstitutions(container) {
    const institutions = mockDataService.getInstitutions();

    container.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h4 class="fw-bold mb-1" style="color: var(--rh-navy-dark);">Approved Technical Institutions Directory</h4>
          <p class="text-muted small mb-0">Institutions under active regulatory tracking and complaint history index</p>
        </div>
      </div>

      <div class="rh-card shadow-sm">
        <div class="rh-card-header bg-white py-2">
          <span class="small text-muted fw-bold">${institutions.length} Institutions Registered in System</span>
        </div>
        <div class="rh-card-body p-0">
          <div class="table-responsive">
            <table class="rh-table">
              <thead>
                <tr>
                  <th>AICTE ID</th>
                  <th>Institution Name</th>
                  <th>Category</th>
                  <th>State & District</th>
                  <th>Total Grievances</th>
                  <th>Open</th>
                  <th>Overdue</th>
                  <th>Risk Band</th>
                  <th class="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${institutions.map(inst => `
                  <tr>
                    <td><span class="badge bg-light text-muted border">${inst.aicteId}</span></td>
                    <td>
                      <div class="fw-bold text-dark">${inst.name}</div>
                      <small class="text-muted">Head: ${inst.directorName}</small>
                    </td>
                    <td><small>${inst.category}</small></td>
                    <td><small class="text-muted">${inst.district}, ${inst.state}</small></td>
                    <td><span class="badge bg-light text-dark border">${inst.totalCases}</span></td>
                    <td><span class="fw-bold ${inst.openCases > 0 ? 'text-warning' : 'text-muted'}">${inst.openCases}</span></td>
                    <td><span class="fw-bold ${inst.overdueCases > 0 ? 'text-danger' : 'text-muted'}">${inst.overdueCases}</span></td>
                    <td>
                      <span class="rh-badge ${inst.riskBand === 'Critical Review' ? 'priority-critical' : (inst.riskBand === 'High Attention' ? 'priority-high' : (inst.riskBand === 'Medium Risk' ? 'priority-medium' : 'status-received'))}">
                        ${inst.riskBand}
                      </span>
                    </td>
                    <td class="text-end">
                      <button class="btn btn-sm btn-outline-primary py-0 px-2 btn-view-inst-cases" data-name="${inst.name}">
                        View Cases
                      </button>
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    container.querySelectorAll(".btn-view-inst-cases").forEach(btn => {
      btn.addEventListener("click", () => {
        this.searchQuery = btn.getAttribute("data-name");
        this.switchView("registry");
      });
    });
  }

  /* =========================================================================
     VIEW 6: REPORTS & ANALYTICS
     ========================================================================= */
  renderReports(container) {
    const metrics = mockDataService.getDashboardMetrics();
    const { kpis, monthlyTrends, priorityCounts } = metrics;

    container.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h4 class="fw-bold mb-1" style="color: var(--rh-navy-dark);">Regulatory Analytics & Performance Reports</h4>
          <p class="text-muted small mb-0">System turnaround, SLA compliance audits, and grievance aging analysis</p>
        </div>
        <button class="btn btn-rh-secondary btn-sm" id="btnExportFullReport">
          <i class="bi bi-file-earmark-spreadsheet me-1"></i> Download Case Report (CSV)
        </button>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="p-3 bg-white border rounded text-center shadow-sm">
            <small class="text-muted fw-bold">TOTAL REGISTERED</small>
            <h3 class="mb-0 fw-bold text-primary mt-1">${kpis.totalCases}</h3>
          </div>
        </div>
        <div class="col-md-3">
          <div class="p-3 bg-white border rounded text-center shadow-sm">
            <small class="text-muted fw-bold">RESOLUTION RATE</small>
            <h3 class="mb-0 fw-bold text-success mt-1">${kpis.resolutionRate}%</h3>
          </div>
        </div>
        <div class="col-md-3">
          <div class="p-3 bg-white border rounded text-center shadow-sm">
            <small class="text-muted fw-bold">SLA COMPLIANCE</small>
            <h3 class="mb-0 fw-bold text-warning mt-1">${kpis.slaComplianceRate}%</h3>
          </div>
        </div>
        <div class="col-md-3">
          <div class="p-3 bg-white border rounded text-center shadow-sm">
            <small class="text-muted fw-bold">AVG TURNAROUND</small>
            <h3 class="mb-0 fw-bold text-dark mt-1">${kpis.avgTurnaroundDays} Days</h3>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-lg-6">
          <div class="rh-card shadow-sm h-100">
            <div class="rh-card-header">
              <h6 class="rh-card-title">Case Aging Analysis (Active Cases)</h6>
            </div>
            <div class="rh-card-body">
              <canvas id="chartAging" height="200"></canvas>
            </div>
          </div>
        </div>
        <div class="col-lg-6">
          <div class="rh-card shadow-sm h-100">
            <div class="rh-card-header">
              <h6 class="rh-card-title">Severity & Priority Workload Share</h6>
            </div>
            <div class="rh-card-body">
              <canvas id="chartPriorityReport" height="200"></canvas>
            </div>
          </div>
        </div>
      </div>
    `;

    // Setup reports charts
    if (typeof Chart !== "undefined") {
      const ctxAging = document.getElementById("chartAging")?.getContext("2d");
      if (ctxAging) {
        this.chartInstances.aging = new Chart(ctxAging, {
          type: "bar",
          data: {
            labels: ["< 15 Days", "15 - 30 Days", "30 - 60 Days", "> 60 Days (Critical)"],
            datasets: [{
              label: "Pending Cases",
              data: [18, 12, 7, 5],
              backgroundColor: ["#10B981", "#3B82F6", "#F59E0B", "#EF4444"]
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } }
          }
        });
      }

      const ctxPrio = document.getElementById("chartPriorityReport")?.getContext("2d");
      if (ctxPrio) {
        this.chartInstances.prio = new Chart(ctxPrio, {
          type: "pie",
          data: {
            labels: Object.keys(priorityCounts),
            datasets: [{
              data: Object.values(priorityCounts),
              backgroundColor: ["#E11D48", "#EA580C", "#0284C7", "#64748B"]
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false
          }
        });
      }
    }

    container.querySelector("#btnExportFullReport").addEventListener("click", () => {
      mockDataService.exportCasesCSV();
    });
  }

  /* =========================================================================
     VIEW 7: ACTIVITY LOG
     ========================================================================= */
  renderActivity(container) {
    const logs = mockDataService.getActivityLog();

    container.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h4 class="fw-bold mb-1" style="color: var(--rh-navy-dark);">Administrative Audit & Activity Log</h4>
          <p class="text-muted small mb-0">Immutable chronological record of regulatory actions, status revisions, and escalations</p>
        </div>
      </div>

      <div class="rh-card shadow-sm">
        <div class="rh-card-header bg-white py-2">
          <span class="small text-muted fw-bold">Recent Regulatory Activity (${logs.length} logged actions)</span>
        </div>
        <div class="rh-card-body p-0">
          <div class="table-responsive">
            <table class="rh-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Case ID</th>
                  <th>Authorized Officer</th>
                  <th>Action Taken</th>
                  <th>Operational Details</th>
                </tr>
              </thead>
              <tbody>
                ${logs.map(log => `
                  <tr>
                    <td><small class="text-muted font-monospace">${log.timestamp}</small></td>
                    <td><a href="#" class="btn-open-workspace fw-bold text-primary" data-id="${log.caseId}">${log.caseId}</a></td>
                    <td><strong class="text-dark">${log.officer}</strong></td>
                    <td><span class="badge bg-light text-dark border">${log.action}</span></td>
                    <td><span class="small text-secondary">${log.details}</span></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    container.querySelectorAll(".btn-open-workspace").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const caseId = btn.getAttribute("data-id");
        this.openCaseWorkspace(caseId);
      });
    });
  }

  /* =========================================================================
     VIEW 8: SETTINGS & DEMO CONTROLS
     ========================================================================= */
  renderSettings(container) {
    const activeRole = mockDataService.getActiveRole();
    const casesCount = mockDataService.cases.length;
    const instCount = mockDataService.institutions.length;
    const bureausCount = mockDataService.bureaus.length;

    container.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h4 class="fw-bold mb-1" style="color: var(--rh-navy-dark);">System Settings &amp; Demonstration Controls</h4>
          <p class="text-muted small mb-0">Configure simulated roles, persistent state, turnaround policies, and mock datasets</p>
        </div>
        <div>
          <button class="btn btn-outline-danger btn-sm" id="btnSettingsResetDemo">
            <i class="bi bi-arrow-counterclockwise me-1"></i> Reset Demo Data to Seed
          </button>
        </div>
      </div>

      <!-- Demo Environment Notice Card -->
      <div class="alert alert-primary d-flex align-items-center gap-3 border-0 shadow-sm mb-4" style="background-color: #EFF6FF; border-left: 4px solid #0284C7 !important;">
        <i class="bi bi-info-circle-fill fs-3 text-primary"></i>
        <div>
          <strong class="d-block text-dark">Simulated Regulatory Environment &bull; Zero External Database Mode</strong>
          <span class="small text-secondary">
            This console operates on an isolated, deterministic in-browser data architecture. Mutations (case assignments, notes, status updates, escalations) update local state instantly without altering any production databases.
          </span>
        </div>
      </div>

      <div class="row g-4">
        <!-- Column 1: Role Configuration & Active Session -->
        <div class="col-lg-6">
          <div class="rh-card shadow-sm h-100">
            <div class="rh-card-header bg-white py-2">
              <span class="fw-bold small text-dark"><i class="bi bi-person-badge me-2 text-primary"></i>Simulated Officer Role Switching</span>
            </div>
            <div class="rh-card-body">
              <p class="small text-muted mb-3">
                Select an authorized administrative identity to test role-specific workflows and audit tracing across bureaus:
              </p>

              <div class="d-flex flex-column gap-2 mb-4">
                ${[
                  { role: "Director General", title: "Dr. A. K. Mittal", desc: "Director General & Member Secretary &bull; Executive Escalation Authority" },
                  { role: "Bureau Head (Approval)", title: "Smt. Sunita Rao", desc: "Bureau Head &bull; Institutional Approvals & Statutory Licensing" },
                  { role: "Section Head (PGRC)", title: "Dr. Ramesh Verma", desc: "Section Officer &bull; Public Grievance Redressal Cell" },
                  { role: "Legal Officer", title: "Adv. Rajesh Kumar", desc: "Senior Standing Counsel &bull; Court Matters & RTI Cell" },
                  { role: "Senior Coordinator", title: "Sh. Vikramaditya Sen", desc: "National Regulatory Coordinator &bull; Anti-Ragging Cell" }
                ].map(r => `
                  <div class="form-check p-3 border rounded ${activeRole === r.role ? 'border-primary bg-light' : 'bg-white'}" style="cursor: pointer;">
                    <input class="form-check-input role-radio-input" type="radio" name="settingsRoleRadio" id="role_${r.role.replace(/[\s()]+/g, '_')}" value="${r.role}" ${activeRole === r.role ? 'checked' : ''}>
                    <label class="form-check-label w-100 ms-2" for="role_${r.role.replace(/[\s()]+/g, '_')}" style="cursor: pointer;">
                      <div class="fw-bold text-dark">${r.title}</div>
                      <div class="small text-muted">${r.desc}</div>
                    </label>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        </div>

        <!-- Column 2: Dataset Controls & SLA Policy Settings -->
        <div class="col-lg-6">
          <!-- Theme Settings Card -->
          <div class="rh-card shadow-sm mb-4">
            <div class="rh-card-header bg-white py-2 d-flex justify-content-between align-items-center">
              <span class="fw-bold small text-dark"><i class="bi bi-palette me-2 text-primary"></i>Display Theme Preferences</span>
              <span class="badge bg-light text-dark border">Instant Adaptation</span>
            </div>
            <div class="rh-card-body">
              <p class="small text-muted mb-3">Select your display theme. The entire dashboard, case tables, modals, badges, and charts adapt smoothly with high contrast.</p>
              <div class="btn-group w-100" role="group">
                <button type="button" class="btn btn-outline-primary btn-sm settings-theme-btn ${(this.currentTheme || 'system') === 'light' ? 'active' : ''}" data-theme="light">
                  <i class="bi bi-sun me-1"></i> Light Mode
                </button>
                <button type="button" class="btn btn-outline-primary btn-sm settings-theme-btn ${(this.currentTheme || 'system') === 'dark' ? 'active' : ''}" data-theme="dark">
                  <i class="bi bi-moon-stars me-1"></i> Dark Mode
                </button>
                <button type="button" class="btn btn-outline-primary btn-sm settings-theme-btn ${(this.currentTheme || 'system') === 'system' ? 'active' : ''}" data-theme="system">
                  <i class="bi bi-laptop me-1"></i> System (OS)
                </button>
              </div>
            </div>
          </div>

          <div class="rh-card shadow-sm mb-4">
            <div class="rh-card-header bg-white py-2">
              <span class="fw-bold small text-dark"><i class="bi bi-database-gear me-2 text-primary"></i>Mock Dataset Inventory &amp; State</span>
            </div>
            <div class="rh-card-body">
              <div class="row g-2 text-center mb-3">
                <div class="col-4">
                  <div class="p-2 border rounded bg-light">
                    <small class="text-muted d-block fw-bold">Active Cases</small>
                    <span class="fs-4 fw-bold text-primary">${casesCount}</span>
                  </div>
                </div>
                <div class="col-4">
                  <div class="p-2 border rounded bg-light">
                    <small class="text-muted d-block fw-bold">Institutions</small>
                    <span class="fs-4 fw-bold text-dark">${instCount}</span>
                  </div>
                </div>
                <div class="col-4">
                  <div class="p-2 border rounded bg-light">
                    <small class="text-muted d-block fw-bold">Bureaus</small>
                    <span class="fs-4 fw-bold text-success">${bureausCount}</span>
                  </div>
                </div>
              </div>

              <div class="d-flex gap-2">
                <button class="btn btn-rh-secondary btn-sm flex-grow-1" id="btnSettingsExportCSV">
                  <i class="bi bi-file-earmark-spreadsheet me-1"></i> Export Cases CSV
                </button>
                <button class="btn btn-rh-primary btn-sm flex-grow-1" id="btnSettingsExportJSON">
                  <i class="bi bi-code-square me-1"></i> Export Cases JSON
                </button>
              </div>
            </div>
          </div>

          <div class="rh-card shadow-sm">
            <div class="rh-card-header bg-white py-2">
              <span class="fw-bold small text-dark"><i class="bi bi-stopwatch me-2 text-primary"></i>Turnaround Time &amp; Escalation Thresholds</span>
            </div>
            <div class="rh-card-body small">
              <div class="mb-3 d-flex justify-content-between align-items-center pb-2 border-bottom">
                <div>
                  <span class="fw-bold text-danger">Critical Priority Turnaround:</span>
                  <div class="text-muted">High-severity allegations (Ragging, Extortion)</div>
                </div>
                <span class="badge bg-danger">72 Hours</span>
              </div>
              <div class="mb-3 d-flex justify-content-between align-items-center pb-2 border-bottom">
                <div>
                  <span class="fw-bold text-warning text-dark">High Priority Turnaround:</span>
                  <div class="text-muted">Faculty shortages, infrastructure non-compliance</div>
                </div>
                <span class="badge bg-warning text-dark">144 Hours</span>
              </div>
              <div class="mb-3 d-flex justify-content-between align-items-center pb-2 border-bottom">
                <div>
                  <span class="fw-bold text-primary">Medium Priority Turnaround:</span>
                  <div class="text-muted">Curricular, certificate withholding, refunds</div>
                </div>
                <span class="badge bg-primary">360 Hours</span>
              </div>
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <span class="fw-bold text-dark">At-Risk Alert Trigger:</span>
                  <div class="text-muted">Flag cases reaching threshold before breach</div>
                </div>
                <span class="badge bg-info text-dark">&ge; 80% SLA Window</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Theme selector buttons
    container.querySelectorAll(".settings-theme-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const theme = btn.getAttribute("data-theme");
        this.applyTheme(theme, true);
        this.renderSettings(container);
      });
    });

    // Event listeners
    container.querySelectorAll(".role-radio-input").forEach(radio => {
      radio.addEventListener("change", (e) => {
        const newRole = e.target.value;
        mockDataService.setActiveRole(newRole);
        const headerSelect = document.getElementById("activeRoleSelector");
        if (headerSelect) headerSelect.value = newRole;
        this.showNotification(`Simulated role switched to: ${newRole}`, "info");
        this.renderSettings(container);
      });
    });

    const resetBtn = container.querySelector("#btnSettingsResetDemo");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        if (confirm("Reset all simulated cases, investigation notes, and activity to initial seed dataset?")) {
          mockDataService.resetDemoData();
          this.showNotification("Simulated dataset successfully restored to original seed state.", "success");
          this.renderSettings(container);
        }
      });
    }

    const exportCsvBtn = container.querySelector("#btnSettingsExportCSV");
    if (exportCsvBtn) {
      exportCsvBtn.addEventListener("click", () => {
        mockDataService.exportCasesCSV();
      });
    }

    const exportJsonBtn = container.querySelector("#btnSettingsExportJSON");
    if (exportJsonBtn) {
      exportJsonBtn.addEventListener("click", () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(mockDataService.cases, null, 2));
        const dlAnchor = document.createElement("a");
        dlAnchor.setAttribute("href", dataStr);
        dlAnchor.setAttribute("download", `ResolveHub_Simulated_Cases_${new Date().toISOString().split("T")[0]}.json`);
        document.body.appendChild(dlAnchor);
        dlAnchor.click();
        dlAnchor.remove();
      });
    }
  }
}

// Instantiate on DOM load
document.addEventListener("DOMContentLoaded", () => {
  window.resolveHubApp = new DashboardApp();
});

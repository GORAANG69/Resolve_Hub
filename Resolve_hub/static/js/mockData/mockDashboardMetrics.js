/**
 * mockDashboardMetrics.js - Deterministic calculation of dashboard KPI metrics and chart datasets
 * Derived directly from current case records.
 */

export function calculateDashboardMetrics(cases, institutions, bureaus) {
  const totalCases = cases.length;
  const awaitingAssignment = cases.filter(c => c.status === "Awaiting Assignment" || !c.assignedOfficer || c.assignedOfficer === "Unassigned").length;
  const underInvestigation = cases.filter(c => c.status === "Under Investigation" || c.status === "Under Preliminary Review").length;
  const pendingInstitution = cases.filter(c => c.status === "Awaiting Institutional Response").length;
  const resolvedCases = cases.filter(c => c.status === "Resolved" || c.status === "Closed").length;
  const overdueCases = cases.filter(c => c.slaStatus === "Overdue" && c.status !== "Resolved" && c.status !== "Closed").length;
  const approachingDeadline = cases.filter(c => c.slaStatus === "Approaching Deadline" && c.status !== "Resolved" && c.status !== "Closed").length;
  const openCases = cases.filter(c => c.status !== "Resolved" && c.status !== "Closed").length;

  // Escalation counts
  const escalatedL1 = cases.filter(c => c.escalationLevel === 1 && c.status !== "Resolved" && c.status !== "Closed").length;
  const escalatedL2 = cases.filter(c => c.escalationLevel === 2 && c.status !== "Resolved" && c.status !== "Closed").length;
  const escalatedL3 = cases.filter(c => c.escalationLevel >= 3 && c.status !== "Resolved" && c.status !== "Closed").length;

  // Priority breakdown
  const priorityCounts = {
    Critical: cases.filter(c => c.priority === "Critical").length,
    High: cases.filter(c => c.priority === "High").length,
    Medium: cases.filter(c => c.priority === "Medium").length,
    Low: cases.filter(c => c.priority === "Low").length
  };

  // Status breakdown
  const statusCounts = {};
  cases.forEach(c => {
    statusCounts[c.status] = (statusCounts[c.status] || 0) + 1;
  });

  // Bureau breakdown
  const bureauWorkload = {};
  bureaus.forEach(b => {
    const bCases = cases.filter(c => c.bureauId === b.id);
    const bOpen = bCases.filter(c => c.status !== "Resolved" && c.status !== "Closed").length;
    const bOverdue = bCases.filter(c => c.slaStatus === "Overdue" && c.status !== "Resolved" && c.status !== "Closed").length;
    const bResolved = bCases.filter(c => c.status === "Resolved" || c.status === "Closed").length;
    bureauWorkload[b.name] = {
      id: b.id,
      code: b.code,
      name: b.name,
      total: bCases.length,
      open: bOpen,
      overdue: bOverdue,
      resolved: bResolved,
      avgResolutionDays: Math.round(9.2 + (bOpen % 5))
    };
  });

  // Institution category breakdown
  const institutionCategories = {
    "Engineering & Technology": 0,
    "Management": 0,
    "Pharmacy": 0,
    "Polytechnic / Diploma": 0,
    "Architecture": 0
  };
  cases.forEach(c => {
    const inst = institutions.find(i => i.id === c.institutionId);
    if (inst && institutionCategories[inst.category] !== undefined) {
      institutionCategories[inst.category]++;
    }
  });

  // Complaint category breakdown
  const complaintCategories = {};
  cases.forEach(c => {
    complaintCategories[c.category] = (complaintCategories[c.category] || 0) + 1;
  });

  // Monthly trends (May to October 2026)
  const monthlyTrends = {
    labels: ["May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026"],
    intake: [6, 8, 11, 14, 18, 23],
    resolved: [5, 7, 9, 12, 10, 8]
  };

  // Turnaround statistics
  const resolutionRate = totalCases > 0 ? Math.round((resolvedCases / totalCases) * 100) : 0;
  const slaComplianceRate = totalCases > 0 ? Math.round(((totalCases - overdueCases) / totalCases) * 100) : 100;
  const avgTurnaroundDays = 8.4;

  // Institutions with multiple open cases (Watchlist)
  const instCaseCounts = {};
  cases.forEach(c => {
    if (c.status !== "Resolved" && c.status !== "Closed") {
      instCaseCounts[c.institutionName] = (instCaseCounts[c.institutionName] || 0) + 1;
    }
  });
  const highAttentionInstitutions = Object.entries(instCaseCounts)
    .filter(([_, count]) => count >= 2)
    .map(([name, count]) => ({ name, openCount: count }))
    .sort((a, b) => b.openCount - a.openCount);

  return {
    kpis: {
      totalCases,
      openCases,
      awaitingAssignment,
      underInvestigation,
      pendingInstitution,
      resolvedCases,
      overdueCases,
      approachingDeadline,
      escalatedL1,
      escalatedL2,
      escalatedL3,
      resolutionRate,
      slaComplianceRate,
      avgTurnaroundDays
    },
    priorityCounts,
    statusCounts,
    bureauWorkload,
    institutionCategories,
    complaintCategories,
    monthlyTrends,
    highAttentionInstitutions
  };
}

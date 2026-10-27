/**
 * mockCaseHistory.js - Detailed Investigation Notes, Evidence Records, and Timelines
 * Provides rich chronological activity for case workspaces.
 */

export const mockCaseHistory = {
  "AICTE-2026-REG-0101": {
    notes: [
      {
        id: "NOTE-101-1",
        author: "Dr. Ramesh Verma (PGRC)",
        date: "2026-09-14 11:30",
        content: "Preliminary scrutiny of bank receipts confirms unaccounted collection of ₹45,000 per student under miscellaneous development fund. Formal Show Cause Notice (SCN) drafted."
      },
      {
        id: "NOTE-101-2",
        author: "Dr. Ramesh Verma (PGRC)",
        date: "2026-09-28 15:45",
        content: "Deadline for SCN response expired without submission from college management. Case escalated to Level 2 (Bureau Head review). Recommend on-site vigilance audit."
      },
      {
        id: "NOTE-101-3",
        author: "Dr. Priya Sundaram (Vigilance)",
        date: "2026-10-15 10:20",
        content: "Regional committee appointed for surprise physical inspection on October 29. Bank accounts under scrutiny with District Magistrate assistance."
      }
    ],
    timeline: [
      { date: "2026-09-12 09:15", title: "Grievance Intake", actor: "CPGRAMS Ingestion", description: "Complaint registered via CPGRAMS Portal ref CPG/2026/091823. Initial priority set to High." },
      { date: "2026-09-13 14:00", title: "Automated AI Triage", actor: "System Triage Engine", description: "Categorized under Financial Irregularities. Routed to Public Grievance Redressal Cell (PGRC). Priority raised to Critical due to widespread student impact." },
      { date: "2026-09-14 11:30", title: "Officer Assigned", actor: "Smt. Sunita Rao", description: "Assigned to Dr. Ramesh Verma for priority scrutiny." },
      { date: "2026-09-18 16:20", title: "Show Cause Issued", actor: "Dr. Ramesh Verma", description: "Notice issued to Principal & Chairman ref AICTE/PGRC/2026/SCN-481 giving 10 working days to respond." },
      { date: "2026-09-28 15:45", title: "SLA Breached & Escalated", actor: "SLA Autopilot", description: "Resolution window elapsed without institutional compliance. Escalated to Level 2 (Bureau Head)." },
      { date: "2026-10-22 17:00", title: "Vigilance Audit Ordered", actor: "Adv. Rajesh Kumar", description: "Joint surprise inspection committee formed." }
    ]
  },
  "AICTE-2026-REG-0102": {
    notes: [
      {
        id: "NOTE-102-1",
        author: "Smt. Sunita Rao (Approval Bureau)",
        date: "2026-10-08 14:15",
        content: "Verified AICTE portal database. No application for dual degree collaboration was ever sanctioned for academic session 2026-27. Marketing brochure forwarded to Legal Cell."
      },
      {
        id: "NOTE-102-2",
        author: "Smt. Sunita Rao (Approval Bureau)",
        date: "2026-10-20 16:00",
        content: "Institution submitted interim letter claiming program is a 'certificate course'. Not acceptable under AICTE APH Chapter 3 guidelines. Clarification sought within 3 days."
      }
    ],
    timeline: [
      { date: "2026-10-05 10:45", title: "Case Logged", actor: "Letter OCR Intake", description: "Parent grievance letter scanned and ingested with prospectus attachment." },
      { date: "2026-10-06 11:00", title: "Assigned to Approval Cell", actor: "AI Triage", description: "Assigned to Smt. Sunita Rao (Approval & Licensing Bureau)." },
      { date: "2026-10-08 14:30", title: "Interim Directive Issued", actor: "Smt. Sunita Rao", description: "Directive issued to halt fresh admissions in unapproved AI-FinTech PGDM program." },
      { date: "2026-10-24 12:00", title: "Institutional Reply Received", actor: "Apex Global Academy", description: "Interim rejoinder received; currently under legal evaluation." }
    ]
  },
  "AICTE-2026-REG-0106": {
    notes: [
      {
        id: "NOTE-106-1",
        author: "Sh. Vikramaditya Sen (Anti-Ragging)",
        date: "2026-10-22 18:30",
        content: "CRITICAL: Spoke with victim's family and medical superintendent of District Civil Hospital. Student sustained multiple fractures. FIR No. 892/2026 filed at Kasna PS."
      },
      {
        id: "NOTE-106-2",
        author: "Dr. A. K. Mittal (Director General)",
        date: "2026-10-24 10:00",
        content: "Emergency review meeting held. Institute management suspended the hostel warden and 4 senior students. Standing Committee to submit penalty recommendation."
      }
    ],
    timeline: [
      { date: "2026-10-22 17:30", title: "Emergency Referral Logged", actor: "National Anti-Ragging Helpline", description: "Urgent red alert intake regarding hospitalized 1st year diploma student." },
      { date: "2026-10-22 18:00", title: "Escalated to Level 1", actor: "System Triage", description: "Auto-classified Critical; SLA set to strict 48-hour window." },
      { date: "2026-10-24 18:01", title: "Escalated to Level 3", actor: "SLA Autopilot", description: "Mandatory FIR copy from college administration not submitted within SLA. Escalated directly to Member Secretary & Director General." },
      { date: "2026-10-26 09:30", title: "Directorate Hearing Convened", actor: "Dr. A. K. Mittal", description: "Show-cause issued for withdrawal of institutional approval." }
    ]
  }
};

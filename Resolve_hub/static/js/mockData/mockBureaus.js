/**
 * mockBureaus.js - Illustrative AICTE Administrative Units and Case Officers
 * Deterministic organizational hierarchy for Resolve_Hub demonstration.
 */

export const mockBureaus = [
  {
    id: "BUR-APPR",
    code: "APPR",
    name: "Approval & Licensing Bureau",
    description: "Evaluates institutional approvals, renewal licenses, program expansions, and accreditation norms.",
    headName: "Smt. Sunita Rao",
    headRole: "Bureau Head & Advisor",
    email: "bureau.approval@resolvehub.local",
    cells: [
      {
        id: "CELL-APPR",
        code: "APPR-CELL",
        name: "Institutional Approval Cell",
        description: "Scrutiny of new institution applications, extension of approval (EOA), and closure requests.",
        leadOfficer: "Sh. R. K. Mukherjee",
        defaultSlaHours: 120,
        bureauId: "BUR-APPR"
      },
      {
        id: "CELL-ACCR",
        code: "ACCR-CELL",
        name: "Accreditation & Standards Cell",
        description: "Monitoring adherence to academic standards, NBA accreditation criteria, and faculty ratios.",
        leadOfficer: "Smt. Meenakshi Iyer",
        defaultSlaHours: 168,
        bureauId: "BUR-APPR"
      }
    ]
  },
  {
    id: "BUR-PGRC",
    code: "PGRC",
    name: "Grievance Redressal Bureau",
    description: "Centrally registers and investigates institutional grievances from stakeholders against approved colleges.",
    headName: "Dr. Ramesh Verma",
    headRole: "Bureau Head & Senior Advisor",
    email: "bureau.pgrc@resolvehub.local",
    cells: [
      {
        id: "CELL-PGRC",
        code: "PGRC-CELL",
        name: "Public Grievance Redressal Cell (PGRC)",
        description: "Intake and resolution of general institutional non-compliance, arbitrary fees, and student mistreatment.",
        leadOfficer: "Dr. Ramesh Verma",
        defaultSlaHours: 144,
        bureauId: "BUR-PGRC"
      },
      {
        id: "CELL-SFTY",
        code: "SFTY-CELL",
        name: "Anti-Ragging & Campus Safety Cell",
        description: "Critical investigations into ragging, hostel safety violations, harassment, and campus violence.",
        leadOfficer: "Sh. Vikramaditya Sen",
        defaultSlaHours: 48,
        bureauId: "BUR-PGRC"
      }
    ]
  },
  {
    id: "BUR-LEGL",
    code: "LEGL",
    name: "Compliance & Legal Affairs Bureau",
    description: "Handles judicial matters, RTI queries, vigilance inspections, and regulatory enforcement.",
    headName: "Adv. Rajesh Kumar",
    headRole: "Legal Advisor & Bureau Coordinator",
    email: "bureau.legal@resolvehub.local",
    cells: [
      {
        id: "CELL-LEGL",
        code: "LEGL-CELL",
        name: "Legal Affairs & RTI Cell",
        description: "High Court/Supreme Court directives, legal notices, and statutory RTI requests.",
        leadOfficer: "Adv. Rajesh Kumar",
        defaultSlaHours: 72,
        bureauId: "BUR-LEGL"
      },
      {
        id: "CELL-VIGL",
        code: "VIGL-CELL",
        name: "Inspection & Vigilance Cell",
        description: "Inquiries into ghost faculty, fraudulent affiliations, capitation fee extortion, and financial fraud.",
        leadOfficer: "Dr. Priya Sundaram",
        defaultSlaHours: 96,
        bureauId: "BUR-LEGL"
      }
    ]
  },
  {
    id: "BUR-RO",
    code: "RO",
    name: "Regional Coordination Bureau",
    description: "Decentralized regional office oversight for localized investigations, on-site audits, and dispute mediation.",
    headName: "Er. Anand Joshi",
    headRole: "Chief Regional Coordinator",
    email: "bureau.regional@resolvehub.local",
    cells: [
      {
        id: "CELL-RON",
        code: "RO-NORTH",
        name: "Northern Regional Office Cell (Kanpur/Delhi)",
        description: "Northern states: UP, Delhi NCR, Haryana, Punjab, Uttarakhand, Himachal Pradesh.",
        leadOfficer: "Er. Anand Joshi",
        defaultSlaHours: 168,
        bureauId: "BUR-RO"
      },
      {
        id: "CELL-ROS",
        code: "RO-SOUTH",
        name: "Southern Regional Office Cell (Chennai/Bangalore)",
        description: "Southern states: Tamil Nadu, Karnataka, Kerala, Andhra Pradesh, Telangana.",
        leadOfficer: "Dr. K. Swaminathan",
        defaultSlaHours: 168,
        bureauId: "BUR-RO"
      },
      {
        id: "CELL-ROW",
        code: "RO-WEST",
        name: "Western Regional Office Cell (Mumbai/Bhopal)",
        description: "Western & Central states: Maharashtra, Gujarat, Goa, Madhya Pradesh.",
        leadOfficer: "Dr. Alok Nath",
        defaultSlaHours: 168,
        bureauId: "BUR-RO"
      },
      {
        id: "CELL-ROE",
        code: "RO-EAST",
        name: "Eastern Regional Office Cell (Kolkata)",
        description: "Eastern & North-Eastern states: West Bengal, Odisha, Bihar, Jharkhand, Assam.",
        leadOfficer: "Sh. B. K. Ray",
        defaultSlaHours: 168,
        bureauId: "BUR-RO"
      }
    ]
  }
];

export const mockOfficers = [
  { id: "OFF-01", name: "Dr. A. K. Mittal", role: "Director General & Member Secretary", bureau: "Central Administration", email: "director.general@resolvehub.local" },
  { id: "OFF-02", name: "Smt. Sunita Rao", role: "Bureau Head (Approval & Licensing)", bureau: "Approval & Licensing Bureau", email: "sunita.rao@resolvehub.local" },
  { id: "OFF-03", name: "Dr. Ramesh Verma", role: "Section Head (Public Grievance Cell)", bureau: "Grievance Redressal Bureau", email: "ramesh.verma@resolvehub.local" },
  { id: "OFF-04", name: "Adv. Rajesh Kumar", role: "Legal & Compliance Officer", bureau: "Compliance & Legal Affairs Bureau", email: "rajesh.kumar@resolvehub.local" },
  { id: "OFF-05", name: "Sh. Vikramaditya Sen", role: "Senior Coordinator (Anti-Ragging)", bureau: "Grievance Redressal Bureau", email: "vikram.sen@resolvehub.local" },
  { id: "OFF-06", name: "Dr. Priya Sundaram", role: "Chief Vigilance Inspector", bureau: "Compliance & Legal Affairs Bureau", email: "priya.sundaram@resolvehub.local" },
  { id: "OFF-07", name: "Er. Anand Joshi", role: "Regional Officer (North)", bureau: "Regional Coordination Bureau", email: "anand.joshi@resolvehub.local" },
  { id: "OFF-08", name: "Smt. Meenakshi Iyer", role: "Standards & Accreditation Officer", bureau: "Approval & Licensing Bureau", email: "meenakshi.iyer@resolvehub.local" }
];

import { NavLink } from "react-router-dom";

const NAV_SECTIONS = [
  {
    label: "Nurse",
    items: [
      {
        to: "/intake",
        label: "Patient Intake",
        icon: (
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="2" y="2" width="12" height="12" rx="2" />
            <path d="M8 5v6M5 8h6" />
          </svg>
        ),
      },
      {
        to: "/queue",
        label: "Patient Queue",
        icon: (
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M2 4h12M2 8h9M2 12h11" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "Doctor",
    items: [
      {
        to: "/consult",
        label: "Consultation",
        icon: (
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3 3h10v7H3zM6 13h4M8 10v3" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "Admin",
    items: [
      {
        to: "/eval",
        label: "Evaluation",
        icon: (
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M2 12L5 8l3 2 3-5 3 2" />
          </svg>
        ),
      },
    ],
  },
];

const QUICK_LINKS = [
  { label: "WHO Guidelines",  href: "https://www.who.int/publications/who-guidelines" },
  { label: "UpToDate",        href: "https://www.uptodate.com" },
  { label: "MDCalc",          href: "https://www.mdcalc.com" },
  { label: "Drugs.com",       href: "https://www.drugs.com" },
  { label: "ICD-10 Codes",    href: "https://www.icd10data.com" },
  { label: "NICE Guidelines", href: "https://www.nice.org.uk/guidance" },
];

export function SideNav() {
  return (
    <nav className="side-nav">
      {/* Logo */}
      <div className="nav-logo">
        <div className="nav-logo-mark">Triage AI</div>
        <div className="nav-logo-sub">Clinical Decision Support</div>
        <div className="nav-accent-rule" />
      </div>

      {/* Navigation */}
      {NAV_SECTIONS.map((section) => (
        <div key={section.label}>
          <div className="nav-section-label">{section.label}</div>
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </div>
      ))}

      <div className="nav-spacer" />

      {/* Quick reference */}
      <hr className="nav-divider" />
      <div className="nav-quick-links">
        <div
          style={{
            fontSize: "0.58rem",
            fontWeight: 600,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--text-muted)",
            padding: "0 var(--s-3) var(--s-2)",
            fontFamily: "var(--font-body)",
          }}
        >
          Reference
        </div>
        {QUICK_LINKS.map((link) => (
          <a
            key={link.label}
            href={link.href}
            target="_blank"
            rel="noreferrer"
            className="nav-quick-link"
          >
            <svg
              viewBox="0 0 11 11"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              style={{ opacity: 0.4 }}
            >
              <path d="M1 10L10 1M10 1H5M10 1v5" />
            </svg>
            {link.label}
          </a>
        ))}
      </div>

      {/* Footer */}
      <div className="nav-footer">
        <p>Triage AI — v0.1 development</p>
        <p>For clinical decision support only.</p>
        <p>Not a substitute for clinical judgment.</p>
      </div>
    </nav>
  );
}
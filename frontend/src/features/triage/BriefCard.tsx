import type { BriefResponse } from "../../core/entities/triage";
import { UrgencyBadge } from "../../components/shared/UrgencyBadge";
import { DrugFlagBanner } from "../../components/shared/DrugFlagBanner";

interface BriefCardProps {
  brief: BriefResponse;
}

export function BriefCard({ brief }: BriefCardProps) {
  return (
    <div className="card fade-up" style={{ display: "flex", flexDirection: "column", gap: "var(--s-5)" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--s-3)", justifyContent: "space-between" }}>
        <h3 style={{ fontFamily: "var(--font-display)" }}>60-Second Brief</h3>
        <UrgencyBadge level={brief.urgency_level} label={brief.urgency_label} />
      </div>

      {/* Summary */}
      <p style={{ color: "var(--text-primary)", lineHeight: 1.7 }}>{brief.summary}</p>

      {/* Drug flag */}
      {brief.drug_flag_summary && (
        <DrugFlagBanner summary={brief.drug_flag_summary} />
      )}

      <hr className="divider" />

      {/* Two-column layout */}
      <div className="grid-2" style={{ gap: "var(--s-6)" }}>
        {/* Left */}
        <div>
          <h4 style={{ marginBottom: "var(--s-3)" }}>Top Differentials</h4>
          <ol style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
            {brief.top_differentials.map((d, i) => (
              <li
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--s-2)",
                  fontSize: "0.9rem",
                  color: "var(--text-primary)",
                }}
              >
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    background: "var(--bg-overlay)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                {d}
              </li>
            ))}
          </ol>
        </div>

        {/* Right */}
        <div>
          <h4 style={{ marginBottom: "var(--s-3)" }}>Red Flags</h4>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--s-2)" }}>
            {brief.red_flags.map((flag) => (
              <span key={flag} className="chip chip-danger">
                ⚑ {flag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Suggested questions */}
      {brief.suggested_questions.length > 0 && (
        <>
          <hr className="divider" />
          <div>
            <h4 style={{ marginBottom: "var(--s-3)" }}>Suggested Questions</h4>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--s-2)" }}>
              {brief.suggested_questions.map((q, i) => (
                <li
                  key={i}
                  style={{ fontSize: "0.875rem", color: "var(--text-secondary)", paddingLeft: "var(--s-4)", borderLeft: "2px solid var(--border-strong)" }}
                >
                  {q}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
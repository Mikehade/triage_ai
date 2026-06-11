import type { PatientDetail } from "../../core/entities/patient";
import { TRIAGE_STATUS_LABELS, TRIAGE_STATUS_COLORS } from "../../core/constants/urgency";
import { timeAgo, computeAge } from "../../core/entities/patient";

interface PatientHeaderProps {
  patient: PatientDetail;
}

export function PatientHeader({ patient }: PatientHeaderProps) {
  const urgency = patient.triage_result?.urgency;
  const age = patient.date_of_birth ? computeAge(patient.date_of_birth) : null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--s-5)",
        padding: "var(--s-4) var(--s-5)",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Urgency colour strip */}
      {urgency && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: 4,
            background: `var(--urgency-${urgency.level})`,
            borderRadius: "var(--r-lg) 0 0 var(--r-lg)",
          }}
        />
      )}

      {/* Avatar */}
      <div
        style={{
          marginLeft: urgency ? "var(--s-2)" : 0,
          width: 48,
          height: 48,
          borderRadius: "50%",
          background: "var(--bg-overlay)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.3rem",
          flexShrink: 0,
          border: "2px solid var(--border-strong)",
        }}
      >
        {patient.sex === "female" ? "👩" : "👨"}
      </div>

      {/* Name + meta */}
      <div style={{ flex: 1 }}>
        <p
          style={{
            fontWeight: 700,
            color: "var(--text-primary)",
            fontSize: "1.05rem",
            letterSpacing: "-0.01em",
            fontFamily: "var(--font-display)",
          }}
        >
          {patient.full_name}
        </p>
        <div
          style={{
            display: "flex",
            gap: "var(--s-3)",
            flexWrap: "wrap",
            marginTop: 4,
          }}
        >
          {age !== null && (
            <span
              style={{
                fontSize: "0.78rem",
                color: "var(--text-muted)",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              🎂 {age} years
            </span>
          )}
          {patient.date_of_birth && (
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              DOB: {new Date(patient.date_of_birth).toLocaleDateString()}
            </span>
          )}
          {patient.phone_number && (
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              📞 {patient.phone_number}
            </span>
          )}
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            🕒 Arrived {timeAgo(patient.created_at)}
          </span>
        </div>
      </div>

      {/* Status badges */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--s-2)",
          alignItems: "flex-end",
        }}
      >
        <span
          style={{
            fontSize: "0.7rem",
            fontWeight: 700,
            padding: "3px 10px",
            borderRadius: 100,
            border: "1px solid currentColor",
            color: TRIAGE_STATUS_COLORS[patient.triage_status],
          }}
        >
          {TRIAGE_STATUS_LABELS[patient.triage_status]}
        </span>

        {urgency && (
          <span className={`badge badge-urgency-${urgency.level}`}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "currentColor",
                display: "inline-block",
                flexShrink: 0,
              }}
            />
            {urgency.label}
          </span>
        )}
      </div>
    </div>
  );
}
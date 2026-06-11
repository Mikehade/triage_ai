import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageShell } from "../components/shared/PageShell";
import { IntakeForm } from "../features/intake/IntakeForm";
import { useIntake } from "../hooks/useIntake";
import type { TriageResultResponse } from "../core/entities/triage";
import type { IntakeResponse } from "../core/entities/patient";
import { computeAge } from "../core/entities/patient";

interface SubmitResult {
  intake: IntakeResponse;
  triage: TriageResultResponse;
  patientName?: string;
  dob?: string;
  phone?: string;
  sex?: string;
}

function UrgencyRing({ level }: { level: 1 | 2 | 3 | 4 | 5 }) {
  const colors = {
    1: "#5c7a9e",
    2: "#2e8bc0",
    3: "#d4a017",
    4: "#d4621a",
    5: "#d43a3a",
  };
  return (
    <div
      style={{
        width: 52,
        height: 52,
        borderRadius: "50%",
        border: `3px solid ${colors[level]}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "1.4rem",
        flexShrink: 0,
        background: `${colors[level]}18`,
        boxShadow: `0 0 16px ${colors[level]}30`,
      }}
    >
      {level >= 5 ? "🚨" : level >= 4 ? "⚠️" : level >= 3 ? "🔶" : "✓"}
    </div>
  );
}

export default function NursePage() {
  const navigate = useNavigate();
  const { submitting, error, submitIntakeAndTriage } = useIntake();
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [formKey, setFormKey] = useState(0);

  const handleSubmit = async (
    payload: Parameters<typeof submitIntakeAndTriage>[0]
  ) => {
    const res = await submitIntakeAndTriage(payload);
    if (res) {
      const name =
        [payload.first_name, payload.last_name].filter(Boolean).join(" ") ||
        undefined;
      setResult({
        ...res,
        patientName: name,
        dob: payload.date_of_birth,
        phone: payload.phone_number,
        sex: payload.sex,
      });
    }
  };

  const handleNewIntake = () => {
    setResult(null);
    setFormKey((k) => k + 1);
  };

  const goToConsult = () => {
    if (result?.intake.patient_id) {
      navigate("/consult", {
        state: { patientId: result.intake.patient_id },
      });
    }
  };

  const age = result?.dob ? computeAge(result.dob) : result?.intake.age;

  return (
    <PageShell>
      <div className="page-header">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div>
            <div className="eyebrow">Nurse Workstation</div>
            <h1>Patient Intake</h1>
            <p>
              Register a new patient or select an existing one, then complete
              the clinical form.
            </p>
          </div>
          {result && (
            <button className="btn btn-primary" onClick={handleNewIntake}>
              + New Intake
            </button>
          )}
        </div>
      </div>

      {!result ? (
        <IntakeForm
          key={formKey}
          onSubmit={handleSubmit}
          submitting={submitting}
          error={error}
        />
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--s-5)",
            maxWidth: 760,
          }}
        >
          <div className="alert alert-success">
            ✓ Intake submitted and triage complete.
          </div>

          {/* ── Result summary card — clickable to go to consult ─── */}
          <div
            className="card card-elevated fade-up"
            style={{
              cursor: result?.intake.patient_id ? "pointer" : "default",
              transition: "border-color 0.18s, box-shadow 0.18s",
              position: "relative",
            }}
            onClick={result?.intake.patient_id ? goToConsult : undefined}
            onMouseEnter={(e) => {
              if (!result?.intake.patient_id) return;
              (e.currentTarget as HTMLDivElement).style.borderColor =
                "var(--accent)";
              (e.currentTarget as HTMLDivElement).style.boxShadow =
                "var(--shadow-glow)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.borderColor = "";
              (e.currentTarget as HTMLDivElement).style.boxShadow = "";
            }}
          >
            {/* Click hint */}
            {result?.intake.patient_id && (
              <div
                style={{
                  position: "absolute",
                  top: "var(--s-4)",
                  right: "var(--s-4)",
                  fontSize: "0.72rem",
                  color: "var(--accent)",
                  opacity: 0.7,
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                Open consultation →
              </div>
            )}

            {/* Patient identity */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--s-4)",
                marginBottom: "var(--s-5)",
              }}
            >
              <UrgencyRing level={result.triage.urgency_level} />
              <div>
                <h3 style={{ fontFamily: "var(--font-display)" }}>
                  {result.patientName ?? "Patient"}
                </h3>
                <p
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    marginTop: 3,
                    display: "flex",
                    gap: 8,
                    flexWrap: "wrap",
                  }}
                >
                  {age && age > 0 && <span>Age: {age} years</span>}
                  {result.sex && (
                    <span style={{ textTransform: "capitalize" }}>
                      · {result.sex}
                    </span>
                  )}
                  {result.phone && <span>· {result.phone}</span>}
                </p>
              </div>
              <span
                className={`badge badge-urgency-${result.triage.urgency_level}`}
                style={{ marginLeft: "auto", marginRight: "var(--s-8)" }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: "currentColor",
                    display: "inline-block",
                  }}
                />
                {result.triage.urgency_label}
              </span>
            </div>

            {/* Urgency reasoning */}
            <p
              style={{
                fontSize: "0.875rem",
                color: "var(--text-secondary)",
                lineHeight: 1.7,
                marginBottom: "var(--s-5)",
                padding: "var(--s-3) var(--s-4)",
                background: "var(--bg-base)",
                borderRadius: "var(--r-md)",
                borderLeft: "3px solid var(--border-accent)",
              }}
            >
              {result.triage.urgency_reasoning}
            </p>

            {/* Red flags */}
            {result.triage.red_flags.length > 0 && (
              <div style={{ marginBottom: "var(--s-4)" }}>
                <div className="section-label">Red Flags</div>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "var(--s-2)",
                    marginTop: "var(--s-2)",
                  }}
                >
                  {result.triage.red_flags.map((f) => (
                    <span key={f} className="chip chip-danger">
                      ⚑ {f}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Differentials */}
            {result.triage.differentials.length > 0 && (
              <div>
                <div className="section-label">Top Differentials</div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--s-2)",
                    marginTop: "var(--s-2)",
                  }}
                >
                  {result.triage.differentials.slice(0, 3).map((d) => (
                    <div
                      key={d.rank}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "var(--s-3)",
                        padding: "var(--s-2) var(--s-3)",
                        background: "var(--bg-base)",
                        borderRadius: "var(--r-md)",
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 700,
                          color: "var(--text-muted)",
                          fontSize: "0.72rem",
                          width: 20,
                          textAlign: "center",
                          fontFamily: "var(--font-mono)",
                        }}
                      >
                        #{d.rank}
                      </span>
                      <span
                        style={{
                          flex: 1,
                          color: "var(--text-primary)",
                          fontSize: "0.875rem",
                        }}
                      >
                        {d.condition}
                      </span>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--text-secondary)",
                          fontFamily: "var(--font-mono)",
                        }}
                      >
                        {Math.round(d.confidence * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Actions row */}
          <div style={{ display: "flex", gap: "var(--s-3)" }}>
            <button
              className="btn btn-primary"
              onClick={goToConsult}
              disabled={!result?.intake.patient_id}
            >
              Open Consultation →
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleNewIntake}
            >
              + New Intake
            </button>
          </div>
        </div>
      )}
    </PageShell>
  );
}
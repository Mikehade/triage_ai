import { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PageShell } from "../components/shared/PageShell";
import { BriefCard } from "../features/triage/BriefCard";
import { NoteEditor } from "../features/consult/NoteEditor";
import { PatientHeader } from "../components/shared/PatientHeader";
import { Spinner } from "../components/ui/Spinner";
import { PatientCardSkeleton } from "../components/ui/Skeleton";
import { usePatientDetail, usePatientSearch } from "../hooks/useIntake";
import { useBrief } from "../hooks/useTriage";
import { useConsult } from "../hooks/useConsult";
import { TRIAGE_STATUS_LABELS, TRIAGE_STATUS_COLORS } from "../core/constants/urgency";
import type { PatientSummary } from "../core/entities/patient";

/* ── Inline patient search for consult page ────────────────────────────── */
function ConsultPatientSearch({
  onSelect,
}: {
  onSelect: (p: PatientSummary) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const { results, searching, search, clear } = usePatientSearch();
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    search(query);
    setOpen(query.length > 1);
  }, [query]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = (p: PatientSummary) => {
    onSelect(p);
    setQuery("");
    clear();
    setOpen(false);
  };

  return (
    <div ref={wrapperRef} style={{ position: "relative", maxWidth: 480 }}>
      <div className="field" style={{ marginBottom: 0 }}>
        <div style={{ position: "relative" }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search patient by name or phone…"
            autoComplete="off"
            style={{ paddingLeft: 38 }}
          />
          {/* Search icon */}
          <svg
            style={{
              position: "absolute",
              left: 11,
              top: "50%",
              transform: "translateY(-50%)",
              opacity: 0.4,
              width: 16,
              height: 16,
              pointerEvents: "none",
            }}
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <circle cx="6.5" cy="6.5" r="4.5" />
            <path d="M10.5 10.5L14 14" />
          </svg>
          {searching && (
            <span
              className="spinner"
              style={{
                position: "absolute",
                right: 10,
                top: "50%",
                transform: "translateY(-50%)",
              }}
            />
          )}
        </div>
      </div>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 300,
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--r-lg)",
            boxShadow: "var(--shadow-lg)",
            maxHeight: 300,
            overflowY: "auto",
          }}
        >
          {results.length === 0 && !searching && query.length > 1 && (
            <div
              style={{
                padding: "var(--s-4)",
                fontSize: "0.875rem",
                color: "var(--text-muted)",
                textAlign: "center",
              }}
            >
              No patients found for "{query}"
            </div>
          )}
          {results.map((patient) => (
            <button
              key={patient.id}
              type="button"
              onClick={() => handleSelect(patient)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                width: "100%",
                padding: "10px 14px",
                background: "transparent",
                border: "none",
                borderBottom: "1px solid var(--border)",
                cursor: "pointer",
                textAlign: "left",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.background =
                  "var(--bg-overlay)")
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.background =
                  "transparent")
              }
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: "var(--bg-overlay)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.9rem",
                  flexShrink: 0,
                }}
              >
                {patient.sex === "female" ? "👩" : "👨"}
              </div>
              <div style={{ flex: 1 }}>
                <p
                  style={{
                    fontWeight: 500,
                    color: "var(--text-primary)",
                    fontSize: "0.875rem",
                  }}
                >
                  {patient.full_name}
                </p>
                <p
                  style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}
                >
                  {patient.date_of_birth
                    ? new Date(patient.date_of_birth).toLocaleDateString()
                    : ""}
                  {patient.phone_number ? ` · ${patient.phone_number}` : ""}
                </p>
              </div>
              <span
                style={{
                  fontSize: "0.68rem",
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: 100,
                  border: "1px solid currentColor",
                  color: TRIAGE_STATUS_COLORS[patient.triage_status],
                  whiteSpace: "nowrap",
                }}
              >
                {TRIAGE_STATUS_LABELS[patient.triage_status]}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main page ─────────────────────────────────────────────────────────── */
export default function ConsultPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const [patientId, setPatientId] = useState<string | null>(
    location.state?.patientId ?? null
  );

  const { patient, loading: patientLoading, error: patientError } =
    usePatientDetail(patientId);
  const { brief, state: briefState, error: briefError, fetchBrief, runTriageThenPoll } =
    useBrief();
  const { note, loading: consultLoading, error: consultError, generateNote, signNote } =
    useConsult();

  useEffect(() => {
    if (!patientId) return;
    if (patient?.brief) return;
    fetchBrief(patientId);
  }, [patientId, patient]);

  const handleGenerateNote = () => {
    if (!patientId || !patient?.triage_result?.id) return;
    generateNote({
      patient_id: patientId,
      triage_result_id: patient.triage_result.id,
    });
  };

  const displayBrief = patient?.brief ?? brief;

  return (
    <PageShell>
      {/* ── Page header with inline search ───────────────────────────── */}
      <div className="page-header">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "var(--s-4)",
          }}
        >
          <div>
            <div className="eyebrow">Doctor Workstation</div>
            <h1>Consultation</h1>
            <p>Review triage brief, generate a SOAP note, refer or discharge.</p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "var(--s-3)" }}>
            <ConsultPatientSearch
              onSelect={(p) => {
                setPatientId(p.id);
              }}
            />
            {patientId && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => navigate("/queue")}
              >
                ← Queue
              </button>
            )}
          </div>
        </div>
      </div>

      {/* No patient yet — show prompt with image area */}
      {!patientId && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "var(--s-5)",
            padding: "var(--s-16) var(--s-8)",
            textAlign: "center",
          }}
        >
          {/* Illustration */}
          <div
            style={{
              width: 120,
              height: 120,
              borderRadius: "50%",
              background: "var(--bg-surface)",
              border: "2px dashed var(--border-strong)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "3rem",
            }}
          >
            🩺
          </div>
          <div>
            <h3 style={{ color: "var(--text-secondary)", marginBottom: "var(--s-2)" }}>
              No patient selected
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              Search for a patient above, or open one from the queue.
            </p>
          </div>
          <div style={{ display: "flex", gap: "var(--s-3)" }}>
            <button className="btn btn-primary" onClick={() => navigate("/queue")}>
              Open Patient Queue
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => navigate("/intake")}
            >
              New Intake
            </button>
          </div>
        </div>
      )}

      {/* Patient error */}
      {patientError && (
        <div className="alert alert-danger" style={{ maxWidth: 600, marginBottom: "var(--s-4)" }}>
          {patientError}
        </div>
      )}

      {/* Loading */}
      {patientLoading && <PatientCardSkeleton />}

      {/* Patient loaded */}
      {patient && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--s-6)",
          }}
        >
          {/* ── Patient header ──────────────────────────────────────── */}
          <PatientHeader patient={patient} />

          {/* ── Two-column layout: brief + clinical actions ─────────── */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 340px",
              gap: "var(--s-6)",
              alignItems: "start",
            }}
          >
            {/* Left — Brief & note */}
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-5)" }}>
              {/* Triage in progress */}
              {!displayBrief && briefState === "polling" && (
                <div
                  className="card"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--s-4)",
                    color: "var(--text-secondary)",
                  }}
                >
                  <Spinner />
                  <div>
                    <p
                      style={{
                        fontWeight: 500,
                        color: "var(--text-primary)",
                        marginBottom: 3,
                      }}
                    >
                      Triage in progress…
                    </p>
                    <p style={{ fontSize: "0.82rem" }}>
                      Checking every few seconds. Usually under a minute.
                    </p>
                  </div>
                </div>
              )}

              {briefState === "timeout" && (
                <div className="alert alert-warning">
                  Triage is taking longer than expected.
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ marginLeft: "var(--s-4)" }}
                    onClick={() => runTriageThenPoll(patientId!)}
                  >
                    Run Triage
                  </button>
                </div>
              )}

              {!displayBrief &&
                briefState !== "polling" &&
                briefState !== "timeout" &&
                patient.triage_status === "pending" && (
                  <div className="card" style={{ maxWidth: 500 }}>
                    <p
                      style={{
                        color: "var(--text-secondary)",
                        marginBottom: "var(--s-4)",
                        fontSize: "0.875rem",
                      }}
                    >
                      Triage not yet complete for this patient.
                    </p>
                    <button
                      className="btn btn-primary"
                      onClick={() => runTriageThenPoll(patientId!)}
                      disabled={briefState === "loading"}
                    >
                      {briefState === "loading" ? (
                        <Spinner label="Running triage…" />
                      ) : (
                        "Run Triage"
                      )}
                    </button>
                  </div>
                )}

              {briefError && (
                <div className="alert alert-danger">{briefError}</div>
              )}

              {/* Brief card */}
              {displayBrief && <BriefCard brief={displayBrief} />}

              {/* Note editor */}
              {note && (
                <NoteEditor
                  note={note}
                  onSign={signNote}
                  signing={consultLoading}
                />
              )}
            </div>

            {/* Right — Clinical actions panel */}
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-4)" }}>
              {/* Generate note card */}
              {displayBrief && !note && (
                <div className="card card-elevated">
                  <div
                    style={{
                      fontSize: "1.5rem",
                      marginBottom: "var(--s-3)",
                      textAlign: "center",
                    }}
                  >
                    📋
                  </div>
                  <h4 style={{ textAlign: "center", marginBottom: "var(--s-2)" }}>
                    Clinical Note
                  </h4>
                  <p
                    style={{
                      fontSize: "0.82rem",
                      color: "var(--text-secondary)",
                      marginBottom: "var(--s-4)",
                      textAlign: "center",
                      lineHeight: 1.55,
                    }}
                  >
                    Generate a pre-filled SOAP note from triage data.
                  </p>
                  {consultError && (
                    <div
                      className="alert alert-danger"
                      style={{ marginBottom: "var(--s-3)", fontSize: "0.8rem" }}
                    >
                      {consultError}
                    </div>
                  )}
                  {!patient.triage_result && (
                    <div
                      className="alert alert-warning"
                      style={{ marginBottom: "var(--s-3)", fontSize: "0.8rem" }}
                    >
                      No triage result linked yet.
                    </div>
                  )}
                  <button
                    className="btn btn-primary"
                    style={{ width: "100%" }}
                    onClick={handleGenerateNote}
                    disabled={consultLoading || !patient.triage_result}
                  >
                    {consultLoading ? (
                      <Spinner label="Drafting note…" />
                    ) : (
                      "Generate SOAP Note"
                    )}
                  </button>
                </div>
              )}

              {/* Quick actions */}
              <div className="card card-elevated">
                <div className="section-label" style={{ marginBottom: "var(--s-3)" }}>
                  Quick Actions
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--s-2)",
                  }}
                >
                  <button
                    className="btn btn-secondary"
                    style={{ justifyContent: "flex-start", gap: "var(--s-3)" }}
                    onClick={() => navigate("/queue")}
                  >
                    <span>≡</span> Back to Queue
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ justifyContent: "flex-start", gap: "var(--s-3)" }}
                    onClick={() => navigate("/intake")}
                  >
                    <span>+</span> New Intake
                  </button>
                </div>
              </div>

              {/* Patient meta card */}
              <div
                className="card"
                style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}
              >
                <div className="section-label" style={{ marginBottom: "var(--s-3)" }}>
                  Patient Details
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--s-2)",
                  }}
                >
                  {patient.date_of_birth && (
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <span style={{ color: "var(--text-muted)" }}>DOB</span>
                      <span>
                        {new Date(patient.date_of_birth).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                  <div
                    style={{ display: "flex", justifyContent: "space-between" }}
                  >
                    <span style={{ color: "var(--text-muted)" }}>Sex</span>
                    <span style={{ textTransform: "capitalize" }}>
                      {patient.sex}
                    </span>
                  </div>
                  {patient.phone_number && (
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <span style={{ color: "var(--text-muted)" }}>Phone</span>
                      <span>{patient.phone_number}</span>
                    </div>
                  )}
                  <div
                    style={{ display: "flex", justifyContent: "space-between" }}
                  >
                    <span style={{ color: "var(--text-muted)" }}>Status</span>
                    <span
                      style={{
                        color: TRIAGE_STATUS_COLORS[patient.triage_status],
                        fontWeight: 600,
                      }}
                    >
                      {TRIAGE_STATUS_LABELS[patient.triage_status]}
                    </span>
                  </div>
                </div>
              </div>

              {/* Reference links */}
              <div className="card" style={{ padding: "var(--s-4)" }}>
                <div className="section-label" style={{ marginBottom: "var(--s-3)" }}>
                  Clinical References
                </div>
                {[
                  { label: "WHO Drug Info", href: "https://www.who.int/medicines" },
                  { label: "UpToDate", href: "https://www.uptodate.com" },
                  { label: "MDCalc Scores", href: "https://www.mdcalc.com" },
                  { label: "NICE Guidelines", href: "https://www.nice.org.uk/guidance" },
                ].map((link) => (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "6px 0",
                      fontSize: "0.8rem",
                      color: "var(--text-secondary)",
                      borderBottom: "1px solid var(--border)",
                      textDecoration: "none",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLAnchorElement).style.color =
                        "var(--accent)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLAnchorElement).style.color =
                        "var(--text-secondary)";
                    }}
                  >
                    {link.label}
                    <span style={{ opacity: 0.4, fontSize: "0.7rem" }}>↗</span>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
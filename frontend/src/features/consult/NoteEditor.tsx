import { useState, useEffect } from "react";
import type { ClinicalNoteResponse } from "../../core/entities/consult";
import { Spinner } from "../../components/ui/Spinner";

interface NoteEditorProps {
  note: ClinicalNoteResponse;
  onSign: (noteId: string, doctorId: string) => Promise<void>;
  signing: boolean;
}

const DOCTOR_ID_STUB = "00000000-0000-0000-0000-000000000001";

const SOAP_SECTIONS = [
  {
    key: "subjective" as const,
    label: "Subjective",
    hint: "Patient-reported symptoms and history",
    icon: "🗣",
    color: "var(--accent)",
  },
  {
    key: "objective" as const,
    label: "Objective",
    hint: "Examination findings and vitals",
    icon: "📊",
    color: "var(--success)",
  },
  {
    key: "assessment" as const,
    label: "Assessment",
    hint: "Clinical impression and diagnosis",
    icon: "🔍",
    color: "var(--warning)",
  },
  {
    key: "plan" as const,
    label: "Plan",
    hint: "Treatment, medications, follow-up",
    icon: "📋",
    color: "var(--urgency-2)",
  },
];

export function NoteEditor({ note, onSign, signing }: NoteEditorProps) {
  const [fields, setFields] = useState({
    subjective: note.subjective,
    objective: note.objective,
    assessment: note.assessment,
    plan: note.plan,
  });

  useEffect(() => {
    setFields({
      subjective: note.subjective,
      objective: note.objective,
      assessment: note.assessment,
      plan: note.plan,
    });
  }, [note]);

  const isReadOnly = note.doctor_signed;

  return (
    <div className="card fade-up">
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "var(--s-6)",
          paddingBottom: "var(--s-4)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div>
          <h3 style={{ fontFamily: "var(--font-display)" }}>SOAP Note</h3>
          <p
            style={{
              fontSize: "0.78rem",
              color: "var(--text-muted)",
              marginTop: 3,
            }}
          >
            {new Date(note.created_at).toLocaleDateString(undefined, {
              weekday: "short",
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </p>
        </div>
        {isReadOnly ? (
          <span className="badge badge-success">
            ✓ Signed
            {note.signed_at
              ? ` · ${new Date(note.signed_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}`
              : ""}
          </span>
        ) : (
          <span className="badge badge-neutral">Draft — unsigned</span>
        )}
      </div>

      {/* SOAP sections */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--s-5)",
        }}
      >
        {SOAP_SECTIONS.map(({ key, label, hint, icon, color }) => (
          <div key={key}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--s-2)",
                marginBottom: "var(--s-2)",
              }}
            >
              <span style={{ fontSize: "0.9rem" }}>{icon}</span>
              <label
                style={{
                  margin: 0,
                  color,
                  fontWeight: 600,
                  fontSize: "0.82rem",
                  letterSpacing: "0.04em",
                }}
              >
                {label}
              </label>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  fontWeight: 400,
                }}
              >
                — {hint}
              </span>
            </div>
            <textarea
              rows={5}
              value={fields[key]}
              onChange={(e) => setFields((f) => ({ ...f, [key]: e.target.value }))}
              disabled={isReadOnly}
              style={{
                borderLeft: `3px solid ${color}`,
                borderRadius: "0 var(--r-md) var(--r-md) 0",
                ...(isReadOnly ? { opacity: 0.6, cursor: "default" } : {}),
              }}
            />
          </div>
        ))}
      </div>

      {/* Sign action */}
      {!isReadOnly && (
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginTop: "var(--s-5)",
            paddingTop: "var(--s-4)",
            borderTop: "1px solid var(--border)",
            gap: "var(--s-3)",
            alignItems: "center",
          }}
        >
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Signing locks this note for the record.
          </p>
          <button
            className="btn btn-primary"
            disabled={signing}
            onClick={() => onSign(note.id, DOCTOR_ID_STUB)}
          >
            {signing ? (
              <Spinner label="Signing…" />
            ) : (
              "Sign & Finalise Note"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
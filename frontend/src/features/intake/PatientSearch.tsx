import { useState, useRef, useEffect } from "react";
import { usePatientSearch } from "../../hooks/useIntake";
import type { PatientSummary } from "../../core/entities/patient";
import { TRIAGE_STATUS_LABELS, TRIAGE_STATUS_COLORS } from "../../core/constants/urgency";

export type SelectionState = "idle" | "searching" | "selected" | "new_patient";

interface PatientSearchProps {
  onSelect: (patient: PatientSummary) => void;
  onNewPatient: () => void;
  selectedPatient: PatientSummary | null;
  onClear: () => void;
}

export function PatientSearch({
  onSelect,
  onNewPatient,
  selectedPatient,
  onClear,
}: PatientSearchProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const { results, searching, search, clear } = usePatientSearch();
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    search(query);
    setOpen(query.length > 0);
  }, [query, search]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = (patient: PatientSummary) => {
    onSelect(patient);
    setQuery("");
    clear();
    setOpen(false);
  };

  const handleNewPatient = () => {
    setQuery("");
    clear();
    setOpen(false);
    onNewPatient();
  };

  // ── Selected state ─────────────────────────────────────────────────────────
  if (selectedPatient) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
          background: "var(--accent-dim)",
          border: "1px solid rgba(79,142,247,0.3)",
          borderRadius: "var(--r-md)",
        }}
      >
        <span style={{ fontSize: "1rem" }}>👤</span>
        <div style={{ flex: 1 }}>
          <p style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.9rem" }}>
            {selectedPatient.full_name}
          </p>
          <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            {selectedPatient.date_of_birth
              ? new Date(selectedPatient.date_of_birth).toLocaleDateString()
              : ""}
            {selectedPatient.phone_number ? ` · ${selectedPatient.phone_number}` : ""}
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onClear}>
          Change
        </button>
      </div>
    );
  }

  // ── Search input + dropdown ────────────────────────────────────────────────
  return (
    <div ref={wrapperRef} style={{ position: "relative" }}>
      <div className="field">
        <label>Find existing patient</label>
        <div style={{ position: "relative" }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or phone number…"
            autoComplete="off"
          />
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

      {/* Dropdown */}
      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            zIndex: 200,
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--r-md)",
            boxShadow: "var(--shadow-lg)",
            maxHeight: 280,
            overflowY: "auto",
            marginTop: -8,
          }}
        >
          {results.length === 0 && !searching && query.length > 1 && (
            <div
              style={{
                padding: "var(--s-3) var(--s-4)",
                fontSize: "0.875rem",
                color: "var(--text-muted)",
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
                gap: 10,
                width: "100%",
                padding: "10px 14px",
                background: "transparent",
                border: "none",
                borderBottom: "1px solid var(--border)",
                cursor: "pointer",
                textAlign: "left",
                transition: "background 0.1s",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--bg-overlay)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
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
                <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                  {patient.date_of_birth
                    ? new Date(patient.date_of_birth).toLocaleDateString()
                    : ""}
                  {patient.phone_number ? ` · ${patient.phone_number}` : ""}
                </p>
              </div>
              <span
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  padding: "2px 7px",
                  borderRadius: 100,
                  background: "var(--bg-base)",
                  color: TRIAGE_STATUS_COLORS[patient.triage_status],
                  border: "1px solid currentColor",
                  whiteSpace: "nowrap",
                }}
              >
                {TRIAGE_STATUS_LABELS[patient.triage_status]}
              </span>
            </button>
          ))}

          {/* New patient option always shown at bottom */}
          <button
            type="button"
            onClick={handleNewPatient}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              width: "100%",
              padding: "10px 14px",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: "var(--accent)",
              fontSize: "0.875rem",
              fontWeight: 500,
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "var(--accent-dim)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "transparent")
            }
          >
            <span style={{ fontSize: "1rem" }}>+</span>
            Register as new patient
          </button>
        </div>
      )}
    </div>
  );
}
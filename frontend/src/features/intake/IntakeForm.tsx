import { useState, useEffect, useRef } from "react";
import { TagInput } from "./TagInput";
import { usePatientSearch } from "../../hooks/useIntake";
import { TRIAGE_STATUS_LABELS, TRIAGE_STATUS_COLORS } from "../../core/constants/urgency";
import type {
  IntakeRequest,
  PatientSummary,
  Sex,
  VitalsInput,
} from "../../core/entities/patient";
import { computeAge } from "../../core/entities/patient";

type PatientMode = "new_patient" | "picking" | "selected";

interface IntakeFormProps {
  onSubmit: (payload: IntakeRequest) => void;
  submitting: boolean;
  error: string | null;
}

/* ── Inline patient picker panel ───────────────────────────────────────────── */
function PatientPicker({ onSelect, onCancel }: {
  onSelect: (p: PatientSummary) => void;
  onCancel: () => void;
}) {
  const [query, setQuery] = useState("");
  const { results, searching, search } = usePatientSearch();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Load all patients on mount (empty query = browse all)
    search("");
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    search(query);
  }, [query]);

  return (
    <div
      className="card card-elevated fade-up"
      style={{ padding: "var(--s-5)" }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "var(--s-4)",
        }}
      >
        <div>
          <h4 style={{ color: "var(--text-primary)", marginBottom: 2 }}>
            Select Existing Patient
          </h4>
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Search by name or phone number
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onCancel}>
          ✕ Cancel
        </button>
      </div>

      {/* Search input */}
      <div className="field" style={{ marginBottom: "var(--s-3)", position: "relative" }}>
        <div style={{ position: "relative" }}>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or phone…"
            autoComplete="off"
            style={{ paddingLeft: 38 }}
          />
          <svg
            style={{
              position: "absolute",
              left: 11,
              top: "50%",
              transform: "translateY(-50%)",
              opacity: 0.35,
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

      {/* Results list */}
      <div
        style={{
          maxHeight: 320,
          overflowY: "auto",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-md)",
          background: "var(--bg-base)",
        }}
      >
        {!searching && results.length === 0 && (
          <div
            style={{
              padding: "var(--s-8)",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "0.875rem",
            }}
          >
            {query.length > 0
              ? `No patients found for "${query}"`
              : "No patients registered yet"}
          </div>
        )}

        {results.map((patient, idx) => (
          <button
            key={patient.id}
            type="button"
            onClick={() => onSelect(patient)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              width: "100%",
              padding: "11px 14px",
              background: "transparent",
              border: "none",
              borderBottom:
                idx < results.length - 1
                  ? "1px solid var(--border)"
                  : "none",
              cursor: "pointer",
              textAlign: "left",
              transition: "background 0.1s",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.background =
                "var(--bg-elevated)")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.background = "transparent")
            }
          >
            {/* Avatar */}
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                background: "var(--bg-overlay)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1rem",
                flexShrink: 0,
                border: "1px solid var(--border-strong)",
              }}
            >
              {patient.sex === "female" ? "👩" : "👨"}
            </div>

            {/* Name + meta */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <p
                style={{
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  fontSize: "0.9rem",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {patient.full_name}
              </p>
              <p
                style={{
                  fontSize: "0.72rem",
                  color: "var(--text-secondary)",
                  marginTop: 2,
                }}
              >
                {patient.date_of_birth
                  ? new Date(patient.date_of_birth).toLocaleDateString()
                  : ""}
                {patient.phone_number ? ` · ${patient.phone_number}` : ""}
                {patient.date_of_birth
                  ? ` · Age ${computeAge(patient.date_of_birth)}`
                  : ""}
              </p>
            </div>

            {/* Status badge */}
            <span
              style={{
                fontSize: "0.66rem",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: 100,
                border: "1px solid currentColor",
                color: TRIAGE_STATUS_COLORS[patient.triage_status],
                whiteSpace: "nowrap",
                flexShrink: 0,
              }}
            >
              {TRIAGE_STATUS_LABELS[patient.triage_status]}
            </span>

            {/* Select chevron */}
            <span
              style={{
                color: "var(--text-muted)",
                fontSize: "0.9rem",
                flexShrink: 0,
                marginLeft: 4,
              }}
            >
              →
            </span>
          </button>
        ))}
      </div>

      {results.length > 0 && (
        <p
          style={{
            fontSize: "0.72rem",
            color: "var(--text-muted)",
            marginTop: "var(--s-2)",
            textAlign: "right",
          }}
        >
          {results.length} patient{results.length !== 1 ? "s" : ""} shown
        </p>
      )}
    </div>
  );
}

/* ── Main form ──────────────────────────────────────────────────────────────── */
export function IntakeForm({ onSubmit, submitting, error }: IntakeFormProps) {
  const [mode, setMode] = useState<PatientMode>("new_patient");
  const [selectedPatient, setSelectedPatient] = useState<PatientSummary | null>(null);

  // New patient fields
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [dob, setDob] = useState("");
  const [phone, setPhone] = useState("");
  const [sex, setSex] = useState<Sex>("male");

  // Clinical fields
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [durationHours, setDurationHours] = useState("");
  const [medications, setMedications] = useState<string[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [additionalHistory, setAdditionalHistory] = useState("");

  // Vitals
  const [pulseBpm, setPulseBpm] = useState("");
  const [systolicBp, setSystolicBp] = useState("");
  const [diastolicBp, setDiastolicBp] = useState("");
  const [spo2, setSpo2] = useState("");
  const [tempC, setTempC] = useState("");

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (mode === "new_patient") {
      if (firstName.trim().length < 2) e.firstName = "Min 2 characters";
      if (lastName.trim().length < 2) e.lastName = "Min 2 characters";
      if (!dob) e.dob = "Date of birth is required";
      else if (computeAge(dob) <= 0) e.dob = "Date of birth must be in the past";
    }
    if (chiefComplaint.trim().length < 10)
      e.chiefComplaint = "Please describe the complaint (min 10 characters)";
    if (!durationHours || parseInt(durationHours) < 1)
      e.durationHours = "Must be at least 1 hour";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = () => {
    if (!validate()) return;

    const vitals: VitalsInput = {};
    if (pulseBpm)    vitals.pulse_bpm          = Number(pulseBpm);
    if (systolicBp)  vitals.systolic_bp         = Number(systolicBp);
    if (diastolicBp) vitals.diastolic_bp        = Number(diastolicBp);
    if (spo2)        vitals.oxygen_saturation   = Number(spo2);
    if (tempC)       vitals.temperature_celsius = Number(tempC);

    const age =
      mode === "selected" && selectedPatient
        ? computeAge(selectedPatient.date_of_birth)
        : computeAge(dob);

    const payload: IntakeRequest = {
      age,
      sex,
      chief_complaint: chiefComplaint,
      symptom_duration_hours: Number(durationHours),
      current_medications: medications,
      allergies,
      additional_history: additionalHistory || undefined,
      ...(Object.keys(vitals).length > 0 ? { vitals } : {}),
      ...(mode === "selected" && selectedPatient
        ? { patient_id: selectedPatient.id }
        : {
            patient_id: null,
            first_name: firstName,
            last_name: lastName,
            date_of_birth: dob,
            phone_number: phone || undefined,
          }),
    };

    onSubmit(payload);
  };

  const handlePatientSelected = (patient: PatientSummary) => {
    setSelectedPatient(patient);
    setSex(patient.sex);
    setMode("selected");
    setErrors({});
  };

  const resetAll = () => {
    setMode("new_patient");
    setSelectedPatient(null);
    setFirstName(""); setLastName(""); setDob(""); setPhone("");
    setSex("male");
    setChiefComplaint(""); setDurationHours("");
    setMedications([]); setAllergies([]);
    setAdditionalHistory("");
    setPulseBpm(""); setSystolicBp(""); setDiastolicBp("");
    setSpo2(""); setTempC("");
    setErrors({});
  };

  const dobAge = dob && computeAge(dob) > 0 ? computeAge(dob) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-5)", maxWidth: 800 }}>

      {/* ── Mode tab switcher ─────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          gap: 2,
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-lg)",
          padding: 4,
          width: "fit-content",
        }}
      >
        <button
          type="button"
          className={`btn btn-sm${mode === "new_patient" ? " btn-primary" : " btn-ghost"}`}
          onClick={() => {
            setSelectedPatient(null);
            setMode("new_patient");
          }}
        >
          + New Patient
        </button>
        <button
          type="button"
          className={`btn btn-sm${mode === "picking" || mode === "selected" ? " btn-primary" : " btn-ghost"}`}
          onClick={() => {
            if (mode !== "selected") setMode("picking");
          }}
        >
          {mode === "selected" && selectedPatient
            ? `👤 ${selectedPatient.full_name}`
            : "Select Existing Patient"}
        </button>
        {mode === "selected" && selectedPatient && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setMode("picking")}
            title="Change patient"
            style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}
          >
            Change
          </button>
        )}
      </div>

      {/* ── Inline patient picker ─────────────────────────────────────────── */}
      {mode === "picking" && (
        <PatientPicker
          onSelect={handlePatientSelected}
          onCancel={() => setMode(selectedPatient ? "selected" : "new_patient")}
        />
      )}

      {/* ── Clinical form (hidden while picker is open) ───────────────────── */}
      {mode !== "picking" && (
        <div className="card card-elevated">

          {/* New patient registration fields */}
          {mode === "new_patient" && (
            <>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "3px 10px",
                  background: "var(--accent-dim)",
                  borderRadius: "var(--r-sm)",
                  marginBottom: "var(--s-5)",
                  fontSize: "0.76rem",
                  color: "var(--accent)",
                  fontWeight: 500,
                }}
              >
                <span>+</span> New Patient Registration
              </div>

              <div className="grid-2">
                <div className="field">
                  <label>First Name</label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="e.g. Emeka"
                    autoFocus
                  />
                  {errors.firstName && <p className="field-error">{errors.firstName}</p>}
                </div>
                <div className="field">
                  <label>Last Name</label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="e.g. Okafor"
                  />
                  {errors.lastName && <p className="field-error">{errors.lastName}</p>}
                </div>
              </div>

              <div className="grid-2">
                <div className="field">
                  <label>Date of Birth</label>
                  <input
                    type="date"
                    value={dob}
                    max={new Date().toISOString().split("T")[0]}
                    onChange={(e) => setDob(e.target.value)}
                  />
                  {errors.dob && <p className="field-error">{errors.dob}</p>}
                  {dobAge !== null && (
                    <p className="field-hint">
                      Age:{" "}
                      <strong style={{ color: "var(--text-primary)" }}>
                        {dobAge} years
                      </strong>
                    </p>
                  )}
                </div>
                <div className="field">
                  <label>Phone Number (optional)</label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+234 801 234 5678"
                  />
                </div>
              </div>

              <hr className="divider" />
            </>
          )}

          {/* Selected patient banner */}
          {mode === "selected" && selectedPatient && (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 14px",
                  background: "var(--accent-dim)",
                  border: "1px solid var(--border-accent)",
                  borderRadius: "var(--r-md)",
                  marginBottom: "var(--s-5)",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    background: "var(--bg-overlay)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "1rem",
                    flexShrink: 0,
                  }}
                >
                  {selectedPatient.sex === "female" ? "👩" : "👨"}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.92rem" }}>
                    {selectedPatient.full_name}
                  </p>
                  <p style={{ fontSize: "0.74rem", color: "var(--text-secondary)", marginTop: 2 }}>
                    {selectedPatient.date_of_birth
                      ? `DOB: ${new Date(selectedPatient.date_of_birth).toLocaleDateString()} · Age ${computeAge(selectedPatient.date_of_birth)}`
                      : ""}
                    {selectedPatient.phone_number ? ` · ${selectedPatient.phone_number}` : ""}
                  </p>
                </div>
                <button
                  className="btn btn-ghost btn-sm"
                  type="button"
                  onClick={() => setMode("picking")}
                >
                  Change patient
                </button>
              </div>
              <hr className="divider" />
            </>
          )}

          {/* Biological sex */}
          <div className="field" style={{ maxWidth: 220 }}>
            <label>Biological Sex</label>
            <select value={sex} onChange={(e) => setSex(e.target.value as Sex)}>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Presentation */}
          <div className="section-label" style={{ marginBottom: "var(--s-4)", marginTop: "var(--s-2)" }}>
            Presentation
          </div>

          <div className="field">
            <label>Chief Complaint</label>
            <textarea
              rows={3}
              value={chiefComplaint}
              onChange={(e) => setChiefComplaint(e.target.value)}
              placeholder="Describe the primary complaint in the patient's own words…"
            />
            {errors.chiefComplaint && <p className="field-error">{errors.chiefComplaint}</p>}
          </div>

          <div style={{ maxWidth: 260 }}>
            <div className="field">
              <label>Symptom Duration (hours)</label>
              <input
                type="number"
                min={1}
                value={durationHours}
                onChange={(e) => setDurationHours(e.target.value)}
                placeholder="e.g. 6"
              />
              {errors.durationHours && <p className="field-error">{errors.durationHours}</p>}
            </div>
          </div>

          {/* Medical history */}
          <div className="section-label" style={{ marginBottom: "var(--s-4)", marginTop: "var(--s-2)" }}>
            Medical History
          </div>

          <TagInput
            label="Current Medications"
            value={medications}
            onChange={setMedications}
            placeholder="Type medication name and press Enter…"
          />

          <TagInput
            label="Allergies"
            value={allergies}
            onChange={setAllergies}
            placeholder="Type allergen and press Enter…"
            variant="danger"
          />

          <div className="field">
            <label>Additional History</label>
            <textarea
              rows={3}
              value={additionalHistory}
              onChange={(e) => setAdditionalHistory(e.target.value)}
              placeholder="PMH, surgical history, social history, relevant context…"
            />
          </div>

          {/* Vitals */}
          <div className="section-label" style={{ marginBottom: "var(--s-4)", marginTop: "var(--s-2)" }}>
            Vitals{" "}
            <span
              style={{
                fontWeight: 400,
                fontSize: "0.72rem",
                color: "var(--text-muted)",
                textTransform: "none",
                letterSpacing: 0,
              }}
            >
              — optional
            </span>
          </div>

          <div className="grid-3" style={{ gap: "var(--s-3)" }}>
            {[
              { label: "Pulse (bpm)",  val: pulseBpm,    set: setPulseBpm,    placeholder: "72" },
              { label: "Systolic BP",  val: systolicBp,  set: setSystolicBp,  placeholder: "120" },
              { label: "Diastolic BP", val: diastolicBp, set: setDiastolicBp, placeholder: "80" },
              { label: "SpO₂ (%)",     val: spo2,        set: setSpo2,        placeholder: "98" },
              { label: "Temp (°C)",    val: tempC,       set: setTempC,       placeholder: "37.2", step: "0.1" },
            ].map(({ label, val, set, placeholder, step }) => (
              <div className="field" key={label} style={{ marginBottom: 0 }}>
                <label>{label}</label>
                <input
                  type="number"
                  step={step}
                  value={val}
                  onChange={(e) => set(e.target.value)}
                  placeholder={placeholder}
                />
              </div>
            ))}
          </div>

          {error && (
            <div className="alert alert-danger" style={{ marginTop: "var(--s-5)" }}>
              {error}
            </div>
          )}

          {/* Footer actions */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: "var(--s-6)",
              paddingTop: "var(--s-4)",
              borderTop: "1px solid var(--border)",
            }}
          >
            <button className="btn btn-ghost btn-sm" type="button" onClick={resetAll}>
              Reset form
            </button>
            <button
              className="btn btn-primary btn-lg"
              onClick={handleSubmit}
              disabled={submitting}
              type="button"
            >
              {submitting ? (
                <>
                  <span className="spinner" />
                  Analysing presentation…
                </>
              ) : (
                "Submit & Triage →"
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
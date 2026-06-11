import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { PageShell } from "../components/shared/PageShell";
import { Spinner } from "../components/ui/Spinner";
import { PatientCardSkeleton } from "../components/ui/Skeleton";
import { usePatientList } from "../hooks/useIntake";
import {
  TRIAGE_STATUS_LABELS,
  TRIAGE_STATUS_COLORS,
} from "../core/constants/urgency";
import type { PatientDetail } from "../core/entities/patient";
import { timeAgo } from "../core/entities/patient";

type SortKey = "name" | "urgency" | "status" | "arrived";
type SortDir = "asc" | "desc";

function UrgencyPip({ level }: { level: 1 | 2 | 3 | 4 | 5 }) {
  const labels = ["", "Routine", "Low", "Moderate", "High", "Critical"];
  return (
    <span className={`badge badge-urgency-${level}`}>
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: "currentColor",
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      {labels[level]}
    </span>
  );
}

function SortArrow({
  col,
  active,
  dir,
}: {
  col: SortKey;
  active: SortKey;
  dir: SortDir;
}) {
  const isActive = col === active;
  return (
    <span className={`sort-arrow${isActive ? " active" : ""}`}>
      {isActive ? (dir === "asc" ? " ↑" : " ↓") : " ↕"}
    </span>
  );
}

function StatTile({
  value,
  label,
  accent,
}: {
  value: number | string;
  label: string;
  accent?: string;
}) {
  return (
    <div className="stat-tile">
      <div
        className="stat-value"
        style={{ color: accent || "var(--text-primary)" }}
      >
        {value}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default function QueuePage() {
  const { data, loading, error, page, goToPage, refetch } = usePatientList();
  const navigate = useNavigate();

  const [sortKey, setSortKey] = useState<SortKey>("arrived");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => { refetch(); }, []);

  const handleOpen = (patientId: string) => {
    navigate("/consult", { state: { patientId } });
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const patients = data?.patients ?? [];

  const filtered = useMemo(() => {
    if (statusFilter === "all") return patients;
    return patients.filter((p) => p.triage_status === statusFilter);
  }, [patients, statusFilter]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "name") {
        cmp = a.full_name.localeCompare(b.full_name);
      } else if (sortKey === "urgency") {
        const la = a.triage_result?.urgency.level ?? 0;
        const lb = b.triage_result?.urgency.level ?? 0;
        cmp = la - lb;
      } else if (sortKey === "status") {
        cmp = a.triage_status.localeCompare(b.triage_status);
      } else {
        cmp =
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = data?.total_pages ?? 1;
  const totalPatients = data?.total ?? 0;

  // Stats derived from current page data
  const critical = patients.filter(
    (p) => p.triage_result?.urgency.level === 5
  ).length;
  const highUrgency = patients.filter(
    (p) => (p.triage_result?.urgency.level ?? 0) >= 4
  ).length;
  const pending = patients.filter((p) => p.triage_status === "pending").length;

  const statusOptions = [
    "all",
    "pending",
    "triaged",
    "in_consultation",
    "documented",
    "referred",
    "discharged",
  ];

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
            <div className="eyebrow">Nurse / Doctor</div>
            <h1>Patient Queue</h1>
            <p>Active patients — click any row to open consultation.</p>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={refetch}
            disabled={loading}
            style={{ marginTop: 4 }}
          >
            {loading ? <Spinner /> : "↻ Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "var(--s-5)" }}>
          {error}
        </div>
      )}

      {/* ── Stat tiles ─────────────────────────────────────────────────── */}
      {!loading && data && (
        <div
          className="grid-3"
          style={{ marginBottom: "var(--s-6)", maxWidth: 600 }}
        >
          <StatTile value={totalPatients} label="Total patients" />
          <StatTile
            value={highUrgency}
            label="High / critical"
            accent={highUrgency > 0 ? "var(--urgency-4)" : undefined}
          />
          <StatTile
            value={pending}
            label="Awaiting triage"
            accent={pending > 0 ? "var(--warning)" : undefined}
          />
        </div>
      )}

      {/* ── Filters ───────────────────────────────────────────────────── */}
      {data && patients.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: "var(--s-2)",
            flexWrap: "wrap",
            marginBottom: "var(--s-4)",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: "0.76rem",
              color: "var(--text-muted)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              marginRight: "var(--s-1)",
            }}
          >
            Filter:
          </span>
          {statusOptions.map((s) => (
            <button
              key={s}
              className={`btn btn-sm${statusFilter === s ? " btn-primary" : " btn-secondary"}`}
              onClick={() => setStatusFilter(s)}
              style={{ textTransform: "capitalize", padding: "4px 12px" }}
            >
              {s === "all" ? "All" : TRIAGE_STATUS_LABELS[s as keyof typeof TRIAGE_STATUS_LABELS] ?? s}
            </button>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && !data && (
        <div
          style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}
        >
          {[1, 2, 3, 4].map((i) => (
            <PatientCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && data && patients.length === 0 && (
        <div className="empty-state">
          <div style={{ fontSize: "2.5rem", marginBottom: "var(--s-4)" }}>🏥</div>
          <p>No active patients in the queue.</p>
          <button
            className="btn btn-primary"
            style={{ marginTop: "var(--s-4)" }}
            onClick={() => navigate("/intake")}
          >
            + Register first patient
          </button>
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────────────── */}
      {sorted.length > 0 && (
        <div
          className="card"
          style={{ padding: 0, overflow: "hidden", marginBottom: "var(--s-6)" }}
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th
                    onClick={() => toggleSort("name")}
                    style={{ paddingLeft: "var(--s-4)", minWidth: 180 }}
                  >
                    Patient
                    <SortArrow col="name" active={sortKey} dir={sortDir} />
                  </th>
                  <th style={{ minWidth: 100 }}>DOB</th>
                  <th
                    onClick={() => toggleSort("urgency")}
                    style={{ minWidth: 120 }}
                  >
                    Urgency
                    <SortArrow col="urgency" active={sortKey} dir={sortDir} />
                  </th>
                  <th
                    onClick={() => toggleSort("status")}
                    style={{ minWidth: 130 }}
                  >
                    Status
                    <SortArrow col="status" active={sortKey} dir={sortDir} />
                  </th>
                  <th style={{ minWidth: 160 }}>Top differential</th>
                  <th
                    onClick={() => toggleSort("arrived")}
                    style={{ minWidth: 100 }}
                  >
                    Arrived
                    <SortArrow col="arrived" active={sortKey} dir={sortDir} />
                  </th>
                  <th style={{ width: 48 }} />
                </tr>
              </thead>
              <tbody>
                {sorted.map((patient) => {
                  const urgency = patient.triage_result?.urgency;
                  const level = urgency?.level ?? 0;
                  return (
                    <tr
                      key={patient.id}
                      className={`patient-row${level >= 4 ? ` urgency-${level}` : ""}`}
                      onClick={() => handleOpen(patient.id)}
                    >
                      <td style={{ paddingLeft: "var(--s-4)" }}>
                        <div
                          style={{
                            fontWeight: 600,
                            color: "var(--text-primary)",
                            fontSize: "0.9rem",
                          }}
                        >
                          {patient.full_name}
                        </div>
                        {patient.phone_number && (
                          <div
                            style={{
                              fontSize: "0.72rem",
                              color: "var(--text-muted)",
                              marginTop: 1,
                            }}
                          >
                            {patient.phone_number}
                          </div>
                        )}
                      </td>
                      <td style={{ fontSize: "0.82rem" }}>
                        {patient.date_of_birth
                          ? new Date(patient.date_of_birth).toLocaleDateString()
                          : "—"}
                      </td>
                      <td>
                        {urgency ? (
                          <UrgencyPip level={urgency.level} />
                        ) : (
                          <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                            —
                          </span>
                        )}
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: "0.72rem",
                            fontWeight: 600,
                            padding: "2px 9px",
                            borderRadius: 100,
                            border: "1px solid currentColor",
                            color: TRIAGE_STATUS_COLORS[patient.triage_status],
                            whiteSpace: "nowrap",
                          }}
                        >
                          {patient.triage_status === "pending" && (
                            <span className="pulse" style={{ marginRight: 4 }}>
                              ●
                            </span>
                          )}
                          {TRIAGE_STATUS_LABELS[patient.triage_status]}
                        </span>
                      </td>
                      <td style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                        {patient.triage_result?.top_differentials?.[0] ?? "—"}
                      </td>
                      <td
                        style={{
                          fontSize: "0.78rem",
                          color: "var(--text-muted)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {timeAgo(patient.created_at)}
                      </td>
                      <td>
                        <button
                          className="btn btn-ghost btn-sm btn-icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpen(patient.id);
                          }}
                          title="Open consultation"
                        >
                          →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Red flag chips row at bottom if critical patients */}
          {critical > 0 && (
            <div
              style={{
                padding: "var(--s-3) var(--s-4)",
                borderTop: "1px solid var(--border)",
                background: "rgba(212,58,58,0.05)",
                display: "flex",
                alignItems: "center",
                gap: "var(--s-2)",
                fontSize: "0.78rem",
                color: "var(--urgency-5)",
              }}
            >
              <span>🚨</span>
              <strong>{critical}</strong> critical patient{critical > 1 ? "s" : ""}{" "}
              require immediate attention
            </div>
          )}
        </div>
      )}

      {/* Pagination — only shown when backend has multiple pages AND > 1 page */}
      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--s-3)",
            justifyContent: "center",
            marginTop: "var(--s-2)",
          }}
        >
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => goToPage(page - 1)}
            disabled={page === 1 || loading}
          >
            ← Previous
          </button>
          <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            Page {page} of {totalPages}
            <span style={{ color: "var(--text-muted)", marginLeft: 8 }}>
              ({totalPatients} patients)
            </span>
          </span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => goToPage(page + 1)}
            disabled={page === totalPages || loading}
          >
            Next →
          </button>
        </div>
      )}
    </PageShell>
  );
}
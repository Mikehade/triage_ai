import { PageShell } from "../components/shared/PageShell";
import { Spinner } from "../components/ui/Spinner";
import { useEvaluation } from "../hooks/useEvaluation";
import { EVAL_SCORE_THRESHOLD } from "../core/constants/urgency";

export default function EvalPage() {
  const { result, loading, error, runEval } = useEvaluation();

  return (
    <PageShell>
      <div className="page-header">
        <div className="eyebrow">Admin</div>
        <h1>Evaluation Dashboard</h1>
        <p>LLM-as-Judge scoring of recent triage traces. Triggers prompt improvement if rolling average falls below {EVAL_SCORE_THRESHOLD}.</p>
      </div>

      <div style={{ marginBottom: "var(--s-6)", display: "flex", gap: "var(--s-3)", alignItems: "center" }}>
        <button className="btn btn-primary" onClick={() => runEval(24)} disabled={loading}>
          {loading ? <Spinner label="Running evaluation…" /> : "Run Evaluation (24h)"}
        </button>
        <button className="btn btn-secondary" onClick={() => runEval(72)} disabled={loading}>
          72h window
        </button>
      </div>

      {error && <div className="alert alert-danger" style={{ marginBottom: "var(--s-4)" }}>{error}</div>}

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-6)" }}>
          {/* Score overview */}
          <div className="grid-3">
            <div className="card card-elevated" style={{ textAlign: "center" }}>
              <p style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: "var(--s-2)" }}>
                Rolling Avg Score
              </p>
              <p style={{
                fontSize: "2.5rem",
                fontFamily: "var(--font-display)",
                color: result.rolling_avg_score >= EVAL_SCORE_THRESHOLD ? "var(--success)" : "var(--danger)",
              }}>
                {result.rolling_avg_score.toFixed(1)}
                <span style={{ fontSize: "1rem", color: "var(--text-muted)" }}>/10</span>
              </p>
            </div>

            <div className="card card-elevated" style={{ textAlign: "center" }}>
              <p style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: "var(--s-2)" }}>
                Spans Evaluated
              </p>
              <p style={{ fontSize: "2.5rem", fontFamily: "var(--font-display)", color: "var(--text-primary)" }}>
                {result.scores.length}
              </p>
            </div>

            <div className="card card-elevated" style={{ textAlign: "center" }}>
              <p style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: "var(--s-2)" }}>
                Prompt Status
              </p>
              <div style={{ paddingTop: "var(--s-2)" }}>
                {result.improvement_triggered ? (
                  <span className="badge badge-success">Improved</span>
                ) : (
                  <span className="badge badge-neutral">No Change</span>
                )}
              </div>
            </div>
          </div>

          {/* Failure patterns */}
          {result.failure_patterns.length > 0 && (
            <div className="card">
              <h3 style={{ fontFamily: "var(--font-display)", marginBottom: "var(--s-5)" }}>Failure Patterns</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-4)" }}>
                {result.failure_patterns.map((fp) => (
                  <div key={fp.pattern_id} style={{ padding: "var(--s-4)", background: "var(--bg-elevated)", borderRadius: "var(--r-md)", borderLeft: "3px solid var(--urgency-3)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--s-2)" }}>
                      <strong style={{ fontSize: "0.875rem", color: "var(--text-primary)" }}>{fp.description}</strong>
                      <span className="badge badge-neutral">{fp.affected_span_count} spans</span>
                    </div>
                    <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                      <strong style={{ color: "var(--text-muted)" }}>Fix: </strong>
                      {fp.suggested_fix}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Score table */}
          <div className="card" style={{ padding: 0 }}>
            <div style={{ padding: "var(--s-5) var(--s-6)", borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ fontFamily: "var(--font-display)" }}>Score Detail</h3>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Span ID</th>
                    <th>Relevance</th>
                    <th>Completeness</th>
                    <th>Ranking</th>
                    <th>Safety</th>
                    <th>Composite</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.scores.map((s) => (
                    <tr key={s.span_id}>
                      <td>
                        <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                          {s.span_id.slice(0, 10)}…
                        </code>
                      </td>
                      <td>{s.relevance.toFixed(1)}</td>
                      <td>{s.completeness.toFixed(1)}</td>
                      <td>{s.ranking.toFixed(1)}</td>
                      <td>{s.safety.toFixed(1)}</td>
                      <td style={{ fontWeight: 600, color: s.below_threshold ? "var(--danger)" : "var(--success)" }}>
                        {s.composite.toFixed(1)}
                      </td>
                      <td>
                        {s.below_threshold ? (
                          <span className="badge badge-urgency-5">Below</span>
                        ) : (
                          <span className="badge badge-success">Pass</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Improved prompt */}
          {result.improvement && (
            <div className="card">
              <h3 style={{ fontFamily: "var(--font-display)", marginBottom: "var(--s-4)" }}>
                New Prompt Version
              </h3>
              <pre style={{
                background: "var(--bg-base)",
                border: "1px solid var(--border)",
                borderRadius: "var(--r-md)",
                padding: "var(--s-4)",
                fontSize: "0.8rem",
                fontFamily: "var(--font-mono)",
                color: "var(--text-secondary)",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                lineHeight: 1.6,
              }}>
                {result.improvement.new_version_content}
              </pre>
            </div>
          )}
        </div>
      )}
    </PageShell>
  );
}
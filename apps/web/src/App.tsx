import { useEffect, useMemo, useState } from "react";

type ToolReceipt = {
  sequence: number;
  tool: string;
  status: string;
  reason_code: string;
  duration_ms: number;
  retry_of?: number | null;
};

type TaskState = {
  task_id: string;
  fixture_id: string;
  status: "accepted" | "queued" | "running" | "completed" | "blocked" | "failed";
  current_step: string;
  ready_for_human_review?: boolean;
  ready_for_submission?: boolean;
  submission_executed?: boolean;
  high_risk_actions_locked?: boolean;
  blocking_reason_codes?: string[];
  cloud_execution_id?: string | null;
  bundle_url?: string | null;
  provider?: Record<string, unknown>;
  tool_receipts?: ToolReceipt[];
  evidence_summary?: {
    requirement_count: number;
    evidence_count: number;
    matched_count: number;
    missing_items: Array<{ description?: string; reason_code?: string }>;
  };
  validation_summary?: {
    passed_count: number;
    failed: Array<{ code?: string; severity?: string; message?: string }>;
  };
  artifacts?: string[];
};

const terminal = new Set(["completed", "blocked", "failed"]);

const routeStages = [
  "Event intake",
  "ADK routing",
  "Evidence analysis",
  "Deterministic gates",
  "Controlled delivery"
];

function StatusMark({ value }: { value: string }) {
  return <span className={`status status-${value}`}>{value.replaceAll("_", " ")}</span>;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function App() {
  const [task, setTask] = useState<TaskState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"evidence" | "validation" | "artifacts">("evidence");

  useEffect(() => {
    if (!task || terminal.has(task.status)) return;
    const timer = window.setInterval(async () => {
      const response = await fetch(`/api/v1/tasks/${task.task_id}`);
      if (response.ok) setTask(await response.json());
    }, 2000);
    return () => window.clearInterval(timer);
  }, [task]);

  const modelLabel = useMemo(() => {
    const provider = task?.provider;
    if (!provider) return "Pending execution";
    return String(provider.model_version || provider.configured_model || "Recorded in receipt");
  }, [task]);

  async function launch(fixtureId: string) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/v1/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fixture_id: fixtureId })
      });
      if (!response.ok) throw new Error("The demo task could not be accepted.");
      const accepted = await response.json();
      const state = await fetch(accepted.status_url);
      setTask(await state.json());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unexpected request failure");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <nav className="nav" aria-label="Primary navigation">
        <button className="brand" onClick={() => setTask(null)} aria-label="ProofBid home">
          <span className="brand-mark">PB</span>
          <span>ProofBid</span>
        </button>
        <span className="nav-note">Evidence-driven autonomous tender agent</span>
        <span className="safety-chip">High-risk actions locked</span>
      </nav>

      {!task ? (
        <>
          <section className="hero">
            <div className="eyebrow">Taskmaster workflow · Google ADK + Gemini</div>
            <h1>From tender event to a reviewable delivery package.</h1>
            <p>
              ProofBid autonomously routes a bounded professional workflow, binds every claim to
              evidence, validates every artifact, and refuses to fabricate missing authority.
            </p>
            <div className="hero-proof" aria-label="Workflow proof points">
              <Metric label="Interaction" value="One event" />
              <Metric label="Execution" value="Background" />
              <Metric label="Delivery" value="Word · Excel · ZIP" />
            </div>
          </section>

          <section className="case-section" aria-labelledby="cases-title">
            <div className="section-heading">
              <div>
                <span className="kicker">Synthetic, public-safe fixtures</span>
                <h2 id="cases-title">Choose the evidence condition</h2>
              </div>
              <p>No arbitrary upload. No customer data. No submission action.</p>
            </div>
            <div className="case-grid">
              <article className="case-card case-complete">
                <div className="case-index">01</div>
                <StatusMark value="complete evidence" />
                <h3>Complete tender package</h3>
                <p>
                  All qualification, pricing, delivery, and submission-package evidence is present.
                </p>
                <ul>
                  <li>Autonomous tool routing</li>
                  <li>Two deterministic validation layers</li>
                  <li>Preparation package released</li>
                </ul>
                <button disabled={busy} onClick={() => launch("complete_tender")}>
                  Run green case <span aria-hidden="true">→</span>
                </button>
              </article>
              <article className="case-card case-blocked">
                <div className="case-index">02</div>
                <StatusMark value="missing authority" />
                <h3>Authorization missing</h3>
                <p>
                  The tender is workable, but the project-specific authorization is not evidenced.
                </p>
                <ul>
                  <li>No inferred or fabricated authority</li>
                  <li>Explicit blocking reason codes</li>
                  <li>Reviewable missing-item package</li>
                </ul>
                <button disabled={busy} onClick={() => launch("blocked_missing_authorization")}>
                  Run blocked case <span aria-hidden="true">→</span>
                </button>
              </article>
            </div>
            {error && <p className="error" role="alert">{error}</p>}
          </section>
        </>
      ) : (
        <section className="workbench">
          <header className="task-header">
            <div>
              <button className="back" onClick={() => setTask(null)}>← Demo cases</button>
              <span className="kicker">Task {task.task_id}</span>
              <h1>{task.fixture_id === "complete_tender" ? "Complete tender" : "Missing authorization"}</h1>
            </div>
            <div className="task-status">
              <StatusMark value={task.status} />
              <span>{task.current_step.replaceAll("_", " ")}</span>
            </div>
          </header>

          <div className="route" aria-label="Agent route">
            {routeStages.map((stage, index) => (
              <div className="route-stage" key={stage}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{stage}</strong>
              </div>
            ))}
          </div>

          <div className="workbench-grid">
            <section className="panel timeline-panel">
              <div className="panel-heading">
                <div>
                  <span className="kicker">Agent execution</span>
                  <h2>Tool-call timeline</h2>
                </div>
                <span className="mono">{task.tool_receipts?.length || 0} calls</span>
              </div>
              <ol className="timeline">
                {(task.tool_receipts || []).map((receipt) => (
                  <li key={receipt.sequence}>
                    <span className="timeline-sequence">{String(receipt.sequence).padStart(2, "0")}</span>
                    <div>
                      <strong>{receipt.tool.replaceAll("_", " ")}</strong>
                      <small>{receipt.reason_code}{receipt.retry_of ? ` · retry of ${receipt.retry_of}` : ""}</small>
                    </div>
                    <span className={`receipt receipt-${receipt.status}`}>{receipt.status}</span>
                    <span className="duration">{receipt.duration_ms.toFixed(1)} ms</span>
                  </li>
                ))}
                {!task.tool_receipts?.length && <li className="pending-row">Waiting for background tool receipts…</li>}
              </ol>
            </section>

            <aside className="panel decision-panel">
              <span className="kicker">Deterministic decision</span>
              <h2>{task.status === "completed" ? "Preparation package ready for controlled submission" : task.status === "blocked" ? "Package blocked with evidence gaps" : "Validation in progress"}</h2>
              <div className="decision-grid">
                <Metric label="Human review" value={task.ready_for_human_review === undefined ? "Pending" : task.ready_for_human_review ? "Ready" : "Blocked"} />
                <Metric label="Submission readiness" value={task.ready_for_submission === undefined ? "Pending" : task.ready_for_submission ? "Ready" : "Blocked"} />
                <Metric label="Submission executed" value="No" />
                <Metric label="Risk actions" value="Locked" />
              </div>
              <div className="provider-proof">
                <span>Model receipt</span>
                <strong>{modelLabel}</strong>
                <small>{task.cloud_execution_id || "Local execution — cloud ID pending deployment"}</small>
              </div>
              {!!task.blocking_reason_codes?.length && (
                <div className="blocking-proof">
                  <span>Blocking reason</span>
                  {task.blocking_reason_codes.map((code) => <code key={code}>{code}</code>)}
                </div>
              )}
              {task.bundle_url && (
                <a className="download" href={task.bundle_url}>Download validated ZIP <span aria-hidden="true">↓</span></a>
              )}
            </aside>
          </div>

          <section className="panel review-panel">
            <div className="tabs" role="tablist" aria-label="Review views">
              {(["evidence", "validation", "artifacts"] as const).map((name) => (
                <button key={name} role="tab" aria-selected={tab === name} onClick={() => setTab(name)}>{name}</button>
              ))}
            </div>
            {tab === "evidence" && (
              <div className="review-content metrics-row">
                <Metric label="Requirements" value={task.evidence_summary?.requirement_count ?? "—"} />
                <Metric label="Evidence refs" value={task.evidence_summary?.evidence_count ?? "—"} />
                <Metric label="Compliant matches" value={task.evidence_summary?.matched_count ?? "—"} />
                <Metric label="Missing items" value={task.evidence_summary?.missing_items.length ?? "—"} />
              </div>
            )}
            {tab === "validation" && (
              <div className="review-content">
                <p className="validation-count">{task.validation_summary?.passed_count ?? 0} deterministic checks passed</p>
                {(task.validation_summary?.failed || []).map((finding) => (
                  <div className="finding" key={`${finding.code}-${finding.message}`}>
                    <strong>{finding.code}</strong><span>{finding.severity}</span><p>{finding.message}</p>
                  </div>
                ))}
                {!task.validation_summary?.failed.length && <p>No failed validation findings.</p>}
              </div>
            )}
            {tab === "artifacts" && (
              <div className="review-content artifact-list">
                {(task.artifacts || []).map((artifact) => <code key={artifact}>{artifact}</code>)}
              </div>
            )}
          </section>
        </section>
      )}

      <footer>
        <span>ProofBid · Synthetic evidence only</span>
        <span>Google ADK · Gemini 3.5 Flash · Cloud Run</span>
      </footer>
    </main>
  );
}

export default App;

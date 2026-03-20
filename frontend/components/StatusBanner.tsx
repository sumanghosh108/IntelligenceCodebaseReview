"use client";

interface ProgressStep {
  phase: string;
  label: string;
  status: string; // "pending" | "running" | "done" | "skipped" | "failed"
  duration_ms: number | null;
}

interface QuickStats {
  repo_name: string;
  total_files: number;
  total_lines: number;
  total_functions: number;
  languages: string[];
  branch: string;
}

interface StageError {
  phase: string;
  error: string;
  timestamp: string;
}

interface Props {
  status: string;
  currentPhase?: string;
  progressSteps?: ProgressStep[];
  quickStats?: QuickStats | null;
  errors: string[];
  stageErrors?: StageError[];
}

export default function StatusBanner({ status, currentPhase, progressSteps, quickStats, errors, stageErrors }: Props) {
  const isActive = !["completed", "failed"].includes(status);
  const doneCount = progressSteps?.filter(s => s.status === "done").length || 0;
  const failedCount = progressSteps?.filter(s => s.status === "failed").length || 0;
  const totalCount = progressSteps?.length || 1;
  const progressPct = Math.round((doneCount / totalCount) * 100);

  return (
    <div className="card max-w-3xl mx-auto mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {isActive && (
            <div className="w-5 h-5 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          )}
          <span className="font-medium">
            {status === "completed" ? "Analysis Complete" : status === "failed" ? "Analysis Failed" : "Analyzing Repository..."}
          </span>
        </div>
        <span className="text-sm text-[var(--text-secondary)]">
          {doneCount}/{totalCount} steps {progressPct > 0 ? `(${progressPct}%)` : ""}
          {failedCount > 0 ? ` · ${failedCount} failed` : ""}
        </span>
      </div>

      {/* Quick Stats Card (appears early) */}
      {quickStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4 p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
          <div className="text-center">
            <p className="text-lg font-bold text-[var(--accent)]">{quickStats.repo_name}</p>
            <p className="text-[10px] text-[var(--text-secondary)]">Repository</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[var(--accent)]">{quickStats.total_files}</p>
            <p className="text-[10px] text-[var(--text-secondary)]">Files</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[var(--accent)]">{quickStats.total_lines.toLocaleString()}</p>
            <p className="text-[10px] text-[var(--text-secondary)]">Lines</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-[var(--accent)]">{quickStats.languages.join(", ")}</p>
            <p className="text-[10px] text-[var(--text-secondary)]">Languages</p>
          </div>
        </div>
      )}

      {/* Progress bar */}
      <div className="score-bar mb-4">
        <div
          className="score-fill transition-all duration-500"
          style={{
            width: `${progressPct}%`,
            background: status === "failed" ? "var(--accent-red)" : "var(--accent)",
          }}
        />
      </div>

      {/* Step-by-step progress */}
      {progressSteps && progressSteps.length > 0 && (
        <div className="space-y-1.5 max-h-80 overflow-y-auto">
          {progressSteps.map((step, i) => (
            <div key={i} className={`flex items-center gap-2 text-sm px-2 py-1 rounded ${
              step.status === "running" ? "bg-[var(--accent)]/10" : ""
            }`}>
              {/* Status icon */}
              <span className="w-5 text-center flex-shrink-0">
                {step.status === "done" && <span className="text-[var(--accent-green)]">✓</span>}
                {step.status === "running" && (
                  <span className="inline-block w-3 h-3 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
                )}
                {step.status === "pending" && <span className="text-[var(--text-secondary)]">○</span>}
                {step.status === "skipped" && <span className="text-[var(--text-secondary)]">–</span>}
                {step.status === "failed" && <span className="text-red-400">✗</span>}
              </span>

              {/* Label */}
              <span className={`flex-1 ${
                step.status === "done" ? "text-[var(--text-primary)]" :
                step.status === "running" ? "text-[var(--accent)] font-medium" :
                step.status === "failed" ? "text-red-400" :
                "text-[var(--text-secondary)]"
              }`}>
                {step.label}
              </span>

              {/* Duration */}
              {step.duration_ms !== null && step.duration_ms !== undefined && (
                <span className="text-xs text-[var(--text-secondary)]">
                  {step.duration_ms < 1000 ? `${step.duration_ms}ms` : `${(step.duration_ms / 1000).toFixed(1)}s`}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Stage Errors (per-stage failures) */}
      {stageErrors && stageErrors.length > 0 && (
        <div className="mt-3 p-3 bg-yellow-900/20 border border-yellow-700 rounded-lg">
          <p className="text-xs font-medium text-yellow-400 mb-1">Stage Errors ({stageErrors.length})</p>
          {stageErrors.map((se, i) => (
            <div key={i} className="text-sm text-yellow-300 mb-1">
              <span className="font-mono text-xs text-yellow-500">[{se.phase}]</span>{" "}
              {se.error}
            </div>
          ))}
        </div>
      )}

      {/* Fatal Errors */}
      {errors.length > 0 && (
        <div className="mt-3 p-3 bg-red-900/20 border border-red-800 rounded-lg">
          {errors.map((err, i) => (
            <p key={i} className="text-sm text-red-400">{err}</p>
          ))}
        </div>
      )}
    </div>
  );
}

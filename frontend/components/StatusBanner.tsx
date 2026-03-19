"use client";

interface Props {
  status: string;
  errors: string[];
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: "Pending", color: "badge-yellow" },
  cloning: { label: "Cloning Repository", color: "badge-blue" },
  parsing: { label: "Parsing Code", color: "badge-blue" },
  embedding: { label: "Generating Embeddings", color: "badge-blue" },
  analyzing: { label: "Running AI Analysis", color: "badge-purple" },
  completed: { label: "Completed", color: "badge-green" },
  failed: { label: "Failed", color: "badge-red" },
};

export default function StatusBanner({ status, errors }: Props) {
  const info = STATUS_LABELS[status] || { label: status, color: "badge-blue" };

  return (
    <div className="card max-w-2xl mx-auto mb-6">
      <div className="flex items-center justify-between">
        <span className="text-sm text-[var(--text-secondary)]">Status</span>
        <span className={`badge ${info.color}`}>{info.label}</span>
      </div>
      {status === "analyzing" && (
        <div className="mt-3">
          <div className="score-bar">
            <div
              className="score-fill bg-[var(--accent)]"
              style={{ width: "60%", animation: "pulse 2s infinite" }}
            />
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Running multi-pass analysis with LLM...
          </p>
        </div>
      )}
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

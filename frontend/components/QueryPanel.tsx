"use client";
import { useState } from "react";
import { queryCodebase, agentQuery } from "@/lib/api";

interface Props {
  repoUrl: string;
  jobId?: string;
}

type Mode = "agent" | "rag";

interface AgentStep {
  type: string;
  content: string;
  step: number;
  tool?: string;
  tool_input?: string;
  duration_ms?: number;
}

function confidenceLabel(val: unknown): { text: string; badge: string } {
  if (typeof val === "number") {
    if (val >= 0.7) return { text: `${(val * 100).toFixed(0)}%`, badge: "badge-green" };
    if (val >= 0.4) return { text: `${(val * 100).toFixed(0)}%`, badge: "badge-yellow" };
    return { text: `${(val * 100).toFixed(0)}%`, badge: "badge-red" };
  }
  if (typeof val === "string") {
    if (val === "high") return { text: "High", badge: "badge-green" };
    if (val === "medium") return { text: "Medium", badge: "badge-yellow" };
    return { text: val, badge: "badge-red" };
  }
  return { text: "N/A", badge: "badge-red" };
}

function renderAnswer(val: unknown): string {
  if (typeof val === "string") return val;
  if (typeof val === "object" && val !== null) return JSON.stringify(val, null, 2);
  return String(val ?? "No answer returned");
}

const stepIcon = (type: string) => {
  switch (type) {
    case "think": return "🧠";
    case "action": return "🔧";
    case "observation": return "👁";
    case "answer": return "✅";
    case "error": return "❌";
    default: return "•";
  }
};

const stepColor = (type: string) => {
  switch (type) {
    case "think": return "var(--accent-yellow)";
    case "action": return "var(--accent)";
    case "observation": return "var(--text-secondary)";
    case "answer": return "var(--accent-green)";
    case "error": return "var(--accent-red)";
    default: return "var(--text-primary)";
  }
};

export default function QueryPanel({ repoUrl, jobId }: Props) {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>(jobId ? "agent" : "rag");
  const [loading, setLoading] = useState(false);

  // RAG state
  const [ragAnswer, setRagAnswer] = useState<Record<string, unknown> | null>(null);

  // Agent state
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [agentAnswer, setAgentAnswer] = useState<string | null>(null);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setRagAnswer(null);
    setAgentSteps([]);
    setAgentAnswer(null);

    if (mode === "agent" && jobId) {
      try {
        await agentQuery(jobId, question, (event) => {
          const step = event as unknown as AgentStep;
          setAgentSteps((prev) => [...prev, step]);
          if (step.type === "answer") {
            setAgentAnswer(step.content);
          }
        });
      } catch (err) {
        setAgentSteps((prev) => [
          ...prev,
          { type: "error", content: String(err), step: 0 },
        ]);
      }
    } else {
      try {
        const result = await queryCodebase(repoUrl, question);
        console.log("RAG response:", result);
        setRagAnswer(result);
      } catch {
        setRagAnswer({ error: "Failed to query codebase" });
      }
    }
    setLoading(false);
  };

  return (
    <div className="card max-w-4xl mx-auto mt-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-[var(--accent)]">
          Ask About the Codebase
        </h3>
        {jobId && (
          <div className="flex gap-1 bg-[var(--bg-primary)] rounded-lg p-1 border border-[var(--border)]">
            <button
              onClick={() => setMode("agent")}
              className={`px-3 py-1 text-xs rounded font-medium transition ${
                mode === "agent"
                  ? "bg-[var(--accent)] text-[var(--bg-primary)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              🤖 Agent
            </button>
            <button
              onClick={() => setMode("rag")}
              className={`px-3 py-1 text-xs rounded font-medium transition ${
                mode === "rag"
                  ? "bg-[var(--accent)] text-[var(--bg-primary)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              📄 RAG
            </button>
          </div>
        )}
      </div>

      <p className="text-xs text-[var(--text-secondary)] mb-3">
        {mode === "agent"
          ? "Agent autonomously explores the codebase — searches files, reads code, traces dependencies, and synthesizes an answer."
          : "Direct embedding search — finds relevant code chunks and asks the LLM to answer."}
      </p>

      <form onSubmit={handleQuery} className="flex gap-2 mb-4">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g., How does authentication work?"
          className="flex-1 px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-6 py-2 bg-[var(--accent)] text-[var(--bg-primary)] font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 transition"
        >
          {loading ? "Exploring..." : mode === "agent" ? "🤖 Ask Agent" : "Ask"}
        </button>
      </form>

      {/* Agent Steps Display */}
      {mode === "agent" && agentSteps.length > 0 && (
        <div className="space-y-2 mb-4">
          {agentSteps.map((step, i) => (
            <div
              key={i}
              className={`p-3 rounded-lg border border-[var(--border)] ${
                step.type === "answer"
                  ? "bg-[var(--bg-primary)] border-[var(--accent-green)]"
                  : "bg-[var(--bg-primary)]"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span>{stepIcon(step.type)}</span>
                <span
                  className="text-xs font-semibold uppercase"
                  style={{ color: stepColor(step.type) }}
                >
                  {step.type}
                </span>
                {step.step > 0 && (
                  <span className="text-xs text-[var(--text-secondary)]">
                    Step {step.step}
                  </span>
                )}
                {step.tool && (
                  <span className="badge badge-blue text-xs">{step.tool}</span>
                )}
                {step.duration_ms != null && (
                  <span className="text-xs text-[var(--text-secondary)] ml-auto">
                    {step.duration_ms}ms
                  </span>
                )}
              </div>

              {step.type === "action" && step.tool_input && (
                <p className="text-xs font-mono text-[var(--text-secondary)] mb-1">
                  {step.tool_input}
                </p>
              )}

              {step.type === "observation" ? (
                <details className="text-sm">
                  <summary className="cursor-pointer text-[var(--text-secondary)] text-xs">
                    Show result ({step.content.length} chars)
                  </summary>
                  <pre className="mt-1 text-xs overflow-x-auto whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {step.content}
                  </pre>
                </details>
              ) : step.type === "answer" ? (
                <p className="whitespace-pre-wrap text-sm">{step.content}</p>
              ) : (
                <p className="text-sm text-[var(--text-secondary)]">
                  {step.content}
                </p>
              )}
            </div>
          ))}

          {loading && (
            <div className="p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] animate-pulse">
              <span className="text-xs text-[var(--text-secondary)]">
                Agent is thinking...
              </span>
            </div>
          )}
        </div>
      )}

      {/* RAG Answer Display */}
      {mode === "rag" && ragAnswer && (
        <div className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
          {ragAnswer.error ? (
            <p className="text-red-400">{String(ragAnswer.error)}</p>
          ) : (
            <>
              <p className="mb-3 whitespace-pre-wrap">
                {renderAnswer(ragAnswer.answer)}
              </p>

              {ragAnswer.confidence != null && (
                <span
                  className={`badge ${confidenceLabel(ragAnswer.confidence).badge}`}
                >
                  Confidence: {confidenceLabel(ragAnswer.confidence).text}
                </span>
              )}

              {ragAnswer.relevant_files &&
                Array.isArray(ragAnswer.relevant_files) &&
                (ragAnswer.relevant_files as string[]).length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm text-[var(--text-secondary)] mb-1">
                      Relevant files:
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {(ragAnswer.relevant_files as string[]).map((f, i) => (
                        <span
                          key={i}
                          className="text-xs font-mono px-2 py-1 bg-[var(--bg-secondary)] rounded"
                        >
                          {String(f)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

              {ragAnswer.sources &&
                Array.isArray(ragAnswer.sources) &&
                (ragAnswer.sources as Record<string, unknown>[]).length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm text-[var(--text-secondary)] mb-1">
                      Sources:
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {(ragAnswer.sources as Record<string, unknown>[]).map(
                        (s, i) => (
                          <span
                            key={i}
                            className="text-xs font-mono px-2 py-1 bg-[var(--bg-secondary)] rounded"
                          >
                            {String(s.file_path || s)}{" "}
                            {s.start_line
                              ? `(L${s.start_line}-${s.end_line})`
                              : ""}
                          </span>
                        )
                      )}
                    </div>
                  </div>
                )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

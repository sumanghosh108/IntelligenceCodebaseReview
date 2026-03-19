"use client";
import { useState } from "react";
import { queryCodebase } from "@/lib/api";

interface Props {
  repoUrl: string;
}

export default function QueryPanel({ repoUrl }: Props) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    try {
      const result = await queryCodebase(repoUrl, question);
      setAnswer(result);
    } catch {
      setAnswer({ error: "Failed to query codebase" });
    }
    setLoading(false);
  };

  return (
    <div className="card max-w-4xl mx-auto mt-6">
      <h3 className="text-lg font-semibold mb-3 text-[var(--accent)]">
        Ask About the Codebase (RAG)
      </h3>
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
          {loading ? "..." : "Ask"}
        </button>
      </form>

      {answer && (
        <div className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
          {answer.error ? (
            <p className="text-red-400">{String(answer.error)}</p>
          ) : (
            <>
              <p className="mb-3">{String(answer.answer || "")}</p>
              {answer.confidence && (
                <span
                  className={`badge ${
                    answer.confidence === "high"
                      ? "badge-green"
                      : answer.confidence === "medium"
                      ? "badge-yellow"
                      : "badge-red"
                  }`}
                >
                  Confidence: {String(answer.confidence)}
                </span>
              )}
              {answer.relevant_files && (
                <div className="mt-3">
                  <p className="text-sm text-[var(--text-secondary)] mb-1">Relevant files:</p>
                  <div className="flex flex-wrap gap-1">
                    {(answer.relevant_files as string[]).map((f, i) => (
                      <span key={i} className="text-xs font-mono px-2 py-1 bg-[var(--bg-secondary)] rounded">
                        {f}
                      </span>
                    ))}
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

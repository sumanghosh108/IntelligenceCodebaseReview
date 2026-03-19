"use client";
import { useState } from "react";

interface Props {
  onSubmit: (repoUrl: string, branch: string) => void;
  loading: boolean;
}

export default function AnalysisForm({ onSubmit, loading }: Props) {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (repoUrl.trim()) {
      onSubmit(repoUrl.trim(), branch.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card max-w-2xl mx-auto">
      <h2 className="text-xl font-bold mb-4">Analyze Repository</h2>
      <div className="mb-4">
        <label className="block text-sm text-[var(--text-secondary)] mb-1">
          GitHub Repository URL
        </label>
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
          disabled={loading}
        />
      </div>
      <div className="mb-4">
        <label className="block text-sm text-[var(--text-secondary)] mb-1">
          Branch
        </label>
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          className="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
          disabled={loading}
        />
      </div>
      <button
        type="submit"
        disabled={loading || !repoUrl.trim()}
        className="w-full py-3 bg-[var(--accent)] text-[var(--bg-primary)] font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 transition"
      >
        {loading ? "Analyzing..." : "Start Analysis"}
      </button>
    </form>
  );
}

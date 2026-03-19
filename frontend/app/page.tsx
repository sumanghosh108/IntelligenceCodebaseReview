"use client";
import { useState, useEffect, useCallback } from "react";
import AnalysisForm from "@/components/AnalysisForm";
import StatusBanner from "@/components/StatusBanner";
import ResultDashboard from "@/components/ResultDashboard";
import QueryPanel from "@/components/QueryPanel";
import { startAnalysis, getStatus, getFullResult, checkHealth } from "@/lib/api";

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [status, setStatus] = useState<string>("");
  const [errors, setErrors] = useState<string[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<{ ollama_connected: boolean; available_models: string[] } | null>(null);

  useEffect(() => {
    checkHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const pollStatus = useCallback(async (url: string) => {
    const poll = async () => {
      try {
        const s = await getStatus(url);
        setStatus(s.status);
        setErrors(s.errors || []);

        if (s.status === "completed") {
          const fullResult = await getFullResult(url);
          setResult(fullResult);
          setLoading(false);
          return;
        }

        if (s.status === "failed") {
          setLoading(false);
          return;
        }

        setTimeout(poll, 3000);
      } catch {
        setTimeout(poll, 5000);
      }
    };
    poll();
  }, []);

  const handleSubmit = async (url: string, branch: string) => {
    setRepoUrl(url);
    setLoading(true);
    setResult(null);
    setErrors([]);
    setStatus("pending");

    try {
      await startAnalysis(url, branch);
      pollStatus(url);
    } catch {
      setStatus("failed");
      setErrors(["Failed to start analysis. Is the backend running?"]);
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen p-6">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold mb-2">
          Intelligence Codebase Review
        </h1>
        <p className="text-[var(--text-secondary)]">
          Production-grade open-source codebase analysis system
        </p>
        {health && (
          <div className="mt-3 flex justify-center gap-3">
            <span
              className={`badge ${
                health.ollama_connected ? "badge-green" : "badge-red"
              }`}
            >
              Ollama: {health.ollama_connected ? "Connected" : "Disconnected"}
            </span>
            {health.available_models && (
              <span className="badge badge-blue">
                Models: {health.available_models.join(", ") || "none"}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Analysis Form */}
      <AnalysisForm onSubmit={handleSubmit} loading={loading} />

      {/* Status */}
      {status && (
        <div className="mt-6">
          <StatusBanner status={status} errors={errors} />
        </div>
      )}

      {/* Results */}
      {result && result.status === "completed" && (
        <div className="mt-6">
          <ResultDashboard data={result} />
          <QueryPanel repoUrl={repoUrl} />
        </div>
      )}
    </main>
  );
}

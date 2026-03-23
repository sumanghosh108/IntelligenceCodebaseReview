"use client";
import { useState, useEffect, useCallback } from "react";
import AnalysisForm from "@/components/AnalysisForm";
import StatusBanner from "@/components/StatusBanner";
import ResultDashboard from "@/components/ResultDashboard";
import QueryPanel from "@/components/QueryPanel";
import { startAnalysis, getStatus, getFullResult, checkHealth, downloadReport } from "@/lib/api";

interface ProgressStep {
  phase: string;
  label: string;
  status: string;
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

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [jobId, setJobId] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [currentPhase, setCurrentPhase] = useState<string>("");
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [quickStats, setQuickStats] = useState<QuickStats | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [stageErrors, setStageErrors] = useState<StageError[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<{
    llm_provider?: string;
    model?: string;
    multi_agent_enabled?: boolean;
    api_provider?: { status: string; provider?: string; model?: string };
  } | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    checkHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const pollStatus = useCallback(async (jid: string) => {
    const poll = async () => {
      try {
        const s = await getStatus(jid);
        setStatus(s.status);
        setCurrentPhase(s.current_phase || "");
        setProgressSteps(s.progress_steps || []);
        setQuickStats(s.quick_stats || null);
        setErrors(s.errors || []);
        setStageErrors(s.stage_errors || []);

        if (s.status === "completed") {
          const fullResult = await getFullResult(jid);
          setResult(fullResult);
          setLoading(false);
          return;
        }

        if (s.status === "failed") {
          setLoading(false);
          return;
        }

        setTimeout(poll, 1500);
      } catch {
        setTimeout(poll, 3000);
      }
    };
    poll();
  }, []);

  const handleSubmit = async (url: string, branch: string) => {
    setRepoUrl(url);
    setLoading(true);
    setResult(null);
    setErrors([]);
    setStageErrors([]);
    setStatus("pending");
    setCurrentPhase("");
    setProgressSteps([]);
    setQuickStats(null);
    setJobId("");

    try {
      const resp = await startAnalysis(url, branch);
      const jid = resp.job_id;
      setJobId(jid);

      if (resp.status === "in_progress") {
        // Already running, just poll
      }
      pollStatus(jid);
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
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            {/* Provider status */}
            <span className={`badge ${
              health.api_provider?.status === "healthy" ? "badge-green" : "badge-red"
            }`}>
              OpenRouter: {health.api_provider?.status === "healthy" ? "Connected" : "Error"}
            </span>

            {/* Model */}
            {health.model && (
              <span className="badge badge-blue">{health.model}</span>
            )}

            {/* Multi-agent badge */}
            {health.multi_agent_enabled && (
              <span className="badge badge-blue">Multi-Agent</span>
            )}
          </div>
        )}
      </div>

      {/* Analysis Form */}
      <AnalysisForm onSubmit={handleSubmit} loading={loading} />

      {/* Job ID display */}
      {jobId && (
        <div className="text-center mt-2">
          <span className="text-xs text-[var(--text-secondary)]">
            Job: <code className="font-mono">{jobId}</code>
          </span>
        </div>
      )}

      {/* Progressive Status */}
      {status && (
        <div className="mt-6">
          <StatusBanner
            status={status}
            currentPhase={currentPhase}
            progressSteps={progressSteps}
            quickStats={quickStats}
            errors={errors}
            stageErrors={stageErrors}
          />
        </div>
      )}

      {/* Results */}
      {result && result.status === "completed" && (
        <div className="mt-6">
          {/* Download Button */}
          <div className="flex justify-end mb-4">
            <button
              onClick={async () => {
                setDownloading(true);
                try {
                  await downloadReport(jobId, repoUrl);
                } catch {
                  alert("Failed to download report. Is the backend running?");
                } finally {
                  setDownloading(false);
                }
              }}
              disabled={downloading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all
                bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              {downloading ? "Generating ZIP..." : "Download Full Report (.zip)"}
            </button>
          </div>

          <ResultDashboard data={result} repoUrl={repoUrl} />
          <QueryPanel repoUrl={repoUrl} jobId={jobId} />
        </div>
      )}
    </main>
  );
}

const API_BASE = "/api";

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function startAnalysis(repoUrl: string, branch: string = "main") {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl, branch }),
  });
  return res.json();
}

export async function getStatus(jobId: string) {
  const res = await fetch(`${API_BASE}/analysis/${jobId}/status`);
  return res.json();
}

export async function getFullResult(jobId: string) {
  const res = await fetch(`${API_BASE}/analysis/${jobId}/result`);
  return res.json();
}

export async function getMeta(jobId: string) {
  const res = await fetch(`${API_BASE}/analysis/${jobId}/meta`);
  return res.json();
}

export async function getSection(section: string, jobId: string) {
  const res = await fetch(`${API_BASE}/analysis/${jobId}/${section}`);
  return res.json();
}

export async function queryCodebase(repoUrl: string, question: string) {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl, question }),
  });
  return res.json();
}

export async function getImpactAnalysis(jobId: string, target: string, targetType: string = "file") {
  const res = await fetch(`${API_BASE}/analysis/${jobId}/impact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, target_type: targetType }),
  });
  return res.json();
}

export async function agentQuery(
  jobId: string,
  question: string,
  onEvent: (event: Record<string, unknown>) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/analysis/${jobId}/agent-query-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Agent query failed" }));
    throw new Error(err.detail || "Agent query failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data === "[DONE]") return;
        try {
          const event = JSON.parse(data);
          onEvent(event);
        } catch {
          // skip malformed events
        }
      }
    }
  }
}

export async function downloadReport(jobId: string, repoUrl: string) {
  const res = await fetch(`${API_BASE}/analysis/${jobId}/download`);
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const repoName = repoUrl.replace(/\/+$/, "").split("/").pop() || "repo";
  const a = document.createElement("a");
  a.href = url;
  a.download = `${repoName}-analysis.zip`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

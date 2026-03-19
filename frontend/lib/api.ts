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

export async function getStatus(repoUrl: string) {
  const res = await fetch(
    `${API_BASE}/analysis/status?repo_url=${encodeURIComponent(repoUrl)}`
  );
  return res.json();
}

export async function getFullResult(repoUrl: string) {
  const res = await fetch(
    `${API_BASE}/analysis/result?repo_url=${encodeURIComponent(repoUrl)}`
  );
  return res.json();
}

export async function getSection(section: string, repoUrl: string) {
  const res = await fetch(
    `${API_BASE}/analysis/${section}?repo_url=${encodeURIComponent(repoUrl)}`
  );
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

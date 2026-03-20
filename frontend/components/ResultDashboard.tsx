"use client";
import { useState } from "react";

interface Props {
  data: Record<string, unknown>;
  repoUrl?: string;
}

type TabKey =
  | "health"
  | "quality"
  | "overview"
  | "tech"
  | "modules"
  | "files"
  | "functions"
  | "dependencies"
  | "callgraph"
  | "flow"
  | "views"
  | "production"
  | "security"
  | "cost"
  | "recommendations"
  | "interview"
  | "synthesis"
  | "api_contracts"
  | "db_schema"
  | "perf_bottlenecks"
  | "complexity"
  | "architecture"
  | "security_threats"
  | "failure_modes"
  | "timeline"
  | "auto_docs";

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "health", label: "Health", icon: "❤" },
  { key: "quality", label: "Quality", icon: "🔍" },
  { key: "overview", label: "Overview", icon: "📋" },
  { key: "tech", label: "Tech Stack", icon: "⚙" },
  { key: "modules", label: "Modules", icon: "📦" },
  { key: "files", label: "Files", icon: "📄" },
  { key: "functions", label: "Functions", icon: "ƒ" },
  { key: "dependencies", label: "Dependencies", icon: "🔗" },
  { key: "callgraph", label: "Call Graph", icon: "📞" },
  { key: "flow", label: "Flow", icon: "➜" },
  { key: "views", label: "Views", icon: "👁" },
  { key: "production", label: "Production", icon: "🏭" },
  { key: "security", label: "Security", icon: "🔒" },
  { key: "cost", label: "Cost", icon: "💰" },
  { key: "recommendations", label: "Actions", icon: "💡" },
  { key: "interview", label: "Interview", icon: "🎤" },
  { key: "synthesis", label: "Synthesis", icon: "🔬" },
  { key: "api_contracts", label: "API Contracts", icon: "🌐" },
  { key: "db_schema", label: "DB Schema", icon: "🗄" },
  { key: "perf_bottlenecks", label: "Performance", icon: "⚡" },
  { key: "complexity", label: "Complexity", icon: "🧮" },
  { key: "architecture", label: "Architecture", icon: "🏗" },
  { key: "security_threats", label: "Threats", icon: "🛡" },
  { key: "failure_modes", label: "Failures", icon: "💥" },
  { key: "timeline", label: "Timeline", icon: "📅" },
  { key: "auto_docs", label: "Auto Docs", icon: "📝" },
];

export default function ResultDashboard({ data, repoUrl }: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("health");

  return (
    <div className="max-w-6xl mx-auto">
      {/* Tab nav */}
      <div className="flex flex-wrap gap-2 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
              activeTab === tab.key
                ? "bg-[var(--accent)] text-[var(--bg-primary)]"
                : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            <span className="text-xs">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="card">
        {activeTab === "health" && <HealthDashboardPanel data={data.health_dashboard} />}
        {activeTab === "quality" && <CodeQualityPanel data={data.code_quality} />}
        {activeTab === "overview" && <OverviewPanel data={data.repo_overview} />}
        {activeTab === "tech" && <TechPanel data={data.tech_stack} />}
        {activeTab === "modules" && <ModulesPanel data={data.modules} />}
        {activeTab === "files" && <FilesPanel data={data.file_analyses} repoUrl={repoUrl} />}
        {activeTab === "functions" && <FunctionsPanel data={data.function_analyses} />}
        {activeTab === "dependencies" && <DepsPanel data={data.dependencies} />}
        {activeTab === "callgraph" && <CallGraphPanel data={data.call_graph} />}
        {activeTab === "flow" && <FlowPanel data={data} />}
        {activeTab === "views" && <AbstractionViewsPanel data={data.abstraction_views} />}
        {activeTab === "production" && <ProductionPanel data={data.production_readiness} />}
        {activeTab === "security" && <SecurityPanel data={data.security_analysis} />}
        {activeTab === "cost" && <CostPanel data={data.cost_analysis} />}
        {activeTab === "recommendations" && <RecommendationsPanel data={data.recommendations} />}
        {activeTab === "interview" && <InterviewPanel data={data.interview_explainer} />}
        {activeTab === "synthesis" && <SynthesisPanel data={data.master_synthesis} />}
        {activeTab === "api_contracts" && <APIContractsPanel data={data.api_contracts} />}
        {activeTab === "db_schema" && <DBSchemaPanel data={data.db_schema} />}
        {activeTab === "perf_bottlenecks" && <PerfBottlenecksPanel data={data.perf_bottlenecks} />}
        {activeTab === "complexity" && <ComplexityPanel data={data.complexity_score} />}
        {activeTab === "architecture" && <ArchitecturePanel data={data.architecture_patterns} />}
        {activeTab === "security_threats" && <SecurityThreatsPanel data={data.security_threats} />}
        {activeTab === "failure_modes" && <FailureModesPanel data={data.failure_modes} />}
        {activeTab === "timeline" && <TimelinePanel data={data.timeline} />}
        {activeTab === "auto_docs" && <AutoDocsPanel data={data.auto_docs} />}
      </div>
    </div>
  );
}

// ============ Shared Components ============

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-3 text-[var(--accent)]">{title}</h3>
      {children}
    </div>
  );
}

function JsonBlock({ data }: { data: unknown }) {
  if (!data) return <p className="text-[var(--text-secondary)]">No data available</p>;
  return <pre className="text-sm overflow-x-auto">{JSON.stringify(data, null, 2)}</pre>;
}

function itemToString(item: unknown): string {
  if (typeof item === "string") return item;
  if (typeof item === "number" || typeof item === "boolean") return String(item);
  if (item && typeof item === "object") {
    const obj = item as Record<string, unknown>;
    if (obj.name && obj.description) return `${obj.name}: ${obj.description}`;
    if (obj.name) return String(obj.name);
    if (obj.description) return String(obj.description);
    if (obj.title && obj.description) return `${obj.title}: ${obj.description}`;
    if (obj.title) return String(obj.title);
    return JSON.stringify(item);
  }
  return String(item ?? "");
}

function ListItems({ items }: { items: unknown[] | undefined }) {
  if (!items || items.length === 0) return <p className="text-[var(--text-secondary)]">None</p>;
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2">
          <span className="text-[var(--accent)] mt-1">&#8226;</span>
          <span>{itemToString(item)}</span>
        </li>
      ))}
    </ul>
  );
}

function ScoreBar({ score, max = 10, label }: { score: number; max?: number; label?: string }) {
  const pct = (score / max) * 100;
  const color = score >= 7 ? "var(--accent-green)" : score >= 4 ? "var(--accent-yellow)" : "var(--accent-red)";
  return (
    <div className="flex items-center gap-3">
      {label && <span className="text-sm font-medium w-36">{label}</span>}
      <div className="flex-1 score-bar">
        <div className="score-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-sm font-bold" style={{ color }}>{score}/{max}</span>
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: unknown }) {
  const val = Number(confidence);
  if (!val && val !== 0) return null;
  const pct = Math.round(val * 100);
  const color = pct >= 80 ? "badge-green" : pct >= 50 ? "badge-yellow" : "badge-red";
  return <span className={`badge ${color} text-xs`}>Confidence: {pct}%</span>;
}

// ============ NEW: Health Dashboard Panel ============

function HealthDashboardPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const overall = Number(d.overall_score || 0);
  const stats = d.stats as Record<string, unknown> | undefined;
  const ttu = d.time_to_understand as string | undefined;

  return (
    <>
      {/* Overall Score - Big display */}
      <div className="text-center mb-8 p-6 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
        <p className="text-6xl font-bold mb-2" style={{
          color: overall >= 7 ? "var(--accent-green)" : overall >= 4 ? "var(--accent-yellow)" : "var(--accent-red)"
        }}>{overall}/10</p>
        <p className="text-[var(--text-secondary)] text-lg">Overall Health Score</p>
        {ttu && <p className="text-sm text-[var(--text-secondary)] mt-2">Estimated Time to Understand: <strong>{ttu}</strong></p>}
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {[
            { label: "Files", value: stats.total_files },
            { label: "Lines", value: stats.total_lines },
            { label: "Functions", value: stats.total_functions },
            { label: "Languages", value: Array.isArray(stats.languages) ? stats.languages.length : "?" },
          ].map((s, i) => (
            <div key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
              <p className="text-2xl font-bold text-[var(--accent)]">{String(s.value)}</p>
              <p className="text-xs text-[var(--text-secondary)]">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Score bars */}
      <Section title="Score Breakdown">
        <div className="space-y-3">
          {["code_quality", "production_readiness", "security", "scalability"].map((key) => {
            const cat = d[key] as Record<string, unknown> | undefined;
            if (!cat) return null;
            return (
              <ScoreBar key={key} score={Number(cat.score || 0)} label={key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())} />
            );
          })}
        </div>
      </Section>

      {/* Details per category */}
      {["code_quality", "production_readiness", "security", "scalability"].map((key) => {
        const cat = d[key] as Record<string, unknown> | undefined;
        if (!cat) return null;
        const title = key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
        const details = cat.details as string[] | undefined;
        const issues = cat.issues as string[] | undefined;
        return (
          <Section key={key} title={`${title} — Details`}>
            {details && details.length > 0 && (
              <div className="mb-3">
                {details.map((d, i) => (
                  <p key={i} className="text-sm text-[var(--accent-green)] flex items-start gap-2">
                    <span>✓</span><span>{d}</span>
                  </p>
                ))}
              </div>
            )}
            {issues && issues.length > 0 && (
              <div>
                {issues.map((issue, i) => (
                  <p key={i} className="text-sm text-[var(--accent-red)] flex items-start gap-2">
                    <span>✗</span><span>{issue}</span>
                  </p>
                ))}
              </div>
            )}
          </Section>
        );
      })}
    </>
  );
}

// ============ Code Quality Intelligence Panel ============

function CodeQualityPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const score = Number(d.score || 0);
  const totalIssues = Number(d.total_issues || 0);
  const ruleBased = Number(d.rule_based_count || 0);
  const aiDetected = Number(d.ai_detected_count || 0);
  const bySeverity = d.by_severity as Record<string, number> | undefined;
  const byCategory = d.by_category as Record<string, number> | undefined;
  const issues = (Array.isArray(d.issues) ? d.issues : []) as Array<Record<string, unknown>>;

  const sevColor = (s: string) =>
    s === "critical" ? "badge-red" : s === "high" ? "badge-red" : s === "medium" ? "badge-yellow" : "badge-green";
  const catLabel = (c: string) => c.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());

  return (
    <>
      {/* Score + stats header */}
      <div className="text-center mb-8 p-6 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
        <p className="text-6xl font-bold mb-2" style={{
          color: score >= 7 ? "var(--accent-green)" : score >= 4 ? "var(--accent-yellow)" : "var(--accent-red)"
        }}>{score}/10</p>
        <p className="text-[var(--text-secondary)] text-lg">Code Quality Score</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { label: "Total Issues", value: totalIssues, color: totalIssues > 10 ? "var(--accent-red)" : "var(--accent)" },
          { label: "Rule-Based", value: ruleBased, color: "var(--accent)" },
          { label: "AI-Detected", value: aiDetected, color: "var(--accent)" },
          { label: "Critical", value: bySeverity?.critical || 0, color: (bySeverity?.critical || 0) > 0 ? "var(--accent-red)" : "var(--accent-green)" },
        ].map((s, i) => (
          <div key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
            <p className="text-2xl font-bold" style={{ color: s.color }}>{String(s.value)}</p>
            <p className="text-xs text-[var(--text-secondary)]">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Severity breakdown */}
      {bySeverity && Object.keys(bySeverity).length > 0 && (
        <Section title="By Severity">
          <div className="flex flex-wrap gap-2">
            {["critical", "high", "medium", "low"].map(sev => {
              const count = bySeverity[sev] || 0;
              if (count === 0) return null;
              return (
                <span key={sev} className={`badge ${sevColor(sev)}`}>
                  {sev}: {count}
                </span>
              );
            })}
          </div>
        </Section>
      )}

      {/* Category breakdown */}
      {byCategory && Object.keys(byCategory).length > 0 && (
        <Section title="By Category">
          <div className="flex flex-wrap gap-2">
            {Object.entries(byCategory).map(([cat, count]) => (
              <span key={cat} className="badge badge-blue">
                {catLabel(cat)}: {count}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Issue list */}
      <Section title="Issues">
        {issues.length === 0 ? (
          <p className="text-[var(--accent-green)]">No code quality issues detected</p>
        ) : (
          <div className="space-y-3">
            {issues.map((iss, i) => (
              <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`badge ${sevColor(String(iss.severity || "low"))} text-xs`}>
                      {String(iss.severity || "low")}
                    </span>
                    <span className="badge badge-blue text-xs">{catLabel(String(iss.category || ""))}</span>
                  </div>
                  {iss.file && String(iss.file) !== "codebase-wide" && (
                    <span className="text-xs font-mono text-[var(--text-secondary)] shrink-0">
                      {String(iss.file)}{iss.line ? `:${iss.line}` : ""}
                    </span>
                  )}
                </div>
                <p className="font-medium text-sm mb-2">{String(iss.issue || "")}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="text-[var(--accent-red)] shrink-0">Impact:</span>
                    <span className="text-[var(--text-secondary)]">{String(iss.impact || "")}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[var(--accent-green)] shrink-0">Fix:</span>
                    <span className="text-[var(--text-secondary)]">{String(iss.fix || "")}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </>
  );
}

// ============ Existing Panels (enhanced) ============

function OverviewPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
      <ConfidenceBadge confidence={d.confidence} />
      <Section title="Summary"><p>{String(d.summary || "")}</p></Section>
      <Section title="Problem"><p>{String(d.problem || "")}</p></Section>
      <Section title="Target Users"><p>{String(d.users || "")}</p></Section>
      <Section title="System Type"><span className="badge badge-blue">{String(d.system_type || "")}</span></Section>
      <Section title="Core Features"><ListItems items={d.core_features as string[]} /></Section>
    </>
  );
}

function TechPanel({ data }: { data: unknown }) {
  const d = data as Record<string, string[]> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
      <Section title="Languages">
        <div className="flex flex-wrap gap-2">
          {(d.languages || []).map((l, i) => <span key={i} className="badge badge-blue">{itemToString(l)}</span>)}
        </div>
      </Section>
      <Section title="Frameworks">
        <div className="flex flex-wrap gap-2">
          {(d.frameworks || []).map((f, i) => <span key={i} className="badge badge-green">{itemToString(f)}</span>)}
        </div>
      </Section>
      <Section title="Libraries"><ListItems items={d.libraries} /></Section>
      <Section title="Database"><ListItems items={d.database} /></Section>
      <Section title="Infrastructure"><ListItems items={d.infra_tools} /></Section>
      <Section title="AI/ML"><ListItems items={d.ai_ml} /></Section>
    </>
  );
}

function ModulesPanel({ data }: { data: unknown }) {
  const modules = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>;
  if (modules.length === 0) return <JsonBlock data={data} />;
  return (
    <div className="space-y-4">
      {modules.map((m, i) => (
        <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-[var(--accent)]">{String(m.module)}</h4>
            <ConfidenceBadge confidence={m.confidence} />
          </div>
          <p className="text-sm text-[var(--text-secondary)] mt-1">{String(m.responsibility)}</p>
          <div className="flex flex-wrap gap-1 mt-2">
            {(Array.isArray(m.folders) ? m.folders : []).map((f: unknown, j: number) => (
              <span key={j} className="text-xs px-2 py-1 bg-[var(--bg-secondary)] rounded">{itemToString(f)}</span>
            ))}
          </div>
          {Array.isArray(m.depends_on) && m.depends_on.length > 0 && (
            <p className="text-xs text-[var(--text-secondary)] mt-2">
              Depends on: {m.depends_on.map(itemToString).join(", ")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function FilesPanel({ data, repoUrl }: { data: unknown; repoUrl?: string }) {
  const files = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>;
  if (files.length === 0) return <JsonBlock data={data} />;
  return (
    <div className="space-y-3">
      {files.map((f, i) => {
        const importance = String(f.importance || "");
        const risk = String(f.risk_level || "");
        const importanceBadge = importance === "critical" ? "badge-red" : importance === "important" ? "badge-yellow" : "badge-green";
        return (
          <details key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
            <summary className="cursor-pointer flex items-center gap-2">
              <span className="font-mono text-sm text-[var(--accent)]">{String(f.file_path)}</span>
              {importance && <span className={`badge ${importanceBadge} text-xs`}>{importance}</span>}
              {risk && risk !== "low" && <span className="badge badge-red text-xs">Risk: {risk}</span>}
              {f.dependent_count !== undefined && Number(f.dependent_count) > 0 && (
                <span className="text-xs text-[var(--text-secondary)]">{String(f.dependent_count)} dependents</span>
              )}
            </summary>
            <div className="mt-3 space-y-2 text-sm">
              <p><strong>Purpose:</strong> {String(f.purpose || "")}</p>
              <p><strong>Role:</strong> {String(f.role || "")}</p>
              <p><strong>Impact:</strong> {String(f.impact || "")}</p>
              <p><strong>Dependencies:</strong> {(Array.isArray(f.dependencies) ? f.dependencies.map(itemToString) : []).join(", ")}</p>
              {Array.isArray(f.patterns) && f.patterns.length > 0 && (
                <p><strong>Patterns:</strong> {f.patterns.map(itemToString).join(", ")}</p>
              )}
              {Array.isArray(f.code_smells) && f.code_smells.length > 0 && (
                <div>
                  <strong className="text-[var(--accent-red)]">Code Smells:</strong>
                  <ListItems items={f.code_smells} />
                </div>
              )}
              <ConfidenceBadge confidence={f.confidence} />
            </div>
          </details>
        );
      })}
    </div>
  );
}

function FunctionsPanel({ data }: { data: unknown }) {
  const funcs = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>;
  if (funcs.length === 0) return <JsonBlock data={data} />;
  return (
    <div className="space-y-3">
      {funcs.map((f, i) => (
        <details key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
          <summary className="cursor-pointer">
            <span className="font-mono text-[var(--accent)]">{String(f.function_name)}</span>
            <span className="text-xs text-[var(--text-secondary)] ml-2">{String(f.file_path || "")}</span>
          </summary>
          <div className="mt-3 space-y-2 text-sm">
            <p><strong>Description:</strong> {String(f.description || "")}</p>
            <p><strong>Logic:</strong> {String(f.logic || "")}</p>
            <p><strong>External:</strong> {String(f.external_interaction || "None")}</p>
            {Array.isArray(f.edge_cases) && f.edge_cases.length > 0 && (
              <div><strong>Edge Cases:</strong><ListItems items={f.edge_cases} /></div>
            )}
            {f.performance_notes ? (
              <p><strong>Performance:</strong> {String(f.performance_notes)}</p>
            ) : null}
            <ConfidenceBadge confidence={f.confidence} />
          </div>
        </details>
      ))}
    </div>
  );
}

function DepsPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
      <Section title="Core Modules"><ListItems items={d.core_modules as string[]} /></Section>
      <Section title="Isolated Components"><ListItems items={d.isolated_components as string[]} /></Section>
      <Section title="Circular Dependencies">
        {(d.circular_dependencies as string[][] || []).length === 0 ? (
          <p className="text-[var(--accent-green)]">No circular dependencies detected</p>
        ) : (
          <JsonBlock data={d.circular_dependencies} />
        )}
      </Section>
      {d.graph_data && (
        <Section title="Graph Statistics">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center">
              <p className="text-2xl font-bold text-[var(--accent)]">{String((d.graph_data as Record<string, unknown>).total_files)}</p>
              <p className="text-xs text-[var(--text-secondary)]">Files</p>
            </div>
            <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center">
              <p className="text-2xl font-bold text-[var(--accent)]">{String((d.graph_data as Record<string, unknown>).total_dependencies)}</p>
              <p className="text-xs text-[var(--text-secondary)]">Dependencies</p>
            </div>
          </div>
        </Section>
      )}
    </>
  );
}

// ============ NEW: Call Graph Panel ============

function CallGraphPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        {[
          { label: "Functions", value: d.total_functions },
          { label: "Call Edges", value: d.total_calls },
          { label: "Entry Points", value: Array.isArray(d.entry_points) ? d.entry_points.length : 0 },
        ].map((s, i) => (
          <div key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
            <p className="text-2xl font-bold text-[var(--accent)]">{String(s.value)}</p>
            <p className="text-xs text-[var(--text-secondary)]">{s.label}</p>
          </div>
        ))}
      </div>

      <Section title="Entry Points (No Callers)">
        {Array.isArray(d.entry_points) && d.entry_points.length > 0 ? (
          <div className="space-y-1">
            {(d.entry_points as Array<Record<string, string>>).map((ep, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-[var(--accent-green)]">→</span>
                <span className="font-mono">{ep.name}</span>
                <span className="text-xs text-[var(--text-secondary)]">{ep.file}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[var(--text-secondary)]">None detected</p>
        )}
      </Section>

      <Section title="Hot Functions (Most Called)">
        {Array.isArray(d.hot_functions) && d.hot_functions.length > 0 ? (
          <div className="space-y-2">
            {(d.hot_functions as Array<Record<string, unknown>>).map((hf, i) => (
              <div key={i} className="flex items-center gap-3 p-2 bg-[var(--bg-primary)] rounded border border-[var(--border)]">
                <span className="text-lg font-bold text-[var(--accent-red)]">{String(hf.callers)}</span>
                <div>
                  <span className="font-mono text-sm">{String(hf.name)}</span>
                  <span className="text-xs text-[var(--text-secondary)] ml-2">{String(hf.file)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[var(--text-secondary)]">None detected</p>
        )}
      </Section>

      <Section title="Leaf Functions (No Outgoing Calls)">
        <ListItems items={(d.leaf_functions as Array<Record<string, string>> || []).map(f => `${f.name} (${f.file})`)} />
      </Section>
    </>
  );
}

// ============ NEW: Abstraction Views Panel ============

function AbstractionViewsPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const [view, setView] = useState<"beginner" | "developer" | "architect">("beginner");
  const viewLabels = [
    { key: "beginner" as const, label: "Beginner", desc: "Simple explanation" },
    { key: "developer" as const, label: "Developer", desc: "Modules + flow" },
    { key: "architect" as const, label: "Architect", desc: "Design + tradeoffs" },
  ];

  const beginner = d.beginner as Record<string, unknown> | undefined;
  const developer = d.developer as Record<string, unknown> | undefined;
  const architect = d.architect as Record<string, unknown> | undefined;

  return (
    <>
      <ConfidenceBadge confidence={d.confidence} />
      <div className="flex gap-2 mb-6">
        {viewLabels.map((v) => (
          <button
            key={v.key}
            onClick={() => setView(v.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex-1 ${
              view === v.key
                ? "bg-[var(--accent)] text-[var(--bg-primary)]"
                : "bg-[var(--bg-secondary)] text-[var(--text-secondary)]"
            }`}
          >
            <div>{v.label}</div>
            <div className="text-xs opacity-70">{v.desc}</div>
          </button>
        ))}
      </div>

      {view === "beginner" && beginner && (
        <>
          <Section title="What Does This Software Do?">
            <p className="text-lg">{String(beginner.summary || "")}</p>
          </Section>
          {beginner.analogy ? (
            <Section title="Think Of It Like...">
              <p className="italic text-[var(--accent)]">{String(beginner.analogy)}</p>
            </Section>
          ) : null}
          <Section title="Key Concepts"><ListItems items={beginner.key_concepts as string[]} /></Section>
        </>
      )}

      {view === "developer" && developer && (
        <>
          <Section title="Developer Summary"><p>{String(developer.summary || "")}</p></Section>
          <Section title="Module Guide"><ListItems items={developer.module_guide as string[]} /></Section>
          <Section title="Key Patterns"><ListItems items={developer.key_patterns as string[]} /></Section>
          <Section title="Start Reading Here"><ListItems items={developer.start_reading as string[]} /></Section>
          {Array.isArray(developer.gotchas) && developer.gotchas.length > 0 && (
            <Section title="Gotchas"><ListItems items={developer.gotchas as string[]} /></Section>
          )}
        </>
      )}

      {view === "architect" && architect && (
        <>
          <Section title="Architect Summary"><p>{String(architect.summary || "")}</p></Section>
          <Section title="Design Patterns"><ListItems items={architect.design_patterns as string[]} /></Section>
          <Section title="Tradeoffs"><ListItems items={architect.tradeoffs as string[]} /></Section>
          {architect.scalability ? (
            <Section title="Scalability"><p>{String(architect.scalability)}</p></Section>
          ) : null}
          <Section title="Technical Debt"><ListItems items={architect.technical_debt as string[]} /></Section>
          <Section title="What Would Change At Scale"><ListItems items={architect.at_scale_changes as string[]} /></Section>
        </>
      )}
    </>
  );
}

// ============ NEW: Recommendations Panel ============

function RecommendationsPanel({ data }: { data: unknown }) {
  const recs = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>;
  if (recs.length === 0) return <JsonBlock data={data} />;

  const effortColor = (e: string) => e === "low" ? "badge-green" : e === "medium" ? "badge-yellow" : "badge-red";
  const impactColor = (i: string) => i === "high" ? "badge-green" : i === "medium" ? "badge-yellow" : "badge-red";

  return (
    <div className="space-y-4">
      {recs.map((rec, i) => (
        <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="font-semibold text-[var(--accent)]">
                {String(rec.priority ? `#${rec.priority} ` : "")}
                {String(rec.title || `Recommendation ${i + 1}`)}
              </h4>
              {rec.category ? (
                <span className="badge badge-blue text-xs mt-1 inline-block">{String(rec.category)}</span>
              ) : null}
            </div>
            <div className="flex gap-1">
              {rec.effort ? <span className={`badge ${effortColor(String(rec.effort))} text-xs`}>Effort: {String(rec.effort)}</span> : null}
              {rec.impact ? <span className={`badge ${impactColor(String(rec.impact))} text-xs`}>Impact: {String(rec.impact)}</span> : null}
            </div>
          </div>
          <p className="text-sm mt-2">{String(rec.description || "")}</p>
          {Array.isArray(rec.affected_files) && rec.affected_files.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {rec.affected_files.map((f: unknown, j: number) => (
                <span key={j} className="text-xs font-mono px-2 py-0.5 bg-[var(--bg-secondary)] rounded">{itemToString(f)}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ============ Existing Panels ============

function FlowPanel({ data }: { data: Record<string, unknown> }) {
  const flow = data.system_flow as Record<string, unknown> | undefined;
  const diagram = data.flow_diagram as string | undefined;
  return (
    <>
      {flow && (
        <>
          <ConfidenceBadge confidence={flow.confidence} />
          <Section title="Entry Point"><p>{String(flow.entry_point || "")}</p></Section>
          <Section title="Execution Steps"><ListItems items={flow.steps as string[]} /></Section>
          <Section title="Processing Stages"><ListItems items={flow.processing_stages as string[]} /></Section>
          {flow.e2e_trace ? (
            <Section title="End-to-End Trace"><p className="font-mono text-sm">{String(flow.e2e_trace)}</p></Section>
          ) : null}
        </>
      )}
      {diagram && (
        <Section title="Flow Diagram (Mermaid)">
          <pre className="text-sm bg-[var(--bg-primary)] p-4 rounded-lg border border-[var(--border)] overflow-x-auto">{diagram}</pre>
        </Section>
      )}
    </>
  );
}

function ProductionPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  const score = Number(d.score || 0);
  const detScore = d.deterministic_score as number | undefined;
  return (
    <>
      <ConfidenceBadge confidence={d.confidence} />
      <Section title="Production Readiness Score">
        <div className="space-y-3">
          <ScoreBar score={score} label="LLM Assessment" />
          {detScore !== undefined && <ScoreBar score={detScore} label="Deterministic" />}
        </div>
      </Section>
      <Section title="Strengths"><ListItems items={d.strengths as string[]} /></Section>
      <Section title="Weaknesses"><ListItems items={d.weaknesses as string[]} /></Section>
      <Section title="Missing Components"><ListItems items={d.missing_components as string[]} /></Section>
      {Array.isArray(d.deterministic_details) && d.deterministic_details.length > 0 && (
        <Section title="Verified Details">
          {(d.deterministic_details as string[]).map((det, i) => (
            <p key={i} className="text-sm text-[var(--accent-green)] flex items-start gap-2"><span>✓</span><span>{det}</span></p>
          ))}
        </Section>
      )}
      {Array.isArray(d.deterministic_issues) && d.deterministic_issues.length > 0 && (
        <Section title="Verified Issues">
          {(d.deterministic_issues as string[]).map((iss, i) => (
            <p key={i} className="text-sm text-[var(--accent-red)] flex items-start gap-2"><span>✗</span><span>{iss}</span></p>
          ))}
        </Section>
      )}
    </>
  );
}

function SecurityPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const issues = d.issues as Array<Record<string, unknown>> | string[] | undefined;
  const detScore = d.deterministic_score as number | undefined;

  return (
    <>
      <ConfidenceBadge confidence={d.confidence} />
      <Section title="Overall Severity">
        <span className={`badge ${
          d.overall_severity === "critical" || d.overall_severity === "high" ? "badge-red"
          : d.overall_severity === "medium" ? "badge-yellow" : "badge-green"
        }`}>{String(d.overall_severity || d.severity || "unknown")}</span>
        {detScore !== undefined && (
          <span className="ml-3"><ScoreBar score={detScore} label="Deterministic Score" /></span>
        )}
      </Section>
      <Section title="Issues">
        {Array.isArray(issues) && issues.length > 0 ? (
          <div className="space-y-2">
            {issues.map((issue, i) => {
              if (typeof issue === "object" && issue !== null) {
                const obj = issue as Record<string, unknown>;
                const sevColor = String(obj.severity || "") === "critical" ? "badge-red"
                  : String(obj.severity || "") === "high" ? "badge-red"
                  : String(obj.severity || "") === "medium" ? "badge-yellow" : "badge-green";
                return (
                  <div key={i} className="p-3 bg-[var(--bg-primary)] rounded border border-[var(--border)]">
                    <div className="flex items-center gap-2">
                      <span className={`badge ${sevColor} text-xs`}>{String(obj.severity || "")}</span>
                      <span className="font-medium text-sm">{String(obj.type || "")}</span>
                    </div>
                    <p className="text-sm mt-1">{String(obj.description || "")}</p>
                    {obj.location ? <p className="text-xs font-mono text-[var(--text-secondary)] mt-1">{String(obj.location)}</p> : null}
                    {obj.fix ? <p className="text-xs text-[var(--accent-green)] mt-1">Fix: {String(obj.fix)}</p> : null}
                  </div>
                );
              }
              return <p key={i} className="text-sm">• {itemToString(issue)}</p>;
            })}
          </div>
        ) : (
          <p className="text-[var(--accent-green)]">No issues detected</p>
        )}
      </Section>
      <Section title="Recommendations"><ListItems items={d.recommendations as string[]} /></Section>
      {Array.isArray(d.deterministic_issues) && d.deterministic_issues.length > 0 && (
        <Section title="Detected by Static Analysis">
          {(d.deterministic_issues as string[]).map((iss, i) => (
            <p key={i} className="text-sm text-[var(--accent-red)] flex items-start gap-2"><span>⚠</span><span>{iss}</span></p>
          ))}
        </Section>
      )}
    </>
  );
}

function CostPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
      <Section title="Cost Level"><span className="badge badge-blue">{String(d.cost_level || "")}</span></Section>
      <Section title="Paid Tools"><ListItems items={d.paid_tools as string[]} /></Section>
      <Section title="Free Alternatives"><ListItems items={d.free_alternatives as string[]} /></Section>
    </>
  );
}

function InterviewPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
      <ConfidenceBadge confidence={d.confidence} />
      <Section title="High-Level Explanation"><p>{String(d.explanation || "")}</p></Section>
      <Section title="Architecture"><p>{String(d.architecture || "")}</p></Section>
      <Section title="Key Challenges"><ListItems items={d.challenges as string[]} /></Section>
      <Section title="Design Decisions"><ListItems items={d.design_decisions as string[]} /></Section>
    </>
  );
}

function SynthesisPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
      <ConfidenceBadge confidence={d.confidence} />
      <Section title="Overview"><p>{String(d.overview || "")}</p></Section>
      <Section title="Architecture"><p>{String(d.architecture || "")}</p></Section>
      <Section title="Modules"><p>{String(d.modules || "")}</p></Section>
      <Section title="Flow"><p>{String(d.flow || "")}</p></Section>
      <Section title="Strengths"><ListItems items={d.strengths as string[]} /></Section>
      <Section title="Weaknesses"><ListItems items={d.weaknesses as string[]} /></Section>
    </>
  );
}

// ============ API Contracts Panel ============

function APIContractsPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const endpoints = (Array.isArray(d.endpoints) ? d.endpoints : []) as Array<Record<string, unknown>>;
  const totalEndpoints = Number(d.total_endpoints || endpoints.length);

  const methodColor = (m: string) => {
    const upper = m.toUpperCase();
    return upper === "GET" ? "badge-green" : upper === "POST" ? "badge-blue" : upper === "PUT" ? "badge-yellow" : upper === "DELETE" ? "badge-red" : "badge-blue";
  };

  return (
    <>
      <div className="text-center mb-6 p-4 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
        <p className="text-4xl font-bold text-[var(--accent)]">{totalEndpoints}</p>
        <p className="text-[var(--text-secondary)]">API Endpoints Detected</p>
      </div>

      {endpoints.length === 0 ? (
        <p className="text-[var(--text-secondary)]">No API endpoints detected</p>
      ) : (
        <div className="space-y-2">
          {endpoints.map((ep, i) => (
            <div key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
              <div className="flex items-center gap-3">
                <span className={`badge ${methodColor(String(ep.method || ""))} text-xs font-mono`}>
                  {String(ep.method || "").toUpperCase()}
                </span>
                <span className="font-mono text-sm text-[var(--accent)]">{String(ep.path || "")}</span>
                {ep.auth_required && <span className="badge badge-yellow text-xs">Auth</span>}
              </div>
              {ep.description && <p className="text-sm text-[var(--text-secondary)] mt-1">{String(ep.description)}</p>}
              <div className="flex flex-wrap gap-2 mt-2 text-xs text-[var(--text-secondary)]">
                {ep.file && <span className="font-mono">{String(ep.file)}</span>}
                {ep.input_params && <span>Params: {String(ep.input_params)}</span>}
                {ep.output_model && <span>Response: {String(ep.output_model)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ============ DB Schema Panel ============

function DBSchemaPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const models = (Array.isArray(d.models) ? d.models : []) as Array<Record<string, unknown>>;
  const relationships = (Array.isArray(d.relationships) ? d.relationships : []) as Array<Record<string, unknown>>;

  return (
    <>
      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
          <p className="text-2xl font-bold text-[var(--accent)]">{models.length}</p>
          <p className="text-xs text-[var(--text-secondary)]">Models</p>
        </div>
        <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
          <p className="text-2xl font-bold text-[var(--accent)]">{relationships.length}</p>
          <p className="text-xs text-[var(--text-secondary)]">Relationships</p>
        </div>
      </div>

      <Section title="Models">
        {models.length === 0 ? (
          <p className="text-[var(--text-secondary)]">No database models detected</p>
        ) : (
          <div className="space-y-3">
            {models.map((m, i) => (
              <details key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
                <summary className="cursor-pointer flex items-center gap-2">
                  <span className="font-semibold text-[var(--accent)]">{String(m.name || m.model || "")}</span>
                  {m.table_name && <span className="text-xs font-mono text-[var(--text-secondary)]">({String(m.table_name)})</span>}
                  {m.orm && <span className="badge badge-blue text-xs">{String(m.orm)}</span>}
                </summary>
                <div className="mt-2">
                  {m.file && <p className="text-xs font-mono text-[var(--text-secondary)] mb-2">{String(m.file)}</p>}
                  {Array.isArray(m.fields) && m.fields.length > 0 && (
                    <div className="space-y-1">
                      {(m.fields as Array<Record<string, unknown>>).map((f, j) => (
                        <div key={j} className="flex items-center gap-2 text-sm">
                          <span className="font-mono text-[var(--accent)]">{String(f.name || "")}</span>
                          <span className="text-[var(--text-secondary)]">{String(f.type || "")}</span>
                          {f.primary_key && <span className="badge badge-yellow text-xs">PK</span>}
                          {f.nullable === false && <span className="badge badge-red text-xs">NOT NULL</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </details>
            ))}
          </div>
        )}
      </Section>

      {relationships.length > 0 && (
        <Section title="Relationships">
          <div className="space-y-1">
            {relationships.map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="font-mono text-[var(--accent)]">{String(r.from || r.source || "")}</span>
                <span className="text-[var(--text-secondary)]">→</span>
                <span className="font-mono text-[var(--accent)]">{String(r.to || r.target || "")}</span>
                {r.type && <span className="badge badge-blue text-xs">{String(r.type)}</span>}
              </div>
            ))}
          </div>
        </Section>
      )}
    </>
  );
}

// ============ Performance Bottlenecks Panel ============

function PerfBottlenecksPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const issues = (Array.isArray(d.issues) ? d.issues : []) as Array<Record<string, unknown>>;
  const totalIssues = Number(d.total_issues || issues.length);

  const sevColor = (s: string) =>
    s === "critical" ? "badge-red" : s === "high" ? "badge-red" : s === "medium" ? "badge-yellow" : "badge-green";

  return (
    <>
      <div className="text-center mb-6 p-4 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
        <p className="text-4xl font-bold" style={{
          color: totalIssues > 5 ? "var(--accent-red)" : totalIssues > 0 ? "var(--accent-yellow)" : "var(--accent-green)"
        }}>{totalIssues}</p>
        <p className="text-[var(--text-secondary)]">Performance Issues Detected</p>
      </div>

      {issues.length === 0 ? (
        <p className="text-[var(--accent-green)]">No performance bottlenecks detected</p>
      ) : (
        <div className="space-y-3">
          {issues.map((iss, i) => (
            <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
              <div className="flex items-center gap-2 mb-2">
                <span className={`badge ${sevColor(String(iss.severity || "medium"))} text-xs`}>
                  {String(iss.severity || "medium")}
                </span>
                <span className="badge badge-blue text-xs">{String(iss.type || iss.category || "")}</span>
              </div>
              <p className="font-medium text-sm">{String(iss.description || iss.issue || "")}</p>
              {iss.file && (
                <p className="text-xs font-mono text-[var(--text-secondary)] mt-1">
                  {String(iss.file)}{iss.line ? `:${iss.line}` : ""}
                </p>
              )}
              {iss.fix && (
                <p className="text-xs text-[var(--accent-green)] mt-1">Fix: {String(iss.fix)}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ============ Complexity Panel ============

function ComplexityPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const score = Number(d.score || 0);
  const level = String(d.level || "");
  const breakdown = d.breakdown as Record<string, unknown> | undefined;

  const levelColor = level === "critical" ? "var(--accent-red)" : level === "high" ? "var(--accent-red)" : level === "moderate" ? "var(--accent-yellow)" : "var(--accent-green)";

  return (
    <>
      <div className="text-center mb-8 p-6 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
        <p className="text-6xl font-bold mb-2" style={{ color: levelColor }}>{score}/10</p>
        <p className="text-[var(--text-secondary)] text-lg">Complexity Score</p>
        <span className={`badge ${level === "critical" || level === "high" ? "badge-red" : level === "moderate" ? "badge-yellow" : "badge-green"} mt-2`}>
          {level.toUpperCase()}
        </span>
      </div>

      {breakdown && (
        <Section title="Score Breakdown">
          <div className="space-y-3">
            {Object.entries(breakdown).map(([key, val]) => {
              const v = val as Record<string, unknown>;
              return (
                <div key={key} className="flex items-center justify-between p-2 bg-[var(--bg-primary)] rounded border border-[var(--border)]">
                  <span className="text-sm font-medium">{key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</span>
                  <span className="font-bold text-[var(--accent)]">
                    {typeof v === "number" ? String(v) : typeof v === "object" && v ? String(v.score || v.value || JSON.stringify(v)) : String(v)}
                  </span>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {Array.isArray(d.details) && d.details.length > 0 && (
        <Section title="Details"><ListItems items={d.details as string[]} /></Section>
      )}

      {Array.isArray(d.hotspots) && d.hotspots.length > 0 && (
        <Section title="Complexity Hotspots">
          <div className="space-y-1">
            {(d.hotspots as Array<Record<string, unknown>>).map((h, i) => (
              <div key={i} className="flex items-center justify-between text-sm p-2 bg-[var(--bg-primary)] rounded">
                <span className="font-mono">{String(h.file || h.name || "")}</span>
                <span className="font-bold text-[var(--accent-red)]">{String(h.complexity || h.score || "")}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </>
  );
}

// ============ Architecture Panel ============

function ArchitecturePanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const patterns = (Array.isArray(d.patterns) ? d.patterns : []) as Array<Record<string, unknown>>;

  return (
    <>
      {d.primary_pattern && (
        <div className="text-center mb-6 p-4 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
          <p className="text-2xl font-bold text-[var(--accent)]">{String(d.primary_pattern)}</p>
          <p className="text-[var(--text-secondary)]">Primary Architecture Pattern</p>
        </div>
      )}

      <Section title="Detected Patterns">
        {patterns.length === 0 ? (
          <p className="text-[var(--text-secondary)]">No specific patterns detected</p>
        ) : (
          <div className="space-y-3">
            {patterns.map((p, i) => (
              <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-semibold text-[var(--accent)]">{String(p.pattern || p.name || "")}</h4>
                  {p.confidence !== undefined && <ConfidenceBadge confidence={p.confidence} />}
                </div>
                {p.description && <p className="text-sm text-[var(--text-secondary)]">{String(p.description)}</p>}
                {Array.isArray(p.evidence) && p.evidence.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {p.evidence.map((e: unknown, j: number) => (
                      <span key={j} className="text-xs font-mono px-2 py-0.5 bg-[var(--bg-secondary)] rounded">{itemToString(e)}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      {Array.isArray(d.layers) && d.layers.length > 0 && (
        <Section title="Architectural Layers">
          <div className="space-y-2">
            {(d.layers as Array<Record<string, unknown>>).map((l, i) => (
              <div key={i} className="flex items-center gap-3 p-2 bg-[var(--bg-primary)] rounded border border-[var(--border)]">
                <span className="text-lg font-bold text-[var(--accent)]">{i + 1}</span>
                <div>
                  <span className="font-medium">{String(l.name || l.layer || "")}</span>
                  {l.description && <p className="text-xs text-[var(--text-secondary)]">{String(l.description)}</p>}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </>
  );
}

// ============ Security Threats Panel ============

function SecurityThreatsPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const threats = (Array.isArray(d.threats) ? d.threats : []) as Array<Record<string, unknown>>;
  const overallRisk = String(d.overall_risk || "unknown");

  const riskColor = (r: string) =>
    r === "critical" ? "badge-red" : r === "high" ? "badge-red" : r === "medium" ? "badge-yellow" : "badge-green";

  return (
    <>
      <div className="text-center mb-6 p-4 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
        <span className={`badge ${riskColor(overallRisk)} text-lg px-4 py-1`}>
          Overall Risk: {overallRisk.toUpperCase()}
        </span>
      </div>

      <ConfidenceBadge confidence={d.confidence} />

      <Section title="Threats">
        {threats.length === 0 ? (
          <p className="text-[var(--accent-green)]">No security threats identified</p>
        ) : (
          <div className="space-y-3">
            {threats.map((t, i) => (
              <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className={`badge ${riskColor(String(t.severity || ""))} text-xs`}>
                    {String(t.severity || "")}
                  </span>
                  {t.category && <span className="badge badge-blue text-xs">{String(t.category)}</span>}
                  {t.likelihood && (
                    <span className="text-xs text-[var(--text-secondary)]">
                      Likelihood: {String(t.likelihood)}
                    </span>
                  )}
                </div>
                <p className="font-medium text-sm">{String(t.threat || t.description || "")}</p>
                {t.attack_surface && (
                  <p className="text-xs text-[var(--text-secondary)] mt-1">Attack Surface: {String(t.attack_surface)}</p>
                )}
                {t.impact && (
                  <p className="text-xs text-[var(--accent-red)] mt-1">Impact: {String(t.impact)}</p>
                )}
                {t.mitigation && (
                  <p className="text-xs text-[var(--accent-green)] mt-1">Mitigation: {String(t.mitigation)}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      {Array.isArray(d.attack_surfaces) && d.attack_surfaces.length > 0 && (
        <Section title="Attack Surfaces"><ListItems items={d.attack_surfaces as string[]} /></Section>
      )}

      {Array.isArray(d.recommendations) && d.recommendations.length > 0 && (
        <Section title="Recommendations"><ListItems items={d.recommendations as string[]} /></Section>
      )}
    </>
  );
}

// ============ Failure Modes Panel ============

function FailureModesPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const modes = (Array.isArray(d.failure_modes) ? d.failure_modes : []) as Array<Record<string, unknown>>;
  const resilienceScore = d.resilience_score as number | undefined;

  const probColor = (p: string) =>
    p === "high" ? "badge-red" : p === "medium" ? "badge-yellow" : "badge-green";

  return (
    <>
      {resilienceScore !== undefined && (
        <div className="text-center mb-6 p-4 bg-[var(--bg-primary)] rounded-xl border border-[var(--border)]">
          <p className="text-4xl font-bold" style={{
            color: resilienceScore >= 7 ? "var(--accent-green)" : resilienceScore >= 4 ? "var(--accent-yellow)" : "var(--accent-red)"
          }}>{resilienceScore}/10</p>
          <p className="text-[var(--text-secondary)]">Resilience Score</p>
        </div>
      )}

      <ConfidenceBadge confidence={d.confidence} />

      <Section title="Failure Modes">
        {modes.length === 0 ? (
          <p className="text-[var(--accent-green)]">No critical failure modes detected</p>
        ) : (
          <div className="space-y-3">
            {modes.map((m, i) => (
              <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`badge ${probColor(String(m.probability || "low"))} text-xs`}>
                    {String(m.probability || "low")} probability
                  </span>
                </div>
                <p className="font-medium text-sm">{String(m.mode || m.description || "")}</p>
                {m.impact && <p className="text-xs text-[var(--accent-red)] mt-1">Impact: {String(m.impact)}</p>}
                {Array.isArray(m.affected_components) && m.affected_components.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {m.affected_components.map((c: unknown, j: number) => (
                      <span key={j} className="text-xs font-mono px-2 py-0.5 bg-[var(--bg-secondary)] rounded">{itemToString(c)}</span>
                    ))}
                  </div>
                )}
                {m.current_handling && (
                  <p className="text-xs text-[var(--text-secondary)] mt-1">Current: {String(m.current_handling)}</p>
                )}
                {m.recommendation && (
                  <p className="text-xs text-[var(--accent-green)] mt-1">Fix: {String(m.recommendation)}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      {Array.isArray(d.critical_gaps) && d.critical_gaps.length > 0 && (
        <Section title="Critical Gaps"><ListItems items={d.critical_gaps as string[]} /></Section>
      )}
    </>
  );
}

// ============ Timeline Panel ============

function TimelinePanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  if (d.available === false) {
    return <p className="text-[var(--text-secondary)]">Git history not available: {String(d.error || "")}</p>;
  }

  const timeSpan = d.time_span as Record<string, unknown> | undefined;
  const velocity = d.velocity as Record<string, unknown> | undefined;
  const contributors = d.contributors as Record<string, unknown> | undefined;
  const hotspots = (Array.isArray(d.hotspots) ? d.hotspots : []) as Array<Record<string, unknown>>;
  const activeModules = (Array.isArray(d.active_modules) ? d.active_modules : []) as Array<Record<string, unknown>>;
  const abandonedCode = (Array.isArray(d.abandoned_code) ? d.abandoned_code : []) as Array<Record<string, unknown>>;
  const recentActivity = (Array.isArray(d.recent_activity) ? d.recent_activity : []) as Array<Record<string, unknown>>;

  const trendColor = (t: string) =>
    t === "accelerating" ? "badge-green" : t === "decelerating" ? "badge-red" : "badge-yellow";

  return (
    <>
      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
          <p className="text-2xl font-bold text-[var(--accent)]">{String(d.total_commits || 0)}</p>
          <p className="text-xs text-[var(--text-secondary)]">Commits</p>
        </div>
        {timeSpan && (
          <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
            <p className="text-2xl font-bold text-[var(--accent)]">{String(timeSpan.span_human || "")}</p>
            <p className="text-xs text-[var(--text-secondary)]">Time Span</p>
          </div>
        )}
        {contributors && (
          <>
            <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
              <p className="text-2xl font-bold text-[var(--accent)]">{String(contributors.total || 0)}</p>
              <p className="text-xs text-[var(--text-secondary)]">Contributors</p>
            </div>
            <div className="p-3 bg-[var(--bg-primary)] rounded-lg text-center border border-[var(--border)]">
              <p className="text-2xl font-bold" style={{
                color: Number(contributors.bus_factor || 0) <= 1 ? "var(--accent-red)" : "var(--accent)"
              }}>{String(contributors.bus_factor || 0)}</p>
              <p className="text-xs text-[var(--text-secondary)]">Bus Factor</p>
            </div>
          </>
        )}
      </div>

      {/* Velocity */}
      {velocity && (
        <Section title="Development Velocity">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm">Avg: <strong>{String(velocity.avg_commits_per_week || 0)}</strong> commits/week</span>
            <span className={`badge ${trendColor(String(velocity.trend || ""))} text-xs`}>
              {String(velocity.trend || "stable")}
            </span>
          </div>
          {Array.isArray(velocity.weekly_breakdown) && (
            <div className="flex items-end gap-1 h-16">
              {(velocity.weekly_breakdown as number[]).map((count, i) => {
                const max = Math.max(...(velocity.weekly_breakdown as number[]), 1);
                const h = (count / max) * 100;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                    <div
                      className="w-full rounded-t"
                      style={{ height: `${h}%`, background: i < 4 ? "var(--accent)" : "var(--text-secondary)", minHeight: count > 0 ? "4px" : "0" }}
                      title={`Week -${i}: ${count} commits`}
                    />
                  </div>
                );
              })}
            </div>
          )}
          <div className="flex justify-between text-xs text-[var(--text-secondary)] mt-1">
            <span>This week</span>
            <span>12 weeks ago</span>
          </div>
        </Section>
      )}

      {/* Top Contributors */}
      {contributors && Array.isArray((contributors as Record<string, unknown>).top_contributors) && (
        <Section title="Top Contributors">
          <div className="space-y-2">
            {((contributors as Record<string, unknown>).top_contributors as Array<Record<string, unknown>>).map((c, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-sm font-medium w-40 truncate">{String(c.name || "")}</span>
                <div className="flex-1 score-bar">
                  <div className="score-fill" style={{ width: `${Number(c.percentage || 0)}%`, background: "var(--accent)" }} />
                </div>
                <span className="text-xs text-[var(--text-secondary)]">{String(c.commits || 0)} ({String(c.percentage || 0)}%)</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Hotspots */}
      {hotspots.length > 0 && (
        <Section title="Change Hotspots (Bug-Prone)">
          <div className="space-y-1">
            {hotspots.slice(0, 10).map((h, i) => (
              <div key={i} className="flex items-center justify-between text-sm p-2 bg-[var(--bg-primary)] rounded border border-[var(--border)]">
                <span className="font-mono truncate flex-1">{String(h.file || "")}</span>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-[var(--text-secondary)]">{String(h.total_changes || 0)} changes</span>
                  <span className={`badge ${h.bug_risk === "high" ? "badge-red" : h.bug_risk === "medium" ? "badge-yellow" : "badge-green"} text-xs`}>
                    {String(h.bug_risk || "low")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Active Modules */}
      {activeModules.length > 0 && (
        <Section title="Active Modules (Last 30 Days)">
          <div className="flex flex-wrap gap-2">
            {activeModules.map((m, i) => (
              <span key={i} className="badge badge-green text-xs">
                {String(m.module || "")} ({String(m.recent_changes || 0)} changes)
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Abandoned Code */}
      {abandonedCode.length > 0 && (
        <Section title="Stale/Abandoned Code">
          <div className="space-y-1">
            {abandonedCode.slice(0, 10).map((a, i) => (
              <div key={i} className="flex items-center justify-between text-sm p-2 bg-[var(--bg-primary)] rounded">
                <span className="font-mono truncate flex-1">{String(a.file || "")}</span>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-[var(--text-secondary)]">{String(a.last_changed_days_ago || 0)}d ago</span>
                  <span className={`badge ${a.status === "abandoned" ? "badge-red" : "badge-yellow"} text-xs`}>
                    {String(a.status || "")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Recent Activity */}
      {recentActivity.length > 0 && (
        <Section title="Recent Commits">
          <div className="space-y-1">
            {recentActivity.map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-sm p-2 bg-[var(--bg-primary)] rounded">
                <span className="font-mono text-xs text-[var(--accent)] shrink-0">{String(c.hash || "")}</span>
                <span className="flex-1 truncate">{String(c.message || "")}</span>
                <span className="text-xs text-[var(--text-secondary)] shrink-0">{String(c.author || "")}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </>
  );
}

// ============ Auto Docs Panel ============

function AutoDocsPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;

  const modules = (Array.isArray(d.modules) ? d.modules : []) as Array<Record<string, unknown>>;
  const endpoints = (Array.isArray(d.api_endpoints) ? d.api_endpoints : []) as Array<Record<string, unknown>>;
  const config = (Array.isArray(d.configuration) ? d.configuration : []) as Array<Record<string, unknown>>;
  const setup = (Array.isArray(d.setup) ? d.setup : []) as string[];

  return (
    <>
      <ConfidenceBadge confidence={d.confidence} />

      {d.title && (
        <h2 className="text-2xl font-bold text-[var(--accent)] mb-4">{String(d.title)}</h2>
      )}

      <Section title="Overview">
        <p className="whitespace-pre-line">{String(d.overview || "")}</p>
      </Section>

      <Section title="Architecture">
        <p className="whitespace-pre-line">{String(d.architecture || "")}</p>
      </Section>

      {setup.length > 0 && (
        <Section title="Setup Instructions">
          <ol className="list-decimal list-inside space-y-1">
            {setup.map((step, i) => (
              <li key={i} className="text-sm">{itemToString(step)}</li>
            ))}
          </ol>
        </Section>
      )}

      {modules.length > 0 && (
        <Section title="Modules">
          <div className="space-y-2">
            {modules.map((m, i) => (
              <div key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
                <h4 className="font-semibold text-[var(--accent)]">{String(m.name || "")}</h4>
                <p className="text-sm text-[var(--text-secondary)]">{String(m.description || "")}</p>
                {Array.isArray(m.key_files) && m.key_files.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {m.key_files.map((f: unknown, j: number) => (
                      <span key={j} className="text-xs font-mono px-2 py-0.5 bg-[var(--bg-secondary)] rounded">{itemToString(f)}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {endpoints.length > 0 && (
        <Section title="API Endpoints">
          <div className="space-y-1">
            {endpoints.map((ep, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="badge badge-blue text-xs font-mono">{String(ep.method || "")}</span>
                <span className="font-mono text-[var(--accent)]">{String(ep.path || "")}</span>
                <span className="text-[var(--text-secondary)]">{String(ep.description || "")}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {config.length > 0 && (
        <Section title="Configuration">
          <div className="space-y-1">
            {config.map((c, i) => (
              <div key={i} className="flex items-center gap-3 text-sm p-2 bg-[var(--bg-primary)] rounded">
                <span className="font-mono text-[var(--accent)]">{String(c.name || "")}</span>
                <span className="text-[var(--text-secondary)] flex-1">{String(c.description || "")}</span>
                {c.default && <span className="text-xs font-mono text-[var(--text-secondary)]">Default: {String(c.default)}</span>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {d.tech_stack_summary && (
        <Section title="Tech Stack Summary">
          <p>{String(d.tech_stack_summary)}</p>
        </Section>
      )}
    </>
  );
}

"use client";
import { useState } from "react";

interface Props {
  data: Record<string, unknown>;
}

type TabKey =
  | "overview"
  | "tech"
  | "modules"
  | "files"
  | "functions"
  | "dependencies"
  | "flow"
  | "production"
  | "security"
  | "cost"
  | "interview"
  | "synthesis";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "tech", label: "Tech Stack" },
  { key: "modules", label: "Modules" },
  { key: "files", label: "Files" },
  { key: "functions", label: "Functions" },
  { key: "dependencies", label: "Dependencies" },
  { key: "flow", label: "System Flow" },
  { key: "production", label: "Production" },
  { key: "security", label: "Security" },
  { key: "cost", label: "Cost" },
  { key: "interview", label: "Interview" },
  { key: "synthesis", label: "Synthesis" },
];

export default function ResultDashboard({ data }: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  return (
    <div className="max-w-6xl mx-auto">
      {/* Tab nav */}
      <div className="flex flex-wrap gap-2 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === tab.key
                ? "bg-[var(--accent)] text-[var(--bg-primary)]"
                : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="card">
        {activeTab === "overview" && <OverviewPanel data={data.repo_overview} />}
        {activeTab === "tech" && <TechPanel data={data.tech_stack} />}
        {activeTab === "modules" && <ModulesPanel data={data.modules} />}
        {activeTab === "files" && <FilesPanel data={data.file_analyses} />}
        {activeTab === "functions" && <FunctionsPanel data={data.function_analyses} />}
        {activeTab === "dependencies" && <DepsPanel data={data.dependencies} />}
        {activeTab === "flow" && <FlowPanel data={data} />}
        {activeTab === "production" && <ProductionPanel data={data.production_readiness} />}
        {activeTab === "security" && <SecurityPanel data={data.security_analysis} />}
        {activeTab === "cost" && <CostPanel data={data.cost_analysis} />}
        {activeTab === "interview" && <InterviewPanel data={data.interview_explainer} />}
        {activeTab === "synthesis" && <SynthesisPanel data={data.master_synthesis} />}
      </div>
    </div>
  );
}

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
  return <pre className="text-sm">{JSON.stringify(data, null, 2)}</pre>;
}

function itemToString(item: unknown): string {
  if (typeof item === "string") return item;
  if (typeof item === "number" || typeof item === "boolean") return String(item);
  if (item && typeof item === "object") {
    const obj = item as Record<string, unknown>;
    // Handle {name, description} pattern from LLM
    if (obj.name && obj.description) return `${obj.name}: ${obj.description}`;
    if (obj.name) return String(obj.name);
    if (obj.description) return String(obj.description);
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

function OverviewPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
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
          {(d.languages || []).map((l, i) => <span key={i} className="badge badge-blue">{l}</span>)}
        </div>
      </Section>
      <Section title="Frameworks">
        <div className="flex flex-wrap gap-2">
          {(d.frameworks || []).map((f, i) => <span key={i} className="badge badge-green">{f}</span>)}
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
          <h4 className="font-semibold text-[var(--accent)]">{String(m.module)}</h4>
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

function FilesPanel({ data }: { data: unknown }) {
  const files = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>;
  if (files.length === 0) return <JsonBlock data={data} />;
  return (
    <div className="space-y-3">
      {files.map((f, i) => (
        <details key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border)]">
          <summary className="cursor-pointer font-mono text-sm text-[var(--accent)]">
            {String(f.file_path)}
          </summary>
          <div className="mt-3 space-y-2 text-sm">
            <p><strong>Purpose:</strong> {String(f.purpose || "")}</p>
            <p><strong>Role:</strong> {String(f.role || "")}</p>
            <p><strong>Impact:</strong> {String(f.impact || "")}</p>
            <p><strong>Dependencies:</strong> {(Array.isArray(f.dependencies) ? f.dependencies.map(itemToString) : []).join(", ")}</p>
          </div>
        </details>
      ))}
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

function FlowPanel({ data }: { data: Record<string, unknown> }) {
  const flow = data.system_flow as Record<string, unknown> | undefined;
  const diagram = data.flow_diagram as string | undefined;
  return (
    <>
      {flow && (
        <>
          <Section title="Entry Point"><p>{String(flow.entry_point || "")}</p></Section>
          <Section title="Execution Steps"><ListItems items={flow.steps as string[]} /></Section>
          <Section title="Processing Stages"><ListItems items={flow.processing_stages as string[]} /></Section>
        </>
      )}
      {diagram && (
        <Section title="Flow Diagram (Mermaid)">
          <pre className="text-sm">{diagram}</pre>
        </Section>
      )}
    </>
  );
}

function ProductionPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  const score = Number(d.score || 0);
  return (
    <>
      <Section title="Production Readiness Score">
        <div className="flex items-center gap-4">
          <span className="text-4xl font-bold text-[var(--accent)]">{score}/10</span>
          <div className="flex-1">
            <div className="score-bar">
              <div
                className="score-fill"
                style={{
                  width: `${score * 10}%`,
                  background: score >= 7 ? "var(--accent-green)" : score >= 4 ? "var(--accent-yellow)" : "var(--accent-red)",
                }}
              />
            </div>
          </div>
        </div>
      </Section>
      <Section title="Strengths"><ListItems items={d.strengths as string[]} /></Section>
      <Section title="Weaknesses"><ListItems items={d.weaknesses as string[]} /></Section>
      <Section title="Missing Components"><ListItems items={d.missing_components as string[]} /></Section>
    </>
  );
}

function SecurityPanel({ data }: { data: unknown }) {
  const d = data as Record<string, unknown> | undefined;
  if (!d) return <JsonBlock data={data} />;
  return (
    <>
      <Section title="Severity">
        <span className={`badge ${
          d.severity === "high" ? "badge-red" : d.severity === "medium" ? "badge-yellow" : "badge-green"
        }`}>{String(d.severity || "unknown")}</span>
      </Section>
      <Section title="Issues"><ListItems items={d.issues as string[]} /></Section>
      <Section title="Recommendations"><ListItems items={d.recommendations as string[]} /></Section>
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
      <Section title="Overview"><p>{String(d.overview || "")}</p></Section>
      <Section title="Architecture"><p>{String(d.architecture || "")}</p></Section>
      <Section title="Modules"><p>{String(d.modules || "")}</p></Section>
      <Section title="Flow"><p>{String(d.flow || "")}</p></Section>
      <Section title="Strengths"><ListItems items={d.strengths as string[]} /></Section>
      <Section title="Weaknesses"><ListItems items={d.weaknesses as string[]} /></Section>
    </>
  );
}

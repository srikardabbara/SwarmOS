'use client';

import { useState } from 'react';
import { ReactFlow, Background, Controls, MarkerType, Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Trace } from '@/lib/api';
import { analyzeRun, RunIssue, RunView } from '@/lib/analysis';

function IssueCard({ issue }: { issue: RunIssue }) {
  const isWaste = issue.severity === 'waste';
  return (
    <article className={`rounded-lg border p-4 ${isWaste ? 'border-amber-500/30 bg-amber-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
      <p className={`text-xs font-semibold uppercase tracking-wide ${isWaste ? 'text-amber-200' : 'text-red-300'}`}>
        {isWaste ? 'Inefficiency' : 'Error'}
        {issue.agents.length > 0 && (
          <span className="ml-2 font-normal normal-case tracking-normal text-slate-300">
            {issue.agents.join(' → ')}
          </span>
        )}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-slate-100">{issue.message}</p>
    </article>
  );
}

export function RunAnalysis({ trace }: { trace: Trace }) {
  const view = analyzeRun(trace);
  const errors = view.issues.filter((issue) => issue.severity === 'error').length;
  const waste = view.issues.filter((issue) => issue.severity === 'waste').length;

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Agents" value={String(view.agents.length)} />
        <Stat label="Subagents" value={String(view.subagents.length)} />
        <Stat label="Handoffs" value={String(view.handoffs.length)} />
        <Stat
          label="Issues"
          value={String(view.issues.length)}
          tone={view.issues.length > 0 ? 'alert' : 'ok'}
        />
      </section>

      <HandoffMap trace={trace} view={view} />

      <section>
        <h2 className="text-lg font-semibold text-slate-100">Review</h2>
        {view.issues.length === 0 && view.handoffs.length === 0 ? (
          <div className="mt-3 rounded-xl border border-slate-700/50 bg-gradient-to-br from-slate-900 to-slate-950 p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">This run</p>
            <p className="mt-2 text-xl font-semibold text-slate-100">{view.agentName} worked alone</p>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400">
              No subagent was called, so nothing was handed off. The next time this agent calls one, the task, the reply, and any action show up here.
            </p>
          </div>
        ) : (
          <>
            <p className="mt-1 text-sm text-slate-400">
              {errors > 0 && waste > 0 && `${errors} ${errors === 1 ? 'error' : 'errors'} and ${waste} ${waste === 1 ? 'inefficiency' : 'inefficiencies'} on the handoffs.`}
              {errors > 0 && waste === 0 && `${errors} ${errors === 1 ? 'error' : 'errors'} on the handoffs.`}
              {errors === 0 && waste > 0 && `${waste} ${waste === 1 ? 'inefficiency' : 'inefficiencies'} on the handoffs.`}
              {view.issues.length === 0 && 'The handoffs are clean. Nothing unused, and no figure changed between agents.'}
            </p>
            <div className="mt-4 space-y-3">
              {view.issues.map((issue, index) => (
                <IssueCard key={issue.id || index} issue={issue} />
              ))}
            </div>
          </>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-100">Actions</h2>
        {view.issues.length === 0 ? (
          <p className="mt-3 rounded-xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-3 text-sm text-slate-300">
            Nothing to change. This run has no handoff error to fix.
          </p>
        ) : (
          <ol className="mt-3 space-y-3">
            {view.issues.map((issue, index) => (
              <ActionItem key={issue.id || index} trace={trace} issue={issue} index={index} />
            ))}
          </ol>
        )}
      </section>

      {view.handoffs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-slate-100">What was handed off</h2>
          <p className="mt-1 text-sm text-slate-400">What was sent, and what the next agent wrote back.</p>
          <ol className="mt-4 space-y-3">
            {view.handoffs.map((handoff, index) => (
              <li key={handoff.id} className="rounded-xl border border-slate-700/50 bg-slate-950/50 p-4">
                <p className="text-sm font-medium text-slate-100">
                  <span className="mr-2 text-slate-500">{index + 1}</span>
                  {handoff.from}
                  <span className="mx-2 text-purple-300">→</span>
                  {handoff.to}
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg bg-slate-900/70 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Sent</p>
                    {handoff.passed.length > 0 ? handoff.passed.map(([key, value]) => (
                      <p key={key} className="mt-1 text-sm leading-relaxed text-slate-200 whitespace-pre-wrap">
                        <span className="text-slate-400">{key}. </span>{value}
                      </p>
                    )) : (
                      <p className="mt-1 text-sm text-slate-400">Nothing was attached.</p>
                    )}
                  </div>
                  <div className="rounded-lg bg-slate-900/70 p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Came back</p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-200 whitespace-pre-wrap">
                      {handoff.reply || 'No reply text on this handoff.'}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section>
        <h2 className="text-lg font-semibold text-slate-100">Who ran</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-700/50 bg-slate-950/40 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Agents</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {view.agents.map((name) => (
                <span key={name} className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-sm text-emerald-100">
                  {name}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-700/50 bg-slate-950/40 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Subagents</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {view.subagents.length > 0 ? view.subagents.map((name) => (
                <span key={name} className="rounded-full border border-purple-400/30 bg-purple-400/10 px-3 py-1 text-sm text-purple-100">
                  {name}
                </span>
              )) : (
                <span className="text-sm text-slate-400">None called on this run</span>
              )}
            </div>
          </div>
        </div>
        {view.tools.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Tools</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {view.tools.map((name) => (
                <span key={name} className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-xs text-slate-300">
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {view.steps.length > 0 && (
        <details className="rounded-xl border border-slate-700/50 bg-slate-950/30 p-4" open>
          <summary className="cursor-pointer text-sm font-medium text-slate-200">
            Inside {view.agentName}
            <span className="ml-2 font-normal text-slate-500">{view.steps.length} steps</span>
          </summary>
          <p className="mt-2 text-xs text-slate-500">LangGraph ran these while the agent worked.</p>
          <ol className="mt-4 max-h-72 space-y-0 overflow-y-auto border-l border-slate-700 pl-4">
            {view.steps.map((step, index) => (
              <li key={`${step}-${index}`} className="relative py-1.5 text-sm text-slate-300">
                <span className="absolute -left-[21px] top-3 h-2 w-2 rounded-full bg-slate-600" />
                <span className="mr-2 font-mono text-xs text-slate-600">{String(index + 1).padStart(2, '0')}</span>
                {step}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function ActionItem({ trace, issue, index }: { trace: Trace; issue: RunIssue; index: number }) {
  const [copied, setCopied] = useState(false);
  const command = issue.fix && issue.id ? `swarmos apply ${trace.id} ${issue.id}` : '';
  return (
    <li className="rounded-xl border border-slate-700/50 bg-slate-950/50 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {index + 1}. {issue.agents.length > 0 ? issue.agents.join(' → ') : issue.category}
      </p>
      <p className="mt-2 text-sm font-medium leading-relaxed text-slate-100">{issue.action}</p>
      <p className="mt-2 text-sm leading-relaxed text-slate-400">
        <span className="text-slate-500">Result. </span>{issue.result}
      </p>
      {command && (
        <button
          type="button"
          onClick={() => navigator.clipboard.writeText(command).then(() => setCopied(true)).catch(() => setCopied(false))}
          className="mt-3 text-xs text-blue-300 hover:text-blue-200"
        >
          {copied ? 'Copied the apply command' : 'Copy the command to apply this in the graph repo'}
        </button>
      )}
    </li>
  );
}

function HandoffMap({ trace, view }: { trace: Trace; view: RunView }) {
  const subagents = new Set(view.subagents);
  const names = [...view.agents, ...view.subagents.filter((name) => !view.agents.includes(name))];
  const nodes: Node[] = names.map((name, index) => {
    const issue = view.issues.find((item) => item.agents.includes(name));
    const border = issue?.severity === 'error' ? '#ef4444' : issue ? '#f59e0b' : '#10b981';
    return {
      id: name,
      position: { x: (index % 4) * 240, y: subagents.has(name) ? 180 : Math.floor(index / 4) * 150 },
      data: {
        label: (
          <div className="text-center">
            <div className="font-semibold text-slate-100">{name}</div>
            <div className="mt-1 text-xs text-slate-400">{subagents.has(name) ? 'Subagent' : 'Agent'}</div>
          </div>
        ),
      },
      style: {
        background: `${border}1a`,
        border: `2px solid ${border}`,
        borderRadius: 8,
        padding: 16,
        minWidth: 160,
      },
    };
  });
  const seen = new Set<string>();
  const edges: Edge[] = [];
  for (const handoff of view.handoffs) {
    const id = `${handoff.from}->${handoff.to}`;
    if (seen.has(id)) continue;
    seen.add(id);
    const issue = view.issues.find((item) => item.agents.includes(handoff.from) && item.agents.includes(handoff.to));
    const color = issue?.severity === 'error' ? '#f87171' : issue ? '#fbbf24' : '#8b5cf6';
    edges.push({
      id,
      source: handoff.from,
      target: handoff.to,
      animated: trace.status === 'running' || !issue,
      style: { stroke: color, strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color },
    });
  }

  return (
    <section>
      <h2 className="text-lg font-semibold text-slate-100">Handoffs</h2>
      <p className="mt-1 text-sm text-slate-400">
        {view.handoffs.length > 0
          ? 'Each arrow is information passed to the next agent. Amber is unused. Red is a figure that changed.'
          : `${view.agentName} is the only agent on this run.`}
      </p>
      <div className="mt-3 h-[380px] overflow-hidden rounded-lg border border-slate-700/40 bg-slate-950/50">
        <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
          <Background color="#334155" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </section>
  );
}

function Stat({ label, value, tone = 'plain' }: { label: string; value: string; tone?: 'plain' | 'alert' | 'ok' }) {
  const color = tone === 'alert' ? 'text-red-300' : tone === 'ok' ? 'text-green-300' : 'text-slate-100';
  return (
    <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 px-3 py-3">
      <p className={`text-2xl font-semibold ${color}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-400">{label}</p>
    </div>
  );
}

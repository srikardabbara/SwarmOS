'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ReactFlow, Node, Edge, Background, Controls, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api, getProjectKey, ProjectKeyError, Trace, TraceEvent } from '@/lib/api';
import { ProjectUnlock } from '@/components/ProjectUnlock';
import { SiteHeader } from '@/components/SiteHeader';
import { ArrowLeft, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

function LangSmithSetup({ trace }: { trace: Trace }) {
  const setup = trace.metadata?.langsmith;
  if (!setup || typeof setup !== 'object') return null;
  const subagents = Array.isArray(setup.subagents) ? setup.subagents : [];
  const tools = Array.isArray(setup.tools) ? setup.tools : [];
  return (
    <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4 mt-4">
      <h2 className="text-lg font-semibold text-slate-200 mb-1">Setup from the LangSmith trace</h2>
      <p className="text-xs text-slate-400 mb-3">
        {typeof setup.note === 'string' ? setup.note : 'Read from the trace you pasted.'}
      </p>
      <div className="space-y-2 text-sm text-slate-200">
        <p><span className="text-slate-400">Main agent. </span>{setup.main_agent || 'Not named on the trace'}</p>
        <p>
          <span className="text-slate-400">Subagents called. </span>
          {subagents.length > 0 ? subagents.join(', ') : 'None on this trace'}
        </p>
        <p>
          <span className="text-slate-400">Tools that ran. </span>
          {tools.length > 0 ? tools.join(', ') : 'None on this trace'}
        </p>
      </div>
      {typeof setup.instructions === 'string' && setup.instructions && (
        <div className="mt-3">
          <div className="text-xs font-medium text-purple-300">Instructions on the run</div>
          <p className="mt-1 text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">{setup.instructions}</p>
        </div>
      )}
    </div>
  );
}

function HandoffTranscript({ trace }: { trace: Trace }) {
  const turns = (trace.events || []).flatMap((event) => {
    if (event.event_type === 'node_exit' && event.data.wrote && typeof event.data.wrote === 'object') {
      const fields = Object.entries(event.data.wrote as Record<string, string>);
      if (fields.length === 0) return [];
      return [{ id: event.id, kind: 'wrote' as const, agent: event.agent, fields }];
    }
    if (event.event_type === 'handoff') {
      const fields = event.data.passed_fields && typeof event.data.passed_fields === 'object'
        ? Object.entries(event.data.passed_fields as Record<string, string>)
        : [];
      return [{
        id: event.id,
        kind: 'handoff' as const,
        from: event.data.from_agent as string | undefined,
        to: event.data.to_agent as string | undefined,
        fields,
        excerpt: typeof event.data.excerpt === 'string' ? event.data.excerpt : '',
      }];
    }
    return [];
  });

  return (
    <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4 mt-4">
      <h2 className="text-lg font-semibold text-slate-200 mb-1">What each agent passed on</h2>
      <p className="text-xs text-slate-400 mb-3">
        The text on the handoff, then what the next agent actually wrote. A green check can still hide research that was ignored or a figure that changed.
      </p>
      {turns.length === 0 && (
        <p className="text-sm text-slate-400">This run has no handoff text.</p>
      )}
      <div className="space-y-3 max-h-[520px] overflow-y-auto">
        {turns.map((turn) => (
          <div key={turn.id} className="rounded-lg border border-slate-700/40 bg-slate-950/40 p-3">
            <div className="text-sm font-medium text-slate-200">
              {turn.kind === 'wrote'
                ? `${turn.agent || 'Agent'} wrote`
                : `${turn.from || 'An agent'} → ${turn.to || 'the next agent'}`}
            </div>
            {turn.fields.length > 0 ? (
              <div className="mt-2 space-y-2">
                {turn.fields.map(([key, value]) => (
                  <div key={key}>
                    <div className="text-xs font-medium text-purple-300">{key}</div>
                    <p className="text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">{value}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-xs text-slate-400">{turn.kind === 'handoff' && turn.excerpt ? turn.excerpt : 'Nothing was attached.'}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function CommunicationReview({ trace }: { trace: Trace }) {
  const review = trace.metadata?.communication_review;
  const findings = Array.isArray(review?.findings) ? review.findings : [];
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);

  async function copyApply(findingId: string) {
    const command = `swarmos apply ${trace.id} ${findingId}`;
    try {
      await navigator.clipboard.writeText(command);
      setCopiedId(findingId);
      setCopyError(null);
    } catch {
      setCopyError('Select the command below and copy it.');
    }
  }

  return (
    <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4 mt-4">
      <h2 className="text-lg font-semibold text-slate-200 mb-1">Communication review</h2>
      {review?.note && (
        <p className="text-xs text-slate-400 mb-3">{review.note}</p>
      )}
      {copyError && (
        <p className="text-xs text-red-300 mb-3">{copyError}</p>
      )}
      {!review && (
        <p className="text-sm text-slate-400">This run was stored before communication review.</p>
      )}
      {review && findings.length === 0 && (
        <p className="text-sm text-slate-400">No broken or wasteful handoffs found.</p>
      )}
      <div className="space-y-2 max-h-[520px] overflow-y-auto">
        {findings.map((finding: {
          id?: string;
          severity?: string;
          category?: string;
          message?: string;
          recommendation?: string;
          steps?: string[];
          agents?: string[];
          fix?: Record<string, unknown> | null;
          applied?: boolean;
          applied_path?: string;
        }, index: number) => {
          const isWaste = finding.severity === 'waste';
          return (
            <div
              key={finding.id || index}
              className={`p-3 rounded-lg border ${
                isWaste
                  ? 'bg-amber-500/5 border-amber-500/20'
                  : 'bg-red-500/5 border-red-500/20'
              }`}
            >
              <div className="text-sm font-medium text-slate-200">
                {finding.category}
                {finding.agents && finding.agents.length > 0 && (
                  <span className="text-slate-400 font-normal"> · {finding.agents.join(' → ')}</span>
                )}
              </div>
              <div className={`text-xs mt-1 ${isWaste ? 'text-amber-200/80' : 'text-red-300/80'}`}>
                {finding.message}
              </div>
              {finding.steps && finding.steps.length > 0 && (
                <ol className="mt-2 space-y-1 text-xs text-slate-300 list-decimal pl-4">
                  {finding.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              )}
              {finding.fix && finding.id && (
                <div className="mt-3">
                  <p className="text-xs text-slate-400">
                    Run this in the repo that contains the graph. The dashboard does not edit your files.
                  </p>
                  <button
                    type="button"
                    onClick={() => copyApply(finding.id as string)}
                    className="mt-2 px-3 py-1.5 rounded-md bg-blue-500/15 hover:bg-blue-500/25 border border-blue-400/30 text-xs text-blue-200"
                  >
                    {copiedId === finding.id ? 'Copied' : 'Copy apply command'}
                  </button>
                  <pre className="mt-2 overflow-x-auto rounded bg-slate-950/60 px-2 py-1.5 text-xs text-slate-300">
                    swarmos apply {trace.id} {finding.id}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function TracePage() {
  const params = useParams();
  const router = useRouter();
  const traceId = params.id as string;

  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    loadTrace();
  }, [traceId]);

  async function loadTrace() {
    if (!getProjectKey()) {
      setLocked(true);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setLocked(false);
      const data = await api.getTrace(traceId);
      setTrace(data);
      setError(null);
    } catch (err) {
      if (err instanceof ProjectKeyError) {
        setLocked(true);
        return;
      }
      setError('Failed to load trace');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function buildGraph(trace: Trace): { nodes: Node[]; edges: Edge[] } {
    if (!trace.events) return { nodes: [], edges: [] };

    // Extract unique agents
    const agentEvents = trace.events.filter((e) => e.event_type === 'node_entry');
    const uniqueAgents = Array.from(new Set(agentEvents.map((e) => e.agent).filter(Boolean)));

    // Check if there are validation failures
    const hasFailures = trace.validation_results?.some((v) => !v.passed) || false;

    // Create nodes for each agent
    const nodes: Node[] = uniqueAgents.map((agent, index) => {
      const agentEvents = trace.events?.filter((e) => e.agent === agent) || [];
      const hasError = agentEvents.some((e) => e.event_type === 'error');

      let nodeColor = '#3b82f6'; // blue
      let borderColor = '#3b82f6';
      let bgColor = 'rgba(59, 130, 246, 0.1)';

      if (hasError || hasFailures) {
        nodeColor = '#ef4444'; // red
        borderColor = '#ef4444';
        bgColor = 'rgba(239, 68, 68, 0.1)';
      } else if (trace.status === 'completed') {
        nodeColor = '#10b981'; // green
        borderColor = '#10b981';
        bgColor = 'rgba(16, 185, 129, 0.1)';
      }

      return {
        id: agent!,
        type: 'default',
        data: {
          label: (
            <div className="text-center">
              <div className="font-semibold">{agent}</div>
              <div className="text-xs text-slate-400 mt-1">
                {agentEvents.length} events
              </div>
            </div>
          ),
        },
        position: { x: index * 300, y: 100 },
        style: {
          background: bgColor,
          border: `2px solid ${borderColor}`,
          borderRadius: '8px',
          padding: '16px',
          minWidth: '180px',
          boxShadow: `0 0 20px ${borderColor}40`,
        },
      };
    });

    // Create edges based on handoffs or sequence
    const edges: Edge[] = [];
    for (let i = 0; i < uniqueAgents.length - 1; i++) {
      const from = uniqueAgents[i];
      const to = uniqueAgents[i + 1];

      // Check if there's an actual handoff
      const hasHandoff = trace.events?.some(
        (e) =>
          e.event_type === 'handoff' &&
          e.data.from_agent === from &&
          e.data.to_agent === to
      );

      edges.push({
        id: `${from}-${to}`,
        source: from!,
        target: to!,
        animated: trace.status === 'running',
        style: {
          stroke: hasHandoff ? '#8b5cf6' : '#6366f1',
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: hasHandoff ? '#8b5cf6' : '#6366f1',
        },
      });
    }

    return { nodes, edges };
  }

  if (locked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <SiteHeader />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <ProjectUnlock
            onUnlocked={() => {
              loadTrace();
            }}
          />
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <SiteHeader />
        <div className="flex items-center justify-center py-24">
          <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className="text-slate-400 mt-4">Loading trace...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !trace) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <SiteHeader />
        <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-200 mb-2">Error loading trace</h2>
          <p className="text-slate-400 mb-4">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-lg text-blue-400"
          >
            Back to Dashboard
          </button>
        </div>
        </div>
      </div>
    );
  }

  const { nodes, edges } = buildGraph(trace);
  const passedValidations = trace.validation_results?.filter((v) => v.passed).length || 0;
  const totalValidations = trace.validation_results?.length || 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <SiteHeader />
      <div className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <button
            onClick={() => router.push('/')}
            className="flex items-center text-slate-400 hover:text-slate-200 mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-200">{trace.workflow_id}</h1>
              <p className="text-slate-400 text-sm mt-1">Trace ID: {trace.id}</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-sm text-slate-400">Status</div>
                <div className={`text-lg font-semibold ${
                  trace.status === 'completed' ? 'text-green-400' :
                  trace.status === 'failed' ? 'text-red-400' : 'text-blue-400'
                }`}>
                  {trace.status}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="border-b border-slate-700/50 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4">
              <div className="text-3xl font-bold text-blue-400">
                {trace.events?.length || 0}
              </div>
              <div className="text-sm text-slate-400 mt-1">Events Captured</div>
            </div>
            <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4">
              <div className="text-3xl font-bold text-purple-400">
                {nodes.length}
              </div>
              <div className="text-sm text-slate-400 mt-1">Agents</div>
            </div>
            <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4">
              <div className="text-3xl font-bold text-pink-400">
                {edges.length}
              </div>
              <div className="text-sm text-slate-400 mt-1">Transitions</div>
            </div>
            <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4">
              <div className={`text-3xl font-bold ${
                passedValidations === totalValidations ? 'text-green-400' : 'text-red-400'
              }`}>
                {passedValidations}/{totalValidations}
              </div>
              <div className="text-sm text-slate-400 mt-1">Checks Passed</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-3 gap-6">
          {/* Workflow Graph */}
          <div className="col-span-2">
            <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4 h-[500px]">
              <h2 className="text-lg font-semibold text-slate-200 mb-4">Workflow Graph</h2>
              <div className="h-[calc(100%-3rem)] bg-slate-900/50 rounded-lg overflow-hidden">
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  fitView
                  attributionPosition="bottom-left"
                >
                  <Background color="#334155" gap={16} />
                  <Controls />
                </ReactFlow>
              </div>
            </div>
          </div>

          {/* Validation Results */}
          <div className="col-span-1">
            <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-4">
              <h2 className="text-lg font-semibold text-slate-200 mb-4">Validation Results</h2>
              <div className="space-y-2 max-h-[460px] overflow-y-auto">
                {trace.validation_results && trace.validation_results.length > 0 ? (
                  trace.validation_results.map((result) => (
                    <div
                      key={result.id}
                      className={`p-3 rounded-lg border ${
                        result.passed
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-red-500/5 border-red-500/20'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {result.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-slate-200">
                            {result.validation_type}
                          </div>
                          <div className={`text-xs mt-1 ${
                            result.passed ? 'text-green-300/70' : 'text-red-300/70'
                          }`}>
                            {result.message}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-slate-400">
                    <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No validations run</p>
                  </div>
                )}
              </div>
            </div>
            <LangSmithSetup trace={trace} />
            <HandoffTranscript trace={trace} />
            <CommunicationReview trace={trace} />
          </div>
        </div>

        {/* Event Timeline */}
        <div className="mt-6 bg-slate-800/30 border border-slate-700/30 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-slate-200 mb-4">Event Timeline</h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {trace.events && trace.events.length > 0 ? (
              trace.events.map((event, index) => (
                <div
                  key={event.id}
                  className="flex items-start gap-3 p-2 hover:bg-slate-700/20 rounded"
                >
                  <div className="text-xs text-slate-500 w-20 flex-shrink-0 font-mono">
                    {index + 1}.
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-300">
                        {event.event_type}
                      </span>
                      {event.agent && (
                        <span className="text-xs text-slate-400">
                          → {event.agent}
                        </span>
                      )}
                    </div>
                    {event.event_type === 'handoff' && event.data.to_agent && (
                      <div className="text-xs text-purple-400 mt-1">
                        Handoff: {event.data.from_agent} → {event.data.to_agent}
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 flex-shrink-0">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-slate-400">
                <p className="text-sm">No events recorded</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

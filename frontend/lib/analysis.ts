import { Trace } from '@/lib/api';
import { displayAgentName, isInsideStep } from '@/lib/agents';

export type RunIssue = {
  id?: string;
  severity: string;
  category: string;
  agents: string[];
  message: string;
  action: string;
  result: string;
  fix?: Record<string, unknown> | null;
};

export type RunHandoff = {
  id: string;
  from: string;
  to: string;
  passed: [string, string][];
  reply: string;
};

export type RunView = {
  agentName: string;
  agents: string[];
  subagents: string[];
  tools: string[];
  handoffs: RunHandoff[];
  issues: RunIssue[];
  steps: string[];
};

const RESULT: Record<string, string> = {
  unused_context: 'The next run passes less unused text, and this handoff costs fewer tokens.',
  misread: 'The later agent keeps the earlier figure, and the output stops contradicting the handoff.',
  empty_handoff: 'The next agent receives the fields it needs, or this empty handoff is removed.',
  context_loss: 'The next agent starts with the state that was already passed.',
  loop: 'The agents stop handing control back and forth without new information.',
  redundant_agent: 'That step is removed, or it writes something the next agent uses.',
  serial_when_parallel: 'Independent work runs together, and the run gets shorter.',
  weak_synthesis: 'The final agent uses the material the earlier agents produced.',
  effort_mismatch: 'The heavier work sits with the agent that needs it.',
};

type RawFinding = {
  id?: string;
  severity?: string;
  category?: string;
  message?: string;
  recommendation?: string;
  agents?: string[];
  fix?: Record<string, unknown> | null;
};

function rawFindings(trace: Trace): RawFinding[] {
  const review = trace.metadata?.communication_review;
  const findings = review && typeof review === 'object' ? review.findings : undefined;
  return Array.isArray(findings) ? findings : [];
}

export function runIssues(trace: Trace): RunIssue[] {
  return rawFindings(trace)
    .filter((finding) => {
      const names = finding.agents || [];
      return names.length === 0 || names.some((name) => !isInsideStep(name));
    })
    .map((finding) => {
      const category = finding.category || 'handoff';
      return {
        id: finding.id,
        severity: finding.severity === 'waste' ? 'waste' : 'error',
        category,
        agents: (finding.agents || []).filter((name) => !isInsideStep(name)),
        message: finding.message || 'This handoff needs a look.',
        action: finding.recommendation || 'Change what this handoff sends.',
        result: RESULT[category] || 'The next run no longer reports this on the handoff.',
        fix: finding.fix,
      };
    });
}

export function analyzeRun(trace: Trace): RunView {
  const agentName = displayAgentName(trace);
  const setup = trace.metadata?.langsmith;
  const listed = setup && typeof setup === 'object' && Array.isArray(setup.subagents)
    ? setup.subagents.filter((name: unknown): name is string => typeof name === 'string' && name.trim().length > 0)
    : [];
  const tools = setup && typeof setup === 'object' && Array.isArray(setup.tools)
    ? setup.tools.filter((name: unknown): name is string => typeof name === 'string' && name.trim().length > 0)
    : [];

  const steps: string[] = [];
  const seenAgents: string[] = [];
  const handoffs: RunHandoff[] = [];
  const events = trace.events || [];

  events.forEach((event, index) => {
    if (event.event_type === 'node_entry' && event.agent) {
      if (isInsideStep(event.agent)) steps.push(event.agent);
      else if (!seenAgents.includes(event.agent)) seenAgents.push(event.agent);
    }
    if (event.event_type !== 'handoff') return;
    const from = typeof event.data.from_agent === 'string' ? event.data.from_agent : '';
    const to = typeof event.data.to_agent === 'string' ? event.data.to_agent : '';
    if (!from || !to || isInsideStep(from) || isInsideStep(to)) return;
    const passed = event.data.passed_fields && typeof event.data.passed_fields === 'object'
      ? Object.entries(event.data.passed_fields as Record<string, string>).filter(([, value]) => typeof value === 'string' && value.trim())
      : [];
    const replyEvent = events.slice(index + 1).find((item) => item.event_type === 'node_exit' && item.agent === to);
    const wrote = replyEvent?.data.wrote;
    const reply = wrote && typeof wrote === 'object'
      ? Object.values(wrote as Record<string, string>).filter((value) => typeof value === 'string' && value.trim()).join('\n')
      : '';
    handoffs.push({ id: event.id, from, to, passed, reply });
  });

  const subagents = Array.from(new Set(listed));
  const participants = Array.from(new Set([
    ...seenAgents,
    ...handoffs.flatMap((handoff) => [handoff.from, handoff.to]),
  ])).filter((name) => !isInsideStep(name) && !subagents.includes(name));
  const agents = participants.length > 0 ? participants : [agentName];

  return { agentName, agents, subagents, tools, handoffs, issues: runIssues(trace), steps };
}

export function runListLine(trace: Trace): string {
  const issues = runIssues(trace);
  const errors = issues.filter((issue) => issue.severity === 'error').length;
  const waste = issues.filter((issue) => issue.severity === 'waste').length;
  if (errors || waste) {
    const parts = [];
    if (errors) parts.push(`${errors} handoff ${errors === 1 ? 'error' : 'errors'}`);
    if (waste) parts.push(`${waste} to tighten`);
    return parts.join(' · ');
  }
  const setup = trace.metadata?.langsmith;
  const subs = setup && typeof setup === 'object' && Array.isArray(setup.subagents) ? setup.subagents.length : 0;
  if (subs > 0) return `${subs} subagent ${subs === 1 ? 'handoff' : 'handoffs'}`;
  if (setup && typeof setup === 'object') return 'No subagent handoff';
  return '';
}

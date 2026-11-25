/** LangGraph steps that run inside one agent, not agents the user called. */

const GENERIC = new Set([
  'langgraph',
  'runnablesequence',
  'runnablelambda',
  'runnableparallel',
  'call_model',
  'agent',
  'tools',
  'model',
  'chatprompttemplate',
  'prompt',
]);

const HOOKS = new Set(['before_agent', 'after_agent', 'before_model', 'after_model']);

export function isInsideStep(name: string): boolean {
  const lowered = name.trim().toLowerCase();
  if (!lowered || lowered === '__start__' || lowered === '__end__') return true;
  if (GENERIC.has(lowered) || lowered.includes('middleware')) return true;
  const hook = lowered.split('.').pop() || '';
  return HOOKS.has(hook);
}

export function displayAgentName(trace: {
  workflow_id: string;
  metadata?: Record<string, unknown> | null;
}): string {
  const setup = trace.metadata?.langsmith;
  const main =
    setup && typeof setup === 'object' && 'main_agent' in setup
      ? (setup as { main_agent?: unknown }).main_agent
      : undefined;
  if (isInsideStep(trace.workflow_id) && typeof main === 'string' && main.trim()) {
    return main.trim();
  }
  return trace.workflow_id;
}

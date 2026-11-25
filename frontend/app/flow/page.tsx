import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteHeader } from '@/components/SiteHeader';

export const metadata: Metadata = {
  title: 'How it works',
  description: 'From a finished LangGraph product to a steady state where every change shows the handoff, the token waste, and a fact that changed.',
};

const path = [
  {
    label: 'Your product',
    title: 'The LangGraph app already exists',
    body: 'Agents, tools, and state are yours. SwarmOS does not replace LangGraph or LangSmith. The graph keeps running where it runs today.',
  },
  {
    label: 'Connect',
    title: 'Point the graph at a project',
    body: 'Install SwarmOS in that repo, expose run_workflow, and create a project key. The key is how CI and the dashboard share one set of runs. Node names stay the ones you passed to add_node.',
  },
  {
    label: 'Each change',
    title: 'A pull request runs the graph',
    body: 'GitHub Actions runs swarmos test on the scenarios you wrote. The YAML contract is optional and uses your names: who must run, which handoff must happen, which fields must survive.',
  },
  {
    label: 'The run',
    title: 'The handoff is on the page',
    body: 'You see the text each node passed on. An unused field is listed with an approximate token count, because you pay to generate it and pay again when the next model receives it. A number that changed between nodes is shown as both versions. A broken contract fails the pull request.',
  },
  {
    label: 'The fix',
    title: 'The edit happens in your repo',
    body: 'The run names the node and the field. When the edit is safe, you copy swarmos apply and run it locally. The dashboard does not change your files. You push, and the next run confirms the waste or the wrong fact is gone.',
  },
  {
    label: 'Steady state',
    title: 'Every release is checked the same way',
    body: 'New pull requests repeat the loop. Token-heavy fields that nobody used get dropped. A fluent answer that contradicts the previous node is caught before a customer or an executive sees it. A skipped handoff fails CI instead of shipping.',
  },
];

export default function FlowPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <SiteHeader />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <p className="text-sm font-medium text-purple-300">How it works</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-100">
          From the product you already built to a checked release
        </h1>
        <p className="mt-4 text-slate-300 leading-relaxed">
          LangGraph keeps running the nodes. LangSmith keeps the trace. SwarmOS is the layer
          that turns each change into a reading of the handoff: what was passed, what it cost,
          and whether the next node changed a fact.
        </p>

        <div className="mt-8 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/40 p-4">
          <div className="flex min-w-[640px] items-stretch gap-2">
            {[
              ['LangGraph app', 'Nodes you already shipped'],
              ['Pull request', 'CI runs the graph'],
              ['SwarmOS run', 'Handoff, tokens, changed fact'],
              ['Your repo', 'Fix, then the next run'],
              ['Steady state', 'Every release, same check'],
            ].map(([title, detail], index, items) => (
              <div key={title} className="flex flex-1 items-center gap-2">
                <div className="flex-1 rounded-lg border border-purple-400/30 bg-purple-500/10 px-3 py-3">
                  <div className="text-xs font-medium text-purple-200">{index + 1}</div>
                  <div className="mt-1 text-sm font-medium text-slate-100">{title}</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">{detail}</p>
                </div>
                {index < items.length - 1 && (
                  <div className="text-purple-300/80" aria-hidden="true">→</div>
                )}
              </div>
            ))}
          </div>
        </div>

        <ol className="mt-10 flex flex-col gap-0">
          {path.map((stage, index) => (
            <li key={stage.label} className="flex gap-4">
              <div className="flex w-8 shrink-0 flex-col items-center">
                <div className="flex h-8 w-8 items-center justify-center rounded-full border border-purple-400/40 bg-purple-500/10 text-sm font-semibold text-purple-200">
                  {index + 1}
                </div>
                {index < path.length - 1 && (
                  <div className="my-1 w-px flex-1 bg-purple-400/30" />
                )}
              </div>
              <div className={`min-w-0 flex-1 ${index < path.length - 1 ? 'pb-8' : ''}`}>
                <p className="text-xs font-medium uppercase tracking-wide text-purple-300">{stage.label}</p>
                <h2 className="mt-1 text-lg font-medium text-slate-100">{stage.title}</h2>
                <p className="mt-1 text-sm leading-relaxed text-slate-400">{stage.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <section className="mt-12 rounded-lg border border-slate-700/40 bg-slate-800/30 p-5">
          <h2 className="text-lg font-medium text-slate-100">The loop that stays on</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Steady state is this cycle on every pull request. Nothing about the agent names is fixed.
          </p>
          <div className="mt-5 grid gap-3 sm:grid-cols-4">
            {[
              ['Change', 'A pull request edits the graph'],
              ['Run', 'CI executes the graph and posts the trace'],
              ['Read', 'Handoff text, unused tokens, a changed fact'],
              ['Ship', 'The contract passes, or the finding is fixed and re-run'],
            ].map(([title, body], index) => (
              <div key={title} className="relative rounded-lg border border-slate-700/40 bg-slate-950/50 p-3">
                <div className="text-xs font-medium text-purple-300">{index + 1}</div>
                <div className="mt-1 text-sm font-medium text-slate-100">{title}</div>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">{body}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm text-slate-400">
            Setup steps, including the project key and the GitHub Action, are on{' '}
            <Link href="/start" className="text-blue-300 hover:text-blue-200">Instructions</Link>.
          </p>
        </section>
      </div>
    </div>
  );
}

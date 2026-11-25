import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteHeader } from '@/components/SiteHeader';

export const metadata: Metadata = {
  title: 'Instructions',
  description: 'Connect a LangSmith project once, then run swarmos langsmith whenever you want an analysis.',
};

function Callout({
  from,
  title,
  children,
}: {
  from: boolean;
  title: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`mt-3 rounded-lg border p-3 ${
        from ? 'border-blue-400/40 bg-blue-500/10' : 'border-amber-400/40 bg-amber-500/10'
      }`}
    >
      <p className={`text-xs font-semibold uppercase tracking-wide ${from ? 'text-blue-200' : 'text-amber-200'}`}>
        {title}
      </p>
      <div className="mt-1 text-sm leading-relaxed text-slate-200">{children}</div>
    </div>
  );
}

export default function StartPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <SiteHeader />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <p className="text-sm font-medium text-purple-300">Instructions</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-100">
          Connect a project to SwarmOS
        </h1>
        <p className="mt-4 text-slate-300 leading-relaxed">
          Do this once. The project key is created on{' '}
          <Link href="/" className="text-blue-300 hover:text-blue-200">Runs</Link>.
          LANGSMITH_PROJECT is the agent name, the ID beside that name, or the Tracing page address.
          After that, <span className="text-slate-100">swarmos langsmith</span> reads the newest row and posts the analysis to Runs.
        </p>

        <ol className="mt-10 space-y-8">
          <li className="flex gap-4">
            <StepNumber>1</StepNumber>
            <div>
              <h2 className="text-lg font-medium text-slate-100">Make a SwarmOS project</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-400">
                This key is what lets the analysis show up on this website. You create it once.
              </p>
              <Callout from={false} title="Do this on SwarmOS">
                Click <Link href="/" className="text-blue-300 hover:text-blue-200">Runs</Link>.
                Under Create a project, type the name of your LangSmith project.
                Click Create project key. Copy the key that starts with <span className="text-slate-100">swarmos_</span> into Notes.
                SwarmOS shows it once.
              </Callout>
            </div>
          </li>

          <li className="flex gap-4">
            <StepNumber>2</StepNumber>
            <div>
              <h2 className="text-lg font-medium text-slate-100">Copy the LangSmith key and the Tracing page</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-400">
                The Tracing page is the table of runs. Its address stays the same every time you come back.
              </p>
              <Callout from title="Copy this from LangSmith">
                Open Settings, then API Keys, and create a key. For this setup choose{' '}
                <span className="text-slate-100">Personal Access Token</span>. That key reads the traces in your workspace when you run the command on your computer.
                Description can be SwarmOS. Copy the key when LangSmith shows it.
                A <span className="text-slate-100">Service Key</span> is for an unattended job, such as CI.
                <span className="text-slate-100"> Tracing Only</span> can write new traces, and SwarmOS needs to read the ones already there.
                Then open your project and click Tracing, the page with the list of runs. Copy the address in the browser bar.
              </Callout>
            </div>
          </li>

          <li className="flex gap-4">
            <StepNumber>3</StepNumber>
            <div>
              <h2 className="text-lg font-medium text-slate-100">Save the connection in Terminal</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-400">
                Run this in any folder. Put your LangSmith key on the blank line, and put the agent name, or the ID beside it, in quotes.
              </p>
              <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-sm leading-relaxed text-slate-200">
                <code>{`pip install swarmos
export LANGSMITH_API_KEY=
export LANGSMITH_PROJECT="your agent name"
export SWARMOS_API_URL=${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
export SWARMOS_API_KEY=`}</code>
              </pre>
            </div>
          </li>

          <li className="flex gap-4">
            <StepNumber>4</StepNumber>
            <div>
              <h2 className="text-lg font-medium text-slate-100">Run the analysis whenever you want one</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-400">
                This reads the newest row on that Tracing page: the instructions, the tools, and what each agent passed on. Run it again after the agent has a new conversation.
              </p>
              <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-sm leading-relaxed text-slate-200">
                <code>swarmos langsmith</code>
              </pre>
            </div>
          </li>
        </ol>

        <section className="mt-12 rounded-lg border border-green-400/30 bg-green-500/10 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-green-200">The finished result</p>
          <h2 className="mt-1 text-xl font-medium text-slate-100">Open it on Runs</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">
            The command prints a link. Open it, or click{' '}
            <Link href="/" className="text-blue-300 hover:text-blue-200">Runs</Link>, then Refresh, then the new row.
          </p>
          <ul className="mt-4 space-y-2 text-sm text-slate-200">
            <li>
              <span className="text-slate-100">Setup from the trace.</span>
              <span className="text-slate-400"> The instructions LangSmith put on the run, the subagents that were called, and the tools that ran.</span>
            </li>
            <li>
              <span className="text-slate-100">What each agent passed on.</span>
              <span className="text-slate-400"> The task sent to a subagent, then what that subagent wrote back.</span>
            </li>
            <li>
              <span className="text-slate-100">Communication review.</span>
              <span className="text-slate-400"> Text that was sent and never used, with an approximate token count, and a number that changed between agents.</span>
            </li>
          </ul>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            A run with one agent shows that agent&apos;s reply. When the trace includes a subagent, the handoff section shows the task that was sent and the reply that came back.
          </p>
        </section>
      </div>
    </div>
  );
}

function StepNumber({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-purple-400/40 bg-purple-500/10 text-sm font-semibold text-purple-200">
      {children}
    </div>
  );
}

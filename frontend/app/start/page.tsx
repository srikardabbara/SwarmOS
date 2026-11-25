import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { SiteHeader } from '@/components/SiteHeader';

export const metadata: Metadata = {
  title: 'Instructions',
  description: 'Copy the agent name from LangSmith, paste it into SwarmOS, and open the finished run on Runs.',
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

const steps: {
  title: string;
  body: string;
  from?: ReactNode;
  paste?: ReactNode;
  code?: string;
}[] = [
  {
    title: 'Get the folder, not just the chat',
    body: 'The LangSmith page where you typed a message is a test of the agent. SwarmOS needs the files behind that chat.',
    from: (
      <>
        In LangSmith Studio, click <span className="text-slate-100">Files</span> at the top of the chat.
        Download that project, or open the folder already on your computer. If Files is empty, ask the
        person who built the agent for the folder. The chat box alone is not enough.
      </>
    ),
  },
  {
    title: 'Make a project and save the key',
    body: 'This key is the password that lets the run show up on this website.',
    paste: (
      <>
        On this site, click <Link href="/" className="text-blue-300 hover:text-blue-200">Runs</Link>.
        Under Create a project, type the name you saw in LangSmith, such as Schedule manager.
        Click Create project key. Copy the key that starts with <span className="text-slate-100">swarmos_</span> into
        Notes. SwarmOS shows it once.
      </>
    ),
  },
  {
    title: 'Add SwarmOS next to the agent',
    body: 'Open Terminal. Go into the folder from step 1. Paste this and press Enter.',
    code: 'pip install swarmos',
  },
  {
    title: 'Copy the agent names into the test file',
    body: 'SwarmOS has to use the same names LangSmith already uses. It does not invent them.',
    from: (
      <>
        In LangSmith, look at the Turns list in the middle. The blue row is the agent name, such as{' '}
        <span className="text-slate-100">deep_agent</span>. If several agents are listed, write them down in that order.
      </>
    ),
    paste: (
      <>
        In Terminal, run the first line below. Then open <span className="text-slate-100">tests/schedule-manager.yaml</span> and
        replace the sample names with the names you just copied.
      </>
    ),
    code: 'swarmos init --name schedule-manager',
  },
  {
    title: 'Let SwarmOS start the same agent the chat starts',
    body: 'One function tells SwarmOS how to press go.',
    from: (
      <>
        In the LangChain folder, open the Python file that builds the agent. Find the line that finishes it.
        It looks like <span className="text-slate-100">app = workflow.compile()</span> or{' '}
        <span className="text-slate-100">agent = create_agent(...)</span>. Remember that word,{' '}
        <span className="text-slate-100">app</span> or <span className="text-slate-100">agent</span>.
      </>
    ),
    paste: (
      <>
        Paste these lines at the bottom of that same file. If the word you found was{' '}
        <span className="text-slate-100">agent</span>, use <span className="text-slate-100">agent.invoke</span> instead of{' '}
        <span className="text-slate-100">app.invoke</span>.
      </>
    ),
    code: `def run_workflow(input_data, config):
    return app.invoke(input_data, config)`,
  },
  {
    title: 'Run it',
    body: 'This sends one run from your folder to the SwarmOS project you created.',
    paste: (
      <>
        Paste the key from step 2 after <span className="text-slate-100">SWARMOS_API_KEY=</span>.
        Replace <span className="text-slate-100">FILE_NAME</span> with the Python file from step 5, without{' '}
        <span className="text-slate-100">.py</span>. If that file is <span className="text-slate-100">graph.py</span>, type{' '}
        <span className="text-slate-100">graph</span>.
      </>
    ),
    code: `export SWARMOS_API_URL=http://localhost:8000
export SWARMOS_API_KEY=
swarmos test ./tests --workflow FILE_NAME`,
  },
];

export default function StartPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <SiteHeader />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <p className="text-sm font-medium text-purple-300">Instructions</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-100">
          Connect the agent you already built
        </h1>
        <p className="mt-4 text-slate-300 leading-relaxed">
          Blue boxes are what you copy from LangSmith or the LangChain folder. Amber boxes are
          where you paste it. When the last command finishes, the result is on Runs, on this site.
        </p>

        <ol className="mt-10 space-y-8">
          {steps.map((step, index) => (
            <li key={step.title} className="flex gap-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-purple-400/40 bg-purple-500/10 text-sm font-semibold text-purple-200">
                {index + 1}
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-medium text-slate-100">{step.title}</h2>
                <p className="mt-1 text-sm leading-relaxed text-slate-400">{step.body}</p>
                {step.from && <Callout from title="Copy this from LangSmith or LangChain">{step.from}</Callout>}
                {step.paste && <Callout from={false} title="Paste it here">{step.paste}</Callout>}
                {step.code && (
                  <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-sm leading-relaxed text-slate-200">
                    <code>{step.code}</code>
                  </pre>
                )}
              </div>
            </li>
          ))}
        </ol>

        <section className="mt-12 rounded-lg border border-green-400/30 bg-green-500/10 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-green-200">The finished result</p>
          <h2 className="mt-1 text-xl font-medium text-slate-100">Open it on Runs</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">
            Stay on this website. Click <Link href="/" className="text-blue-300 hover:text-blue-200">Runs</Link> in
            the top bar, then Refresh. Click the new row. That page is the output. You do not go back to LangSmith to read it.
          </p>
          <ul className="mt-4 space-y-2 text-sm text-slate-200">
            <li>
              <span className="text-slate-100">What each agent passed on.</span>
              <span className="text-slate-400"> The text one agent handed the next, in order.</span>
            </li>
            <li>
              <span className="text-slate-100">Communication review.</span>
              <span className="text-slate-400"> Text that was sent and never used, with an approximate token count, and a number that changed between agents.</span>
            </li>
            <li>
              <span className="text-slate-100">Validation results.</span>
              <span className="text-slate-400"> Whether the agents ran in the order you pasted into the test file.</span>
            </li>
          </ul>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            One agent, such as <span className="text-slate-200">deep_agent</span> talking only to a model, still
            produces a run. The handoff section fills in when a second agent is in the same folder.
            A sample of a finished multi-agent run is <span className="text-slate-200">examples/exec_report.py</span> in
            the SwarmOS project: the checks can all pass, and the page still shows research that was ignored
            and a figure that changed from 18% to 11%.
          </p>
        </section>
      </div>
    </div>
  );
}

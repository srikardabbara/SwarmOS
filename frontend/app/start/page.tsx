import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Connect a workflow · SwarmOS',
  description: 'Point a LangGraph workflow at SwarmOS and check that the agents collaborate.',
};

const steps = [
  {
    title: 'Install SwarmOS beside the graph',
    body: 'Run this in the project that already contains the LangGraph app. The graph stays where it is.',
    code: `pip install -e /path/to/SwarmOS`,
  },
  {
    title: 'Leave the API running',
    body: 'This dashboard reads from the API on port 8000. Start it from the SwarmOS repo if the Runs page cannot load traces.',
    code: `cd backend
python -m uvicorn api.main:app --reload --port 8000`,
  },
  {
    title: 'Expose the compiled graph as one function',
    body: 'Do not rewrite the agents. SwarmOS calls this function and passes its own callback in config.',
    code: `def run_workflow(input_data, config):
    return app.invoke(input_data, config)`,
  },
  {
    title: 'Write the collaboration you expect',
    body: 'One YAML file. Agent names must match the names you passed to add_node. This file is the investigation: the order, the handoff, and the state that must survive it.',
    code: `name: "Cancel subscription"
description: "Support hands the account to billing with the ids intact"

input:
  messages:
    - role: user
      content: "I want to cancel my subscription"

expectations:
  - type: agent_sequence
    agents: ["support", "billing"]

  - type: handoff_occurred
    from: "support"
    to: "billing"

  - type: context_preserved
    required_keys: ["user_id", "subscription_id"]`,
  },
  {
    title: 'Run the check',
    body: 'The executor runs the graph, applies the YAML, and posts the pass or fail here.',
    code: `from swarmos.runner import TestExecutor, load_scenario

scenario = load_scenario("tests/cancel_subscription.yaml")
executor = TestExecutor(api_url="http://localhost:8000")

result = executor.run_scenario(
    scenario,
    run_workflow,
    workflow_id="cancel-subscription",
)
executor.print_result(result)`,
  },
];

export default function StartPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <Link
                href="/"
                className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent"
              >
                SwarmOS
              </Link>
              <p className="text-slate-400 mt-1">Test agent collaboration, not just agents</p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/50 rounded-lg text-slate-200 transition-colors"
            >
              Runs
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <p className="text-sm font-medium text-purple-300">Connect a workflow</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-100">
          Check the handoff, then read the result here
        </h1>
        <p className="mt-4 text-slate-300 leading-relaxed">
          Each agent can look fine on its own and still drop the account id on the way to the
          next one. SwarmOS runs the graph you already have and checks the collaboration: who
          ran, whether control moved, and whether the state keys you care about were still there.
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
                <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-sm leading-relaxed text-slate-200">
                  <code>{step.code}</code>
                </pre>
              </div>
            </li>
          ))}
        </ol>

        <section className="mt-10 rounded-lg border border-slate-700/40 bg-slate-800/30 p-5">
          <h2 className="text-lg font-medium text-slate-100">Read the run</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Open <Link href="/" className="text-blue-300 hover:text-blue-200">Runs</Link> and
            refresh. A green count means every check held. Open the run when a check is red:
            the graph shows where the agents stopped, and the failing check names the missing
            handoff or the state key that disappeared.
          </p>
          <ul className="mt-4 space-y-2 text-sm text-slate-300">
            <li>
              <span className="text-slate-100">agent_sequence</span>
              <span className="text-slate-400"> — these agents ran, in this order.</span>
            </li>
            <li>
              <span className="text-slate-100">handoff_occurred</span>
              <span className="text-slate-400"> — control moved from one agent to the next. A fixed edge counts.</span>
            </li>
            <li>
              <span className="text-slate-100">context_preserved</span>
              <span className="text-slate-400"> — these state keys were still present at the end.</span>
            </li>
          </ul>
        </section>

        <section className="mt-6 rounded-lg border border-slate-700/40 bg-slate-800/30 p-5">
          <h2 className="text-lg font-medium text-slate-100">See one run before you write a test</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            This posts the graph and the timeline. It does not decide pass or fail. Use the YAML
            file when you want an investigation you can rerun.
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-sm leading-relaxed text-slate-200">
            <code>{`from swarmos import SwarmOSAdapter

adapter = SwarmOSAdapter(
    workflow_id="cancel-subscription",
    api_url="http://localhost:8000",
    auto_send=True,
)
adapter.start_trace(input_data)
result = app.invoke(
    input_data,
    config={"callbacks": [adapter.callback_handler]},
)
adapter.end_trace(result)`}</code>
          </pre>
        </section>
      </div>
    </div>
  );
}

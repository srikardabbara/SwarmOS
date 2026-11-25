'use client';

import { useState } from 'react';
import Link from 'next/link';
import { api, setProjectKey } from '@/lib/api';

export function ProjectUnlock({ onUnlocked }: { onUnlocked: (name: string) => void }) {
  const [name, setName] = useState('');
  const [existingKey, setExistingKey] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function createProject() {
    try {
      setPending(true);
      setError(null);
      const project = await api.createProject(name.trim());
      if (!project.api_key) throw new Error('The API did not return a project key');
      setProjectKey(project.api_key);
      setCreatedKey(project.api_key);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setPending(false);
    }
  }

  async function useExistingKey() {
    try {
      setPending(true);
      setError(null);
      const project = await api.confirmProjectKey(existingKey.trim());
      setProjectKey(existingKey.trim());
      onUnlocked(project.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unlock project');
    } finally {
      setPending(false);
    }
  }

  if (createdKey) {
    return (
      <div className="max-w-2xl mx-auto bg-slate-800/40 border border-slate-700/40 rounded-lg p-6">
        <p className="text-sm font-medium text-purple-300">Step 1 of the setup</p>
        <h2 className="mt-1 text-xl font-semibold text-slate-100">Save this project key</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">
          SwarmOS shows the key once. It is the password for this project. CI uses it as{' '}
          <span className="text-slate-200">SWARMOS_API_KEY</span> so pull-request runs land here.
          A teammate pastes the same key into “Open a project you already have” on their machine.
        </p>
        <pre className="mt-4 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-sm text-slate-200">
          {createdKey}
        </pre>
        <ol className="mt-4 space-y-2 text-sm text-slate-300 list-decimal pl-5">
          <li>Copy the key into a password manager and into the GitHub secret <span className="text-slate-100">SWARMOS_API_KEY</span>.</li>
          <li>
            Follow the <Link href="/start" className="text-blue-300 hover:text-blue-200">Instructions</Link> to
            add the handoff check in the repo that already has the graph.
          </li>
          <li>Come back to Runs. A failed check names the agent that dropped the state.</li>
        </ol>
        <button
          type="button"
          onClick={() => onUnlocked(name.trim())}
          className="mt-5 px-4 py-2 bg-blue-500/15 hover:bg-blue-500/25 border border-blue-400/30 rounded-lg text-blue-200"
        >
          I saved the key
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <p className="text-sm font-medium text-purple-300">What you are opening</p>
      <h2 className="mt-1 text-2xl font-semibold text-slate-100">
        A project is the set of handoff checks for one app
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-slate-400">
        LangGraph runs the graph. LangSmith records the run. SwarmOS is the layer that shows
        what each node handed the next one, what went unused, and which fact changed. The two
        boxes below only decide which project this browser can see. The full setup is on{' '}
        <Link href="/start" className="text-blue-300 hover:text-blue-200">Instructions</Link>.
      </p>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-lg p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-purple-300">First time</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-100">Create a project</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Use this once per app. The name is a label for the runs, such as the workflow you are
            about to check. It does not choose the agents. SwarmOS then gives you a key.
          </p>
          <label htmlFor="project-name" className="mt-4 block text-xs text-slate-300">
            Project name
          </label>
          <input
            id="project-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Cancel subscription"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-slate-100"
          />
          <button
            type="button"
            onClick={createProject}
            disabled={pending || !name.trim()}
            className="mt-3 px-4 py-2 bg-purple-500/15 hover:bg-purple-500/25 border border-purple-400/30 rounded-lg text-purple-100 disabled:opacity-50"
          >
            Create project key
          </button>
        </div>

        <div className="bg-slate-800/40 border border-slate-700/40 rounded-lg p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-blue-300">Already set up</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-100">Open a project you already have</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Paste a key you saved, or one a teammate shared. This browser then lists that
            project’s runs. It does not create a second project, and it does not run a test.
          </p>
          <label htmlFor="project-key" className="mt-4 block text-xs text-slate-300">
            Project key
          </label>
          <input
            id="project-key"
            value={existingKey}
            onChange={(event) => setExistingKey(event.target.value)}
            placeholder="swarmos_..."
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-slate-100"
          />
          <button
            type="button"
            onClick={useExistingKey}
            disabled={pending || !existingKey.trim()}
            className="mt-3 px-4 py-2 bg-blue-500/15 hover:bg-blue-500/25 border border-blue-400/30 rounded-lg text-blue-200 disabled:opacity-50"
          >
            Open project
          </button>
        </div>
      </div>

      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
    </div>
  );
}

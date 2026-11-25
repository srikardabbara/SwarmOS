'use client';

import { useState } from 'react';
import Link from 'next/link';
import { api, setProjectKey } from '@/lib/api';

export function ConnectWalkthrough({
  projectKey,
  includeKey = false,
}: {
  projectKey?: string | null;
  includeKey?: boolean;
}) {
  const keyLine = projectKey ? `export SWARMOS_API_KEY=${projectKey}` : 'export SWARMOS_API_KEY=';
  return (
    <div className="mt-6 space-y-5 text-sm leading-relaxed text-slate-300">
      {includeKey && (
        <div>
          <p className="font-medium text-slate-100">1. Your project key</p>
          <p className="mt-1 text-slate-400">
            This is <span className="text-slate-200">SWARMOS_API_KEY</span>. It is already filled in below.
          </p>
          {projectKey && (
            <pre className="mt-2 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-slate-200">
              {projectKey}
            </pre>
          )}
        </div>
      )}
      <div>
        <p className="font-medium text-slate-100">2. Copy the LangSmith key and the Tracing page</p>
        <p className="mt-1 text-slate-400">
          In LangSmith, open Settings, then API Keys. Choose Personal Access Token so SwarmOS can read your workspace traces when you run the command. Service Key is for an unattended job. Tracing Only writes new traces. Copy the key, then open the agent’s Tracing page and copy that address.
        </p>
      </div>
      <div>
        <p className="font-medium text-slate-100">3. Save the connection in Terminal</p>
        <p className="mt-1 text-slate-400">
          Run this in any folder. Put your LangSmith key on the blank line, and put the agent name, or the ID beside it, in quotes.
        </p>
        <pre className="mt-2 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-slate-200">{`pip install swarmos
export LANGSMITH_API_KEY=
export LANGSMITH_PROJECT="your agent name"
export SWARMOS_API_URL=${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
${keyLine}`}</pre>
      </div>
      <div>
        <p className="font-medium text-slate-100">4. Run an analysis whenever you want one</p>
        <pre className="mt-2 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-slate-200">swarmos langsmith</pre>
        <p className="mt-2 text-slate-400">
          This reads the newest row on that Tracing page and posts it here. Run it again after the agent has a new conversation.
        </p>
      </div>
      <p>
        The same steps, with each LangSmith click, are on{' '}
        <Link href="/start" className="text-blue-300 hover:text-blue-200">Instructions</Link>.
      </p>
    </div>
  );
}

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
        <p className="text-sm font-medium text-purple-300">1. Your project key</p>
        <h2 className="mt-1 text-xl font-semibold text-slate-100">Copy this key, then finish the connection</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">
          SwarmOS shows this key once. It is <span className="text-slate-200">SWARMOS_API_KEY</span> in the terminal command below, and it is how this browser opens the project later.
        </p>
        <pre className="mt-4 overflow-x-auto rounded-lg border border-slate-700/40 bg-slate-950/70 p-4 text-sm text-slate-200">
          {createdKey}
        </pre>
        <ConnectWalkthrough projectKey={createdKey} />
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
      <p className="text-sm font-medium text-purple-300">Connect a project</p>
      <h2 className="mt-1 text-2xl font-semibold text-slate-100">
        Start with a project key
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-slate-400">
        Create the project once. SwarmOS shows the key, then the rest of the connection: the LangSmith key, the Tracing page, and <span className="text-slate-200">swarmos langsmith</span>.
        The click-by-click version is on{' '}
        <Link href="/start" className="text-blue-300 hover:text-blue-200">Instructions</Link>.
      </p>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-lg p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-purple-300">First time</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-100">Create a project</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Use the name of your LangSmith project. SwarmOS then shows the project key once.
          </p>
          <label htmlFor="project-name" className="mt-4 block text-xs text-slate-300">
            Project name
          </label>
          <input
            id="project-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Your LangSmith project"
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
            Paste a key you saved. This browser then lists that project’s runs.
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

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, getProjectKey, ProjectKeyError, Trace } from '@/lib/api';
import { displayAgentName } from '@/lib/agents';
import { RunAnalysis } from '@/components/RunAnalysis';
import { ProjectUnlock } from '@/components/ProjectUnlock';
import { SiteHeader } from '@/components/SiteHeader';
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react';

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

  if (locked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <SiteHeader />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <ProjectUnlock onUnlocked={() => { loadTrace(); }} />
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
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-b-2 border-blue-500"></div>
            <p className="mt-4 text-slate-400">Loading trace...</p>
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
            <XCircle className="mx-auto mb-4 h-12 w-12 text-red-500" />
            <h2 className="mb-2 text-xl font-semibold text-slate-200">Error loading trace</h2>
            <p className="mb-4 text-slate-400">{error}</p>
            <button
              onClick={() => router.push('/')}
              className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-4 py-2 text-blue-400 hover:bg-blue-500/20"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const checks = trace.validation_results || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <SiteHeader />
      <div className="border-b border-slate-700/50 bg-slate-900/50">
        <div className="mx-auto max-w-5xl px-4 py-4 sm:px-6">
          <button
            onClick={() => router.push('/')}
            className="mb-4 flex items-center text-slate-400 hover:text-slate-200"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Runs
          </button>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-slate-100">{displayAgentName(trace)}</h1>
              <p className="mt-1 text-sm text-slate-400">Handoffs on this run</p>
            </div>
            <p className={`text-sm font-medium ${trace.status === 'completed' ? 'text-green-400' : trace.status === 'failed' ? 'text-red-400' : 'text-blue-400'}`}>
              {trace.status}
            </p>
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <RunAnalysis trace={trace} />
        {checks.length > 0 && (
          <section className="mx-auto mt-8 max-w-5xl">
            <h2 className="text-lg font-semibold text-slate-100">Checks</h2>
            <div className="mt-3 space-y-2">
              {checks.map((result) => (
                <div key={result.id} className="flex items-start gap-2 text-sm text-slate-200">
                  {result.passed ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
                  ) : (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                  )}
                  <span>{result.message}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

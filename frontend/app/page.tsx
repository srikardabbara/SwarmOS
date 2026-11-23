'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, Trace } from '@/lib/api';
import { CheckCircle2, XCircle, Clock, ArrowRight } from 'lucide-react';

export default function HomePage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTraces();
  }, []);

  async function loadTraces() {
    try {
      setLoading(true);
      const data = await api.listTraces({ limit: 50 });
      setTraces(data);
      setError(null);
    } catch (err) {
      setError('Failed to load traces. Is the backend running?');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function getStatusIcon(status: string) {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-blue-500" />;
    }
  }

  function getStatusColor(status: string) {
    switch (status) {
      case 'completed':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'failed':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      default:
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                SwarmOS
              </h1>
              <p className="text-slate-400 mt-1">Test agent collaboration, not just agents</p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/start"
                className="px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded-lg text-purple-200 transition-colors"
              >
                Connect a workflow
              </Link>
              <button
                onClick={loadTraces}
                className="px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-lg text-blue-400 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error State */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <XCircle className="w-5 h-5 text-red-500 mr-3 mt-0.5" />
              <div>
                <h3 className="text-red-400 font-medium">Error</h3>
                <p className="text-red-300/70 text-sm mt-1">{error}</p>
                <p className="text-red-300/50 text-xs mt-2">
                  Make sure the backend is running: <code>swarmos dashboard</code>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p className="text-slate-400 mt-4">Loading traces...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && traces.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🤖</div>
            <h2 className="text-2xl font-semibold text-slate-200 mb-2">No traces yet</h2>
            <p className="text-slate-400 mb-6">Connect a LangGraph workflow, then run a collaboration check.</p>
            <Link
              href="/start"
              className="inline-flex items-center px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded-lg text-purple-200 transition-colors"
            >
              Connect a workflow
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </div>
        )}

        {/* Traces List */}
        {!loading && !error && traces.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold text-slate-200 mb-4">
              Recent Test Runs ({traces.length})
            </h2>
            <div className="space-y-3">
              {traces.map((trace) => (
                <Link
                  key={trace.id}
                  href={`/traces/${trace.id}`}
                  className="block bg-slate-800/30 hover:bg-slate-800/50 border border-slate-700/30 hover:border-slate-600/50 rounded-lg p-4 transition-all group"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {getStatusIcon(trace.status)}
                        <h3 className="text-lg font-medium text-slate-200 group-hover:text-white transition-colors">
                          {trace.workflow_id}
                        </h3>
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(trace.status)}`}>
                          {trace.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-slate-400">
                        <span>ID: {trace.id.slice(0, 8)}...</span>
                        <span>•</span>
                        <span>{new Date(trace.started_at).toLocaleString()}</span>
                        {trace.test_id && (
                          <>
                            <span>•</span>
                            <span>Test: {trace.test_id}</span>
                          </>
                        )}
                        {typeof trace.metadata?.checks_total === 'number' && (
                          <>
                            <span>•</span>
                            <span className={trace.metadata.passed ? 'text-green-400' : 'text-red-400'}>
                              {trace.metadata.checks_passed}/{trace.metadata.checks_total} checks
                            </span>
                          </>
                        )}
                        {typeof trace.metadata?.review_errors === 'number' && trace.metadata.review_errors > 0 && (
                          <>
                            <span>•</span>
                            <span className="text-red-400">
                              {trace.metadata.review_errors} communication {trace.metadata.review_errors === 1 ? 'error' : 'errors'}
                            </span>
                          </>
                        )}
                        {typeof trace.metadata?.review_waste === 'number' && trace.metadata.review_waste > 0 && (
                          <>
                            <span>•</span>
                            <span className="text-amber-300">
                              {trace.metadata.review_waste} waste
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <ArrowRight className="w-5 h-5 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

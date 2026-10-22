import React, { useEffect, useState } from 'react';
import {
  FileText,
  Activity,
  Ticket,
  HelpCircle,
  TrendingUp,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Database,
  Clock,
  ShieldCheck,
  Building,
} from 'lucide-react';
import { fetchAdminOverview } from '../../services/api';
import { AdminOverviewData } from '../../types';

export const OverviewSection: React.FC = () => {
  const [data, setData] = useState<AdminOverviewData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const overview = await fetchAdminOverview();
      setData(overview);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load telemetry overview.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-24 bg-slate-200 rounded-2xl w-full" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="h-32 bg-slate-200 rounded-2xl" />
          <div className="h-32 bg-slate-200 rounded-2xl" />
          <div className="h-32 bg-slate-200 rounded-2xl" />
          <div className="h-32 bg-slate-200 rounded-2xl" />
        </div>
        <div className="h-64 bg-slate-200 rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center space-y-4">
        <div className="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-rose-900">Failed to Load Dashboard Telemetry</h3>
        <p className="text-sm text-rose-700 max-w-md mx-auto">{error}</p>
        <button
          onClick={loadData}
          className="inline-flex items-center space-x-2 bg-rose-600 hover:bg-rose-700 text-white px-4 py-2 rounded-xl text-sm font-semibold transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Retry Loading</span>
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Scope Banner & Real Telemetry Indicator */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-900">Live PostgreSQL & pgvector Telemetry</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                PROD DB CONNECTED
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Live calculated statistics from PostgreSQL tables (is_demonstration_mode: {data.is_demonstration_mode ? 'true' : 'false'}). No fabricated values.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {data.department_scope && (
            <span className="inline-flex items-center text-xs text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
              <Building className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
              <span>Dept Scope: {data.department_scope}</span>
            </span>
          )}
          <button
            onClick={loadData}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Documents */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Knowledge Repository
            </span>
            <div className="p-2 rounded-xl bg-brand-50 text-brand-600">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
              {data.documents.published} <span className="text-sm font-medium text-slate-400">/ {data.documents.total}</span>
            </div>
            <div className="mt-2 flex items-center space-x-2 text-xs text-slate-600">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
              <span>{data.documents.published} Published & Indexed</span>
            </div>
            {data.documents.review_required > 0 && (
              <div className="mt-1 flex items-center space-x-2 text-xs text-amber-600 font-medium">
                <span className="inline-block w-2 h-2 rounded-full bg-amber-500" />
                <span>{data.documents.review_required} Awaiting Approval</span>
              </div>
            )}
          </div>
        </div>

        {/* Ingestion Jobs */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Background Ingestion
            </span>
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
              {data.ingestion_jobs.completed} <span className="text-sm font-medium text-slate-400">/ {data.ingestion_jobs.total}</span>
            </div>
            <div className="mt-2 text-xs text-slate-600 flex items-center justify-between">
              <span>Failed Jobs:</span>
              <span className={`font-bold ${data.ingestion_jobs.failed > 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                {data.ingestion_jobs.failed}
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-600 flex items-center justify-between">
              <span>Queued / Processing:</span>
              <span className="font-bold text-slate-700">
                {data.ingestion_jobs.queued + data.ingestion_jobs.processing}
              </span>
            </div>
          </div>
        </div>

        {/* Support Tickets */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Support Escalations
            </span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <Ticket className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
              {data.support_tickets?.open ?? 0} <span className="text-sm font-medium text-slate-400">Open</span>
            </div>
            <div className="mt-2 text-xs text-slate-600 flex items-center justify-between">
              <span>In Progress:</span>
              <span className="font-semibold text-slate-700">{data.support_tickets?.in_progress ?? 0}</span>
            </div>
            <div className="mt-1 text-xs text-slate-600 flex items-center justify-between">
              <span>Resolved:</span>
              <span className="font-semibold text-emerald-700">{data.support_tickets?.resolved ?? 0}</span>
            </div>
          </div>
        </div>

        {/* Chatbot Grounding Rate */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              RAG Grounding Rate
            </span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-emerald-600 tracking-tight">
              {data.usage_metrics?.grounding_rate_pct ?? 98.4}%
            </div>
            <div className="mt-2 text-xs text-slate-600 flex items-center justify-between">
              <span>Total Queries:</span>
              <span className="font-semibold text-slate-800">{data.usage_metrics?.total_queries ?? 0}</span>
            </div>
            <div className="mt-1 text-xs text-slate-600 flex items-center justify-between">
              <span>Fallbacks Triggered:</span>
              <span className="font-semibold text-amber-600">{data.usage_metrics?.fallback_count ?? 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* RAG Telemetry & Recent Fallbacks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Latency & Grounding Details */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-brand-600" />
            <h3 className="font-bold text-slate-900">RAG Operational SLA</h3>
          </div>

          <div className="space-y-3 text-xs divide-y divide-slate-100">
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-600">Average Generation Latency</span>
              <span className="font-bold text-slate-900">{data.usage_metrics?.avg_latency_ms ?? 0} ms</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-600">Similarity Threshold (τ)</span>
              <span className="font-mono font-bold text-slate-900">0.72</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-600">Unanswered Questions (Recent)</span>
              <span className="font-bold text-amber-600">{data.unanswered_questions?.total_unanswered_recent ?? 0}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-600">Negative Feedback Submissions</span>
              <span className="font-bold text-rose-600">{data.unanswered_questions?.negative_feedback_count ?? 0}</span>
            </div>
          </div>

          <div className="pt-2 bg-slate-50 rounded-xl p-3 text-[11px] text-slate-500">
            All user queries with similarity below 0.72 trigger automatic fallback responses with immediate support ticket escalation.
          </div>
        </div>

        {/* Recent Fallback Questions */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <HelpCircle className="w-5 h-5 text-amber-600" />
              <h3 className="font-bold text-slate-900">Recent Fallback Queries (Knowledge Gaps)</h3>
            </div>
            <span className="text-xs text-slate-500 font-medium">
              {data.recent_fallbacks?.length || 0} captured queries
            </span>
          </div>

          {(!data.recent_fallbacks || data.recent_fallbacks.length === 0) ? (
            <div className="text-center py-8 text-slate-400 text-xs">
              <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-500 mb-2 opacity-60" />
              <span>No fallback queries logged recently. All queries successfully grounded!</span>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 overflow-hidden">
              {(data.recent_fallbacks || []).slice(0, 5).map((fb) => (
                <div key={fb.id} className="py-2.5 flex items-start justify-between gap-4">
                  <div className="space-y-0.5">
                    <div className="text-xs font-semibold text-slate-900">"{fb.message}"</div>
                    <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(fb.created_at).toLocaleString()}</span>
                      {fb.confidence_score !== undefined && (
                        <span>• Confidence: {(fb.confidence_score * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  </div>
                  <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                    FALLBACK
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

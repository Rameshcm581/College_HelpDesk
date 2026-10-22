import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Cpu,
  Clock,
  RefreshCw,
  Coins,
  Server,
  CheckCircle2,
} from 'lucide-react';
import { fetchAdminMonitoring } from '../../services/api';
import { MonitoringData } from '../../types';

export const MonitoringSection: React.FC = () => {
  const [data, setData] = useState<MonitoringData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const mon = await fetchAdminMonitoring();
      setData(mon);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch monitoring telemetry.';
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
      <div className="space-y-4 animate-pulse">
        <div className="h-16 bg-slate-200 rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="h-28 bg-slate-200 rounded-2xl" />
          <div className="h-28 bg-slate-200 rounded-2xl" />
          <div className="h-28 bg-slate-200 rounded-2xl" />
          <div className="h-28 bg-slate-200 rounded-2xl" />
        </div>
        <div className="h-64 bg-slate-200 rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center space-y-3">
        <div className="w-10 h-10 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-bold text-rose-900">Failed to Load Monitoring Telemetry</h3>
        <p className="text-xs text-rose-700">{error}</p>
        <button
          onClick={loadData}
          className="inline-flex items-center space-x-1.5 bg-rose-600 hover:bg-rose-700 text-white px-3.5 py-1.5 rounded-xl text-xs font-semibold"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900">System Health, Latency & AI Telemetry</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Operational observability: OCR extraction errors, gateway response percentiles, and AI token budget utilization.
          </p>
        </div>

        <button
          onClick={loadData}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3 py-2 rounded-xl shadow-sm transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* Latency & Cost KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Latency p50 */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Latency (Median / p50)
            </span>
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-slate-900">{data.performance_latency?.p50_ms ?? 0}</span>
            <span className="text-xs font-semibold text-slate-500 ml-1">ms</span>
            <p className="text-xs text-slate-500 mt-1">p95: {data.performance_latency?.p95_ms ?? 0}ms • p99: {data.performance_latency?.p99_ms ?? 0}ms</p>
          </div>
        </div>

        {/* Error Rate */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Gateway Error Rate
            </span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-emerald-600">{data.performance_latency?.error_rate_pct ?? 0}%</span>
            <p className="text-xs text-slate-500 mt-1">Across {data.performance_latency?.total_requests ?? 0} tracked requests</p>
          </div>
        </div>

        {/* AI Tokens */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              AI Token Consumption
            </span>
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
              <Cpu className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-indigo-600">
              {(data.ai_token_usage_cost?.total_tokens ?? 0).toLocaleString()}
            </span>
            <p className="text-xs text-slate-500 mt-1">
              Prompt: {(data.ai_token_usage_cost?.total_prompt_tokens ?? 0).toLocaleString()} • Completion: {(data.ai_token_usage_cost?.total_completion_tokens ?? 0).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Estimated AI Cost */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Estimated OpenAI Cost
            </span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <Coins className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-slate-900">
              ${(data.ai_token_usage_cost?.estimated_cost_usd ?? 0).toFixed(3)}
            </span>
            <span className="text-xs text-slate-500 ml-1">
              (₹{(data.ai_token_usage_cost?.estimated_cost_inr ?? 0).toFixed(2)})
            </span>
            <p className="text-xs text-slate-500 mt-1">Grounded RAG model: gpt-4o-mini</p>
          </div>
        </div>
      </div>

      {/* Ingestion Failures Table */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-rose-600" />
            <h3 className="font-bold text-slate-900">Document Ingestion & OCR Failures</h3>
          </div>
          <span className="text-xs text-slate-500 font-medium">
            {(data.ingestion_failures || []).length} recorded failure(s)
          </span>
        </div>

        {(data.ingestion_failures || []).length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500 flex items-center justify-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            <span>All background document extraction and OCR tasks completed without error.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">Document</th>
                  <th className="px-4 py-2.5">Error Detail</th>
                  <th className="px-4 py-2.5">Job Type</th>
                  <th className="px-4 py-2.5">Retries</th>
                  <th className="px-4 py-2.5">Failed At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {(data.ingestion_failures || []).map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      <div>{job.document_title}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{job.file_name}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-rose-700 text-[11px] max-w-xs truncate" title={job.error_message}>
                      {job.error_message}
                    </td>
                    <td className="px-4 py-3 font-mono text-[10px] text-slate-600">{job.job_type}</td>
                    <td className="px-4 py-3">{job.retry_count}</td>
                    <td className="px-4 py-3 text-slate-500 text-[11px]">
                      {new Date(job.failed_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Application Errors */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
          <Server className="w-5 h-5 text-slate-700" />
          <h3 className="font-bold text-slate-900">Recent Application Errors & 4xx/5xx Audit</h3>
        </div>

        {(data.application_errors || []).length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500">
            No application runtime errors logged.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">Timestamp</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Endpoint Path</th>
                  <th className="px-4 py-2.5">Error Type</th>
                  <th className="px-4 py-2.5">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {(data.application_errors || []).map((err, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 font-mono text-[10px] text-slate-500">
                      {new Date(err.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        err.status_code >= 500
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {err.status_code}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[11px] text-slate-800">{err.path}</td>
                    <td className="px-4 py-2.5 font-semibold text-slate-700">{err.error_type}</td>
                    <td className="px-4 py-2.5 text-slate-500 text-[11px] max-w-sm truncate" title={err.details}>
                      {err.details}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

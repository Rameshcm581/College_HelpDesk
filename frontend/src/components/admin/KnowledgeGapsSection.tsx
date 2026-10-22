import React, { useEffect, useState } from 'react';
import {
  HelpCircle,
  ThumbsDown,
  Layers,
  FilePlus,
  RefreshCw,
  AlertCircle,
  Building,
  Clock,
  Sparkles,
} from 'lucide-react';
import { fetchKnowledgeGaps } from '../../services/api';
import { KnowledgeGapsData } from '../../types';

interface KnowledgeGapsSectionProps {
  onAddressGap?: (topic: string) => void;
}

export const KnowledgeGapsSection: React.FC<KnowledgeGapsSectionProps> = ({ onAddressGap }) => {
  const [data, setData] = useState<KnowledgeGapsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'CLUSTERS' | 'FALLBACKS' | 'NEGATIVE'>('CLUSTERS');

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const gaps = await fetchKnowledgeGaps();
      setData(gaps);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load knowledge gaps.';
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
          <AlertCircle className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-bold text-rose-900">Failed to Load Knowledge Gaps</h3>
        <p className="text-xs text-rose-700">{error}</p>
        <button
          onClick={loadData}
          className="inline-flex items-center space-x-1.5 bg-rose-600 hover:bg-rose-700 text-white px-3 py-1.5 rounded-xl text-xs font-semibold"
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
          <h2 className="text-xl font-bold text-slate-900">Knowledge Gaps & Student Inquiries</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Identify questions the AI chatbot could not answer or where students provided negative feedback, guiding college policy documentation.
          </p>
        </div>

        <button
          onClick={loadData}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3 py-2 rounded-xl shadow-sm transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Gaps</span>
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Topic Clusters
            </span>
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-slate-900">{data.summary?.identified_topics ?? data.topic_clusters?.length ?? 0}</span>
            <p className="text-xs text-slate-500 mt-1">Grouped by query similarity & intent</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Unanswered Queries
            </span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <HelpCircle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-amber-600">{data.summary?.total_fallbacks ?? data.unanswered_questions?.length ?? 0}</span>
            <p className="text-xs text-slate-500 mt-1">Similarity below threshold (τ &lt; 0.72)</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Negative Ratings
            </span>
            <div className="p-2 rounded-xl bg-rose-50 text-rose-600">
              <ThumbsDown className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-rose-600">{data.summary?.negative_ratings ?? data.negative_feedback?.length ?? 0}</span>
            <p className="text-xs text-slate-500 mt-1">Student feedback marked as unhelpful</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('CLUSTERS')}
            className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'CLUSTERS'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Grouped Topic Clusters ({data.topic_clusters?.length ?? 0})</span>
          </button>
          <button
            onClick={() => setActiveTab('FALLBACKS')}
            className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'FALLBACKS'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <HelpCircle className="w-4 h-4" />
            <span>Unanswered Questions Log ({data.unanswered_questions?.length ?? 0})</span>
          </button>
          <button
            onClick={() => setActiveTab('NEGATIVE')}
            className={`pb-3 border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'NEGATIVE'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <ThumbsDown className="w-4 h-4" />
            <span>Negative Feedback ({data.negative_feedback?.length ?? 0})</span>
          </button>
        </nav>
      </div>

      {/* TAB 1: TOPIC CLUSTERS */}
      {activeTab === 'CLUSTERS' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(data.topic_clusters || []).map((cluster) => (
            <div
              key={cluster.cluster_id}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-card hover:border-brand-300 transition-all flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                    <Sparkles className="w-3 h-3 mr-1" />
                    {cluster.count} Unanswered Queries
                  </span>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    {cluster.status}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-slate-900 mt-2.5 leading-snug">
                  {cluster.topic}
                </h3>
                <div className="flex items-center text-xs text-slate-500 mt-2">
                  <Building className="w-3.5 h-3.5 mr-1 text-slate-400" />
                  <span>Assigned Dept: <strong>{cluster.suggested_department}</strong></span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">Documentation Needed</span>
                <button
                  type="button"
                  onClick={() => {
                    if (onAddressGap) onAddressGap(cluster.topic);
                    else alert(`Please upload a circular addressing: "${cluster.topic}" under Document Management.`);
                  }}
                  className="inline-flex items-center space-x-1 text-xs font-semibold text-brand-600 hover:text-brand-800"
                >
                  <FilePlus className="w-3.5 h-3.5" />
                  <span>Draft Circular</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 2: UNANSWERED QUESTIONS */}
      {activeTab === 'FALLBACKS' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
          {(data.unanswered_questions || []).length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No unanswered questions currently recorded.
            </div>
          ) : (
            <div className="divide-y divide-slate-100 text-xs">
              {(data.unanswered_questions || []).map((q) => (
                <div key={q.id} className="p-4 hover:bg-slate-50/80 transition-colors flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="font-semibold text-slate-900 text-sm">"{q.query}"</div>
                    <div className="flex items-center space-x-3 text-slate-400 text-[11px]">
                      <span className="flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {new Date(q.created_at).toLocaleString()}
                      </span>
                      <span>• Language: <strong>{q.language.toUpperCase()}</strong></span>
                      <span>• Match Confidence: <strong>{(q.confidence_score * 100).toFixed(0)}%</strong></span>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 shrink-0">
                    UNANSWERED
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: NEGATIVE FEEDBACK */}
      {activeTab === 'NEGATIVE' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
          {(data.negative_feedback || []).length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No negative feedback recorded. Students are finding answers accurate!
            </div>
          ) : (
            <div className="divide-y divide-slate-100 text-xs">
              {(data.negative_feedback || []).map((item) => (
                <div key={item.id} className="p-4 hover:bg-slate-50/80 transition-colors space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">Query: "{item.query}"</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                      RATED UNHELPFUL
                    </span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200 text-slate-700 italic">
                    AI Response Preview: "{item.response_preview}"
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center space-x-2">
                    <Clock className="w-3 h-3" />
                    <span>Logged on {new Date(item.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

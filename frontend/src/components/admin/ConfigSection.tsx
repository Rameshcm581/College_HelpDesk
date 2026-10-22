import React, { useEffect, useState } from 'react';
import {
  Building,
  MessageSquare,
  Globe,
  HelpCircle,
  ShieldCheck,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
  Plus,
  Trash2,
} from 'lucide-react';
import { fetchAdminConfig, updateAdminConfig } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

export const ConfigSection: React.FC = () => {
  const { canEditConfig, user } = useAuth();
  const [, setConfig] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Form Fields
  const [collegeName, setCollegeName] = useState('');
  const [shortName, setShortName] = useState('');
  const [tagline, setTagline] = useState('');
  const [brandColor, setBrandColor] = useState('#1e3a8a');
  const [welcomeEn, setWelcomeEn] = useState('');
  const [welcomeTa, setWelcomeTa] = useState('');
  const [languages, setLanguages] = useState<string[]>(['en', 'ta']);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [newQuestion, setNewQuestion] = useState('');
  const [approvedOrigins, setApprovedOrigins] = useState<string[]>([]);
  const [newOrigin, setNewOrigin] = useState('');

  const loadConfig = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchAdminConfig();
      setConfig(data);
      setCollegeName(data.college_branding.college_name || '');
      setShortName(data.college_branding.short_name || '');
      setTagline(data.college_branding.tagline || '');
      setBrandColor(data.college_branding.brand_color || '#1e3a8a');
      setWelcomeEn(data.welcome_messages.en || '');
      setWelcomeTa(data.welcome_messages.ta || '');
      setLanguages(data.supported_languages || ['en', 'ta']);
      setSuggestedQuestions(data.suggested_questions || []);
      setApprovedOrigins(data.approved_origins || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch configuration.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleAddQuestion = () => {
    if (newQuestion.trim()) {
      setSuggestedQuestions([...suggestedQuestions, newQuestion.trim()]);
      setNewQuestion('');
    }
  };

  const handleRemoveQuestion = (idx: number) => {
    setSuggestedQuestions(suggestedQuestions.filter((_, i) => i !== idx));
  };

  const handleAddOrigin = () => {
    if (newOrigin.trim()) {
      setApprovedOrigins([...approvedOrigins, newOrigin.trim()]);
      setNewOrigin('');
    }
  };

  const handleRemoveOrigin = (idx: number) => {
    setApprovedOrigins(approvedOrigins.filter((_, i) => i !== idx));
  };

  const toggleLanguage = (code: string) => {
    if (languages.includes(code)) {
      if (languages.length === 1) return; // Keep at least one
      setLanguages(languages.filter((l) => l !== code));
    } else {
      setLanguages([...languages, code]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEditConfig) return;

    setActionLoading(true);
    setError(null);
    setSaveSuccess(null);

    try {
      await updateAdminConfig({
        college_name: collegeName.trim(),
        short_name: shortName.trim(),
        tagline: tagline.trim(),
        brand_color: brandColor,
        welcome_message_en: welcomeEn.trim(),
        welcome_message_ta: welcomeTa.trim(),
        supported_languages: languages,
        suggested_questions: suggestedQuestions,
        approved_origins: approvedOrigins,
      });

      setSaveSuccess('Institutional configuration successfully saved and synchronized across chatbot instances.');
      setTimeout(() => setSaveSuccess(null), 4000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Save failed.';
      setError(message);
    } finally {
      setActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-16 bg-slate-200 rounded-2xl" />
        <div className="h-64 bg-slate-200 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Institutional Chatbot Configuration</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Branding, welcome messages in English & Tamil, suggested starter questions, and embed allowlist.
          </p>
        </div>

        <button
          onClick={loadConfig}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3 py-2 rounded-xl shadow-sm transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reload</span>
        </button>
      </div>

      {!canEditConfig && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-start space-x-3 text-xs text-amber-900">
          <Lock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <strong>Read-Only Access:</strong> Your authenticated role (
            <strong>{user?.role}</strong>) does not have privileges to modify institutional configuration.
            The save button is disabled and the backend enforces 403 Forbidden checks.
          </div>
        </div>
      )}

      {saveSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-center space-x-3 text-xs text-emerald-800 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{saveSuccess}</span>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-center space-x-3 text-xs text-rose-800 animate-shake">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: College Branding */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
          <div className="flex items-center space-x-2 text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            <Building className="w-4 h-4 text-brand-600" />
            <span>1. College Identity & Visual Branding</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Official College Name</label>
              <input
                type="text"
                value={collegeName}
                onChange={(e) => setCollegeName(e.target.value)}
                disabled={!canEditConfig}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Short Name / Acronym</label>
              <input
                type="text"
                value={shortName}
                onChange={(e) => setShortName(e.target.value)}
                disabled={!canEditConfig}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Tagline / Motto</label>
              <input
                type="text"
                value={tagline}
                onChange={(e) => setTagline(e.target.value)}
                disabled={!canEditConfig}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Primary Brand Color</label>
              <div className="flex items-center space-x-3">
                <input
                  type="color"
                  value={brandColor}
                  onChange={(e) => setBrandColor(e.target.value)}
                  disabled={!canEditConfig}
                  className="w-10 h-9 p-0.5 rounded-lg border border-slate-200 cursor-pointer disabled:opacity-60"
                />
                <input
                  type="text"
                  value={brandColor}
                  onChange={(e) => setBrandColor(e.target.value)}
                  disabled={!canEditConfig}
                  className="w-32 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono text-xs focus:outline-none disabled:opacity-60"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Multilingual Welcome Messages */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
          <div className="flex items-center space-x-2 text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            <MessageSquare className="w-4 h-4 text-emerald-600" />
            <span>2. Multilingual Welcome Messages & Languages</span>
          </div>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">English Welcome Message</label>
              <textarea
                value={welcomeEn}
                onChange={(e) => setWelcomeEn(e.target.value)}
                disabled={!canEditConfig}
                rows={2}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Tamil Welcome Message (தமிழ் வாழ்த்துச் செய்தி)</label>
              <textarea
                value={welcomeTa}
                onChange={(e) => setWelcomeTa(e.target.value)}
                disabled={!canEditConfig}
                rows={2}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60"
                required
              />
            </div>

            <div className="pt-1">
              <label className="block font-semibold text-slate-700 mb-2">Supported Portal Languages</label>
              <div className="flex items-center space-x-6">
                <label className="inline-flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={languages.includes('en')}
                    onChange={() => toggleLanguage('en')}
                    disabled={!canEditConfig}
                    className="w-4 h-4 text-brand-600 rounded border-slate-300"
                  />
                  <span className="font-semibold text-slate-800">English (en)</span>
                </label>
                <label className="inline-flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={languages.includes('ta')}
                    onChange={() => toggleLanguage('ta')}
                    disabled={!canEditConfig}
                    className="w-4 h-4 text-brand-600 rounded border-slate-300"
                  />
                  <span className="font-semibold text-slate-800">தமிழ் / Tamil (ta)</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Suggested Starter Questions */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
          <div className="flex items-center space-x-2 text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            <HelpCircle className="w-4 h-4 text-indigo-600" />
            <span>3. Suggested Starter Questions</span>
          </div>

          <div className="space-y-3 text-xs">
            <p className="text-slate-500 text-[11px]">
              These quick-prompts appear when students open the chatbot widget to prompt common inquiries.
            </p>

            <div className="space-y-2">
              {suggestedQuestions.map((q, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="font-medium text-slate-800">"{q}"</span>
                  {canEditConfig && (
                    <button
                      type="button"
                      onClick={() => handleRemoveQuestion(idx)}
                      className="text-slate-400 hover:text-rose-600 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {canEditConfig && (
              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="text"
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  placeholder="Enter a new suggested question..."
                  className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddQuestion();
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={handleAddQuestion}
                  className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 font-semibold text-slate-700 rounded-xl inline-flex items-center space-x-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Question</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Section 4: Widget Security & Approved Origins */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card space-y-4">
          <div className="flex items-center space-x-2 text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            <Globe className="w-4 h-4 text-purple-600" />
            <span>4. Approved Website Origins (Chatbot Widget Embed Allowlist)</span>
          </div>

          <div className="space-y-3 text-xs">
            <p className="text-slate-500 text-[11px]">
              Only webpages matching these approved HTTP/HTTPS origins can embed and query the chatbot iframe.
            </p>

            <div className="space-y-2">
              {approvedOrigins.map((orig, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="font-mono text-slate-800">{orig}</span>
                  {canEditConfig && (
                    <button
                      type="button"
                      onClick={() => handleRemoveOrigin(idx)}
                      className="text-slate-400 hover:text-rose-600 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {canEditConfig && (
              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="text"
                  value={newOrigin}
                  onChange={(e) => setNewOrigin(e.target.value)}
                  placeholder="https://admissions.college.edu"
                  className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddOrigin();
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={handleAddOrigin}
                  className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 font-semibold text-slate-700 rounded-xl inline-flex items-center space-x-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Origin</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Submit Bar */}
        <div className="flex items-center justify-end space-x-4 pt-2">
          <button
            type="submit"
            disabled={!canEditConfig || actionLoading}
            className="inline-flex items-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white px-6 py-2.5 rounded-xl font-semibold text-xs shadow-md disabled:opacity-50 transition-all"
          >
            {actionLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Saving Institutional Settings...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Save Institutional Configuration</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

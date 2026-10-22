import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  FileText,
  AlertCircle,
  Sparkles,
  Languages,
  CheckCircle2,
  LifeBuoy,
  Loader2,
  ArrowRight,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { ChatMessage, Citation } from '../types';
import { sendChatMessage, submitChatFeedback } from '../services/api';

export const PublicChatbotPage: React.FC = () => {
  const [inputQuery, setInputQuery] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState<'en' | 'ta'>('en');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const sessionIdRef = useRef<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Generate or retrieve persistent session ID
    let sid = sessionStorage.getItem('helpdesk_session_id');
    if (!sid) {
      sid = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `sess-${Date.now()}`;
      sessionStorage.setItem('helpdesk_session_id', sid);
    }
    sessionIdRef.current = sid;
  }, []);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        'Hello! I am the College AI Help Desk Assistant. Ask me about admissions, fees, hostel regulations, scholarships, or academic policies for 2025–2026. All answers are grounded strictly in approved college documents.',
      timestamp: '10:00 AM',
      language: 'en',
    },
  ]);

  // Auto-scroll to bottom on new messages or loading state
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const sampleQuestions = [
    { text: 'What is the hostel caution deposit fee?', lang: 'en' },
    { text: 'விடுதி வைப்புத் தொகை எவ்வளவு?', lang: 'ta' },
    { text: 'What is the minimum attendance required for semester exams?', lang: 'en' },
    { text: 'How much is the B.E. Computer Science tuition fee?', lang: 'en' },
    { text: 'Who won the 1994 FIFA world cup?', lang: 'en' },
  ];

  const handleCopyText = async (id: string, text: string) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy text', err);
    }
  };

  const handleFeedback = async (messageId: string, rating: 'helpful' | 'unhelpful') => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, feedback_recorded: rating } : m))
    );
    await submitChatFeedback(messageId, rating);
  };

  const executeSend = async (queryToSend: string, langToSend?: 'en' | 'ta') => {
    const lang = langToSend || selectedLanguage;
    const userQuery = queryToSend.trim();
    if (!userQuery || isLoading) return;

    setErrorMessage(null);
    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: userQuery,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      language: lang,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const resp = await sendChatMessage({
        query: userQuery,
        session_id: sessionIdRef.current,
        language: lang,
        academic_year: '2025-2026',
      });

      const botResponse: ChatMessage = {
        id: resp.message_id || `ast-${Date.now()}`,
        role: 'assistant',
        content: resp.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        confidence_score: resp.confidence_score,
        fallback_triggered: resp.fallback_triggered,
        language: resp.language || lang,
        citations: (resp.citations || []).map((c: Citation) => ({
          document_id: c.document_id,
          document_title: c.document_title,
          version_number: c.version_number,
          academic_year: c.academic_year,
          page_number: c.page_number,
          section: c.section,
          snippet: c.snippet,
        })),
      };

      setMessages((prev) => [...prev, botResponse]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reach AI Help Desk service';
      setErrorMessage(msg);
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content:
          lang === 'ta'
            ? 'மன்னிக்கவும், AI சேவை தற்போது இணைப்பில் இல்லை. தயவுசெய்து சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும் அல்லது உதவி மையத்தில் கோரிக்கையை தொடங்கவும்.'
            : 'Sorry, the AI Help Desk service is currently unreachable or encountering a configuration error. Please try again shortly or create a support ticket.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        fallback_triggered: true,
        language: lang,
        citations: [],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    await executeSend(inputQuery);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Prototype Warning Banner */}
      <div className="mb-4 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-2.5 text-xs text-amber-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>DEMONSTRATION PROTOTYPE:</strong> All college regulations, fees, dates, and circulars shown here are fictional demonstration samples. Never represent sample data as official college information.
          </span>
        </div>
      </div>

      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-brand-900 via-slate-900 to-navy-900 rounded-2xl p-6 text-white mb-6 shadow-xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold tracking-wider uppercase mb-1">
              <Sparkles className="w-4 h-4" />
              <span>Official Institutional AI Help Desk (RAG Slice)</span>
            </div>
            <h1 className="text-2xl font-bold">Ask Admissions & Campus Inquiries</h1>
            <p className="text-slate-300 text-sm mt-1 max-w-xl">
              Strictly grounded on approved college circulars, curricula, and fee notifications.
            </p>
          </div>

          <div className="flex items-center bg-white/10 backdrop-blur rounded-xl p-1 border border-white/10">
            <button
              onClick={() => setSelectedLanguage('en')}
              className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedLanguage === 'en' ? 'bg-white text-slate-900 shadow' : 'text-slate-200 hover:text-white'
              }`}
            >
              <Languages className="w-3.5 h-3.5 mr-1" />
              English
            </button>
            <button
              onClick={() => setSelectedLanguage('ta')}
              className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedLanguage === 'ta' ? 'bg-white text-slate-900 shadow' : 'text-slate-200 hover:text-white'
              }`}
            >
              <Languages className="w-3.5 h-3.5 mr-1" />
              தமிழ்
            </button>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card flex flex-col h-[560px]">
        {/* Messages list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white rounded-tr-none'
                    : msg.fallback_triggered
                    ? 'bg-amber-50 text-slate-900 rounded-tl-none border border-amber-200'
                    : 'bg-slate-100 text-slate-900 rounded-tl-none border border-slate-200/60'
                }`}
              >
                <p className="whitespace-pre-line">{msg.content}</p>

                {/* Safe Fallback Ticket Prompt */}
                {msg.fallback_triggered && msg.role === 'assistant' && (
                  <div className="mt-3 pt-3 border-t border-amber-200/80">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 bg-white rounded-lg p-3 border border-amber-200 text-xs text-amber-900">
                      <div className="flex items-center space-x-2">
                        <LifeBuoy className="w-4 h-4 text-amber-600 shrink-0" />
                        <span className="leading-snug">
                          {selectedLanguage === 'ta'
                            ? 'அங்கீகரிக்கப்பட்ட ஆவணங்களிலிருந்து உறுதிப்படுத்த முடியவில்லை. நிர்வாகியிடம் உதவி கோர விரும்புகிறீர்களா?'
                            : 'Could not verify from approved documents. Need help from college administration?'}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 shrink-0 self-start sm:self-auto">
                        <Link
                          to={`/tickets?mode=create&session_id=${encodeURIComponent(
                            sessionIdRef.current
                          )}&query=${encodeURIComponent(
                            messages.filter((m) => m.role === 'user').slice(-1)[0]?.content || ''
                          )}`}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-lg shadow-sm transition-colors text-xs"
                        >
                          <span>{selectedLanguage === 'ta' ? 'டிக்கெட் உருவாக்குக' : 'Create Ticket'}</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                        <Link
                          to="/tickets?mode=track"
                          className="text-xs text-amber-800 hover:text-amber-950 underline font-medium"
                        >
                          {selectedLanguage === 'ta' ? 'டிக்கெட் நிலை' : 'Track Ticket'}
                        </Link>
                      </div>
                    </div>
                  </div>
                )}

                {/* Citations Card */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-200/80">
                    <div className="flex items-center text-xs font-semibold text-slate-700 mb-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                      Verified Source Citations ({msg.citations.length})
                      {msg.confidence_score !== undefined && (
                        <span className="ml-auto text-[11px] font-normal text-slate-500">
                          Semantic Confidence: {(msg.confidence_score * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      {msg.citations.map((c, idx) => (
                        <div
                          key={idx}
                          className="bg-white border border-slate-200 rounded-lg p-2.5 text-xs text-slate-600 flex items-start space-x-2 shadow-sm"
                        >
                          <FileText className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <div className="font-semibold text-slate-800">{c.document_title}</div>
                            <div className="text-[11px] text-slate-500 mt-0.5">
                              Academic Year: {c.academic_year} • <strong>Page {c.page_number}</strong> • Version {c.version_number}
                              {c.section ? ` • ${c.section}` : ''}
                            </div>
                            {c.snippet && (
                              <div className="text-[11px] text-slate-400 mt-1 italic line-clamp-2">
                                "{c.snippet}"
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Assistant Message Actions: Copy & Feedback */}
                {msg.role === 'assistant' && msg.id !== 'init-1' && (
                  <div className="mt-2.5 pt-2 flex items-center justify-between text-xs text-slate-400 border-t border-slate-200/60">
                    <button
                      type="button"
                      onClick={() => handleCopyText(msg.id, msg.content)}
                      title="Copy answer to clipboard"
                      aria-label="Copy answer to clipboard"
                      className="inline-flex items-center space-x-1 py-1 px-2 rounded-lg hover:bg-slate-200/70 hover:text-slate-700 text-slate-500 transition-colors"
                    >
                      {copiedId === msg.id ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-600 font-medium text-xs">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span className="text-xs">Copy answer</span>
                        </>
                      )}
                    </button>

                    <div className="flex items-center space-x-2">
                      {msg.feedback_recorded ? (
                        <span className="text-emerald-600 font-medium text-xs">
                          ✓ Feedback recorded
                        </span>
                      ) : (
                        <>
                          <span className="text-xs text-slate-400 hidden sm:inline">Helpful?</span>
                          <button
                            type="button"
                            onClick={() => handleFeedback(msg.id, 'helpful')}
                            title="Helpful"
                            aria-label="Mark answer as helpful"
                            className="p-1 rounded-md hover:bg-slate-200/70 hover:text-emerald-600 text-slate-500 transition-colors"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleFeedback(msg.id, 'unhelpful')}
                            title="Not helpful"
                            aria-label="Mark answer as unhelpful"
                            className="p-1 rounded-md hover:bg-slate-200/70 hover:text-rose-500 text-slate-500 transition-colors"
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-400 mt-1 px-1">{msg.timestamp}</span>
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex items-center space-x-2 text-slate-500 text-xs px-2 py-1">
              <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
              <span>Retrieving verified document evidence and generating grounded response...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Chips */}
        <div className="px-6 py-2 border-t border-slate-100 bg-slate-50/60 overflow-x-auto flex space-x-2 scrollbar-none">
          {sampleQuestions.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                executeSend(q.text, q.lang as 'en' | 'ta');
              }}
              className="text-xs text-slate-600 bg-white hover:bg-brand-50 hover:text-brand-700 hover:border-brand-300 border border-slate-200 px-3 py-1.5 rounded-full whitespace-nowrap transition-colors"
            >
              {q.text}
            </button>
          ))}
        </div>

        {/* Input bar */}
        <form onSubmit={handleSend} className="p-4 border-t border-slate-200 flex items-center space-x-3">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isLoading}
            placeholder={
              selectedLanguage === 'ta'
                ? 'உங்கள் கேள்வியைத் தட்டச்சு செய்க...'
                : 'Ask a question about admissions, hostel, exams...'
            }
            className="flex-1 px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !inputQuery.trim()}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center space-x-1.5 shadow transition-all"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>Send</span>
          </button>
        </form>
      </div>

      {errorMessage && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-xs text-slate-500 px-2">
        <div className="flex items-center space-x-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
          <span>Cannot find reliable records? The bot automatically suggests creating a support ticket.</span>
        </div>
        <span>Embedding Widget: <code>&lt;script src="/widget.js"&gt;&lt;/script&gt;</code></span>
      </div>
    </div>
  );
};

import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  X,
  Send,
  FileText,
  AlertCircle,
  Sparkles,
  Languages,
  CheckCircle2,
  LifeBuoy,
  Loader2,
  ArrowRight,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  Minus,
  Maximize2,
  Copy,
  Check,
} from 'lucide-react';
import { ChatMessage, WidgetConfig } from '../types';
import { fetchPublicConfig, submitChatFeedback, streamChatMessage } from '../services/api';

interface ChatbotWidgetProps {
  isStandaloneFrame?: boolean;
  initialConfig?: Partial<WidgetConfig>;
}

export const ChatbotWidget: React.FC<ChatbotWidgetProps> = ({
  isStandaloneFrame = false,
  initialConfig,
}) => {
  const [isOpen, setIsOpen] = useState(isStandaloneFrame);
  const [isMinimized, setIsMinimized] = useState(false);
  const [inputQuery, setInputQuery] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState<'en' | 'ta'>('en');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastFailedQuery, setLastFailedQuery] = useState<string | null>(null);
  const [config, setConfig] = useState<WidgetConfig>({
    college_name: 'St. Jude College of Engineering & Technology',
    current_academic_year: '2025-2026',
    supported_languages: ['en', 'ta'],
    primary_color: '#1e3a8a',
    accent_color: '#059669',
    widget_position: 'bottom-right',
    greeting_en:
      'Hello! I am the College AI Help Desk Assistant. Ask me about admissions, fees, hostel regulations, scholarships, or academic policies for 2025–2026.',
    greeting_ta:
      'வணக்கம்! நான் கல்லூரி AI உதவி மைய உதவியாளர். சேர்க்கை, கட்டணம், விடுதி, தேர்வுகள் அல்லது உதவித்தொகை பற்றி கேளுங்கள்.',
    suggested_questions: [
      { text: 'What is the hostel caution deposit fee?', lang: 'en' },
      { text: 'விடுதி வைப்புத் தொகை எவ்வளவு?', lang: 'ta' },
      { text: 'What is the minimum attendance required for semester exams?', lang: 'en' },
      { text: 'How much is the B.E. Computer Science tuition fee?', lang: 'en' },
    ],
    anti_hallucination_guarantee: true,
    is_demonstration_sample: true,
    allowed_embed_origins: ['http://localhost:5175', 'http://127.0.0.1:5175'],
    ...initialConfig,
  });

  const sessionIdRef = useRef<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Initialize session ID
  useEffect(() => {
    let sid = sessionStorage.getItem('helpdesk_widget_session_id');
    if (!sid) {
      sid = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `sess-${Date.now()}`;
      sessionStorage.setItem('helpdesk_widget_session_id', sid);
    }
    sessionIdRef.current = sid;

    // Fetch config on mount
    fetchPublicConfig().then((fetched) => {
      setConfig((prev) => ({ ...prev, ...fetched, ...initialConfig }));
    });
  }, [initialConfig]);

  // Messages list state
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Seed welcome greeting when config or language updates
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome-msg',
          role: 'assistant',
          content: selectedLanguage === 'ta' ? config.greeting_ta : config.greeting_en,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          language: selectedLanguage,
        },
      ]);
    }
  }, [config, selectedLanguage, messages.length]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, isStreaming]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && !isMinimized) {
      setTimeout(() => inputRef.current?.focus(), 150);
      notifyHost('helpdesk:open');
    } else if (!isOpen) {
      notifyHost('helpdesk:close');
    }
  }, [isOpen, isMinimized]);

  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyText = async (id: string, text: string) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for older contexts or non-https iframes
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

  // Notify parent iframe host via postMessage
  const notifyHost = (type: string, data: any = {}) => {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type, ...data }, '*');
    }
  };

  // Bidirectional PostMessage handshake with host embed script
  useEffect(() => {
    const handleHostMessage = (event: MessageEvent) => {
      const data = event.data;
      if (!data || typeof data !== 'object') return;

      if (data.type === 'helpdesk:command:open') {
        setIsOpen(true);
        setIsMinimized(false);
      } else if (data.type === 'helpdesk:command:close') {
        setIsOpen(false);
      } else if (data.type === 'helpdesk:command:toggle') {
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener('message', handleHostMessage);
    // Notify host script that widget iframe is ready
    notifyHost('helpdesk:ready');

    return () => window.removeEventListener('message', handleHostMessage);
  }, []);

  // Keyboard accessibility: ESC closes widget
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || isLoading) return;

    setErrorMessage(null);
    setLastFailedQuery(null);
    setInputQuery('');

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      language: selectedLanguage,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const tempBotId = `ast-${Date.now()}`;
    let accumulatedText = '';

    // Initialize streaming assistant placeholder
    setMessages((prev) => [
      ...prev,
      {
        id: tempBotId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        language: selectedLanguage,
        citations: [],
      },
    ]);
    setIsStreaming(true);

    await streamChatMessage(
      {
        query,
        session_id: sessionIdRef.current,
        language: selectedLanguage,
        academic_year: config.current_academic_year,
      },
      // onToken
      (token: string) => {
        accumulatedText += token;
        setMessages((prev) =>
          prev.map((msg) => (msg.id === tempBotId ? { ...msg, content: accumulatedText } : msg))
        );
      },
      // onMeta
      (meta) => {
        setIsStreaming(false);
        setIsLoading(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempBotId
              ? {
                  ...msg,
                  confidence_score: meta.confidence_score,
                  fallback_triggered: meta.fallback_triggered,
                  citations: meta.citations,
                }
              : msg
          )
        );
      },
      // onError
      (errText) => {
        setIsStreaming(false);
        setIsLoading(false);
        setErrorMessage(errText);
        setLastFailedQuery(query);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempBotId
              ? {
                  ...msg,
                  content:
                    selectedLanguage === 'ta'
                      ? 'மன்னிக்கவும், AI சேவைப் பிழை ஏற்பட்டது. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.'
                      : 'Sorry, the AI service encountered an error or connection timeout. Please try again.',
                  fallback_triggered: true,
                }
              : msg
          )
        );
      }
    );
  };

  const handleFeedback = async (messageId: string, rating: 'helpful' | 'unhelpful') => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, feedback_recorded: rating } : m))
    );
    await submitChatFeedback(messageId, rating);
  };

  const positionClasses =
    config.widget_position === 'bottom-left'
      ? 'bottom-5 left-5 items-start'
      : 'bottom-5 right-5 items-end';

  return (
    <div
      className={`fixed ${positionClasses} z-[999999] font-sans antialiased text-slate-800 flex flex-col pointer-events-auto`}
      style={{
        maxWidth: '100vw',
      }}
    >
      {/* ── CHAT PANEL ────────────────────────────────────────────────────────── */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="College AI Help Desk Chat Window"
          aria-modal="true"
          className={`mb-3 bg-white rounded-2xl shadow-2xl border border-slate-200/90 flex flex-col overflow-hidden transition-all duration-200 ease-out ${
            isMinimized
              ? 'h-14 w-80'
              : 'w-[calc(100vw-24px)] sm:w-[410px] max-w-[420px] h-[82vh] sm:h-[620px] max-h-[750px]'
          }`}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-900 via-slate-900 to-indigo-950 text-white px-4 py-3 flex items-center justify-between shadow-md shrink-0 select-none">
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0 border border-white/20">
                <Sparkles className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="min-w-0">
                <h2 className="text-sm font-semibold truncate leading-tight">
                  {config.college_name}
                </h2>
                <div className="flex items-center space-x-1.5 text-[11px] text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>AI Help Desk • AY {config.current_academic_year}</span>
                </div>
              </div>
            </div>

            {/* Header Action Controls */}
            <div className="flex items-center space-x-1 shrink-0">
              {/* Language Switcher */}
              <button
                type="button"
                onClick={() => setSelectedLanguage((prev) => (prev === 'en' ? 'ta' : 'en'))}
                title="Toggle English / தமிழ்"
                aria-label="Toggle language between English and Tamil"
                className="px-2 py-1 rounded-md text-xs font-medium bg-white/10 hover:bg-white/20 text-slate-200 transition-colors flex items-center space-x-1 mr-1"
              >
                <Languages className="w-3 h-3" />
                <span>{selectedLanguage === 'en' ? 'தமிழ்' : 'English'}</span>
              </button>

              {/* Track Ticket Quick Link */}
              <a
                href="/tickets?mode=track"
                target="_blank"
                rel="noopener noreferrer"
                title="Track Existing Support Ticket"
                aria-label="Track existing support ticket"
                className="px-2 py-1 rounded-md text-xs font-medium bg-white/10 hover:bg-white/20 text-slate-200 transition-colors flex items-center space-x-1 mr-1"
              >
                <LifeBuoy className="w-3 h-3 text-amber-400" />
                <span className="hidden sm:inline">Track</span>
              </a>

              {/* Minimize Toggle */}
              <button
                type="button"
                onClick={() => setIsMinimized((prev) => !prev)}
                title={isMinimized ? 'Expand' : 'Minimize'}
                aria-label={isMinimized ? 'Expand chat' : 'Minimize chat'}
                className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
              >
                {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
              </button>

              {/* Close Button */}
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Close chat"
                aria-label="Close chat window"
                className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {!isMinimized && (
            <>
              {/* Prototype Notice Banner */}
              {config.is_demonstration_sample && (
                <div className="bg-amber-500/10 border-b border-amber-500/20 px-3 py-1.5 text-[11px] text-amber-800 flex items-center space-x-1.5 shrink-0">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span className="truncate">
                    <strong>DEMO PROTOTYPE:</strong> Fictional college document benchmark.
                  </span>
                </div>
              )}

              {/* Messages Scroll Area */}
              <div
                className="flex-1 p-4 overflow-y-auto space-y-3.5 bg-slate-50/50"
                tabIndex={0}
                aria-label="Conversation messages"
              >
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.role === 'user' ? 'items-end' : 'items-start'
                    }`}
                  >
                    <div
                      className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed shadow-xs ${
                        msg.role === 'user'
                          ? 'bg-blue-700 text-white rounded-tr-none'
                          : msg.fallback_triggered
                          ? 'bg-amber-50 text-slate-900 rounded-tl-none border border-amber-200'
                          : 'bg-white text-slate-900 rounded-tl-none border border-slate-200/80'
                      }`}
                    >
                      <p className="whitespace-pre-line break-words">{msg.content}</p>

                      {/* Streaming cursor */}
                      {isStreaming && msg.role === 'assistant' && !msg.content && (
                        <div className="flex items-center space-x-1 py-1">
                          <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce" />
                          <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:0.2s]" />
                          <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce [animation-delay:0.4s]" />
                        </div>
                      )}

                      {/* Safe Fallback Ticket Card */}
                      {msg.fallback_triggered && msg.role === 'assistant' && (
                        <div className="mt-2.5 pt-2.5 border-t border-amber-200/80">
                          <div className="bg-white rounded-lg p-2.5 border border-amber-200 text-xs text-amber-900 space-y-2">
                            <div className="flex items-start space-x-2">
                              <LifeBuoy className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                              <span className="leading-snug">
                                {selectedLanguage === 'ta'
                                  ? 'அதிகாரப்பூர்வ ஆவணங்களை சரிபார்க்க முடியவில்லை. கல்லூரி பணியாளர்களிடம் உதவி கோர டிக்கெட் உருவாக்க விரும்புகிறீர்களா?'
                                  : 'Could not verify official records. Would you like to create a support ticket for college staff?'}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2 pt-1">
                              <a
                                href={`/tickets?mode=create&session_id=${encodeURIComponent(
                                  sessionIdRef.current
                                )}&query=${encodeURIComponent(
                                  messages.filter((m) => m.role === 'user').slice(-1)[0]?.content || ''
                                )}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center space-x-1 px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-md text-xs shadow-xs transition-colors"
                              >
                                <span>{selectedLanguage === 'ta' ? 'டிக்கெட் உருவாக்குக' : 'Create Ticket'}</span>
                                <ArrowRight className="w-3 h-3" />
                              </a>
                              <a
                                href="/tickets?mode=track"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[11px] text-amber-800 hover:text-amber-950 underline font-medium"
                              >
                                {selectedLanguage === 'ta' ? 'டிக்கெட் நிலை' : 'Track Existing'}
                              </a>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Verified Source Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-slate-200/70">
                          <div className="flex items-center text-[11px] font-semibold text-slate-700 mb-1">
                            <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                            Verified Citations ({msg.citations.length})
                            {msg.confidence_score !== undefined && (
                              <span className="ml-auto font-normal text-slate-400 text-[10px]">
                                {(msg.confidence_score * 100).toFixed(0)}% match
                              </span>
                            )}
                          </div>
                          <div className="space-y-1">
                            {msg.citations.map((c, idx) => (
                              <div
                                key={idx}
                                className="bg-slate-50 border border-slate-200/80 rounded-md p-1.5 text-[11px] text-slate-600 flex items-start space-x-1.5"
                              >
                                <FileText className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                                <div className="min-w-0">
                                  <div className="font-semibold text-slate-800 truncate">
                                    {c.document_title}
                                  </div>
                                  <div className="text-[10px] text-slate-500">
                                    AY {c.academic_year} • <strong>Page {c.page_number}</strong>
                                    {c.section ? ` • ${c.section}` : ''}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Helpful / Unhelpful Feedback Controls & Copy Answer */}
                      {msg.role === 'assistant' && msg.id !== 'welcome-msg' && !isStreaming && (
                        <div className="mt-2 pt-1.5 flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-100">
                          <button
                            type="button"
                            onClick={() => handleCopyText(msg.id, msg.content)}
                            title="Copy answer to clipboard"
                            aria-label="Copy answer to clipboard"
                            className="inline-flex items-center space-x-1 py-0.5 px-1.5 rounded hover:bg-slate-100 hover:text-slate-700 text-slate-500 transition-colors"
                          >
                            {copiedId === msg.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-600" />
                                <span className="text-emerald-600 font-medium">Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>

                          <div className="flex items-center space-x-1.5">
                            {msg.feedback_recorded ? (
                              <span className="text-emerald-600 font-medium text-[10px]">
                                ✓ Feedback recorded
                              </span>
                            ) : (
                              <>
                                <span className="text-[10px] text-slate-400 mr-0.5 hidden sm:inline">Helpful?</span>
                                <button
                                  type="button"
                                  onClick={() => handleFeedback(msg.id, 'helpful')}
                                  title="Helpful"
                                  aria-label="Mark answer as helpful"
                                  className="p-1 rounded hover:bg-slate-100 hover:text-emerald-600 transition-colors"
                                >
                                  <ThumbsUp className="w-3 h-3" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleFeedback(msg.id, 'unhelpful')}
                                  title="Not helpful"
                                  aria-label="Mark answer as unhelpful"
                                  className="p-1 rounded hover:bg-slate-100 hover:text-red-500 transition-colors"
                                >
                                  <ThumbsDown className="w-3 h-3" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 mt-0.5 px-1">{msg.timestamp}</span>
                  </div>
                ))}

                {/* Error Banner & Retry */}
                {errorMessage && (
                  <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center justify-between">
                    <div className="flex items-center space-x-1.5 min-w-0">
                      <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                      <span className="truncate">{errorMessage}</span>
                    </div>
                    {lastFailedQuery && (
                      <button
                        type="button"
                        onClick={() => handleSendMessage(lastFailedQuery)}
                        className="ml-2 inline-flex items-center space-x-1 px-2 py-1 bg-red-100 hover:bg-red-200 text-red-800 rounded font-medium text-[11px] shrink-0"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Retry</span>
                      </button>
                    )}
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Suggested Questions */}
              {messages.length <= 2 && config.suggested_questions?.length > 0 && (
                <div className="px-3 py-2 bg-slate-100/70 border-t border-slate-200/60 overflow-x-auto flex space-x-1.5 shrink-0 scrollbar-none">
                  {config.suggested_questions
                    .filter((q) => q.lang === selectedLanguage || !q.lang)
                    .map((q, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendMessage(q.text)}
                        className="text-[11px] text-slate-700 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 border border-slate-200 px-2.5 py-1 rounded-full whitespace-nowrap shadow-xs transition-colors shrink-0"
                      >
                        {q.text}
                      </button>
                    ))}
                </div>
              )}

              {/* Input Bar */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="p-2.5 bg-white border-t border-slate-200 flex items-center space-x-2 shrink-0"
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  disabled={isLoading}
                  placeholder={
                    selectedLanguage === 'ta'
                      ? 'உங்கள் கேள்வியைத் தட்டச்சு செய்க...'
                      : 'Ask about admissions, hostel, fees, exams...'
                  }
                  className="flex-1 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all disabled:opacity-50"
                  aria-label="User query input"
                />
                <button
                  type="submit"
                  disabled={isLoading || !inputQuery.trim()}
                  className="bg-blue-700 hover:bg-blue-800 disabled:opacity-40 text-white p-2 rounded-xl text-xs font-semibold flex items-center justify-center shadow transition-all shrink-0"
                  aria-label="Send query"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </form>
            </>
          )}
        </div>
      )}

      {/* ── FLOATING LAUNCHER BUTTON ─────────────────────────────────────────── */}
      {!isStandaloneFrame && (
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-label={isOpen ? 'Close help desk chat' : 'Open college AI help desk chat'}
          aria-expanded={isOpen}
          className="group relative flex items-center justify-center w-14 h-14 rounded-full shadow-2xl bg-gradient-to-r from-blue-700 to-indigo-800 hover:from-blue-800 hover:to-indigo-900 text-white transition-transform duration-200 hover:scale-105 active:scale-95 focus:outline-none focus:ring-4 focus:ring-blue-400"
        >
          {/* Status Indicator */}
          <span className="absolute top-0 right-0 flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500 border-2 border-white" />
          </span>

          {isOpen ? (
            <X className="w-6 h-6 transition-transform duration-200" />
          ) : (
            <MessageSquare className="w-6 h-6 transition-transform duration-200" />
          )}

          {/* Hover Tooltip on desktop */}
          {!isOpen && (
            <span className="absolute right-16 bg-slate-900 text-white text-xs px-2.5 py-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-lg pointer-events-none">
              Need help? Ask AI
            </span>
          )}
        </button>
      )}
    </div>
  );
};

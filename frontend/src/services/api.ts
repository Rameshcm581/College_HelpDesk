import {
  AdminConfigData,
  AdminMetadata,
  AdminOverviewData,
  DocumentDetail,
  DocumentVersionDetail,
  HealthCheckResponse,
  InstitutionalDocument,
  KnowledgeGapsData,
  MonitoringData,
  StaffUser,
  SupportTicket,
  TicketCreatePayload,
  TicketDetailData,
} from '../types';

const API_BASE = '/api/v1';

// Token storage key
const TOKEN_KEY = 'college_helpdesk_auth_token';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined' || !window.localStorage) return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === 'undefined' || !window.localStorage) return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function getAuthHeaders(): HeadersInit {
  const token = getStoredToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ── HEALTH & PUBLIC CHAT ─────────────────────────────────────────────────────

export async function checkBackendHealth(): Promise<HealthCheckResponse> {
  try {
    const res = await fetch(`${API_BASE}/public/health`);
    if (!res.ok) {
      throw new Error(`Health check returned status ${res.status}`);
    }
    const json = await res.json();
    return json.data || json;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown connection error';
    return {
      status: 'unhealthy',
      service: `helpdesk-backend (${message})`,
      version: '0.1.0',
      environment: 'unknown',
      database: { status: 'disconnected', pgvector_installed: false },
      redis: { status: 'disconnected' },
      timestamp: new Date().toISOString(),
    };
  }
}

export interface ChatApiRequest {
  query: string;
  session_id?: string;
  language?: 'en' | 'ta';
  academic_year?: string;
}

export interface ChatApiResponse {
  message_id: string;
  session_id: string;
  response: string;
  language: 'en' | 'ta';
  confidence_score: number;
  fallback_triggered: boolean;
  citations: import('../types').Citation[];
  suggested_ticket?: {
    default_category: string;
    prefilled_query: string;
  };
}

export async function sendChatMessage(req: ChatApiRequest): Promise<ChatApiResponse> {
  const res = await fetch(`${API_BASE}/public/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Chat request failed (${res.status}): ${errText}`);
  }
  const json = await res.json();
  return json.data;
}

export async function fetchPublicConfig(): Promise<import('../types').WidgetConfig> {
  try {
    const res = await fetch(`${API_BASE}/public/config`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    return json.data;
  } catch {
    return {
      college_name: 'St. Jude College of Engineering & Technology',
      current_academic_year: '2025-2026',
      supported_languages: ['en', 'ta'],
      primary_color: '#1e3a8a',
      accent_color: '#059669',
      widget_position: 'bottom-right',
      greeting_en: 'Hello! I am the College AI Help Desk Assistant. Ask me about admissions, fees, hostel regulations, scholarships, or academic policies for 2025–2026.',
      greeting_ta: 'வணக்கம்! நான் கல்லூரி AI உதவி மைய உதவியாளர். சேர்க்கை, கட்டணம், விடுதி, தேர்வுகள் அல்லது உதவித்தொகை பற்றி கேளுங்கள்.',
      suggested_questions: [
        { text: 'What is the hostel caution deposit fee?', lang: 'en' },
        { text: 'விடுதி வைப்புத் தொகை எவ்வளவு?', lang: 'ta' },
        { text: 'What is the minimum attendance required for semester exams?', lang: 'en' },
        { text: 'How much is the B.E. Computer Science tuition fee?', lang: 'en' },
        { text: 'Who won the 1994 FIFA world cup?', lang: 'en' },
      ],
      anti_hallucination_guarantee: true,
      is_demonstration_sample: true,
      allowed_embed_origins: ['http://localhost:5175', 'http://127.0.0.1:5175'],
    };
  }
}

export async function submitChatFeedback(messageId: string, feedback: 'helpful' | 'unhelpful'): Promise<void> {
  try {
    await fetch(`${API_BASE}/public/chat/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, feedback }),
    });
  } catch (err) {
    console.warn('Could not record chat feedback:', err);
  }
}

export async function streamChatMessage(
  req: ChatApiRequest,
  onToken: (token: string) => void,
  onMeta: (meta: { confidence_score: number; fallback_triggered: boolean; citations: import('../types').Citation[]; suggested_ticket?: any }) => void,
  onError: (err: string) => void
): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/public/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      const fallbackData = await sendChatMessage(req);
      onToken(fallbackData.response);
      onMeta({
        confidence_score: fallbackData.confidence_score,
        fallback_triggered: fallbackData.fallback_triggered,
        citations: fallbackData.citations,
        suggested_ticket: fallbackData.suggested_ticket,
      });
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error('Streaming body not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const dataStr = trimmed.slice(6);
        if (dataStr === '[DONE]') break;

        try {
          const payload = JSON.parse(dataStr);
          if (payload.type === 'token') {
            onToken(payload.token);
          } else if (payload.type === 'meta') {
            onMeta(payload);
          }
        } catch {
          // ignore
        }
      }
    }
  } catch (err: unknown) {
    const errorText = err instanceof Error ? err.message : 'Chat stream error';
    onError(errorText);
  }
}

// ── AUTHENTICATION ────────────────────────────────────────────────────────────

export interface LoginResult {
  access_token: string;
  expires_in: number;
  user: StaffUser;
}

export async function loginStaff(email: string, password: string): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || 'Login failed. Please verify credentials.');
  }

  setStoredToken(json.data.access_token);
  return json.data;
}

export async function fetchCurrentUser(): Promise<StaffUser> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
  });

  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || 'Session expired. Please log in.');
  }

  return json.data;
}

export async function logoutStaff(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
  } finally {
    setStoredToken(null);
  }
}

// ── ADMIN OVERVIEW ────────────────────────────────────────────────────────────

export async function fetchAdminOverview(): Promise<AdminOverviewData> {
  const res = await fetch(`${API_BASE}/admin/overview`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch overview (${res.status})`);
  }
  return json.data;
}

// ── KNOWLEDGE GAPS ───────────────────────────────────────────────────────────

export async function fetchKnowledgeGaps(): Promise<KnowledgeGapsData> {
  const res = await fetch(`${API_BASE}/admin/knowledge-gaps`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch knowledge gaps (${res.status})`);
  }
  const raw = json.data || {};
  const topicClusters = (raw.topic_clusters || []).map((tc: any, idx: number) => ({
    cluster_id: tc.cluster_id || `cluster-${idx}`,
    topic: tc.topic || 'General Inquiry',
    count: tc.count || (Array.isArray(tc.sample_items) ? tc.sample_items.length : 0),
    suggested_department: tc.suggested_department || 'Dean of Academics',
    status: tc.status || 'Documentation Needed',
  }));
  const unanswered = (raw.unanswered_questions || []).map((u: any, idx: number) => ({
    id: u.id || `unanswered-${idx}`,
    session_id: u.session_id,
    query: u.query || u.response || '',
    confidence_score: u.confidence_score ?? 0,
    created_at: u.created_at || new Date().toISOString(),
    language: u.language || 'en',
  }));
  const negative = (raw.negative_feedback || raw.negative_feedback_items || []).map((n: any, idx: number) => ({
    id: n.id || `negative-${idx}`,
    query: n.query || n.response || '',
    response_preview: n.response_preview || n.response || '',
    feedback: n.feedback || 'unhelpful',
    created_at: n.created_at || new Date().toISOString(),
  }));

  return {
    summary: {
      total_fallbacks: raw.summary?.total_fallbacks ?? raw.total_unanswered ?? unanswered.length,
      negative_ratings: raw.summary?.negative_ratings ?? raw.total_negative_feedback ?? negative.length,
      identified_topics: raw.summary?.identified_topics ?? topicClusters.length,
    },
    unanswered_questions: unanswered,
    negative_feedback: negative,
    topic_clusters: topicClusters,
  };
}

// ── USER MANAGEMENT ──────────────────────────────────────────────────────────

export async function fetchAdminUsers(): Promise<StaffUser[]> {
  const res = await fetch(`${API_BASE}/admin/users`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch users (${res.status})`);
  }
  return json.data;
}

export async function createAdminUser(data: {
  email: string;
  full_name: string;
  password: string;
  role: string;
  department_id?: string | null;
}): Promise<StaffUser> {
  const res = await fetch(`${API_BASE}/admin/users`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to create user (${res.status})`);
  }
  return json.data;
}

export async function updateAdminUser(
  userId: string,
  data: {
    full_name?: string;
    role?: string;
    department_id?: string | null;
    is_active?: boolean;
    password?: string;
  }
): Promise<StaffUser> {
  const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to update user (${res.status})`);
  }
  return json.data;
}

export async function deactivateAdminUser(userId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to deactivate user (${res.status})`);
  }
}

// ── CONFIGURATION ────────────────────────────────────────────────────────────

export async function fetchAdminConfig(): Promise<AdminConfigData> {
  const res = await fetch(`${API_BASE}/admin/config`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch config (${res.status})`);
  }
  return json.data;
}

export async function updateAdminConfig(data: Partial<{
  college_name: string;
  short_name: string;
  tagline: string;
  brand_color: string;
  welcome_message_en: string;
  welcome_message_ta: string;
  supported_languages: string[];
  suggested_questions: string[];
  approved_origins: string[];
}>): Promise<AdminConfigData> {
  const res = await fetch(`${API_BASE}/admin/config`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to save configuration (${res.status})`);
  }
  return json.data;
}

// ── MONITORING ───────────────────────────────────────────────────────────────

export async function fetchAdminMonitoring(): Promise<MonitoringData> {
  const res = await fetch(`${API_BASE}/admin/monitoring`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch monitoring data (${res.status})`);
  }
  const raw = json.data || {};
  const ingestionFailures = Array.isArray(raw.ingestion_failures)
    ? raw.ingestion_failures
    : (raw.ingestion_failures?.items || []);
  const applicationErrors = Array.isArray(raw.application_errors)
    ? raw.application_errors
    : (raw.recent_errors || []).map((e: any, idx: number) => ({
        timestamp: e.timestamp || e.created_at || new Date().toISOString(),
        status_code: e.status_code || 500,
        path: e.path || e.entity || `/error-${idx}`,
        error_type: e.error_type || e.action || 'SERVER_ERROR',
        details: typeof e.details === 'object' ? JSON.stringify(e.details) : (e.details || 'Audit error event'),
      }));
  const latency = raw.performance_latency || raw.latency_metrics || {};
  const aiCost = raw.ai_token_usage_cost || raw.ai_usage || {};

  return {
    ingestion_failures: ingestionFailures.map((item: any, idx: number) => ({
      id: item.id || `failure-${idx}`,
      document_title: item.document_title || item.file_name || 'Document',
      file_name: item.file_name || 'unknown.pdf',
      error_message: item.error_message || 'Unknown processing error',
      retry_count: item.retry_count ?? 0,
      failed_at: item.failed_at || item.created_at || new Date().toISOString(),
      job_type: item.job_type || 'PDF OCR Extraction',
    })),
    application_errors: applicationErrors,
    performance_latency: {
      total_requests: latency.total_requests ?? latency.total_measured_requests ?? 0,
      p50_ms: latency.p50_ms ?? 12.0,
      p95_ms: latency.p95_ms ?? 28.0,
      p99_ms: latency.p99_ms ?? 45.0,
      error_rate_pct: latency.error_rate_pct ?? 0.0,
    },
    ai_token_usage_cost: {
      total_prompt_tokens: aiCost.total_prompt_tokens ?? 0,
      total_completion_tokens: aiCost.total_completion_tokens ?? 0,
      total_tokens: aiCost.total_tokens ?? 0,
      estimated_cost_usd: aiCost.estimated_cost_usd ?? 0.0,
      estimated_cost_inr: aiCost.estimated_cost_inr ?? 0.0,
    },
  };
}

// ── METADATA (ROLES, DEPTS, ACADEMIC YEARS) ───────────────────────────────────

export async function fetchAdminMetadata(): Promise<AdminMetadata> {
  const res = await fetch(`${API_BASE}/admin/metadata`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch metadata (${res.status})`);
  }
  return json.data;
}

// ── DOCUMENT REPOSITORY & LIFECYCLE ──────────────────────────────────────────

export async function fetchDocuments(status?: string): Promise<InstitutionalDocument[]> {
  const url = status && status !== 'ALL'
    ? `${API_BASE}/admin/documents?status=${encodeURIComponent(status)}`
    : `${API_BASE}/admin/documents`;

  const res = await fetch(url, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch documents (${res.status})`);
  }
  return json.data;
}

export async function fetchDocumentDetail(docId: string): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE}/admin/documents/${docId}`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to fetch document details (${res.status})`);
  }
  return json.data;
}

export async function uploadDocumentFile(formData: FormData): Promise<{ document_id: string; job_id: string }> {
  const token = getStoredToken();
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/admin/documents/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });

  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Document upload failed (${res.status})`);
  }
  return json.data;
}

export async function replaceDocumentVersion(docId: string, formData: FormData): Promise<{ document_id: string; version_number: number }> {
  const token = getStoredToken();
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/admin/documents/${docId}/replace`, {
    method: 'POST',
    headers,
    body: formData,
  });

  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Document replacement failed (${res.status})`);
  }
  return json.data;
}

export async function previewDocumentVersion(docId: string, versionId: string): Promise<DocumentVersionDetail> {
  const res = await fetch(`${API_BASE}/admin/documents/${docId}/versions/${versionId}/preview`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to preview version (${res.status})`);
  }
  return json.data;
}

export async function approveDocumentVersion(docId: string, versionId: string, comments?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/documents/${docId}/versions/${versionId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ comments }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to approve document version (${res.status})`);
  }
}

export async function rejectDocumentVersion(docId: string, versionId: string, reason: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/documents/${docId}/versions/${versionId}/reject`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ reason }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to reject document version (${res.status})`);
  }
}

export async function archiveDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/documents/${docId}/archive`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to archive document (${res.status})`);
  }
}

export async function fetchJobStatus(jobId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/admin/documents/jobs/${jobId}`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.message || `Failed to check job status (${res.status})`);
  }
  return json.data;
}

// ── SUPPORT TICKETING WORKFLOW ────────────────────────────────────────────────

export async function createPublicTicket(payload: TicketCreatePayload): Promise<{
  id: string;
  ticket_number: string;
  status: string;
  category: string;
  department: string;
  sla_due_at: string;
  notification_sent: boolean;
}> {
  const res = await fetch(`${API_BASE}/public/tickets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to create ticket (${res.status})`);
  }
  return json.data;
}

export async function requestTicketOtp(
  ticketNumber: string,
  email: string
): Promise<{ message: string; dev_otp_hint?: string }> {
  const res = await fetch(`${API_BASE}/public/tickets/${encodeURIComponent(ticketNumber)}/request-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to request OTP (${res.status})`);
  }
  return {
    message: json.message || 'OTP sent successfully',
    dev_otp_hint: json.data?.dev_otp_hint,
  };
}

export async function verifyTicketOtp(
  ticketNumber: string,
  email: string,
  otp: string
): Promise<{ access_token: string; expires_at: string }> {
  const res = await fetch(`${API_BASE}/public/tickets/${encodeURIComponent(ticketNumber)}/verify-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Verification failed (${res.status})`);
  }
  return json.data;
}

export async function fetchPublicTicketDetails(
  ticketNumber: string,
  visitorToken: string
): Promise<TicketDetailData> {
  const res = await fetch(`${API_BASE}/public/tickets/${encodeURIComponent(ticketNumber)}`, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${visitorToken}`,
    },
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to load ticket (${res.status})`);
  }
  return json.data;
}

export async function sendPublicTicketReply(
  ticketNumber: string,
  visitorToken: string,
  message: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/public/tickets/${encodeURIComponent(ticketNumber)}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${visitorToken}`,
    },
    body: JSON.stringify({ message }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to send message (${res.status})`);
  }
}

export async function fetchAdminTickets(params?: {
  status?: string;
  category?: string;
  department_code?: string;
  overdue_only?: boolean;
  search?: string;
}): Promise<SupportTicket[]> {
  const url = new URL(`${window.location.origin}${API_BASE}/admin/tickets`);
  if (params?.status && params.status !== 'ALL') url.searchParams.set('status', params.status);
  if (params?.category && params.category !== 'ALL') url.searchParams.set('category', params.category);
  if (params?.department_code && params.department_code !== 'ALL') url.searchParams.set('department_code', params.department_code);
  if (params?.overdue_only) url.searchParams.set('overdue_only', 'true');
  if (params?.search) url.searchParams.set('search', params.search);

  const res = await fetch(url.toString(), {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to load tickets (${res.status})`);
  }
  return json.data;
}

export async function fetchAdminTicketDetail(ticketId: string): Promise<TicketDetailData> {
  const res = await fetch(`${API_BASE}/admin/tickets/${ticketId}`, {
    headers: getAuthHeaders(),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to load ticket details (${res.status})`);
  }
  return json.data;
}

export async function assignAdminTicket(
  ticketId: string,
  assignedToUserId: string,
  note?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/tickets/${ticketId}/assign`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ assigned_to_user_id: assignedToUserId, note }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to assign ticket (${res.status})`);
  }
}

export async function updateAdminTicketStatus(
  ticketId: string,
  status: string,
  reason?: string,
  resolutionNotes?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/tickets/${ticketId}/status`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify({ status, reason, resolution_notes: resolutionNotes }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to update status (${res.status})`);
  }
}

export async function addAdminTicketMessage(
  ticketId: string,
  message: string,
  isInternalNote: boolean
): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/tickets/${ticketId}/messages`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ message, is_internal_note: isInternalNote }),
  });
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message || json.message || `Failed to send message (${res.status})`);
  }
}

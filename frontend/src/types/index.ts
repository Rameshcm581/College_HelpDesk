export type SystemHealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'loading';

export type UserRole = 
  | 'SUPER_ADMIN' 
  | 'ADMIN' 
  | 'DEPARTMENT_STAFF' 
  | 'VIEWER' 
  | 'CONTENT_APPROVER' 
  | 'SUPPORT_AGENT' 
  | 'AUDITOR';

export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  database: {
    status: string;
    pgvector_installed: boolean;
  };
  redis: {
    status: string;
  };
  timestamp: string;
}

export interface Citation {
  document_id: string;
  document_title: string;
  version_number: number;
  academic_year: string;
  page_number: number;
  section?: string;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  confidence_score?: number;
  fallback_triggered?: boolean;
  citations?: Citation[];
  language?: 'en' | 'ta';
  feedback_recorded?: 'helpful' | 'unhelpful';
}

export interface WidgetConfig {
  college_name: string;
  college_logo_url?: string;
  current_academic_year: string;
  supported_languages: ('en' | 'ta')[];
  primary_color: string;
  accent_color: string;
  widget_position: 'bottom-right' | 'bottom-left';
  greeting_en: string;
  greeting_ta: string;
  suggested_questions: { text: string; lang: 'en' | 'ta' }[];
  anti_hallucination_guarantee: boolean;
  is_demonstration_sample: boolean;
  allowed_embed_origins: string[];
}

export type TicketStatus = 
  | 'OPEN' 
  | 'ASSIGNED' 
  | 'IN_PROGRESS' 
  | 'WAITING_FOR_USER' 
  | 'RESOLVED' 
  | 'CLOSED';

export type TicketCategory = 
  | 'ADMISSIONS' 
  | 'FEES' 
  | 'EXAMINATIONS' 
  | 'HOSTEL' 
  | 'SCHOLARSHIPS' 
  | 'PLACEMENTS' 
  | 'GENERAL';

export type TicketPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export interface SupportTicket {
  id: string;
  ticket_number: string;
  student_name: string;
  student_email: string;
  student_phone?: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  subject?: string;
  description?: string;
  department_name?: string;
  department_code?: string;
  assigned_to_name?: string | null;
  assigned_to_user_id?: string | null;
  sla_due_at?: string | null;
  is_overdue?: boolean;
  resolved_at?: string | null;
  resolution_notes?: string | null;
  created_at: string;
  updated_at?: string;
  message_count?: number;
}

export interface TicketMessageItem {
  id: string;
  sender_type: 'STUDENT' | 'STAFF' | 'SYSTEM';
  sender_name?: string;
  sender_user_id?: string | null;
  message: string;
  is_internal_note: boolean;
  attachment_urls?: string[];
  created_at: string;
}

export interface TicketStatusHistoryItem {
  id?: string;
  from_status: string;
  to_status: string;
  changed_by?: string;
  change_reason?: string;
  created_at: string;
}

export interface TicketDetailData extends SupportTicket {
  subject: string;
  description: string;
  department: string;
  department_code?: string;
  assigned_to_user_id?: string | null;
  assigned_to_name?: string | null;
  sla_due_at?: string | null;
  is_overdue?: boolean;
  resolved_by_id?: string | null;
  resolved_by_name?: string | null;
  resolution_notes?: string | null;
  resolved_at?: string | null;
  updated_at: string;
  messages: TicketMessageItem[];
  status_history: TicketStatusHistoryItem[];
  conversation_transcript?: {
    role: string;
    content: string;
    created_at: string;
  }[];
}

export interface TicketCreatePayload {
  student_name: string;
  student_email: string;
  student_phone?: string;
  category: string;
  subject: string;
  message: string;
  priority?: string;
  session_id?: string;
}

export interface InstitutionalDocument {
  id: string;
  title: string;
  file_name: string;
  department: string;
  department_code?: string;
  academic_year: string;
  version_number: number;
  active_version_id?: string | null;
  status: 'DRAFT' | 'UPLOADED' | 'PROCESSING' | 'REVIEW_REQUIRED' | 'APPROVED' | 'PUBLISHED' | 'ACTIVE' | 'ARCHIVED' | 'FAILED';
  chunk_count: number;
  page_count?: number;
  file_size_bytes?: number;
  created_at: string;
}

export interface DocumentVersionDetail {
  id: string;
  version_number: number;
  file_name: string;
  status: string;
  page_count: number;
  chunk_count: number;
  checksum_sha256?: string;
  valid_from?: string | null;
  valid_until?: string | null;
  change_summary?: string | null;
  created_at: string;
  approved_at?: string | null;
  extracted_text_preview?: string;
}

export interface DocumentDetail {
  id: string;
  title: string;
  file_name: string;
  version_number: number;
  active_version_id?: string | null;
  status: string;
  file_size_bytes: number;
  checksum_sha256?: string;
  created_at: string;
  versions: DocumentVersionDetail[];
}

export interface StaffUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department_id?: string | null;
  department_name?: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface AdminOverviewData {
  documents: {
    total: number;
    published: number;
    review_required: number;
    archived: number;
    failed: number;
  };
  ingestion_jobs: {
    total: number;
    completed: number;
    processing: number;
    queued: number;
    failed: number;
  };
  support_tickets: {
    total: number;
    open: number;
    in_progress: number;
    resolved: number;
  };
  unanswered_questions: {
    total_unanswered_recent: number;
    negative_feedback_count: number;
  };
  usage_metrics: {
    total_queries: number;
    fallback_count: number;
    grounding_rate_pct: number;
    avg_latency_ms: number;
  };
  recent_fallbacks: Array<{
    id: string;
    session_id?: string;
    message: string;
    confidence_score?: number;
    created_at: string;
  }>;
  is_demonstration_mode: boolean;
  user_role: string;
  department_scope: string | null;
}

export interface KnowledgeGapsData {
  summary: {
    total_fallbacks: number;
    negative_ratings: number;
    identified_topics: number;
  };
  unanswered_questions: Array<{
    id: string;
    session_id?: string;
    query: string;
    confidence_score: number;
    created_at: string;
    language: string;
  }>;
  negative_feedback: Array<{
    id: string;
    query: string;
    response_preview: string;
    feedback: string;
    created_at: string;
  }>;
  topic_clusters: Array<{
    cluster_id: string;
    topic: string;
    count: number;
    suggested_department: string;
    status: string;
  }>;
}

export interface AdminConfigData {
  college_branding: {
    college_name: string;
    short_name: string;
    tagline: string;
    brand_color: string;
  };
  welcome_messages: {
    en: string;
    ta: string;
  };
  supported_languages: string[];
  suggested_questions: string[];
  approved_origins: string[];
}

export interface MonitoringData {
  ingestion_failures: Array<{
    id: string;
    document_title: string;
    file_name: string;
    error_message: string;
    retry_count: number;
    failed_at: string;
    job_type: string;
  }>;
  application_errors: Array<{
    timestamp: string;
    status_code: number;
    path: string;
    error_type: string;
    details: string;
  }>;
  performance_latency: {
    total_requests: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    error_rate_pct: number;
  };
  ai_token_usage_cost: {
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    estimated_cost_inr: number;
  };
}

export interface AdminMetadata {
  roles: Array<{
    code: string;
    name: string;
    description: string;
  }>;
  departments: Array<{
    id: string;
    code: string;
    name: string;
  }>;
  academic_years: Array<{
    id: string;
    code: string;
    is_current: boolean;
  }>;
}

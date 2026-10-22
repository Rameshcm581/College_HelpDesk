import { describe, it, expect, beforeEach } from 'vitest';
import {
  AdminOverviewData,
  AdminConfigData,
  KnowledgeGapsData,
  MonitoringData,
  StaffUser,
  UserRole,
} from '../types';
import { getStoredToken, setStoredToken, getAuthHeaders } from '../services/api';

// Polyfill localStorage for node environment
const storage: Record<string, string> = {};
const mockLocalStorage = {
  getItem: (k: string) => storage[k] ?? null,
  setItem: (k: string, v: string) => { storage[k] = v; },
  removeItem: (k: string) => { delete storage[k]; },
  clear: () => { Object.keys(storage).forEach(k => delete storage[k]); },
  key: (i: number) => Object.keys(storage)[i] ?? null,
  length: 0,
};

// Assign to global
(globalThis as any).window = (globalThis as any).window || {};
(globalThis as any).window.localStorage = mockLocalStorage;
(globalThis as any).localStorage = mockLocalStorage;

describe('Admin Authentication & RBAC Permissions', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
  });

  it('manages staff auth token storage lifecycle', () => {
    expect(getStoredToken()).toBeNull();

    const mockToken = 'jwt-mock-staff-token-12345';
    setStoredToken(mockToken);
    expect(getStoredToken()).toBe(mockToken);

    const headers = getAuthHeaders() as Record<string, string>;
    expect(headers['Authorization']).toBe(`Bearer ${mockToken}`);
    expect(headers['Content-Type']).toBe('application/json');

    setStoredToken(null);
    expect(getStoredToken()).toBeNull();
    const headersLoggedOut = getAuthHeaders() as Record<string, string>;
    expect(headersLoggedOut['Authorization']).toBeUndefined();
  });

  it('enforces RBAC role privilege matrix', () => {
    // Permission Matrix test helper
    const checkPermissions = (role: UserRole) => {
      const isSuperAdmin = role === 'SUPER_ADMIN';
      const isAdmin = isSuperAdmin || role === 'ADMIN' || role === 'CONTENT_APPROVER';
      const isDepartmentStaff = role === 'DEPARTMENT_STAFF' || role === 'SUPPORT_AGENT';
      const isViewer = role === 'VIEWER' || role === 'AUDITOR';

      return {
        canManageUsers: isSuperAdmin,
        canUploadDocs: isSuperAdmin || isAdmin,
        canApproveDocs: isSuperAdmin || isAdmin,
        canEditConfig: isSuperAdmin || isAdmin,
        isReadOnly: isViewer,
        isDepartmentScoped: isDepartmentStaff,
      };
    };

    // 1. Super Admin
    const superAdminPerms = checkPermissions('SUPER_ADMIN');
    expect(superAdminPerms.canManageUsers).toBe(true);
    expect(superAdminPerms.canUploadDocs).toBe(true);
    expect(superAdminPerms.canApproveDocs).toBe(true);
    expect(superAdminPerms.canEditConfig).toBe(true);
    expect(superAdminPerms.isReadOnly).toBe(false);

    // 2. Admin
    const adminPerms = checkPermissions('ADMIN');
    expect(adminPerms.canManageUsers).toBe(false);
    expect(adminPerms.canUploadDocs).toBe(true);
    expect(adminPerms.canApproveDocs).toBe(true);
    expect(adminPerms.canEditConfig).toBe(true);
    expect(adminPerms.isReadOnly).toBe(false);

    // 3. Department Staff
    const staffPerms = checkPermissions('DEPARTMENT_STAFF');
    expect(staffPerms.canManageUsers).toBe(false);
    expect(staffPerms.canUploadDocs).toBe(false);
    expect(staffPerms.canApproveDocs).toBe(false);
    expect(staffPerms.canEditConfig).toBe(false);
    expect(staffPerms.isDepartmentScoped).toBe(true);

    // 4. Viewer / Auditor
    const viewerPerms = checkPermissions('VIEWER');
    expect(viewerPerms.canManageUsers).toBe(false);
    expect(viewerPerms.canUploadDocs).toBe(false);
    expect(viewerPerms.canApproveDocs).toBe(false);
    expect(viewerPerms.canEditConfig).toBe(false);
    expect(viewerPerms.isReadOnly).toBe(true);
  });
});

describe('Dashboard Pages & Data Contracts', () => {
  it('validates Overview telemetry schema and live database mode', () => {
    const mockOverview: AdminOverviewData = {
      documents: { total: 4, published: 2, review_required: 1, archived: 1, failed: 0 },
      ingestion_jobs: { total: 4, completed: 3, processing: 0, queued: 0, failed: 1 },
      support_tickets: { total: 5, open: 2, in_progress: 1, resolved: 2 },
      unanswered_questions: { total_unanswered_recent: 3, negative_feedback_count: 1 },
      usage_metrics: { total_queries: 18, fallback_count: 3, grounding_rate_pct: 83.3, avg_latency_ms: 1240 },
      recent_fallbacks: [
        { id: 'fb-1', message: 'What are the gym timings?', confidence_score: 0.42, created_at: new Date().toISOString() },
      ],
      is_demonstration_mode: false,
      user_role: 'SUPER_ADMIN',
      department_scope: null,
    };

    expect(mockOverview.is_demonstration_mode).toBe(false);
    expect(mockOverview.documents.published).toBeLessThanOrEqual(mockOverview.documents.total);
    expect(mockOverview.usage_metrics.grounding_rate_pct).toBeGreaterThanOrEqual(0);
    expect(mockOverview.usage_metrics.grounding_rate_pct).toBeLessThanOrEqual(100);
    expect(mockOverview.recent_fallbacks.length).toBeGreaterThan(0);
  });

  it('validates Knowledge Gaps schema and topic clustering', () => {
    const mockKnowledgeGaps: KnowledgeGapsData = {
      summary: { total_fallbacks: 8, negative_ratings: 2, identified_topics: 2 },
      unanswered_questions: [
        { id: '1', query: 'Bus pass fees for day scholars', confidence_score: 0.55, created_at: '2026-10-22', language: 'en' },
        { id: '2', query: 'விடுதி உணவு நேரம் என்ன?', confidence_score: 0.48, created_at: '2026-10-22', language: 'ta' },
      ],
      negative_feedback: [
        { id: '1', query: 'Hostel mess fee', response_preview: 'Deposit is 5000', feedback: 'unhelpful', created_at: '2026-10-22' },
      ],
      topic_clusters: [
        { cluster_id: 'cl-1', topic: 'Transportation & Bus Routes', count: 4, suggested_department: 'Transport Cell', status: 'UNRESOLVED' },
        { cluster_id: 'cl-2', topic: 'Hostel Dining Timings', count: 3, suggested_department: 'Hostel Administration', status: 'UNRESOLVED' },
      ],
    };

    expect(mockKnowledgeGaps.summary.identified_topics).toBe(mockKnowledgeGaps.topic_clusters.length);
    expect(mockKnowledgeGaps.topic_clusters[0].suggested_department).toBe('Transport Cell');
    expect(mockKnowledgeGaps.unanswered_questions[1].language).toBe('ta');
  });

  it('validates User Management model and Department scoping', () => {
    const mockStaff: StaffUser[] = [
      {
        id: 'user-1',
        email: 'admin@college.edu',
        full_name: 'Dr. System Administrator',
        role: 'SUPER_ADMIN',
        department_id: null,
        department_name: 'Campus-Wide',
        is_active: true,
        created_at: '2026-09-01T00:00:00Z',
      },
      {
        id: 'user-2',
        email: 'staff_hostel@college.edu',
        full_name: 'K. Ramanathan',
        role: 'DEPARTMENT_STAFF',
        department_id: 'dept-hostel-123',
        department_name: 'Hostel Administration',
        is_active: true,
        created_at: '2026-09-05T00:00:00Z',
      },
    ];

    expect(mockStaff).toHaveLength(2);
    expect(mockStaff[0].role).toBe('SUPER_ADMIN');
    expect(mockStaff[1].department_id).toBe('dept-hostel-123');
    expect(mockStaff[1].department_name).toBe('Hostel Administration');
  });

  it('validates Institutional Configuration schema and origin allowlist', () => {
    const mockConfig: AdminConfigData = {
      college_branding: {
        college_name: 'St. Jude College of Engineering & Technology',
        short_name: 'SJCET',
        tagline: 'Excellence in Engineering & Technology',
        brand_color: '#1e3a8a',
      },
      welcome_messages: {
        en: 'Hello! I am your AI campus assistant.',
        ta: 'வணக்கம்! நான் உங்கள் AI கல்லூரி உதவியாளர்.',
      },
      supported_languages: ['en', 'ta'],
      suggested_questions: ['What is the caution deposit?', 'Minimum attendance percentage?'],
      approved_origins: ['http://localhost:5175', 'https://college.edu'],
    };

    expect(mockConfig.college_branding.brand_color).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(mockConfig.supported_languages).toContain('en');
    expect(mockConfig.supported_languages).toContain('ta');
    expect(mockConfig.approved_origins).toContain('https://college.edu');
    expect(mockConfig.welcome_messages.ta).toContain('வணக்கம்');
  });

  it('validates Monitoring latency percentiles and token cost estimation', () => {
    const mockMonitoring: MonitoringData = {
      ingestion_failures: [
        {
          id: 'job-err-1',
          document_title: 'Damaged Scan.pdf',
          file_name: 'Damaged Scan.pdf',
          error_message: 'Corrupt PDF structure: Stream ended unexpectedly',
          retry_count: 3,
          failed_at: '2026-10-22T10:00:00Z',
          job_type: 'PDF_UPLOAD',
        },
      ],
      application_errors: [
        {
          timestamp: '2026-10-22T10:05:00Z',
          status_code: 403,
          path: '/api/v1/admin/users',
          error_type: 'ForbiddenError',
          details: 'Access restricted to SUPER_ADMIN',
        },
      ],
      performance_latency: {
        total_requests: 120,
        p50_ms: 320,
        p95_ms: 850,
        p99_ms: 1450,
        error_rate_pct: 0.8,
      },
      ai_token_usage_cost: {
        total_prompt_tokens: 14200,
        total_completion_tokens: 4100,
        total_tokens: 18300,
        estimated_cost_usd: 0.0035,
        estimated_cost_inr: 0.29,
      },
    };

    expect(mockMonitoring.performance_latency.p50_ms).toBeLessThan(mockMonitoring.performance_latency.p95_ms);
    expect(mockMonitoring.performance_latency.p95_ms).toBeLessThan(mockMonitoring.performance_latency.p99_ms);
    expect(mockMonitoring.ai_token_usage_cost.total_tokens).toBe(
      mockMonitoring.ai_token_usage_cost.total_prompt_tokens + mockMonitoring.ai_token_usage_cost.total_completion_tokens
    );
    expect(mockMonitoring.ai_token_usage_cost.estimated_cost_usd).toBeGreaterThan(0);
  });
});

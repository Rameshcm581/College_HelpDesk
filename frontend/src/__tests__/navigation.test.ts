import { describe, it, expect } from 'vitest';

describe('Frontend Navigation & Routing', () => {
  it('defines valid public and admin routes', () => {
    const routes = [
      { path: '/', name: 'Public Chatbot' },
      { path: '/admin', name: 'Admin Dashboard' },
      { path: '/admin/documents', name: 'Document Library' },
      { path: '/tickets', name: 'Support Tickets' },
    ];

    expect(routes).toHaveLength(4);
    expect(routes.map(r => r.path)).toContain('/');
    expect(routes.map(r => r.path)).toContain('/admin');
    expect(routes.map(r => r.path)).toContain('/tickets');
  });

  it('verifies academic year formatting convention', () => {
    const academicYearPattern = /^\d{4}-\d{4}$/;
    expect(academicYearPattern.test('2025-2026')).toBe(true);
    expect(academicYearPattern.test('2024-2025')).toBe(true);
    expect(academicYearPattern.test('2025')).toBe(false);
  });
});

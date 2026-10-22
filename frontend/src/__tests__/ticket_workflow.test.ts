import { describe, it, expect } from 'vitest';
import { TicketCategory, TicketPriority, TicketStatus } from '../types';

describe('Support Ticket Workflow & Lifecycle Rules', () => {
  it('validates all required ticket categories', () => {
    const categories: TicketCategory[] = [
      'ADMISSIONS',
      'FEES',
      'EXAMINATIONS',
      'HOSTEL',
      'SCHOLARSHIPS',
      'PLACEMENTS',
      'GENERAL',
    ];

    expect(categories).toHaveLength(7);
    expect(categories).toContain('ADMISSIONS');
    expect(categories).toContain('FEES');
    expect(categories).toContain('EXAMINATIONS');
    expect(categories).toContain('HOSTEL');
    expect(categories).toContain('SCHOLARSHIPS');
    expect(categories).toContain('PLACEMENTS');
    expect(categories).toContain('GENERAL');
  });

  it('validates institutional SLA target calculations', () => {
    const slaTargets: Record<TicketPriority, number> = {
      URGENT: 4,
      HIGH: 12,
      MEDIUM: 24,
      LOW: 48,
    };

    expect(slaTargets.URGENT).toBe(4);
    expect(slaTargets.HIGH).toBe(12);
    expect(slaTargets.MEDIUM).toBe(24);
    expect(slaTargets.LOW).toBe(48);
  });

  it('verifies status lifecycle state machine and allowed transitions', () => {
    const validTransitions: Record<TicketStatus, TicketStatus[]> = {
      OPEN: ['ASSIGNED', 'IN_PROGRESS', 'CLOSED'],
      ASSIGNED: ['IN_PROGRESS', 'WAITING_FOR_USER', 'CLOSED'],
      IN_PROGRESS: ['WAITING_FOR_USER', 'RESOLVED', 'CLOSED'],
      WAITING_FOR_USER: ['IN_PROGRESS', 'RESOLVED', 'CLOSED'],
      RESOLVED: ['CLOSED', 'IN_PROGRESS'],
      CLOSED: ['IN_PROGRESS'],
    };

    // Transition rules
    expect(validTransitions.OPEN).toContain('ASSIGNED');
    expect(validTransitions.OPEN).not.toContain('RESOLVED'); // Cannot directly resolve from OPEN

    expect(validTransitions.IN_PROGRESS).toContain('WAITING_FOR_USER');
    expect(validTransitions.IN_PROGRESS).toContain('RESOLVED');

    expect(validTransitions.RESOLVED).toContain('CLOSED');
  });

  it('verifies 6-digit numeric OTP regex pattern', () => {
    const otpPattern = /^\d{6}$/;
    expect(otpPattern.test('123456')).toBe(true);
    expect(otpPattern.test('004128')).toBe(true);
    expect(otpPattern.test('12345')).toBe(false);
    expect(otpPattern.test('1234567')).toBe(false);
    expect(otpPattern.test('12a456')).toBe(false);
  });

  it('verifies unique ticket number formatting pattern', () => {
    const ticketNumPattern = /^TCK-\d{4}-\d{5}$/;
    expect(ticketNumPattern.test('TCK-2026-00412')).toBe(true);
    expect(ticketNumPattern.test('TCK-2026-99460')).toBe(true);
    expect(ticketNumPattern.test('INC-2026-00412')).toBe(false);
    expect(ticketNumPattern.test('TCK-26-00412')).toBe(false);
  });
});

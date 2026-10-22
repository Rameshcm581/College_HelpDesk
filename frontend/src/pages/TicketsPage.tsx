import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Ticket,
  PlusCircle,
  Search,
  KeyRound,
  ShieldCheck,
  Clock,
  Send,
  AlertCircle,
  CheckCircle2,
  Building,
  User,
  Mail,
  Phone,
  ArrowRight,
  Copy,
  Check,
} from 'lucide-react';
import {
  createPublicTicket,
  fetchPublicTicketDetails,
  requestTicketOtp,
  sendPublicTicketReply,
  verifyTicketOtp,
} from '../services/api';
import { TicketCategory, TicketDetailData, TicketPriority } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { TicketsSection } from '../components/admin/TicketsSection';

export const TicketsPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();

  // Mode: 'create' | 'track' | 'staff'
  const initialMode = isAuthenticated ? 'staff' : (searchParams.get('mode') as 'create' | 'track') || 'create';
  const [activeMode, setActiveMode] = useState<'create' | 'track' | 'staff'>(initialMode);

  // ── 1. TICKET CREATION STATE ────────────────────────────────────────────────
  const [studentName, setStudentName] = useState('');
  const [studentEmail, setStudentEmail] = useState('');
  const [studentPhone, setStudentPhone] = useState('');
  const [category, setCategory] = useState<TicketCategory>(
    (searchParams.get('category')?.toUpperCase() as TicketCategory) || 'ADMISSIONS'
  );
  const [priority, setPriority] = useState<TicketPriority>('MEDIUM');
  const initialQuery = searchParams.get('query') || searchParams.get('message') || '';
  const initialSubject =
    searchParams.get('subject') ||
    (initialQuery ? (initialQuery.length > 50 ? `${initialQuery.slice(0, 47)}...` : initialQuery) : '');
  const [subject, setSubject] = useState(initialSubject);
  const [message, setMessage] = useState(initialQuery);
  const [sessionId] = useState(searchParams.get('session_id') || '');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createdReceipt, setCreatedReceipt] = useState<{
    ticket_number: string;
    department: string;
    sla_due_at: string;
    notification_sent: boolean;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  // ── 2. VISITOR TICKET TRACKING & OTP STATE ──────────────────────────────────
  const [trackTicketNumber, setTrackTicketNumber] = useState(searchParams.get('ticket') || '');
  const [trackEmail, setTrackEmail] = useState('');
  const [otpStep, setOtpStep] = useState<'request' | 'verify' | 'authenticated'>('request');
  const [otpCode, setOtpCode] = useState('');
  const [isOtpLoading, setIsOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [otpMessage, setOtpMessage] = useState<string | null>(null);
  const [visitorToken, setVisitorToken] = useState<string | null>(null);

  const [ticketData, setTicketData] = useState<TicketDetailData | null>(null);
  const [visitorReply, setVisitorReply] = useState('');
  const [isSendingReply, setIsSendingReply] = useState(false);
  const [replySuccess, setReplySuccess] = useState<string | null>(null);

  // Handle Form Submission
  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!studentName.trim() || !studentEmail.trim() || !subject.trim() || !message.trim()) {
      setCreateError('Please complete all required fields (Name, Email, Subject, and Details).');
      return;
    }

    setIsSubmitting(true);
    setCreateError(null);
    try {
      const data = await createPublicTicket({
        student_name: studentName.trim(),
        student_email: studentEmail.trim(),
        student_phone: studentPhone.trim() || undefined,
        category,
        priority,
        subject: subject.trim(),
        message: message.trim(),
        session_id: sessionId || undefined,
      });

      setCreatedReceipt(data);
      // Auto-populate tracking ticket
      setTrackTicketNumber(data.ticket_number);
      setTrackEmail(studentEmail.trim());
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : 'Failed to submit support ticket.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Request OTP
  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackTicketNumber.trim() || !trackEmail.trim()) {
      setOtpError('Please provide both your Ticket Identifier and Registered Email.');
      return;
    }

    setIsOtpLoading(true);
    setOtpError(null);
    setOtpMessage(null);
    try {
      const res = await requestTicketOtp(trackTicketNumber.trim().toUpperCase(), trackEmail.trim());
      setOtpMessage(
        res.dev_otp_hint
          ? `${res.message} (Test OTP code: ${res.dev_otp_hint})`
          : res.message
      );
      if (res.dev_otp_hint) {
        setOtpCode(res.dev_otp_hint);
      }
      setOtpStep('verify');
    } catch (err: unknown) {
      setOtpError(err instanceof Error ? err.message : 'Failed to request OTP code.');
    } finally {
      setIsOtpLoading(false);
    }
  };

  // Verify OTP
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode.trim()) {
      setOtpError('Please enter the 6-digit verification code.');
      return;
    }

    setIsOtpLoading(true);
    setOtpError(null);
    try {
      const res = await verifyTicketOtp(
        trackTicketNumber.trim().toUpperCase(),
        trackEmail.trim(),
        otpCode.trim()
      );
      setVisitorToken(res.access_token);
      // Load details
      const detail = await fetchPublicTicketDetails(trackTicketNumber.trim().toUpperCase(), res.access_token);
      setTicketData(detail);
      setOtpStep('authenticated');
    } catch (err: unknown) {
      setOtpError(err instanceof Error ? err.message : 'Verification failed. Please check code.');
    } finally {
      setIsOtpLoading(false);
    }
  };

  // Visitor Reply
  const handleVisitorReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackTicketNumber || !visitorToken || !visitorReply.trim()) return;

    setIsSendingReply(true);
    setReplySuccess(null);
    try {
      await sendPublicTicketReply(trackTicketNumber.trim().toUpperCase(), visitorToken, visitorReply.trim());
      setVisitorReply('');
      setReplySuccess('Your reply was submitted to college staff.');
      // Refresh ticket details
      const updated = await fetchPublicTicketDetails(trackTicketNumber.trim().toUpperCase(), visitorToken);
      setTicketData(updated);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to send reply.');
    } finally {
      setIsSendingReply(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold text-brand-700 uppercase tracking-wider mb-1">
            <Ticket className="w-4 h-4" />
            <span>Institutional Help Desk</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Support Ticket & Case Management
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Submit a formal inquiry for manual staff review, track an existing case with zero-password OTP security, or manage department queues.
          </p>
        </div>

        {/* View Mode Switcher */}
        <div className="flex flex-wrap gap-1 p-1 bg-slate-100 rounded-2xl border border-slate-200 w-full sm:w-auto">
          <button
            type="button"
            onClick={() => setActiveMode('create')}
            className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl text-xs font-bold transition-all text-center whitespace-nowrap ${
              activeMode === 'create'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Submit New Ticket
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('track')}
            className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl text-xs font-bold transition-all text-center whitespace-nowrap ${
              activeMode === 'track'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Track Existing Ticket
          </button>
          {isAuthenticated && (
            <button
              type="button"
              onClick={() => setActiveMode('staff')}
              className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl text-xs font-bold transition-all text-center whitespace-nowrap ${
                activeMode === 'staff'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Staff Triage Portal
            </button>
          )}
        </div>
      </div>

      {/* ── MODE 1: CREATE SUPPORT TICKET ───────────────────────────────────── */}
      {activeMode === 'create' && (
        <div className="max-w-3xl mx-auto space-y-6">
          {createdReceipt ? (
            <div className="bg-white rounded-3xl border border-emerald-200 p-8 shadow-card text-center space-y-6 animate-fadeIn">
              <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto shadow-xs border border-emerald-100">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="space-y-2">
                <h2 className="text-2xl font-extrabold text-slate-900">Support Ticket Created Successfully!</h2>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Your inquiry has been assigned to the relevant department desk with an institutional SLA target.
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 max-w-md mx-auto space-y-3 text-left text-xs">
                <div className="flex justify-between items-center pb-2 border-b border-slate-200">
                  <span className="text-slate-500 font-bold uppercase text-[10px]">TICKET IDENTIFIER</span>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-base font-extrabold text-brand-700">
                      {createdReceipt.ticket_number}
                    </span>
                    <button
                      onClick={() => copyToClipboard(createdReceipt.ticket_number)}
                      className="p-1 hover:bg-slate-200 rounded text-slate-500 transition-all"
                      title="Copy Ticket ID"
                    >
                      {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Routed Department:</span>
                  <span className="font-semibold text-slate-800">{createdReceipt.department}</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">SLA Resolution Target:</span>
                  <span className="font-mono text-slate-700">
                    {new Date(createdReceipt.sla_due_at).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>

                <div className="flex justify-between items-center pt-1">
                  <span className="text-slate-500 font-medium">Email Dispatch:</span>
                  <span className="text-emerald-700 font-semibold">
                    {createdReceipt.notification_sent ? 'Confirmation email dispatched' : 'Queued (SMTP Unconfigured)'}
                  </span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <button
                  onClick={() => {
                    setActiveMode('track');
                    setOtpStep('request');
                  }}
                  className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white px-6 py-3 rounded-2xl text-xs font-bold shadow-md transition-all"
                >
                  <Search className="w-4 h-4" />
                  <span>Track This Ticket Now</span>
                </button>
                <button
                  onClick={() => {
                    setCreatedReceipt(null);
                    setSubject('');
                    setMessage('');
                  }}
                  className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-6 py-3 rounded-2xl text-xs font-bold transition-all"
                >
                  <PlusCircle className="w-4 h-4" />
                  <span>Create Another Ticket</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-card space-y-6">
              <div className="space-y-1">
                <h2 className="text-xl font-bold text-slate-900">New Student Support Ticket</h2>
                <p className="text-xs text-slate-500">
                  Please provide accurate details so your inquiry can be routed to the appropriate college official.
                </p>
              </div>

              {createError && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center space-x-3 text-rose-700 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              <form onSubmit={handleCreateTicket} className="space-y-4 text-xs">
                {/* Name & Email */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 flex items-center">
                      <User className="w-3.5 h-3.5 mr-1 text-slate-400" /> Student / Visitor Name *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. S. Karthik"
                      value={studentName}
                      onChange={(e) => setStudentName(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 flex items-center">
                      <Mail className="w-3.5 h-3.5 mr-1 text-slate-400" /> Email Address *
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="e.g. karthik.s@example.com"
                      value={studentEmail}
                      onChange={(e) => setStudentEmail(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                    />
                  </div>
                </div>

                {/* Phone & Category */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 flex items-center">
                      <Phone className="w-3.5 h-3.5 mr-1 text-slate-400" /> Phone (Optional)
                    </label>
                    <input
                      type="tel"
                      placeholder="+91 9876543210"
                      value={studentPhone}
                      onChange={(e) => setStudentPhone(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 flex items-center">
                      <Building className="w-3.5 h-3.5 mr-1 text-slate-400" /> Support Category *
                    </label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value as TicketCategory)}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                    >
                      <option value="ADMISSIONS">Admissions Cell</option>
                      <option value="FEES">Accounts & Fees Office</option>
                      <option value="EXAMINATIONS">Controller of Examinations</option>
                      <option value="HOSTEL">Hostel Administration</option>
                      <option value="SCHOLARSHIPS">Scholarships & Welfare</option>
                      <option value="PLACEMENTS">Placement & Career Cell</option>
                      <option value="GENERAL">General Administration</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" /> Priority *
                    </label>
                    <select
                      value={priority}
                      onChange={(e) => setPriority(e.target.value as TicketPriority)}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                    >
                      <option value="LOW">Low (48 Hours Target)</option>
                      <option value="MEDIUM">Medium (24 Hours Target)</option>
                      <option value="HIGH">High (12 Hours Target)</option>
                      <option value="URGENT">Urgent (4 Hours Target)</option>
                    </select>
                  </div>
                </div>

                {/* Subject */}
                <div className="space-y-1.5">
                  <label className="font-bold text-slate-700 block">Inquiry Subject / Topic *</label>
                  <input
                    type="text"
                    required
                    placeholder="Brief headline of your issue or question"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>

                {/* Details */}
                <div className="space-y-1.5">
                  <label className="font-bold text-slate-700 block">Detailed Explanation *</label>
                  <textarea
                    rows={4}
                    required
                    placeholder="Provide specific details, roll numbers, or context..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full inline-flex items-center justify-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white py-3.5 rounded-2xl font-bold text-sm shadow-md transition-all disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                    <span>{isSubmitting ? 'Routing Ticket...' : 'Submit Support Ticket'}</span>
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* ── MODE 2: VISITOR TICKET TRACKING & OTP ───────────────────────────── */}
      {activeMode === 'track' && (
        <div className="max-w-3xl mx-auto space-y-6">
          {otpStep !== 'authenticated' ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-card space-y-6">
              <div className="space-y-1 text-center">
                <div className="w-12 h-12 bg-brand-50 text-brand-600 rounded-2xl flex items-center justify-center mx-auto shadow-xs border border-brand-100 mb-2">
                  <KeyRound className="w-6 h-6" />
                </div>
                <h2 className="text-xl font-bold text-slate-900">Secure Ticket Tracking</h2>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Access your ticket securely without creating a permanent account via one-time email OTP verification.
                </p>
              </div>

              {otpError && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center space-x-3 text-rose-700 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{otpError}</span>
                </div>
              )}

              {otpMessage && (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center space-x-3 text-emerald-800 text-xs">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{otpMessage}</span>
                </div>
              )}

              {otpStep === 'request' ? (
                <form onSubmit={handleRequestOtp} className="space-y-4 text-xs">
                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 block">Ticket Number *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. TCK-2026-00412"
                      value={trackTicketNumber}
                      onChange={(e) => setTrackTicketNumber(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-mono uppercase focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 block">Registered Email Address *</label>
                    <input
                      type="email"
                      required
                      placeholder="e.g. student@example.com"
                      value={trackEmail}
                      onChange={(e) => setTrackEmail(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isOtpLoading}
                    className="w-full inline-flex items-center justify-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white py-3 rounded-2xl font-bold text-xs shadow-md transition-all disabled:opacity-50"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>{isOtpLoading ? 'Sending One-Time Passcode...' : 'Send Verification OTP'}</span>
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyOtp} className="space-y-4 text-xs animate-fadeIn">
                  <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-2xl text-blue-900 space-y-1">
                    <span className="font-bold block">Verification Code Dispatched!</span>
                    <p className="text-[11px] text-blue-700">
                      We sent a 6-digit verification code to <strong>{trackEmail}</strong> for ticket{' '}
                      <strong>{trackTicketNumber}</strong>. Valid for 15 minutes (3 max attempts).
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 block">Enter 6-Digit Code *</label>
                    <input
                      type="text"
                      maxLength={6}
                      required
                      placeholder="123456"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-mono tracking-widest text-center text-xl font-extrabold focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                    />
                  </div>

                  <div className="flex space-x-3">
                    <button
                      type="submit"
                      disabled={isOtpLoading}
                      className="flex-1 inline-flex items-center justify-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white py-3 rounded-2xl font-bold text-xs shadow-md transition-all disabled:opacity-50"
                    >
                      <span>{isOtpLoading ? 'Verifying...' : 'Authenticate & View Ticket'}</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setOtpStep('request')}
                      className="px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-2xl font-bold text-xs transition-all"
                    >
                      Back
                    </button>
                  </div>
                </form>
              )}
            </div>
          ) : ticketData ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-card space-y-6 animate-fadeIn">
              {/* Authenticated Ticket Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-brand-700 bg-brand-50 border border-brand-200 px-2.5 py-0.5 rounded-md">
                      {ticketData.ticket_number}
                    </span>
                    <StatusBadge status={ticketData.status} />
                    <span className="text-xs font-bold text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded uppercase">
                      {ticketData.category}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">{ticketData.subject}</h3>
                </div>

                <button
                  onClick={() => {
                    setOtpStep('request');
                    setTicketData(null);
                    setVisitorToken(null);
                  }}
                  className="text-xs font-semibold text-slate-500 hover:text-slate-800"
                >
                  Exit Session
                </button>
              </div>

              {/* Status Info Card */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 bg-slate-50 rounded-2xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 font-bold block mb-0.5">ROUTED DESK</span>
                  <span className="font-semibold text-slate-900 block">{ticketData.department}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-bold block mb-0.5">SUBMITTED ON</span>
                  <span className="text-slate-700 block">{new Date(ticketData.created_at).toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-bold block mb-0.5">SLA TARGET</span>
                  <span className="font-mono text-slate-800 block">
                    {ticketData.sla_due_at ? new Date(ticketData.sla_due_at).toLocaleDateString() : 'Active'}
                  </span>
                </div>
              </div>

              {/* Resolution Banner */}
              {ticketData.resolution_notes && (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs space-y-1">
                  <span className="font-bold text-emerald-800 flex items-center">
                    <CheckCircle2 className="w-4 h-4 mr-1.5" /> Official Resolution Record
                  </span>
                  <p className="text-emerald-950 font-medium pl-5">{ticketData.resolution_notes}</p>
                </div>
              )}

              {/* Communication Feed */}
              <div className="space-y-3">
                <span className="font-bold text-xs text-slate-700 block">Communication & Message History</span>
                <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                  {ticketData.messages?.map((msg) => (
                    <div
                      key={msg.id}
                      className={`p-3.5 rounded-2xl border text-xs space-y-1.5 ${
                        msg.sender_type === 'STAFF'
                          ? 'bg-blue-50/80 border-blue-200 text-blue-900 ml-4'
                          : 'bg-slate-50 border-slate-200 text-slate-800 mr-4'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-semibold">
                        <span className="font-bold text-slate-700">
                          {msg.sender_type === 'STAFF' ? 'College Staff Response' : 'You (Visitor)'}
                        </span>
                        <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap">{msg.message}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Reply Box */}
              {ticketData.status !== 'CLOSED' ? (
                <form onSubmit={handleVisitorReply} className="space-y-3 pt-3 border-t border-slate-200">
                  {replySuccess && (
                    <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs">
                      {replySuccess}
                    </div>
                  )}
                  <div className="space-y-1.5">
                    <label className="font-bold text-xs text-slate-700 block">
                      Send Follow-Up Message / Documents:
                    </label>
                    <textarea
                      rows={3}
                      value={visitorReply}
                      onChange={(e) => setVisitorReply(e.target.value)}
                      placeholder="Type your message to the support staff..."
                      className="w-full p-3 bg-slate-50 border border-slate-200 rounded-2xl text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                    />
                  </div>
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isSendingReply || !visitorReply.trim()}
                      className="inline-flex items-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl text-xs font-bold shadow-xs transition-all disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{isSendingReply ? 'Sending...' : 'Send Response'}</span>
                    </button>
                  </div>
                </form>
              ) : (
                <div className="p-4 bg-slate-100 rounded-2xl text-center text-xs text-slate-500 font-medium">
                  This support ticket is marked as CLOSED. If you need further assistance, please submit a new ticket.
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* ── MODE 3: STAFF TRIAGE INTEGRATION ────────────────────────────────── */}
      {activeMode === 'staff' && isAuthenticated && (
        <TicketsSection />
      )}
    </div>
  );
};

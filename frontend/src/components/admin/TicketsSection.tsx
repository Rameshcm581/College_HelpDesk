import React, { useEffect, useState } from 'react';
import {
  Ticket,
  Search,
  Filter,
  Clock,
  AlertCircle,
  CheckCircle2,
  User,
  Building,
  Mail,
  MessageSquare,
  Lock,
  Send,
  RefreshCw,
  ChevronRight,
  ShieldAlert,
  Calendar,
  X,
  FileText,
  UserCheck,
} from 'lucide-react';
import {
  addAdminTicketMessage,
  assignAdminTicket,
  fetchAdminMetadata,
  fetchAdminTicketDetail,
  fetchAdminTickets,
  fetchAdminUsers,
  updateAdminTicketStatus,
} from '../../services/api';
import { AdminMetadata, StaffUser, SupportTicket, TicketDetailData, TicketStatus } from '../../types';
import { StatusBadge } from '../StatusBadge';
import { useAuth } from '../../context/AuthContext';

export const TicketsSection: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [staffUsers, setStaffUsers] = useState<StaffUser[]>([]);
  const [metadata, setMetadata] = useState<AdminMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [deptFilter, setDeptFilter] = useState('ALL');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Ticket Detail Modal
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [ticketDetail, setTicketDetail] = useState<TicketDetailData | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<'thread' | 'history' | 'transcript'>('thread');

  // Response / Note form
  const [replyMessage, setReplyMessage] = useState('');
  const [isInternalNote, setIsInternalNote] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // Assign staff
  const [assigneeId, setAssigneeId] = useState('');
  const [isAssigning, setIsAssigning] = useState(false);

  // Status transition modal / prompt
  const [transitionStatus, setTransitionStatus] = useState<TicketStatus | ''>('');
  const [transitionReason, setTransitionReason] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isTransitioning, setIsTransitioning] = useState(false);

  const loadTickets = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchAdminTickets({
        status: statusFilter,
        category: categoryFilter,
        department_code: deptFilter,
        overdue_only: overdueOnly,
        search: searchQuery.trim(),
      });
      setTickets(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load tickets');
    } finally {
      setIsLoading(false);
    }
  };

  const loadInitialData = async () => {
    try {
      const meta = await fetchAdminMetadata();
      setMetadata(meta);
      if (currentUser?.role === 'SUPER_ADMIN' || currentUser?.role === 'ADMIN') {
        const users = await fetchAdminUsers();
        setStaffUsers(users);
      }
    } catch {
      // Non-blocking metadata load
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      loadTickets();
    }, 250);
    return () => clearTimeout(delayDebounce);
  }, [statusFilter, categoryFilter, deptFilter, overdueOnly, searchQuery]);

  const openTicketDetail = async (ticketId: string) => {
    setSelectedTicketId(ticketId);
    setIsDetailLoading(true);
    setDetailError(null);
    setDetailTab('thread');
    setReplyMessage('');
    setIsInternalNote(false);
    setTransitionStatus('');
    try {
      const detail = await fetchAdminTicketDetail(ticketId);
      setTicketDetail(detail);
      setAssigneeId(detail.assigned_to_user_id || '');
    } catch (err: unknown) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load ticket details');
    } finally {
      setIsDetailLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicketId || !replyMessage.trim()) return;

    setIsSending(true);
    try {
      await addAdminTicketMessage(selectedTicketId, replyMessage.trim(), isInternalNote);
      setReplyMessage('');
      // Refresh detail
      const updated = await fetchAdminTicketDetail(selectedTicketId);
      setTicketDetail(updated);
      loadTickets();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsSending(false);
    }
  };

  const handleAssignStaff = async () => {
    if (!selectedTicketId || !assigneeId) return;
    setIsAssigning(true);
    try {
      await assignAdminTicket(selectedTicketId, assigneeId);
      const updated = await fetchAdminTicketDetail(selectedTicketId);
      setTicketDetail(updated);
      loadTickets();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to assign staff');
    } finally {
      setIsAssigning(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!selectedTicketId || !transitionStatus) return;
    if (transitionStatus === 'RESOLVED' && !resolutionNotes.trim()) {
      alert('Resolution notes are mandatory when marking a ticket as RESOLVED.');
      return;
    }

    setIsTransitioning(true);
    try {
      await updateAdminTicketStatus(
        selectedTicketId,
        transitionStatus,
        transitionReason.trim() || undefined,
        resolutionNotes.trim() || undefined
      );
      setTransitionStatus('');
      setTransitionReason('');
      setResolutionNotes('');
      const updated = await fetchAdminTicketDetail(selectedTicketId);
      setTicketDetail(updated);
      loadTickets();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Status update failed');
    } finally {
      setIsTransitioning(false);
    }
  };

  const getPriorityBadgeClass = (priority: string) => {
    switch (priority) {
      case 'URGENT':
        return 'bg-rose-100 text-rose-800 border-rose-300 font-bold';
      case 'HIGH':
        return 'bg-amber-100 text-amber-800 border-amber-300 font-bold';
      case 'MEDIUM':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header Banner */}
      <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center border border-brand-100 shadow-xs">
              <Ticket className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                Support Ticket Triage
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Escalations from chatbot fallbacks, admissions inquiries, and human-intervention workflows.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadTickets}
            disabled={isLoading}
            className="inline-flex items-center space-x-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-4">
        {/* Status Pills */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-none text-xs">
          <span className="text-slate-400 font-bold uppercase tracking-wider text-[10px] mr-1 flex items-center">
            <Filter className="w-3 h-3 mr-1" /> Status:
          </span>
          {[
            { id: 'ALL', label: 'All Tickets' },
            { id: 'OPEN', label: 'Open' },
            { id: 'ASSIGNED', label: 'Assigned' },
            { id: 'IN_PROGRESS', label: 'In Progress' },
            { id: 'WAITING_FOR_USER', label: 'Waiting for User' },
            { id: 'RESOLVED', label: 'Resolved' },
            { id: 'CLOSED', label: 'Closed' },
          ].map((st) => (
            <button
              key={st.id}
              onClick={() => setStatusFilter(st.id)}
              className={`px-3 py-1.5 rounded-xl font-semibold whitespace-nowrap transition-all ${
                statusFilter === st.id
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200'
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>

        {/* Secondary Filters & Search */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-100 text-xs">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search student, email, ticket..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-900"
            />
          </div>

          {/* Category Dropdown */}
          <div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-700 font-medium"
            >
              <option value="ALL">All Categories</option>
              <option value="ADMISSIONS">Admissions</option>
              <option value="FEES">Fees</option>
              <option value="EXAMINATIONS">Examinations</option>
              <option value="HOSTEL">Hostel</option>
              <option value="SCHOLARSHIPS">Scholarships</option>
              <option value="PLACEMENTS">Placements</option>
              <option value="GENERAL">General enquiries</option>
            </select>
          </div>

          {/* Department Filter */}
          <div>
            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-700 font-medium"
            >
              <option value="ALL">All Departments</option>
              {metadata?.departments?.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
          </div>

          {/* Overdue Only Toggle */}
          <div className="flex items-center justify-between sm:justify-start space-x-3 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl">
            <span className="text-slate-700 font-semibold flex items-center">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-500 mr-1.5" /> Overdue Only
            </span>
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="w-4 h-4 text-rose-600 rounded border-slate-300 focus:ring-rose-500 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Tickets List */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center space-x-3 text-rose-700 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="p-12 text-center space-y-3 bg-white rounded-3xl border border-slate-200">
          <div className="w-8 h-8 border-3 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-medium">Filtering tickets from database...</p>
        </div>
      ) : tickets.length === 0 ? (
        <div className="p-12 text-center space-y-3 bg-white rounded-3xl border border-slate-200 text-slate-400">
          <Ticket className="w-12 h-12 mx-auto stroke-[1.2]" />
          <h3 className="text-base font-bold text-slate-700">No support tickets match criteria</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try resetting your status or department filters, or clear your search term.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5">
          {tickets.map((t) => (
            <div
              key={t.id}
              onClick={() => openTicketDetail(t.id)}
              className={`bg-white rounded-2xl border p-5 shadow-card hover:border-brand-300 hover:shadow-md transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                t.is_overdue ? 'border-rose-300 bg-rose-50/20' : 'border-slate-200'
              }`}
            >
              {/* Ticket Meta & Subject */}
              <div className="space-y-2 min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-brand-700 bg-brand-50 border border-brand-200 px-2.5 py-0.5 rounded-md">
                    {t.ticket_number}
                  </span>
                  <span className="text-[11px] font-bold text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded uppercase">
                    {t.category}
                  </span>
                  <StatusBadge status={t.status} />
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded border uppercase ${getPriorityBadgeClass(
                      t.priority
                    )}`}
                  >
                    {t.priority}
                  </span>
                  {t.is_overdue && (
                    <span className="text-[10px] font-extrabold text-rose-700 bg-rose-100 border border-rose-300 px-2 py-0.5 rounded-full flex items-center animate-pulse">
                      <Clock className="w-3 h-3 mr-1" /> OVERDUE
                    </span>
                  )}
                </div>

                <div className="space-y-1">
                  <h4 className="font-bold text-slate-900 text-base leading-snug truncate">
                    {t.subject || 'Student Support Request'}
                  </h4>
                  <p className="text-xs text-slate-500 line-clamp-1">
                    {t.description || 'No description provided.'}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center">
                    <User className="w-3.5 h-3.5 text-slate-400 mr-1" /> {t.student_name}
                  </span>
                  <span className="flex items-center">
                    <Mail className="w-3.5 h-3.5 text-slate-400 mr-1" /> {t.student_email}
                  </span>
                  {t.department_name && (
                    <span className="flex items-center text-slate-600 font-medium">
                      <Building className="w-3.5 h-3.5 text-slate-400 mr-1" /> {t.department_name}
                    </span>
                  )}
                </div>
              </div>

              {/* Assignment & SLA Targets */}
              <div className="flex md:flex-col items-center md:items-end justify-between border-t md:border-t-0 pt-3 md:pt-0 border-slate-100 text-right space-y-1 shrink-0">
                <div className="text-xs">
                  {t.assigned_to_name ? (
                    <span className="font-semibold text-slate-700 flex items-center">
                      <UserCheck className="w-3.5 h-3.5 text-emerald-600 mr-1" /> {t.assigned_to_name}
                    </span>
                  ) : (
                    <span className="text-slate-400 italic">Unassigned</span>
                  )}
                </div>

                {t.sla_due_at && (
                  <div className="text-[11px] text-slate-500 flex items-center">
                    <Clock className="w-3 h-3 text-slate-400 mr-1" />
                    Due:{' '}
                    <span className="font-mono ml-1">
                      {new Date(t.sla_due_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                )}

                <span className="inline-flex items-center text-xs font-bold text-brand-600 hover:text-brand-700 mt-1">
                  Manage <ChevronRight className="w-4 h-4 ml-0.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── TICKET DETAIL MODAL / DRAWER ───────────────────────────────────── */}
      {selectedTicketId && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-y-auto animate-fadeIn">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden my-auto">
            {/* Modal Header */}
            <div className="p-5 sm:p-6 border-b border-slate-200 flex items-start justify-between bg-slate-50/80">
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-brand-700 bg-brand-50 border border-brand-200 px-2.5 py-0.5 rounded-md">
                    {ticketDetail?.ticket_number || 'Loading...'}
                  </span>
                  {ticketDetail && (
                    <>
                      <StatusBadge status={ticketDetail.status} />
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded border uppercase ${getPriorityBadgeClass(
                          ticketDetail.priority
                        )}`}
                      >
                        {ticketDetail.priority}
                      </span>
                      <span className="text-xs font-bold text-slate-600 bg-white border border-slate-200 px-2.5 py-0.5 rounded uppercase">
                        {ticketDetail.category}
                      </span>
                      {ticketDetail.is_overdue && (
                        <span className="text-[11px] font-bold text-rose-700 bg-rose-100 border border-rose-300 px-2 py-0.5 rounded-full">
                          SLA Breached
                        </span>
                      )}
                    </>
                  )}
                </div>
                <h3 className="text-xl font-extrabold text-slate-900">
                  {ticketDetail?.subject || 'Support Ticket Details'}
                </h3>
              </div>

              <button
                onClick={() => setSelectedTicketId(null)}
                className="text-slate-400 hover:text-slate-600 p-2 rounded-xl hover:bg-slate-200/50 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            {isDetailLoading ? (
              <div className="p-16 text-center space-y-3">
                <div className="w-8 h-8 border-3 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto" />
                <p className="text-xs text-slate-500 font-medium">Fetching complete ticket history & transcripts...</p>
              </div>
            ) : detailError ? (
              <div className="p-8 text-center text-rose-600 space-y-2">
                <AlertCircle className="w-8 h-8 mx-auto" />
                <p className="text-sm font-semibold">{detailError}</p>
              </div>
            ) : ticketDetail ? (
              <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
                {/* Information Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-2xl border border-slate-200 text-xs">
                  <div>
                    <span className="text-slate-400 font-bold block mb-1">STUDENT</span>
                    <span className="font-bold text-slate-900 block">{ticketDetail.student_name}</span>
                    <span className="text-slate-600 block">{ticketDetail.student_email}</span>
                    {ticketDetail.student_phone && (
                      <span className="text-slate-500 block">{ticketDetail.student_phone}</span>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-400 font-bold block mb-1">DEPARTMENT ROUTING</span>
                    <span className="font-semibold text-slate-900 block">{ticketDetail.department}</span>
                    <span className="text-slate-500 block">Code: {ticketDetail.department_code || 'GEN'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 font-bold block mb-1">SLA RESOLUTION TARGET</span>
                    <span className="font-mono text-slate-800 block">
                      {ticketDetail.sla_due_at
                        ? new Date(ticketDetail.sla_due_at).toLocaleString()
                        : 'No deadline set'}
                    </span>
                    <span className="text-slate-500 block">
                      Opened: {new Date(ticketDetail.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {/* Resolution Notes Banner (if resolved) */}
                {ticketDetail.resolution_notes && (
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs space-y-1">
                    <span className="font-bold text-emerald-800 flex items-center">
                      <CheckCircle2 className="w-4 h-4 mr-1.5" /> Resolution Record (Resolved by{' '}
                      {ticketDetail.resolved_by_name || 'Staff'})
                    </span>
                    <p className="text-emerald-950 font-medium pl-5">{ticketDetail.resolution_notes}</p>
                  </div>
                )}

                {/* Action Bar: Assign & Status Transitions */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 bg-white rounded-2xl border border-slate-200 shadow-xs">
                  {/* Staff Assignment */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-700 flex items-center">
                      <UserCheck className="w-3.5 h-3.5 mr-1 text-slate-400" /> Assign Ticket Staff
                    </label>
                    <div className="flex space-x-2">
                      <select
                        value={assigneeId}
                        onChange={(e) => setAssigneeId(e.target.value)}
                        className="flex-1 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      >
                        <option value="">Unassigned</option>
                        {staffUsers.length > 0 ? (
                          staffUsers.map((u) => (
                            <option key={u.id} value={u.id}>
                              {u.full_name} ({u.role})
                            </option>
                          ))
                        ) : currentUser ? (
                          <option value={currentUser.id}>Assign to Me ({currentUser.full_name})</option>
                        ) : null}
                      </select>
                      <button
                        onClick={handleAssignStaff}
                        disabled={isAssigning || !assigneeId || assigneeId === ticketDetail.assigned_to_user_id}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-all"
                      >
                        {isAssigning ? 'Saving...' : 'Assign'}
                      </button>
                    </div>
                  </div>

                  {/* Status Lifecycle Transition */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-700 flex items-center">
                      <RefreshCw className="w-3.5 h-3.5 mr-1 text-slate-400" /> Change Status Lifecycle
                    </label>
                    <div className="flex space-x-2">
                      <select
                        value={transitionStatus}
                        onChange={(e) => setTransitionStatus(e.target.value as TicketStatus)}
                        className="flex-1 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      >
                        <option value="">Select New Status...</option>
                        <option value="ASSIGNED">ASSIGNED (In Triage)</option>
                        <option value="IN_PROGRESS">IN_PROGRESS (Under Review)</option>
                        <option value="WAITING_FOR_USER">WAITING_FOR_USER (Awaiting Info)</option>
                        <option value="RESOLVED">RESOLVED (Solution Provided)</option>
                        <option value="CLOSED">CLOSED (Archived)</option>
                      </select>
                      <button
                        onClick={handleUpdateStatus}
                        disabled={isTransitioning || !transitionStatus}
                        className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-all"
                      >
                        {isTransitioning ? 'Updating...' : 'Update'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Additional inputs if transition is RESOLVED */}
                {transitionStatus === 'RESOLVED' && (
                  <div className="p-4 bg-emerald-50/50 border border-emerald-200 rounded-2xl space-y-2 animate-fadeIn text-xs">
                    <label className="font-bold text-emerald-900 block">
                      Resolution Notes (Mandatory for Visitor Notification):
                    </label>
                    <textarea
                      rows={2}
                      value={resolutionNotes}
                      onChange={(e) => setResolutionNotes(e.target.value)}
                      placeholder="Explain how this inquiry was resolved so the visitor receives an official closing record..."
                      className="w-full p-2.5 bg-white border border-emerald-300 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    />
                  </div>
                )}

                {/* Tabs */}
                <div className="flex items-center space-x-4 border-b border-slate-200 pb-2 text-xs font-bold">
                  <button
                    onClick={() => setDetailTab('thread')}
                    className={`pb-2 transition-all flex items-center space-x-1.5 ${
                      detailTab === 'thread'
                        ? 'text-brand-600 border-b-2 border-brand-600'
                        : 'text-slate-400 hover:text-slate-700'
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Communication Thread ({ticketDetail.messages?.length || 0})</span>
                  </button>

                  <button
                    onClick={() => setDetailTab('history')}
                    className={`pb-2 transition-all flex items-center space-x-1.5 ${
                      detailTab === 'history'
                        ? 'text-brand-600 border-b-2 border-brand-600'
                        : 'text-slate-400 hover:text-slate-700'
                    }`}
                  >
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Audit Trail & Lifecycle ({ticketDetail.status_history?.length || 0})</span>
                  </button>

                  {ticketDetail.conversation_transcript && ticketDetail.conversation_transcript.length > 0 && (
                    <button
                      onClick={() => setDetailTab('transcript')}
                      className={`pb-2 transition-all flex items-center space-x-1.5 ${
                        detailTab === 'transcript'
                          ? 'text-brand-600 border-b-2 border-brand-600'
                          : 'text-slate-400 hover:text-slate-700'
                      }`}
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>Chatbot Transcript ({ticketDetail.conversation_transcript.length})</span>
                    </button>
                  )}
                </div>

                {/* Tab 1: Thread */}
                {detailTab === 'thread' && (
                  <div className="space-y-4">
                    <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                      {ticketDetail.messages?.map((msg) => (
                        <div
                          key={msg.id}
                          className={`p-3.5 rounded-2xl border text-xs space-y-1.5 ${
                            msg.is_internal_note
                              ? 'bg-amber-50/80 border-amber-200 text-amber-900 ml-4'
                              : msg.sender_type === 'STAFF'
                              ? 'bg-blue-50 border-blue-200 text-blue-900 ml-4'
                              : 'bg-white border-slate-200 text-slate-800 mr-4'
                          }`}
                        >
                          <div className="flex items-center justify-between text-[10px] text-slate-400 font-semibold">
                            <span className="flex items-center space-x-1">
                              {msg.is_internal_note ? (
                                <span className="font-bold text-amber-700 flex items-center">
                                  <Lock className="w-3 h-3 mr-1" /> Internal Staff Note ({msg.sender_name || 'Staff'})
                                </span>
                              ) : msg.sender_type === 'STAFF' ? (
                                <span className="font-bold text-blue-700">
                                  Staff Reply ({msg.sender_name || 'Staff'})
                                </span>
                              ) : (
                                <span className="font-bold text-slate-700">Student Message ({ticketDetail.student_name})</span>
                              )}
                            </span>
                            <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                          <p className="leading-relaxed whitespace-pre-wrap">{msg.message}</p>
                        </div>
                      ))}
                    </div>

                    {/* Compose Response */}
                    <form onSubmit={handleSendMessage} className="space-y-3 pt-3 border-t border-slate-200">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-700">Compose Response or Note</span>
                        <div className="flex items-center space-x-2">
                          <label className="flex items-center space-x-1.5 cursor-pointer text-amber-800 font-medium bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-lg">
                            <input
                              type="checkbox"
                              checked={isInternalNote}
                              onChange={(e) => setIsInternalNote(e.target.checked)}
                              className="w-3.5 h-3.5 text-amber-600 rounded cursor-pointer"
                            />
                            <Lock className="w-3 h-3 text-amber-600" />
                            <span>Internal Staff Note Only</span>
                          </label>
                        </div>
                      </div>

                      <div className="relative">
                        <textarea
                          rows={3}
                          value={replyMessage}
                          onChange={(e) => setReplyMessage(e.target.value)}
                          placeholder={
                            isInternalNote
                              ? 'Write an internal staff observation (never shared with student)...'
                              : 'Write a response to student (dispatched via email and visible in tracking portal)...'
                          }
                          className={`w-full p-3 rounded-2xl border text-xs focus:outline-none focus:ring-2 ${
                            isInternalNote
                              ? 'bg-amber-50/30 border-amber-300 focus:ring-amber-500/20'
                              : 'bg-slate-50 border-slate-200 focus:bg-white focus:ring-brand-500/20'
                          }`}
                        />
                      </div>

                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={isSending || !replyMessage.trim()}
                          className={`inline-flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-bold text-white transition-all shadow-xs ${
                            isInternalNote
                              ? 'bg-amber-600 hover:bg-amber-700'
                              : 'bg-brand-600 hover:bg-brand-700'
                          } disabled:opacity-50`}
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>{isSending ? 'Sending...' : isInternalNote ? 'Save Note' : 'Send to Student'}</span>
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* Tab 2: Status History */}
                {detailTab === 'history' && (
                  <div className="space-y-3">
                    {ticketDetail.status_history?.map((h, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-start justify-between gap-4"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2 font-semibold">
                            <span className="font-mono text-[11px] text-slate-500">{h.from_status}</span>
                            <span>&rarr;</span>
                            <span className="font-mono text-[11px] text-brand-700 font-bold">{h.to_status}</span>
                          </div>
                          {h.change_reason && <p className="text-slate-600 italic">"{h.change_reason}"</p>}
                          {h.changed_by && <span className="text-[10px] text-slate-400 block">Actor: {h.changed_by}</span>}
                        </div>
                        <span className="text-[10px] text-slate-400 shrink-0">
                          {new Date(h.created_at).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tab 3: Chatbot Reference Transcript */}
                {detailTab === 'transcript' && ticketDetail.conversation_transcript && (
                  <div className="space-y-2.5 max-h-72 overflow-y-auto">
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-900 mb-2">
                      <p className="font-semibold">Associated Pre-Escalation Conversation Transcript</p>
                      <p className="text-[11px] text-blue-700">
                        Chat messages exchanged between the student and the AI chatbot before escalating this ticket.
                      </p>
                    </div>
                    {ticketDetail.conversation_transcript.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border text-xs space-y-1 ${
                          msg.role === 'assistant'
                            ? 'bg-slate-50 border-slate-200 ml-4'
                            : 'bg-white border-blue-200 text-blue-900 mr-4'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase">
                          <span>{msg.role}</span>
                          <span>{new Date(msg.created_at).toLocaleTimeString()}</span>
                        </div>
                        <p className="leading-relaxed">{msg.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};

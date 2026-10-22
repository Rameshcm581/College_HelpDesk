import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Menu,
  ShieldCheck,
  Bot,
  ExternalLink,
  Shield,
  LogOut,
  Users,
  Lock,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AdminLoginModal } from '../components/AdminLoginModal';
import { AdminSidebar, AdminTab } from '../components/admin/AdminSidebar';
import { OverviewSection } from '../components/admin/OverviewSection';
import { DocumentsSection } from '../components/admin/DocumentsSection';
import { KnowledgeGapsSection } from '../components/admin/KnowledgeGapsSection';
import { UserManagementSection } from '../components/admin/UserManagementSection';
import { ConfigSection } from '../components/admin/ConfigSection';
import { MonitoringSection } from '../components/admin/MonitoringSection';
import { TicketsSection } from '../components/admin/TicketsSection';

interface AdminDashboardPageProps {
  defaultTab?: AdminTab;
  enforceRole?: 'staff' | 'admin';
}

const tabTitles: Record<AdminTab, string> = {
  overview: 'Executive Overview & Real-Time Metrics',
  tickets: 'Support Tickets & Queue Management',
  documents: 'Document Repository & Verification Lifecycle',
  'knowledge-gaps': 'Knowledge Gaps & Unanswered Queries',
  users: 'Staff User Management & RBAC Permissions',
  config: 'Institutional Branding & AI Configuration',
  monitoring: 'System Observability, Latency & AI Telemetry',
};

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ defaultTab, enforceRole }) => {
  const { user, isAuthenticated, isLoading, logout, canManageUsers, isDepartmentStaff } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // For department staff, default to 'tickets' instead of 'overview'
  const computedDefaultTab = defaultTab || (isDepartmentStaff ? 'tickets' : 'overview');
  const initialTab = (searchParams.get('tab') as AdminTab) || computedDefaultTab;
  const [activeTab, setActiveTab] = useState<AdminTab>(initialTab);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [loginRoleTab, setLoginRoleTab] = useState<'staff' | 'admin'>('staff');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Enforce staff tab restrictions
  useEffect(() => {
    if (isDepartmentStaff && activeTab !== 'tickets' && activeTab !== 'documents') {
      setActiveTab('tickets');
      setSearchParams({ tab: 'tickets' });
    }
  }, [isDepartmentStaff, activeTab, setSearchParams]);

  const handleTabChange = (tab: AdminTab) => {
    if (isDepartmentStaff && tab !== 'tickets' && tab !== 'documents') {
      return; // Disallow staff from navigating to executive console
    }
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <div className="w-10 h-10 border-4 border-brand-400 border-t-brand-600 rounded-full animate-spin mx-auto" />
          <p className="text-sm text-slate-400 font-medium">Validating institutional credentials...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[85vh] flex items-center justify-center px-4 py-12 animate-fadeIn bg-slate-50">
        <div className="max-w-2xl w-full bg-white rounded-3xl border border-slate-200 p-8 sm:p-12 shadow-xl text-center space-y-6">
          <div className="w-16 h-16 bg-brand-50 text-brand-600 rounded-2xl flex items-center justify-center mx-auto shadow-sm">
            <Lock className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {enforceRole === 'staff' ? 'Department Staff Operations Portal' : 'Institutional Administration Portal'}
            </h1>
            <p className="text-sm text-slate-500 max-w-lg mx-auto">
              {enforceRole === 'staff'
                ? 'Department ticket triage, student issue escalation, and circular verification require authenticated staff credentials.'
                : 'Universal RBAC oversight, document approval, RAG knowledge indexing, and system telemetry require authorized administrator credentials.'}
            </p>
          </div>

          {/* Dual Action Sign-in Triggers */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={() => {
                setLoginRoleTab('staff');
                setIsLoginOpen(true);
              }}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white px-5 py-3 rounded-2xl font-bold text-sm shadow-md transition-all transform hover:-translate-y-0.5"
            >
              <Users className="w-4 h-4" />
              <span>Sign In as Department Staff</span>
            </button>
            <button
              onClick={() => {
                setLoginRoleTab('admin');
                setIsLoginOpen(true);
              }}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-slate-900 hover:bg-slate-800 text-white px-5 py-3 rounded-2xl font-bold text-sm shadow-md transition-all transform hover:-translate-y-0.5"
            >
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>Sign In as Administrator</span>
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 border-t border-slate-100 text-left text-xs text-slate-600">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-900 block mb-0.5">Super Admin</span>
              <span className="text-[11px] text-slate-500">Universal RBAC & User Control</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-900 block mb-0.5">Admin</span>
              <span className="text-[11px] text-slate-500">Upload & Approve Circulars</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-900 block mb-0.5">Dept Staff</span>
              <span className="text-[11px] text-slate-500">Scoped Department Access</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-900 block mb-0.5">Viewer</span>
              <span className="text-[11px] text-slate-500">Read-Only Telemetry Oversight</span>
            </div>
          </div>
        </div>

        <AdminLoginModal
          isOpen={isLoginOpen}
          initialRoleTab={loginRoleTab}
          onClose={() => setIsLoginOpen(false)}
        />
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-100 font-sans">
      {/* 1. Left SaaS Sidebar */}
      <AdminSidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        isDepartmentStaff={isDepartmentStaff}
        canManageUsers={canManageUsers}
        user={user}
        onLogout={() => logout()}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* 2. Main Workspace Layout */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* SaaS Top App Bar */}
        <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between shrink-0 shadow-xs z-20">
          <div className="flex items-center space-x-3 min-w-0">
            {/* Mobile Sidebar Hamburger */}
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="md:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              aria-label="Open sidebar menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Breadcrumb & Section Title */}
            <div className="flex items-center space-x-2 text-xs truncate">
              <span className="font-semibold text-slate-400 hidden sm:inline">
                {isDepartmentStaff ? 'Staff Portal' : 'Admin Console'}
              </span>
              <span className="text-slate-300 hidden sm:inline">/</span>
              <span className="font-bold text-slate-900 truncate">
                {tabTitles[activeTab]}
              </span>
            </div>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center space-x-3 shrink-0">
            <span className="hidden lg:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-600" />
              Verified Circulars AY 2025-2026
            </span>

            <Link
              to="/"
              className="hidden sm:inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl transition-all shadow-xs"
              title="Open Student Chatbot (Live Public View)"
            >
              <Bot className="w-3.5 h-3.5 text-emerald-600" />
              <span>Student Chatbot</span>
              <ExternalLink className="w-3 h-3 text-slate-400 ml-0.5" />
            </Link>

            {/* Quick Profile Badge */}
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-bold text-slate-900 leading-tight truncate max-w-[120px]">
                  {user?.full_name}
                </span>
                <span className="text-[10px] text-brand-700 font-mono font-semibold">
                  {user?.role}
                </span>
              </div>
              <button
                onClick={() => logout()}
                title="Sign Out"
                aria-label="Sign Out"
                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* 3. Main Scrollable Workspace Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          <div className="max-w-7xl mx-auto">
            {activeTab === 'overview' && <OverviewSection />}
            {activeTab === 'tickets' && <TicketsSection />}
            {activeTab === 'documents' && <DocumentsSection />}
            {activeTab === 'knowledge-gaps' && (
              <KnowledgeGapsSection onAddressGap={() => handleTabChange('documents')} />
            )}
            {activeTab === 'users' && <UserManagementSection />}
            {activeTab === 'config' && <ConfigSection />}
            {activeTab === 'monitoring' && <MonitoringSection />}
          </div>
        </main>
      </div>
    </div>
  );
};


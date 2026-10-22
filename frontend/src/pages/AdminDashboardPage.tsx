import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  LayoutDashboard,
  Ticket,
  FileText,
  HelpCircle,
  Users,
  Settings,
  Activity,
  LogOut,
  Shield,
  Building,
  Lock,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AdminLoginModal } from '../components/AdminLoginModal';
import { OverviewSection } from '../components/admin/OverviewSection';
import { DocumentsSection } from '../components/admin/DocumentsSection';
import { KnowledgeGapsSection } from '../components/admin/KnowledgeGapsSection';
import { UserManagementSection } from '../components/admin/UserManagementSection';
import { ConfigSection } from '../components/admin/ConfigSection';
import { MonitoringSection } from '../components/admin/MonitoringSection';
import { TicketsSection } from '../components/admin/TicketsSection';

type AdminTab = 'overview' | 'tickets' | 'documents' | 'knowledge-gaps' | 'users' | 'config' | 'monitoring';

interface AdminDashboardPageProps {
  defaultTab?: AdminTab;
  enforceRole?: 'staff' | 'admin';
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ defaultTab, enforceRole }) => {
  const { user, isAuthenticated, isLoading, logout, canManageUsers, isDepartmentStaff } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // For department staff, default to 'tickets' instead of 'overview'
  const computedDefaultTab = defaultTab || (isDepartmentStaff ? 'tickets' : 'overview');
  const initialTab = (searchParams.get('tab') as AdminTab) || computedDefaultTab;
  const [activeTab, setActiveTab] = useState<AdminTab>(initialTab);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [loginRoleTab, setLoginRoleTab] = useState<'staff' | 'admin'>('staff');

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

  // Dedicated navigation tabs per role
  const navItems = isDepartmentStaff
    ? [
        { id: 'tickets', label: 'Department Support Tickets', icon: Ticket },
        { id: 'documents', label: 'Document Library', icon: FileText },
      ]
    : [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'tickets', label: 'Support Tickets', icon: Ticket },
        { id: 'documents', label: 'Document Management', icon: FileText },
        { id: 'knowledge-gaps', label: 'Knowledge Gaps', icon: HelpCircle },
        { id: 'users', label: 'Staff Accounts', icon: Users, locked: !canManageUsers },
        { id: 'config', label: 'Configuration', icon: Settings },
        { id: 'monitoring', label: 'Monitoring & Latency', icon: Activity },
      ];

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-500 font-medium">Validating institutional credentials...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 animate-fadeIn">
        <div className="bg-white rounded-3xl border border-slate-200 p-8 sm:p-12 shadow-xl text-center space-y-6">
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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 animate-fadeIn">
      {/* Staff Session Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white flex items-center justify-center font-bold text-base shadow shrink-0">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'S'}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-900 text-sm sm:text-base">{user?.full_name}</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-brand-50 text-brand-700 border border-brand-200">
                <Shield className="w-3 h-3 mr-1" />
                {user?.role}
              </span>
            </div>
            <div className="flex items-center space-x-3 text-xs text-slate-500 mt-0.5">
              <span>{user?.email}</span>
              {user?.department_name && (
                <span className="flex items-center text-slate-600">
                  <Building className="w-3.5 h-3.5 mr-1 text-slate-400 shrink-0" />
                  {user.department_name}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 self-end md:self-center">
          <button
            onClick={() => logout()}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 border border-rose-200 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>


      {/* Navigation Tabs Bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-1.5 shadow-card overflow-x-auto">
        <nav className="flex space-x-1 min-w-max">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleTabChange(item.id as AdminTab)}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
                {item.locked && (
                  <span className="ml-1 text-[10px] opacity-75">
                    <Lock className="w-3 h-3 inline" />
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Main Tab Content */}
      <div className="min-h-[500px]">
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
    </div>
  );
};

import React from 'react';
import { Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Ticket,
  FileText,
  HelpCircle,
  Users,
  Settings,
  Activity,
  LogOut,
  Lock,
  Bot,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  LucideIcon,
} from 'lucide-react';
import { StaffUser } from '../../types';

export type AdminTab = 'overview' | 'tickets' | 'documents' | 'knowledge-gaps' | 'users' | 'config' | 'monitoring';

interface NavItem {
  id: AdminTab;
  label: string;
  icon: LucideIcon;
  badge?: string;
  locked?: boolean;
}

interface NavGroup {
  groupTitle: string;
  items: NavItem[];
}

interface AdminSidebarProps {
  activeTab: AdminTab;
  onTabChange: (tab: AdminTab) => void;
  isDepartmentStaff: boolean;
  canManageUsers: boolean;
  user: StaffUser | null;
  onLogout: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const AdminSidebar: React.FC<AdminSidebarProps> = ({
  activeTab,
  onTabChange,
  isDepartmentStaff,
  canManageUsers,
  user,
  onLogout,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  // Categorized SaaS Navigation Menus
  const navGroups: NavGroup[] = isDepartmentStaff
    ? [
        {
          groupTitle: 'Department Operations',
          items: [
            { id: 'tickets', label: 'Department Tickets', icon: Ticket },
            { id: 'documents', label: 'Circular Library', icon: FileText },
          ],
        },
      ]
    : [
        {
          groupTitle: 'Core Management',
          items: [
            { id: 'overview', label: 'Overview Metrics', icon: LayoutDashboard },
            { id: 'tickets', label: 'Support Tickets', icon: Ticket },
            { id: 'documents', label: 'Document Repository', icon: FileText },
          ],
        },
        {
          groupTitle: 'AI & Observability',
          items: [
            { id: 'knowledge-gaps', label: 'Knowledge Gaps', icon: HelpCircle },
            { id: 'monitoring', label: 'Latency & Telemetry', icon: Activity },
          ],
        },
        {
          groupTitle: 'Administration',
          items: [
            { id: 'users', label: 'Staff Accounts', icon: Users, locked: !canManageUsers },
            { id: 'config', label: 'System Configuration', icon: Settings },
          ],
        },
      ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-slate-900 text-slate-300 border-r border-slate-800 select-none">
      {/* 1. SaaS Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80">
        <Link
          to={isDepartmentStaff ? '/staff' : '/admin'}
          className="flex items-center space-x-3 overflow-hidden group"
          title="College AI Help Desk SaaS Portal"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-500 to-indigo-600 flex items-center justify-center text-white shadow-md shrink-0 group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-bold text-white tracking-tight leading-tight truncate">
                College AI Portal
              </span>
              <span className="text-[10px] text-emerald-400 font-mono tracking-wide uppercase font-semibold">
                {isDepartmentStaff ? 'Staff Workspace' : 'Admin Console'}
              </span>
            </div>
          )}
        </Link>

        {/* Desktop Collapse Toggle */}
        <button
          onClick={onToggleCollapse}
          className="hidden md:flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* 2. Categorized Menu Navigation */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-thin scrollbar-thumb-slate-700">
        {navGroups.map((group, groupIdx) => (
          <div key={groupIdx} className="space-y-1">
            {!isCollapsed && (
              <h3 className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                {group.groupTitle}
              </h3>
            )}
            <nav className="space-y-1" aria-label={group.groupTitle}>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      if (item.locked) return;
                      onTabChange(item.id);
                      onCloseMobile();
                    }}
                    disabled={item.locked}
                    title={isCollapsed ? item.label : undefined}
                    className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all relative ${
                      isActive
                        ? 'bg-brand-600 text-white shadow-sm'
                        : item.locked
                        ? 'text-slate-400 opacity-60 cursor-not-allowed'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/80'
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                    {!isCollapsed && <span className="truncate flex-1 text-left">{item.label}</span>}
                    {!isCollapsed && item.locked && (
                      <Lock className="w-3 h-3 text-slate-400 ml-auto shrink-0" />
                    )}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-white rounded-r-full" />
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        ))}

        {/* Public Interface Quick Links */}
        <div className="space-y-1 pt-2 border-t border-slate-800">
          {!isCollapsed && (
            <h3 className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Public Portal
            </h3>
          )}
          <nav className="space-y-1">
            <Link
              to="/"
              className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800/80 transition-all group"
              title={isCollapsed ? 'Student Chatbot Preview' : undefined}
            >
              <Bot className="w-4 h-4 text-emerald-400 shrink-0 group-hover:scale-110 transition-transform" />
              {!isCollapsed && (
                <>
                  <span className="truncate flex-1 text-left">Student Chatbot</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </>
              )}
            </Link>
            <Link
              to="/tickets"
              className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800/80 transition-all group"
              title={isCollapsed ? 'Student Ticket Tracker' : undefined}
            >
              <Ticket className="w-4 h-4 text-brand-400 shrink-0 group-hover:scale-110 transition-transform" />
              {!isCollapsed && (
                <>
                  <span className="truncate flex-1 text-left">Public Ticket Tracker</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </>
              )}
            </Link>
          </nav>
        </div>
      </div>

      {/* 3. Bottom Session Profile & Sign Out */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-brand-500 text-white flex items-center justify-center font-bold text-xs shadow shrink-0">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            {!isCollapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-white truncate leading-tight">
                  {user?.full_name || 'Authenticated User'}
                </p>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <span className="text-[10px] text-brand-300 font-mono font-semibold">
                    {user?.role}
                  </span>
                  {user?.department_name && (
                    <span className="text-[9px] text-slate-400 truncate max-w-[80px]">
                      • {user.department_name}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          <button
            onClick={onLogout}
            className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors shrink-0"
            title="Sign Out"
            aria-label="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={`hidden md:flex flex-col flex-shrink-0 transition-all duration-300 z-30 ${
          isCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-slate-950/70 z-40 md:hidden backdrop-blur-xs animate-fadeIn"
          onClick={onCloseMobile}
        />
      )}

      {/* Mobile Drawer */}
      <div
        className={`fixed inset-y-0 left-0 w-72 z-50 md:hidden transition-transform duration-300 transform ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </div>
    </>
  );
};

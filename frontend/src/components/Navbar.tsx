import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Bot,
  FileText,
  Ticket,
  LayoutDashboard,
  ShieldCheck,
  UserCheck,
  Shield,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AdminLoginModal } from './AdminLoginModal';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navLinks = [
    { to: '/', label: 'Public Chatbot', icon: Bot },
    { to: '/tickets', label: 'Support Tickets', icon: Ticket },
    { to: '/admin/documents', label: 'Document Library', icon: FileText },
    { to: '/admin', label: 'Admin Dashboard', icon: LayoutDashboard },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand Name */}
          <div className="flex items-center">
            <Link
              to="/"
              onClick={() => setIsMobileMenuOpen(false)}
              className="flex items-center space-x-3 group"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-500 flex items-center justify-center text-white shadow-sm shrink-0 group-hover:scale-105 transition-transform">
                <Bot className="w-5 h-5" />
              </div>
              <div className="flex flex-col justify-center">
                <span className="text-base font-bold tracking-tight text-slate-900 leading-tight">
                  College AI Help Desk
                </span>
                <span className="text-[11px] text-slate-500 font-medium leading-none mt-0.5">
                  Academic Regulations & Student Portal
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1" aria-label="Main Navigation">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-brand-600' : 'text-slate-400'}`} />
                  <span className="whitespace-nowrap">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Action Area */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            <span className="hidden lg:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-600 shrink-0" />
              Verified Circulars
            </span>

            {isAuthenticated ? (
              <div className="hidden sm:flex items-center space-x-2">
                <Link
                  to="/admin"
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100 text-xs font-semibold text-slate-800 transition-colors"
                >
                  <Shield className="w-3.5 h-3.5 text-brand-600 shrink-0" />
                  <span className="max-w-[120px] truncate">{user?.full_name}</span>
                  <span className="text-[10px] text-brand-700 bg-brand-100/60 px-1.5 py-0.5 rounded font-mono">
                    {user?.role}
                  </span>
                </Link>
                <button
                  onClick={() => logout()}
                  title="Sign Out"
                  aria-label="Sign Out"
                  className="p-1.5 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsLoginModalOpen(true)}
                className="hidden sm:inline-flex items-center space-x-1.5 text-xs font-semibold bg-brand-600 hover:bg-brand-700 active:scale-95 text-white px-3.5 py-2 rounded-xl shadow-xs transition-all"
              >
                <UserCheck className="w-3.5 h-3.5 shrink-0" />
                <span>Staff Login</span>
              </button>
            )}

            {/* Mobile Menu Hamburger Toggle */}
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen((prev) => !prev)}
              aria-expanded={isMobileMenuOpen}
              aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
              className="md:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-5 space-y-2 shadow-lg animate-fadeIn">
          <nav className="space-y-1" aria-label="Mobile Navigation">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 border border-brand-100'
                      : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-brand-600' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="pt-3 border-t border-slate-100 flex flex-col space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500 px-1 py-1">
              <span className="flex items-center text-emerald-700 font-medium">
                <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                Verified Circulars
              </span>
              <span className="text-[11px] bg-slate-100 px-2 py-0.5 rounded text-slate-600">AY 2025-2026</span>
            </div>

            {isAuthenticated ? (
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex items-center space-x-2">
                  <Shield className="w-4 h-4 text-brand-600" />
                  <span className="text-xs font-semibold text-slate-800">{user?.full_name}</span>
                  <span className="text-[10px] text-brand-700 bg-brand-100/60 px-1.5 py-0.5 rounded font-mono">
                    {user?.role}
                  </span>
                </div>
                <button
                  onClick={() => {
                    logout();
                    setIsMobileMenuOpen(false);
                  }}
                  className="text-xs font-semibold text-rose-600 hover:text-rose-700 px-2 py-1 rounded hover:bg-rose-50"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  setIsLoginModalOpen(true);
                  setIsMobileMenuOpen(false);
                }}
                className="w-full flex items-center justify-center space-x-2 text-sm font-semibold bg-brand-600 hover:bg-brand-700 text-white py-2.5 rounded-xl shadow-sm transition-all"
              >
                <UserCheck className="w-4 h-4" />
                <span>Staff & Administrator Sign In</span>
              </button>
            )}
          </div>
        </div>
      )}

      <AdminLoginModal isOpen={isLoginModalOpen} onClose={() => setIsLoginModalOpen(false)} />
    </header>
  );
};

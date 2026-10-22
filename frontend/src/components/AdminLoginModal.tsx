import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, ShieldAlert, KeyRound, CheckCircle2, UserCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface AdminLoginModalProps {
  isOpen: boolean;
  onClose?: () => void;
  onSuccess?: () => void;
}

export const AdminLoginModal: React.FC<AdminLoginModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const navigate = useNavigate();
  const { login, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [validationError, setValidationError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError('');

    if (!email.trim()) {
      setValidationError('Institutional email is required.');
      return;
    }
    if (!password) {
      setValidationError('Password is required.');
      return;
    }

    const success = await login(email.trim(), password);
    if (success) {
      if (onSuccess) onSuccess();
      if (onClose) onClose();
      navigate('/admin');
    }
  };

  const handleDemoFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setValidationError('');
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-slate-200 transform transition-all animate-fadeIn">
        <div className="flex items-center space-x-3 pb-4 border-b border-slate-100">
          <div className="w-12 h-12 rounded-xl bg-brand-50 text-brand-700 flex items-center justify-center font-bold">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Staff Portal Authentication</h2>
            <p className="text-xs text-slate-500">Sign in with your verified institutional credentials</p>
          </div>
        </div>

        {/* Demo Fast-Login Selector */}
        <div className="mt-4 bg-slate-50 border border-slate-200 rounded-xl p-3">
          <div className="text-xs font-semibold text-slate-700 flex items-center space-x-1.5 mb-2">
            <UserCheck className="w-4 h-4 text-brand-600" />
            <span>Select Staff Role for Quick Access:</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => handleDemoFill('admin@college.edu', 'DevAdminSecret123#!')}
              className="text-left px-2.5 py-1.5 bg-white hover:bg-brand-50 border border-slate-200 hover:border-brand-300 rounded-lg transition-all"
            >
              <div className="font-bold text-slate-900">Super Admin</div>
              <div className="text-[10px] text-slate-500">Universal RBAC privileges</div>
            </button>
            <button
              type="button"
              onClick={() => handleDemoFill('dean_admin@college.edu', 'DeanAdminSecret123#!')}
              className="text-left px-2.5 py-1.5 bg-white hover:bg-brand-50 border border-slate-200 hover:border-brand-300 rounded-lg transition-all"
            >
              <div className="font-bold text-slate-900">Admin (Dean)</div>
              <div className="text-[10px] text-slate-500">Upload & approve circulars</div>
            </button>
            <button
              type="button"
              onClick={() => handleDemoFill('staff_hostel@college.edu', 'StaffSecret123#!')}
              className="text-left px-2.5 py-1.5 bg-white hover:bg-brand-50 border border-slate-200 hover:border-brand-300 rounded-lg transition-all"
            >
              <div className="font-bold text-slate-900">Hostel Staff</div>
              <div className="text-[10px] text-slate-500">Department-scoped access</div>
            </button>
            <button
              type="button"
              onClick={() => handleDemoFill('auditor_viewer@college.edu', 'ViewerSecret123#!')}
              className="text-left px-2.5 py-1.5 bg-white hover:bg-brand-50 border border-slate-200 hover:border-brand-300 rounded-lg transition-all"
            >
              <div className="font-bold text-slate-900">Viewer / Auditor</div>
              <div className="text-[10px] text-slate-500">Read-only oversight</div>
            </button>
          </div>
        </div>

        {/* Error Banners */}
        {(validationError || error) && (
          <div className="mt-4 bg-rose-50 border border-rose-200 rounded-xl p-3.5 flex items-start space-x-2.5 text-xs text-rose-800 animate-shake">
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <span>{validationError || error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Staff Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="staff@college.edu"
                className="w-full pl-9 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <div className="relative">
              <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-9 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
                required
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between">
            {onClose ? (
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
              >
                Cancel
              </button>
            ) : <span />}

            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold shadow-md transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Sign In to Dashboard</span>
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-100 text-[11px] text-slate-500 text-center">
          Backend-enforced Role-Based Access Control (RBAC). Session tokens are cryptographically validated by FastAPI on every request.
        </div>
      </div>
    </div>
  );
};

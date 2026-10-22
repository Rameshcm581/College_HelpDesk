import React from 'react';
import { DocumentsSection } from '../components/admin/DocumentsSection';
import { useAuth } from '../context/AuthContext';
import { AdminLoginModal } from '../components/AdminLoginModal';
import { Lock, UserCheck } from 'lucide-react';

export const DocumentsPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = React.useState(false);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-500 font-medium">Validating credentials...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center animate-fadeIn">
        <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-xl space-y-5">
          <div className="w-14 h-14 bg-brand-50 text-brand-600 rounded-2xl flex items-center justify-center mx-auto">
            <Lock className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Institutional Document Repository</h2>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Managing and auditing verified college circulars and syllabi requires staff authentication.
          </p>
          <button
            onClick={() => setIsLoginOpen(true)}
            className="inline-flex items-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold shadow-md transition-all"
          >
            <UserCheck className="w-4 h-4" />
            <span>Sign In to Access Repository</span>
          </button>
        </div>
        <AdminLoginModal isOpen={isLoginOpen} onClose={() => setIsLoginOpen(false)} />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <DocumentsSection />
    </div>
  );
};

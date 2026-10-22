import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
        <div>
          © 2026 College AI Help Desk Platform. Built for verified institutional knowledge retrieval.
        </div>
        <div className="mt-2 sm:mt-0 flex space-x-4">
          <span>Bilingual: English & தமிழ்</span>
          <span>•</span>
          <span>Zero Hallucination Policy</span>
          <span>•</span>
          <span>SLA: 99.5%</span>
        </div>
      </div>
    </footer>
  );
};

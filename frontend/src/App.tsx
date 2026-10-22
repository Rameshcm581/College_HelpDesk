import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { PublicChatbotPage } from './pages/PublicChatbotPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { TicketsPage } from './pages/TicketsPage';
import { ChatbotWidget } from './components/ChatbotWidget';

const WidgetFrameRoute: React.FC = () => {
  return (
    <div className="w-full h-full min-h-screen bg-transparent flex flex-col justify-end p-2 sm:p-4">
      <ChatbotWidget isStandaloneFrame={false} />
    </div>
  );
};

const MainLayout: React.FC = () => {
  const location = useLocation();
  const isWidgetRoute = location.pathname.startsWith('/widget');

  if (isWidgetRoute) {
    return <WidgetFrameRoute />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 relative">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<PublicChatbotPage />} />
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/admin/documents" element={<DocumentsPage />} />
          <Route path="/staff" element={<AdminDashboardPage defaultTab="tickets" enforceRole="staff" />} />
          <Route path="/staff/documents" element={<DocumentsPage />} />
          <Route path="/tickets" element={<TicketsPage />} />
        </Routes>
      </main>
      <Footer />
      {/* Floating Widget available across portal except when on dedicated full-page chatbot */}
      {location.pathname !== '/' && <ChatbotWidget />}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <MainLayout />
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;

import React, { createContext, useContext, useEffect, useState } from 'react';
import { fetchCurrentUser, loginStaff, logoutStaff, setStoredToken, getStoredToken } from '../services/api';
import { StaffUser } from '../types';

interface AuthContextType {
  user: StaffUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  isSuperAdmin: boolean;
  isAdmin: boolean;
  isDepartmentStaff: boolean;
  isViewer: boolean;
  canManageUsers: boolean;
  canUploadDocs: boolean;
  canApproveDocs: boolean;
  canEditConfig: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<StaffUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const initAuth = async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await fetchCurrentUser();
      setUser(userData);
      setError(null);
    } catch (err) {
      console.warn('Initial session validation failed:', err);
      setStoredToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await loginStaff(email, password);
      setUser(result.user);
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Invalid login credentials.';
      setError(message);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await logoutStaff();
    } catch (err) {
      console.warn('Logout API call error:', err);
    } finally {
      setUser(null);
      setError(null);
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    try {
      const userData = await fetchCurrentUser();
      setUser(userData);
    } catch {
      setUser(null);
    }
  };

  const role = user?.role;
  const isSuperAdmin = role === 'SUPER_ADMIN';
  const isAdmin = isSuperAdmin || role === 'ADMIN' || role === 'CONTENT_APPROVER';
  const isDepartmentStaff = role === 'DEPARTMENT_STAFF' || role === 'SUPPORT_AGENT';
  const isViewer = role === 'VIEWER' || role === 'AUDITOR';

  const canManageUsers = isSuperAdmin;
  const canUploadDocs = isSuperAdmin || isAdmin;
  const canApproveDocs = isSuperAdmin || isAdmin;
  const canEditConfig = isSuperAdmin || isAdmin;

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        error,
        login,
        logout,
        refreshUser,
        isSuperAdmin,
        isAdmin,
        isDepartmentStaff,
        isViewer,
        canManageUsers,
        canUploadDocs,
        canApproveDocs,
        canEditConfig,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

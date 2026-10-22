import React, { useEffect, useState } from 'react';
import {
  UserPlus,
  Shield,
  Building,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
  Edit2,
  Trash2,
  UserCheck,
  UserX,
} from 'lucide-react';
import {
  createAdminUser,
  deactivateAdminUser,
  fetchAdminMetadata,
  fetchAdminUsers,
  updateAdminUser,
} from '../../services/api';
import { AdminMetadata, StaffUser, UserRole } from '../../types';
import { ConfirmationModal } from '../ConfirmationModal';
import { useAuth } from '../../context/AuthContext';

export const UserManagementSection: React.FC = () => {
  const { user: currentUser, canManageUsers } = useAuth();
  const [users, setUsers] = useState<StaffUser[]>([]);
  const [metadata, setMetadata] = useState<AdminMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add User Modal
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [addName, setAddName] = useState('');
  const [addEmail, setAddEmail] = useState('');
  const [addPassword, setAddPassword] = useState('');
  const [addRole, setAddRole] = useState<UserRole>('DEPARTMENT_STAFF');
  const [addDept, setAddDept] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Edit User Modal
  const [editTarget, setEditTarget] = useState<StaffUser | null>(null);
  const [editName, setEditName] = useState('');
  const [editRole, setEditRole] = useState<UserRole>('DEPARTMENT_STAFF');
  const [editDept, setEditDept] = useState<string>('');
  const [editActive, setEditActive] = useState(true);
  const [editPassword, setEditPassword] = useState('');

  // Deactivate confirmation
  const [deactivateTarget, setDeactivateTarget] = useState<StaffUser | null>(null);

  const loadData = async () => {
    if (!canManageUsers) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const [userList, meta] = await Promise.all([
        fetchAdminUsers(),
        fetchAdminMetadata(),
      ]);
      setUsers(userList);
      setMetadata(meta);
      if (meta.departments.length > 0 && !addDept) {
        setAddDept(meta.departments[0].id);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load staff users.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [canManageUsers]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!addName.trim() || !addEmail.trim() || !addPassword) {
      setFormError('Full name, email, and password are required.');
      return;
    }

    if (addRole === 'DEPARTMENT_STAFF' && !addDept) {
      setFormError('Department Staff role requires an assigned department.');
      return;
    }

    setActionLoading(true);
    try {
      await createAdminUser({
        full_name: addName.trim(),
        email: addEmail.trim(),
        password: addPassword,
        role: addRole,
        department_id: addDept || null,
      });

      setIsAddOpen(false);
      setAddName('');
      setAddEmail('');
      setAddPassword('');
      loadData();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'User creation failed.';
      setFormError(message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleEditOpen = (u: StaffUser) => {
    setEditTarget(u);
    setEditName(u.full_name);
    setEditRole(u.role);
    setEditDept(u.department_id || '');
    setEditActive(u.is_active);
    setEditPassword('');
    setFormError(null);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editTarget) return;

    setActionLoading(true);
    try {
      await updateAdminUser(editTarget.id, {
        full_name: editName.trim(),
        role: editRole,
        department_id: editDept || null,
        is_active: editActive,
        password: editPassword ? editPassword : undefined,
      });

      setEditTarget(null);
      loadData();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'User update failed.';
      setFormError(message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDeactivate = async () => {
    if (!deactivateTarget) return;
    setActionLoading(true);
    try {
      await deactivateAdminUser(deactivateTarget.id);
      setDeactivateTarget(null);
      loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Deactivation failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Role Badge Helper
  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'SUPER_ADMIN':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'ADMIN':
      case 'CONTENT_APPROVER':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'DEPARTMENT_STAFF':
      case 'SUPPORT_AGENT':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'VIEWER':
      case 'AUDITOR':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  if (!canManageUsers) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 space-y-3 animate-fadeIn">
        <div className="flex items-center space-x-2 text-amber-900 font-bold">
          <Lock className="w-5 h-5 text-amber-600" />
          <span>Role-Based Access Control Notice</span>
        </div>
        <p className="text-xs text-amber-800 leading-relaxed">
          Staff User Management is strictly restricted to the <strong>SUPER_ADMIN</strong> role. 
          Your currently authenticated role is <strong>{currentUser?.role || 'VIEWER'}</strong>. 
          The backend enforces this restriction with <code>403 Forbidden</code> response checks.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Staff Account & Role Management</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage institutional staff accounts, assign granular RBAC roles, and enforce departmental data boundaries.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3 py-2 rounded-xl shadow-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => {
              setIsAddOpen(true);
              setFormError(null);
            }}
            className="inline-flex items-center space-x-1.5 bg-brand-600 hover:bg-brand-700 text-white px-3.5 py-2 rounded-xl text-xs font-semibold shadow-sm transition-all"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Staff Account</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 flex items-center space-x-2 text-xs text-rose-800">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-brand-600 mb-2" />
            <span>Loading user accounts from PostgreSQL...</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 tracking-wider">
                <tr>
                  <th className="px-5 py-3">Staff Name & Email</th>
                  <th className="px-5 py-3">Assigned Role</th>
                  <th className="px-5 py-3">Department Boundary</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Created</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="font-bold text-slate-900">{u.full_name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{u.email}</div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${getRoleBadge(u.role)}`}>
                        <Shield className="w-3 h-3 mr-1" />
                        {u.role}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center text-slate-600">
                        <Building className="w-3.5 h-3.5 mr-1 text-slate-400" />
                        {u.department_name || (u.role === 'SUPER_ADMIN' ? 'Universal Campus' : 'General')}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      {u.is_active ? (
                        <span className="inline-flex items-center text-emerald-700 font-semibold">
                          <UserCheck className="w-3.5 h-3.5 mr-1" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center text-slate-400 font-semibold">
                          <UserX className="w-3.5 h-3.5 mr-1" />
                          Deactivated
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 font-mono text-[11px]">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-2">
                      <button
                        onClick={() => handleEditOpen(u)}
                        className="text-brand-600 hover:text-brand-800 font-semibold inline-flex items-center space-x-1"
                        title="Edit Account Details"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        <span>Edit</span>
                      </button>

                      {u.is_active && u.id !== currentUser?.id && (
                        <button
                          onClick={() => setDeactivateTarget(u)}
                          className="text-rose-600 hover:text-rose-800 font-semibold inline-flex items-center space-x-1"
                          title="Deactivate Account"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Deactivate</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── MODAL: ADD STAFF ACCOUNT ────────────────────────────────────────── */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Provision New Staff Account</h3>
              <button
                onClick={() => setIsAddOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            {formError && (
              <div className="mt-3 bg-rose-50 border border-rose-200 rounded-xl p-2.5 text-xs text-rose-800">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  placeholder="e.g. Dr. Priya Sundaram"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Email Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  value={addEmail}
                  onChange={(e) => setAddEmail(e.target.value)}
                  placeholder="priya.s@college.edu"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Initial Password <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  value={addPassword}
                  onChange={(e) => setAddPassword(e.target.value)}
                  placeholder="Min 8 characters"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Role</label>
                  <select
                    value={addRole}
                    onChange={(e) => setAddRole(e.target.value as UserRole)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    <option value="DEPARTMENT_STAFF">Department Staff</option>
                    <option value="ADMIN">Admin</option>
                    <option value="VIEWER">Viewer</option>
                    <option value="SUPER_ADMIN">Super Admin</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Department</label>
                  <select
                    value={addDept}
                    onChange={(e) => setAddDept(e.target.value)}
                    disabled={addRole === 'SUPER_ADMIN'}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                  >
                    <option value="">Campus-Wide / None</option>
                    {metadata?.departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-3.5 py-2 text-slate-600 hover:text-slate-800 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-1.5 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-xl font-semibold shadow-sm disabled:opacity-50"
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <UserPlus className="w-3.5 h-3.5" />}
                  <span>Create Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: EDIT STAFF ACCOUNT ───────────────────────────────────────── */}
      {editTarget && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Edit Staff Account: {editTarget.email}</h3>
              <button
                onClick={() => setEditTarget(null)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            {formError && (
              <div className="mt-3 bg-rose-50 border border-rose-200 rounded-xl p-2.5 text-xs text-rose-800">
                {formError}
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="mt-4 space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Role</label>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value as UserRole)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    <option value="DEPARTMENT_STAFF">Department Staff</option>
                    <option value="ADMIN">Admin</option>
                    <option value="VIEWER">Viewer</option>
                    <option value="SUPER_ADMIN">Super Admin</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Department</label>
                  <select
                    value={editDept}
                    onChange={(e) => setEditDept(e.target.value)}
                    disabled={editRole === 'SUPER_ADMIN'}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                  >
                    <option value="">Campus-Wide / None</option>
                    {metadata?.departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Reset Password (leave blank to keep unchanged)</label>
                <input
                  type="password"
                  value={editPassword}
                  onChange={(e) => setEditPassword(e.target.value)}
                  placeholder="New password (optional)"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="editActive"
                  checked={editActive}
                  onChange={(e) => setEditActive(e.target.checked)}
                  className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500 border-slate-300"
                />
                <label htmlFor="editActive" className="font-semibold text-slate-700">
                  Account is Active (can authenticate)
                </label>
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setEditTarget(null)}
                  className="px-3.5 py-2 text-slate-600 hover:text-slate-800 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-1.5 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-xl font-semibold shadow-sm disabled:opacity-50"
                >
                  {actionLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Deactivation */}
      <ConfirmationModal
        isOpen={!!deactivateTarget}
        title="Deactivate Staff Account?"
        message={`Are you sure you want to deactivate ${deactivateTarget?.full_name} (${deactivateTarget?.email})? They will no longer be able to log in to the administrative portal.`}
        confirmLabel="Deactivate User"
        confirmVariant="danger"
        isLoading={actionLoading}
        onConfirm={handleConfirmDeactivate}
        onCancel={() => setDeactivateTarget(null)}
      />
    </div>
  );
};

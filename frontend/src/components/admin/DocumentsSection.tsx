import React, { useEffect, useState } from 'react';
import {
  FileUp,
  Search,
  Calendar,
  Building,
  Layers,
  Eye,
  CheckCircle,
  XCircle,
  Archive,
  RefreshCw,
  AlertCircle,
  Download,
  FileText,
  UploadCloud,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import {
  approveDocumentVersion,
  archiveDocument,
  fetchAdminMetadata,
  fetchDocumentDetail,
  fetchDocuments,
  previewDocumentVersion,
  rejectDocumentVersion,
  replaceDocumentVersion,
  uploadDocumentFile,
} from '../../services/api';
import {
  AdminMetadata,
  DocumentDetail,
  DocumentVersionDetail,
  InstitutionalDocument,
} from '../../types';
import { StatusBadge } from '../StatusBadge';
import { ConfirmationModal } from '../ConfirmationModal';
import { useAuth } from '../../context/AuthContext';

export const DocumentsSection: React.FC = () => {
  const { canUploadDocs, canApproveDocs } = useAuth();
  const [documents, setDocuments] = useState<InstitutionalDocument[]>([]);
  const [metadata, setMetadata] = useState<AdminMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedYear, setSelectedYear] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');

  // Modals
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isReplaceOpen, setIsReplaceOpen] = useState(false);
  const [targetReplaceDoc, setTargetReplaceDoc] = useState<InstitutionalDocument | null>(null);

  // Preview Modal
  const [previewData, setPreviewData] = useState<DocumentVersionDetail | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Detail Modal (Versions)
  const [detailData, setDetailData] = useState<DocumentDetail | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // Action Confirmation Modals
  const [confirmApprove, setConfirmApprove] = useState<{ docId: string; versionId: string } | null>(null);
  const [confirmReject, setConfirmReject] = useState<{ docId: string; versionId: string } | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [confirmArchive, setConfirmArchive] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Upload Form State
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadYear, setUploadYear] = useState('2025-2026');
  const [uploadDept, setUploadDept] = useState('GENERAL');
  const [uploadSummary, setUploadSummary] = useState('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const loadDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [docs, meta] = await Promise.all([
        fetchDocuments(selectedStatus),
        fetchAdminMetadata(),
      ]);
      setDocuments(docs);
      setMetadata(meta);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch document repository.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [selectedStatus]);

  // Handlers
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a valid PDF document.');
      return;
    }
    if (!uploadTitle.trim()) {
      setUploadError('Document title is required.');
      return;
    }

    setUploadError(null);
    setActionLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('title', uploadTitle.trim());
      formData.append('academic_year_code', uploadYear);
      formData.append('department_code', uploadDept);
      if (uploadSummary.trim()) {
        formData.append('change_summary', uploadSummary.trim());
      }

      await uploadDocumentFile(formData);
      setUploadSuccess('Document successfully uploaded and queued for background OCR/text extraction!');
      setTimeout(() => {
        setIsUploadOpen(false);
        setUploadSuccess(null);
        setUploadFile(null);
        setUploadTitle('');
        setUploadSummary('');
        loadDocuments();
      }, 1500);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed.';
      setUploadError(message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReplaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetReplaceDoc || !uploadFile) {
      setUploadError('Please select a replacement PDF file.');
      return;
    }
    if (!uploadSummary.trim()) {
      setUploadError('Please specify the revision change summary.');
      return;
    }

    setUploadError(null);
    setActionLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('change_summary', uploadSummary.trim());

      await replaceDocumentVersion(targetReplaceDoc.id, formData);
      setUploadSuccess(`New version staged successfully! Previous active version remains active until approved.`);
      setTimeout(() => {
        setIsReplaceOpen(false);
        setUploadSuccess(null);
        setUploadFile(null);
        setUploadSummary('');
        setTargetReplaceDoc(null);
        loadDocuments();
      }, 1500);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Version replacement failed.';
      setUploadError(message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenPreview = async (docId: string, versionId: string) => {
    setIsPreviewOpen(true);
    setPreviewLoading(true);
    try {
      const data = await previewDocumentVersion(docId, versionId);
      setPreviewData(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load preview.';
      alert(message);
      setIsPreviewOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleOpenVersions = async (docId: string) => {
    setIsDetailOpen(true);
    setDetailLoading(true);
    try {
      const data = await fetchDocumentDetail(docId);
      setDetailData(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load document history.';
      alert(message);
      setIsDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleConfirmApprove = async () => {
    if (!confirmApprove) return;
    setActionLoading(true);
    try {
      await approveDocumentVersion(confirmApprove.docId, confirmApprove.versionId);
      setConfirmApprove(null);
      await loadDocuments();
      if (isDetailOpen && detailData) {
        handleOpenVersions(detailData.id);
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Approval failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmReject = async () => {
    if (!confirmReject) return;
    setActionLoading(true);
    try {
      await rejectDocumentVersion(confirmReject.docId, confirmReject.versionId, rejectReason || 'Document rejected by reviewer');
      setConfirmReject(null);
      setRejectReason('');
      await loadDocuments();
      if (isDetailOpen && detailData) {
        handleOpenVersions(detailData.id);
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Rejection failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!confirmArchive) return;
    setActionLoading(true);
    try {
      await archiveDocument(confirmArchive);
      setConfirmArchive(null);
      await loadDocuments();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Archival failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Filter docs
  const filteredDocs = documents.filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (doc.file_name && doc.file_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (doc.department && doc.department.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesYear = selectedYear === 'ALL' || doc.academic_year === selectedYear;
    return matchesSearch && matchesYear;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header and Upload Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Institutional Document Repository</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage official college circulars, verify extracted text, approve versions, and control the RAG knowledge index.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadDocuments}
            disabled={isLoading}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-3 py-2 rounded-xl shadow-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-brand-600' : ''}`} />
            <span>Refresh</span>
          </button>

          {canUploadDocs ? (
            <button
              onClick={() => setIsUploadOpen(true)}
              className="inline-flex items-center space-x-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-sm transition-all"
            >
              <FileUp className="w-4 h-4" />
              <span>Upload Document</span>
            </button>
          ) : (
            <span className="inline-flex items-center space-x-1 text-xs text-slate-400 bg-slate-100 px-3 py-2 rounded-xl border border-slate-200">
              <Lock className="w-3.5 h-3.5" />
              <span>Read-Only Role</span>
            </span>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-card flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search circulars, department, or file..."
            className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500 flex items-center">
              <Calendar className="w-3.5 h-3.5 mr-1 text-slate-400" />
              Academic Year:
            </span>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="ALL">All Academic Years</option>
              {metadata?.academic_years.map((ay) => (
                <option key={ay.id} value={ay.code}>
                  {ay.code} {ay.is_current ? '(Current)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="PUBLISHED">Published / Active</option>
              <option value="REVIEW_REQUIRED">Review Required</option>
              <option value="UPLOADED">Uploaded / Ingesting</option>
              <option value="ARCHIVED">Archived</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-center space-x-3 text-xs text-rose-800">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Documents Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-slate-500 space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-brand-600" />
            <span>Loading document repository from database...</span>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 space-y-3">
            <FileText className="w-10 h-10 mx-auto text-slate-300" />
            <div className="text-sm font-semibold text-slate-700">No Institutional Documents Found</div>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              No circulars match your current filter criteria. Use the "Upload Document" button above to ingest new PDFs.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 tracking-wider">
                <tr>
                  <th className="px-5 py-3">Document Title & Filename</th>
                  <th className="px-5 py-3">Department</th>
                  <th className="px-5 py-3">Academic Year</th>
                  <th className="px-5 py-3">Chunks</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="font-bold text-slate-900">{doc.title}</div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">{doc.file_name}</div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center text-slate-600">
                        <Building className="w-3.5 h-3.5 mr-1 text-slate-400" />
                        {doc.department}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-800">
                      {doc.academic_year} (v{doc.version_number})
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center text-slate-600 font-mono">
                        <Layers className="w-3.5 h-3.5 mr-1 text-slate-400" />
                        {doc.chunk_count}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-2">
                      {/* View Versions / History */}
                      <button
                        onClick={() => handleOpenVersions(doc.id)}
                        className="text-brand-600 hover:text-brand-800 font-semibold inline-flex items-center space-x-1"
                        title="View Historical Versions & Chunks"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Versions</span>
                      </button>

                      {/* Replace Version (Stage New Version) */}
                      {canUploadDocs && doc.status !== 'ARCHIVED' && (
                        <button
                          onClick={() => {
                            setTargetReplaceDoc(doc);
                            setIsReplaceOpen(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center space-x-1"
                          title="Stage New Version (Keeps Active Version Online)"
                        >
                          <FileUp className="w-3.5 h-3.5" />
                          <span>Replace</span>
                        </button>
                      )}

                      {/* Archive */}
                      {canApproveDocs && doc.status !== 'ARCHIVED' && (
                        <button
                          onClick={() => setConfirmArchive(doc.id)}
                          className="text-rose-600 hover:text-rose-800 font-semibold inline-flex items-center space-x-1"
                          title="Archive Document (Deactivates from RAG)"
                        >
                          <Archive className="w-3.5 h-3.5" />
                          <span>Archive</span>
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

      {/* ── MODAL 1: UPLOAD NEW DOCUMENT ────────────────────────────────────── */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 sm:p-7 shadow-2xl border border-slate-200 animate-fadeIn">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Upload Institutional Circular</h3>
                  <p className="text-xs text-slate-500">PDF will be checked, chunked, and queued for extraction</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsUploadOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            {uploadSuccess && (
              <div className="mt-4 bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center space-x-2 text-xs text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{uploadSuccess}</span>
              </div>
            )}

            {uploadError && (
              <div className="mt-4 bg-rose-50 border border-rose-200 rounded-xl p-3 flex items-center space-x-2 text-xs text-rose-800">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="mt-4 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Document Title <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="e.g. UG Admissions Handbook 2025-2026"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Academic Year</label>
                  <select
                    value={uploadYear}
                    onChange={(e) => setUploadYear(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {metadata?.academic_years.map((ay) => (
                      <option key={ay.id} value={ay.code}>
                        {ay.code} {ay.is_current ? '(Current)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Department</label>
                  <select
                    value={uploadDept}
                    onChange={(e) => setUploadDept(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {metadata?.departments.map((d) => (
                      <option key={d.id} value={d.code}>
                        {d.name} ({d.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Select PDF Document <span className="text-rose-500">*</span>
                </label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl file:mr-3 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
                  required
                />
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Only valid PDF files up to 25MB allowed. Magic header verification enabled.
                </span>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Upload Notes / Change Summary</label>
                <input
                  type="text"
                  value={uploadSummary}
                  onChange={(e) => setUploadSummary(e.target.value)}
                  placeholder="e.g. Official syllabus update approved by Academic Council"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-3.5 py-2 text-slate-600 hover:text-slate-800 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-1.5 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-xl font-semibold shadow-sm disabled:opacity-50"
                >
                  {actionLoading ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <FileUp className="w-3.5 h-3.5" />
                  )}
                  <span>Upload & Queue Ingestion</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL 2: REPLACE DOCUMENT VERSION ────────────────────────────────── */}
      {isReplaceOpen && targetReplaceDoc && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 animate-fadeIn">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Stage Replacement Version: {targetReplaceDoc.title}
                </h3>
                <p className="text-xs text-slate-500">Current version: v{targetReplaceDoc.version_number}</p>
              </div>
              <button
                type="button"
                onClick={() => setIsReplaceOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            {uploadSuccess && (
              <div className="mt-4 bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center space-x-2 text-xs text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{uploadSuccess}</span>
              </div>
            )}

            {uploadError && (
              <div className="mt-4 bg-rose-50 border border-rose-200 rounded-xl p-3 flex items-center space-x-2 text-xs text-rose-800">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleReplaceSubmit} className="mt-4 space-y-3.5 text-xs">
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-[11px] text-amber-900">
                Safe Staging: The active version (v{targetReplaceDoc.version_number}) will remain online and answer chatbot queries until this replacement version is extracted, verified, and approved.
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Replacement PDF File <span className="text-rose-500">*</span>
                </label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl file:mr-3 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Revision Reason / Change Summary <span className="text-rose-500">*</span>
                </label>
                <textarea
                  value={uploadSummary}
                  onChange={(e) => setUploadSummary(e.target.value)}
                  placeholder="e.g. Revised exam timetable per Senate circular #42"
                  rows={2}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
                  required
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsReplaceOpen(false)}
                  className="px-3.5 py-2 text-slate-600 hover:text-slate-800 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="inline-flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl font-semibold shadow-sm disabled:opacity-50"
                >
                  {actionLoading ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <FileUp className="w-3.5 h-3.5" />
                  )}
                  <span>Stage Version v{targetReplaceDoc.version_number + 1}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL 3: DOCUMENT VERSION HISTORY & REVIEW ──────────────────────── */}
      {isDetailOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto animate-fadeIn">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Document Version History: {detailData?.title}
                </h3>
                <p className="text-xs text-slate-500">ID: {detailData?.id}</p>
              </div>
              <button
                type="button"
                onClick={() => setIsDetailOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            {detailLoading ? (
              <div className="p-8 text-center text-xs text-slate-500">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-brand-600 mb-2" />
                <span>Loading version records...</span>
              </div>
            ) : detailData?.versions.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500">No versions found.</div>
            ) : (
              <div className="mt-4 space-y-3">
                {detailData?.versions.map((ver) => (
                  <div
                    key={ver.id}
                    className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-900 text-sm">Version {ver.version_number}</span>
                        <StatusBadge status={ver.status} />
                        {detailData.active_version_id === ver.id && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            CURRENTLY ACTIVE IN RAG
                          </span>
                        )}
                      </div>
                      <div className="text-slate-500 font-mono text-[11px]">{ver.file_name}</div>
                      <div className="text-slate-600">
                        Pages: <span className="font-semibold">{ver.page_count}</span> • Chunks:{' '}
                        <span className="font-semibold">{ver.chunk_count}</span> • Created:{' '}
                        <span className="font-semibold">{new Date(ver.created_at).toLocaleDateString()}</span>
                      </div>
                      {ver.change_summary && (
                        <div className="text-[11px] text-slate-500 italic">"{ver.change_summary}"</div>
                      )}
                    </div>

                    <div className="flex items-center space-x-2">
                      {/* Preview Text */}
                      <button
                        onClick={() => handleOpenPreview(detailData.id, ver.id)}
                        className="px-2.5 py-1.5 bg-white border border-slate-200 hover:border-slate-300 rounded-lg text-brand-600 font-semibold inline-flex items-center space-x-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Preview Text</span>
                      </button>

                      {/* Download */}
                      <a
                        href={`/api/v1/admin/documents/${detailData.id}/download?version_number=${ver.version_number}`}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1.5 bg-white border border-slate-200 hover:border-slate-300 rounded-lg text-slate-700 font-semibold inline-flex items-center space-x-1"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download</span>
                      </a>

                      {/* Approve / Reject Actions */}
                      {canApproveDocs && (ver.status === 'REVIEW_REQUIRED' || ver.status === 'UPLOADED') && (
                        <>
                          <button
                            onClick={() => setConfirmApprove({ docId: detailData.id, versionId: ver.id })}
                            className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg inline-flex items-center space-x-1"
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>
                          <button
                            onClick={() => setConfirmReject({ docId: detailData.id, versionId: ver.id })}
                            className="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-lg inline-flex items-center space-x-1"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── MODAL 4: TEXT & CHUNKS PREVIEW ──────────────────────────────────── */}
      {isPreviewOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[85vh] flex flex-col animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">Extracted Content Preview</h3>
                <p className="text-xs text-slate-500 font-mono">
                  {previewData?.file_name} (v{previewData?.version_number})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsPreviewOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="py-2 flex items-center space-x-4 text-xs text-slate-600 border-b border-slate-100">
              <span>Pages: <strong>{previewData?.page_count}</strong></span>
              <span>Vector Chunks: <strong>{previewData?.chunk_count}</strong></span>
              <span>Status: <strong>{previewData?.status}</strong></span>
            </div>

            <div className="flex-1 overflow-y-auto my-3 p-3 bg-slate-50 border border-slate-200 rounded-xl font-mono text-[11px] leading-relaxed text-slate-800 whitespace-pre-wrap">
              {previewLoading ? 'Loading extraction preview...' : previewData?.extracted_text_preview || 'No text extracted.'}
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setIsPreviewOpen(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── CONFIRMATION MODALS ────────────────────────────────────────────── */}
      <ConfirmationModal
        isOpen={!!confirmApprove}
        title="Approve Document Version?"
        message="Approving this version will trigger asynchronous pgvector indexing. Once indexed, the new version will become active and answer public chatbot queries."
        confirmLabel="Approve & Index"
        confirmVariant="primary"
        isLoading={actionLoading}
        onConfirm={handleConfirmApprove}
        onCancel={() => setConfirmApprove(null)}
      />

      {confirmReject && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 animate-fadeIn">
            <h3 className="text-base font-bold text-slate-900">Reject Document Version</h3>
            <p className="text-xs text-slate-600 mt-1">
              Please specify why this extracted document version is being rejected:
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Incomplete scan or outdated fee tables..."
              rows={3}
              className="mt-3 w-full p-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => setConfirmReject(null)}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReject}
                disabled={actionLoading}
                className="px-4 py-2 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-sm"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmationModal
        isOpen={!!confirmArchive}
        title="Archive Institutional Document?"
        message="Archiving will remove this document and all its versions from the public chatbot vector search immediately. Students will no longer receive answers from this circular."
        confirmLabel="Archive Document"
        confirmVariant="danger"
        isLoading={actionLoading}
        onConfirm={handleConfirmArchive}
        onCancel={() => setConfirmArchive(null)}
      />
    </div>
  );
};

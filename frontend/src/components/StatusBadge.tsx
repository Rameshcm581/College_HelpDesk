import React from 'react';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const norm = status.toUpperCase();

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-300';

  if (norm === 'PUBLISHED' || norm === 'HEALTHY' || norm === 'RESOLVED') {
    colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (norm === 'PENDING_REVIEW' || norm === 'IN_PROGRESS' || norm === 'DEGRADED') {
    colorClasses = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (norm === 'ASSIGNED') {
    colorClasses = 'bg-indigo-50 text-indigo-700 border-indigo-200';
  } else if (norm === 'WAITING_FOR_USER') {
    colorClasses = 'bg-orange-50 text-orange-700 border-orange-200';
  } else if (norm === 'DRAFT' || norm === 'OPEN') {
    colorClasses = 'bg-blue-50 text-blue-700 border-blue-200';
  } else if (norm === 'ARCHIVED' || norm === 'UNHEALTHY' || norm === 'CLOSED') {
    colorClasses = 'bg-rose-50 text-rose-700 border-rose-200';
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClasses}`}
    >
      {norm}
    </span>
  );
};

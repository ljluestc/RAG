import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Clock,
  Eye,
  Users,
  CheckCircle2,
  XCircle,
  MessageSquare,
  Calendar,
  MoreVertical,
  ExternalLink,
} from 'lucide-react';
import { applicationsAPI } from '@/services/api';
import { format } from 'date-fns';

const statusColumns = [
  { id: 'PENDING', label: 'Applied', icon: Clock, color: 'bg-gray-500' },
  { id: 'VIEWED', label: 'Viewed', icon: Eye, color: 'bg-blue-500' },
  { id: 'SCREENING', label: 'Screening', icon: MessageSquare, color: 'bg-yellow-500' },
  { id: 'INTERVIEWING', label: 'Interviewing', icon: Users, color: 'bg-purple-500' },
  { id: 'OFFERED', label: 'Offered', icon: CheckCircle2, color: 'bg-green-500' },
  { id: 'REJECTED', label: 'Rejected', icon: XCircle, color: 'bg-red-500' },
];

export default function Applications() {
  const [viewMode, setViewMode] = useState<'board' | 'list'>('board');

  const { data: applications, isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: () => applicationsAPI.getAll(),
  });

  const { data: stats } = useQuery({
    queryKey: ['applications', 'stats'],
    queryFn: () => applicationsAPI.getStats(),
  });

  const groupedApplications = statusColumns.reduce((acc, status) => {
    acc[status.id] = applications?.data?.applications?.filter(
      (app: any) => app.status === status.id
    ) || [];
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Applications</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {stats?.data?.totalApplications || 0}
              </p>
            </div>
            <div className="rounded-lg bg-blue-100 p-3">
              <Clock className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Response Rate</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {stats?.data?.metrics?.responseRate?.toFixed(0) || 0}%
              </p>
            </div>
            <div className="rounded-lg bg-green-100 p-3">
              <Eye className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Interview Rate</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {stats?.data?.metrics?.interviewRate?.toFixed(0) || 0}%
              </p>
            </div>
            <div className="rounded-lg bg-purple-100 p-3">
              <Users className="h-6 w-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Offer Rate</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {stats?.data?.metrics?.offerRate?.toFixed(0) || 0}%
              </p>
            </div>
            <div className="rounded-lg bg-yellow-100 p-3">
              <CheckCircle2 className="h-6 w-6 text-yellow-600" />
            </div>
          </div>
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">
          {applications?.data?.applications?.length || 0} Applications
        </h2>
        <div className="flex items-center space-x-2 rounded-lg bg-gray-100 p-1">
          <button
            onClick={() => setViewMode('board')}
            className={`rounded px-3 py-1.5 text-sm font-medium ${
              viewMode === 'board'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Board
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`rounded px-3 py-1.5 text-sm font-medium ${
              viewMode === 'list'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            List
          </button>
        </div>
      </div>

      {/* Kanban Board View */}
      {viewMode === 'board' && (
        <div className="overflow-x-auto pb-4">
          <div className="inline-flex gap-4" style={{ minWidth: '100%' }}>
            {statusColumns.map((column) => {
              const Icon = column.icon;
              const apps = groupedApplications[column.id] || [];

              return (
                <div key={column.id} className="flex-shrink-0" style={{ width: '280px' }}>
                  <div className="mb-3 flex items-center space-x-2">
                    <div className={`rounded p-1.5 ${column.color.replace('bg-', 'bg-opacity-20 bg-')}`}>
                      <Icon className={`h-4 w-4 ${column.color.replace('bg-', 'text-')}`} />
                    </div>
                    <h3 className="font-semibold text-gray-900">{column.label}</h3>
                    <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700">
                      {apps.length}
                    </span>
                  </div>

                  <div className="space-y-3">
                    {apps.map((app: any) => (
                      <div key={app.id} className="card-hover group cursor-pointer">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-semibold text-gray-900 group-hover:text-primary-600">
                              {app.job?.title}
                            </h4>
                            <p className="mt-1 text-sm text-gray-600">{app.job?.company}</p>
                            <div className="mt-2 flex items-center space-x-2 text-xs text-gray-500">
                              <Calendar className="h-3 w-3" />
                              <span>Applied {format(new Date(app.createdAt), 'MMM d')}</span>
                            </div>
                            {app.notes && (
                              <p className="mt-2 text-xs text-gray-500 line-clamp-2">{app.notes}</p>
                            )}
                          </div>
                          <button className="rounded p-1 opacity-0 hover:bg-gray-100 group-hover:opacity-100">
                            <MoreVertical className="h-4 w-4 text-gray-400" />
                          </button>
                        </div>
                      </div>
                    ))}

                    {apps.length === 0 && (
                      <div className="rounded-lg border-2 border-dashed border-gray-200 p-6 text-center">
                        <p className="text-sm text-gray-400">No applications</p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Job
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Applied
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Last Updated
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {isLoading && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <div className="flex items-center justify-center">
                        <div className="h-8 w-8 spinner"></div>
                      </div>
                    </td>
                  </tr>
                )}

                {!isLoading && applications?.data?.applications?.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                      No applications yet. Start applying to jobs!
                    </td>
                  </tr>
                )}

                {applications?.data?.applications?.map((app: any) => {
                  const statusColumn = statusColumns.find((s) => s.id === app.status);
                  const StatusIcon = statusColumn?.icon || Clock;

                  return (
                    <tr key={app.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-900">{app.job?.title}</p>
                          {app.applicationUrl && (
                            <a
                              href={app.applicationUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="mt-1 inline-flex items-center text-xs text-primary-600 hover:text-primary-700"
                            >
                              View application
                              <ExternalLink className="ml-1 h-3 w-3" />
                            </a>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {app.job?.company}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center space-x-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            app.status === 'PENDING'
                              ? 'bg-gray-100 text-gray-800'
                              : app.status === 'VIEWED'
                              ? 'bg-blue-100 text-blue-800'
                              : app.status === 'SCREENING'
                              ? 'bg-yellow-100 text-yellow-800'
                              : app.status === 'INTERVIEWING'
                              ? 'bg-purple-100 text-purple-800'
                              : app.status === 'OFFERED'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          <StatusIcon className="h-3 w-3" />
                          <span>{statusColumn?.label}</span>
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {format(new Date(app.createdAt), 'MMM d, yyyy')}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {format(new Date(app.updatedAt), 'MMM d, yyyy')}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="rounded p-1 hover:bg-gray-100">
                          <MoreVertical className="h-4 w-4 text-gray-400" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

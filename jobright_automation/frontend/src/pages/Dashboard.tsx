import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {  Briefcase, FileText, TrendingUp, Clock, ArrowRight, Target, Users, Bot } from 'lucide-react';
import { analyticsAPI, jobsAPI, applicationsAPI } from '@/services/api';

export default function Dashboard() {
  const { data: analytics } = useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: () => analyticsAPI.getDashboard(),
  });

  const { data: recommendedJobs } = useQuery({
    queryKey: ['jobs', 'recommendations'],
    queryFn: () => jobsAPI.getRecommendations(5),
  });

  const { data: recentApplications } = useQuery({
    queryKey: ['applications', 'recent'],
    queryFn: () => applicationsAPI.getAll({ limit: 5 }),
  });

  const { data: stats } = useQuery({
    queryKey: ['applications', 'stats'],
    queryFn: () => applicationsAPI.getStats(),
  });

  const statsCards = [
    {
      name: 'Total Applications',
      value: stats?.data?.totalApplications || 0,
      icon: FileText,
      color: 'bg-blue-500',
      change: '+12%',
    },
    {
      name: 'Recommended Jobs',
      value: recommendedJobs?.data?.length || 0,
      icon: Target,
      color: 'bg-green-500',
      change: '+25',
    },
    {
      name: 'Response Rate',
      value: `${stats?.data?.metrics?.responseRate?.toFixed(0) || 0}%`,
      icon: TrendingUp,
      color: 'bg-purple-500',
      change: '+5%',
    },
    {
      name: 'Interview Rate',
      value: `${stats?.data?.metrics?.interviewRate?.toFixed(0) || 0}%`,
      icon: Users,
      color: 'bg-orange-500',
      change: '+3%',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="card bg-gradient-to-r from-primary-600 to-secondary-600 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Welcome back!</h2>
            <p className="mt-2 text-white/90">
              You have {recommendedJobs?.data?.length || 0} new job recommendations waiting for you.
            </p>
          </div>
          <Link to="/copilot" className="btn bg-white text-primary-700 hover:bg-gray-100">
            <Bot className="mr-2 h-5 w-5" />
            Ask Orion AI
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="mt-2 text-3xl font-bold text-gray-900">{stat.value}</p>
                  <p className="mt-2 text-sm text-green-600">{stat.change} from last week</p>
                </div>
                <div className={`rounded-lg ${stat.color} p-3`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recommended Jobs */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900">Recommended Jobs</h3>
          <Link to="/jobs" className="flex items-center text-sm font-medium text-primary-600 hover:text-primary-700">
            View all
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </div>

        <div className="space-y-4">
          {!recommendedJobs?.data?.length && (
            <div className="text-center py-12 text-gray-500">
              <Briefcase className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <p>No job recommendations yet.</p>
              <p className="text-sm mt-1">Complete your profile to get personalized recommendations!</p>
            </div>
          )}

          {recommendedJobs?.data?.map((job: any) => (
            <Link
              key={job.id}
              to={`/jobs/${job.id}`}
              className="block rounded-lg border p-4 transition-shadow hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <h4 className="font-semibold text-gray-900">{job.title}</h4>
                    {job.matchScore && (
                      <span className="badge badge-primary">
                        {job.matchScore}% match
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-600">{job.company}</p>
                  <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                    <span>{job.location}</span>
                    <span>•</span>
                    <span className="capitalize">{job.jobType}</span>
                    {job.salary && (
                      <>
                        <span>•</span>
                        <span>{job.salary}</span>
                      </>
                    )}
                  </div>
                </div>
                <button className="btn btn-primary btn-sm">
                  Apply
                </button>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent Applications */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900">Recent Applications</h3>
          <Link to="/applications" className="flex items-center text-sm font-medium text-primary-600 hover:text-primary-700">
            View all
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </div>

        <div className="space-y-4">
          {!recentApplications?.data?.applications?.length && (
            <div className="text-center py-12 text-gray-500">
              <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <p>No applications yet.</p>
              <p className="text-sm mt-1">Start applying to jobs to track your progress!</p>
            </div>
          )}

          {recentApplications?.data?.applications?.map((application: any) => (
            <div
              key={application.id}
              className="flex items-center justify-between rounded-lg border p-4"
            >
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900">{application.job?.title}</h4>
                <p className="text-sm text-gray-600">{application.job?.company}</p>
                <div className="mt-2 flex items-center space-x-2 text-xs text-gray-500">
                  <Clock className="h-3 w-3" />
                  <span>Applied {new Date(application.createdAt).toLocaleDateString()}</span>
                </div>
              </div>
              <span className={`badge ${
                application.status === 'SUBMITTED' ? 'badge-primary' :
                application.status === 'SCREENING' ? 'badge-warning' :
                application.status === 'INTERVIEWING' ? 'badge-success' :
                application.status === 'OFFERED' ? 'badge-success' :
                application.status === 'REJECTED' ? 'badge-danger' :
                'badge-gray'
              }`}>
                {application.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

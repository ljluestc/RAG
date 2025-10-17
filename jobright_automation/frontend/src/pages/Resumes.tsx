import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Download, Eye, Edit, Trash2, Star, FileText } from 'lucide-react';
import { resumesAPI } from '@/services/api';
import { toast } from 'sonner';

export default function Resumes() {
  const [selectedResume, setSelectedResume] = useState<string | null>(null);

  const { data: resumes, isLoading, refetch } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => resumesAPI.getAll(),
  });

  const handleDownload = async (resumeId: string, name: string) => {
    try {
      const response = await resumesAPI.getPDF(resumeId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Resume downloaded!');
    } catch (error) {
      toast.error('Failed to download resume');
    }
  };

  const handleDelete = async (resumeId: string) => {
    if (!confirm('Are you sure you want to delete this resume?')) return;

    try {
      await resumesAPI.delete(resumeId);
      toast.success('Resume deleted');
      refetch();
    } catch (error) {
      toast.error('Failed to delete resume');
    }
  };

  const getATSScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">My Resumes</h2>
          <p className="mt-1 text-sm text-gray-600">
            Create and manage your resumes with AI-powered optimization
          </p>
        </div>
        <button className="btn btn-primary">
          <Plus className="mr-2 h-5 w-5" />
          Create Resume
        </button>
      </div>

      {/* Resume Grid */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 spinner"></div>
        </div>
      )}

      {!isLoading && resumes?.data?.length === 0 && (
        <div className="card text-center py-12">
          <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No resumes yet</h3>
          <p className="text-gray-600 mb-6">Create your first resume to get started</p>
          <button className="btn btn-primary">
            <Plus className="mr-2 h-5 w-5" />
            Create Your First Resume
          </button>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {resumes?.data?.map((resume: any) => (
          <div
            key={resume.id}
            className={`card-hover cursor-pointer ${
              selectedResume === resume.id ? 'ring-2 ring-primary-500' : ''
            }`}
            onClick={() => setSelectedResume(resume.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <h3 className="font-semibold text-gray-900">{resume.name}</h3>
                  {resume.isDefault && (
                    <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-600 capitalize">
                  {resume.template} template
                </p>

                {/* ATS Score */}
                {resume.atsScore !== null && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">ATS Score</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-semibold ${getATSScoreColor(
                          resume.atsScore
                        )}`}
                      >
                        {resume.atsScore}%
                      </span>
                    </div>
                    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`h-full ${
                          resume.atsScore >= 80
                            ? 'bg-green-500'
                            : resume.atsScore >= 60
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${resume.atsScore}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Last updated */}
                <p className="mt-3 text-xs text-gray-500">
                  Updated {new Date(resume.updatedAt).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-4 flex items-center space-x-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload(resume.id, resume.name);
                }}
                className="btn btn-outline flex-1"
              >
                <Download className="mr-2 h-4 w-4" />
                Download
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                }}
                className="rounded-lg p-2 hover:bg-gray-100"
                title="Preview"
              >
                <Eye className="h-4 w-4 text-gray-600" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                }}
                className="rounded-lg p-2 hover:bg-gray-100"
                title="Edit"
              >
                <Edit className="h-4 w-4 text-gray-600" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(resume.id);
                }}
                className="rounded-lg p-2 hover:bg-red-50"
                title="Delete"
              >
                <Trash2 className="h-4 w-4 text-red-600" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* AI Optimization Section */}
      {resumes?.data?.length > 0 && (
        <div className="card bg-gradient-to-r from-primary-50 to-secondary-50">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                AI Resume Optimization
              </h3>
              <p className="mt-2 text-sm text-gray-600">
                Optimize your resume for specific jobs using AI. Get personalized suggestions to
                improve your ATS score and increase your chances of landing interviews.
              </p>
            </div>
            <button className="btn btn-primary whitespace-nowrap">
              Optimize Resume
            </button>
          </div>
        </div>
      )}

      {/* Tips Section */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Resume Tips</h3>
        <div className="space-y-3">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 mt-1">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100">
                <span className="text-xs font-bold text-primary-700">1</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                Tailor for each job
              </p>
              <p className="text-sm text-gray-600">
                Customize your resume for each position by highlighting relevant skills and experience
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 mt-1">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100">
                <span className="text-xs font-bold text-primary-700">2</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                Use action verbs
              </p>
              <p className="text-sm text-gray-600">
                Start bullet points with strong action verbs like "Developed," "Led," or "Achieved"
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 mt-1">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100">
                <span className="text-xs font-bold text-primary-700">3</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                Quantify achievements
              </p>
              <p className="text-sm text-gray-600">
                Include numbers and metrics to demonstrate impact (e.g., "Increased sales by 25%")
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 mt-1">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100">
                <span className="text-xs font-bold text-primary-700">4</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                Keep it concise
              </p>
              <p className="text-sm text-gray-600">
                Aim for 1-2 pages maximum and use bullet points for easy scanning
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

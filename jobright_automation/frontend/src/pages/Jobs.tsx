import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Search, MapPin, Briefcase, DollarSign, Filter, Star, Bookmark, X } from 'lucide-react';
import { jobsAPI } from '@/services/api';
import { toast } from 'sonner';

export default function Jobs() {
  const [searchQuery, setSearchQuery] = useState('');
  const [location, setLocation] = useState('');
  const [filters, setFilters] = useState({
    jobType: [] as string[],
    workArrangement: [] as string[],
    experienceLevel: [] as string[],
    visaSponsorship: undefined as boolean | undefined,
    minSalary: '',
    maxSalary: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['jobs', searchQuery, location, filters],
    queryFn: () => jobsAPI.search({
      query: searchQuery || undefined,
      location: location || undefined,
      jobType: filters.jobType.length > 0 ? filters.jobType : undefined,
      workArrangement: filters.workArrangement.length > 0 ? filters.workArrangement : undefined,
      experienceLevel: filters.experienceLevel.length > 0 ? filters.experienceLevel : undefined,
      visaSponsorship: filters.visaSponsorship,
      salaryMin: filters.minSalary ? parseInt(filters.minSalary) : undefined,
      salaryMax: filters.maxSalary ? parseInt(filters.maxSalary) : undefined,
    }),
  });

  const handleSaveJob = async (jobId: string) => {
    try {
      await jobsAPI.save(jobId);
      toast.success('Job saved!');
      refetch();
    } catch (error) {
      toast.error('Failed to save job');
    }
  };

  const handleUnsaveJob = async (jobId: string) => {
    try {
      await jobsAPI.unsave(jobId);
      toast.success('Job removed from saved');
      refetch();
    } catch (error) {
      toast.error('Failed to unsave job');
    }
  };

  const toggleFilter = (category: keyof typeof filters, value: string) => {
    setFilters((prev) => {
      const current = prev[category] as string[];
      const newValue = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return { ...prev, [category]: newValue };
    });
  };

  const clearFilters = () => {
    setFilters({
      jobType: [],
      workArrangement: [],
      experienceLevel: [],
      visaSponsorship: undefined,
      minSalary: '',
      maxSalary: '',
    });
  };

  const activeFiltersCount =
    filters.jobType.length +
    filters.workArrangement.length +
    filters.experienceLevel.length +
    (filters.visaSponsorship !== undefined ? 1 : 0) +
    (filters.minSalary ? 1 : 0) +
    (filters.maxSalary ? 1 : 0);

  return (
    <div className="space-y-6">
      {/* Search Bar */}
      <div className="card">
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Job title, keywords, or company"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-10"
              />
            </div>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="City, state, or remote"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="input pl-10"
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="btn btn-outline"
            >
              <Filter className="mr-2 h-4 w-4" />
              Filters
              {activeFiltersCount > 0 && (
                <span className="ml-2 rounded-full bg-primary-600 px-2 py-0.5 text-xs text-white">
                  {activeFiltersCount}
                </span>
              )}
            </button>
            {activeFiltersCount > 0 && (
              <button onClick={clearFilters} className="text-sm text-gray-600 hover:text-gray-900">
                Clear all filters
              </button>
            )}
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="border-t pt-4">
              <div className="grid gap-6 md:grid-cols-3">
                {/* Job Type */}
                <div>
                  <h4 className="mb-3 font-medium text-gray-900">Job Type</h4>
                  <div className="space-y-2">
                    {['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP'].map((type) => (
                      <label key={type} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={filters.jobType.includes(type)}
                          onChange={() => toggleFilter('jobType', type)}
                          className="mr-2 rounded border-gray-300"
                        />
                        <span className="text-sm capitalize">{type.replace('_', ' ').toLowerCase()}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Work Arrangement */}
                <div>
                  <h4 className="mb-3 font-medium text-gray-900">Work Arrangement</h4>
                  <div className="space-y-2">
                    {['REMOTE', 'HYBRID', 'ONSITE'].map((arrangement) => (
                      <label key={arrangement} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={filters.workArrangement.includes(arrangement)}
                          onChange={() => toggleFilter('workArrangement', arrangement)}
                          className="mr-2 rounded border-gray-300"
                        />
                        <span className="text-sm capitalize">{arrangement.toLowerCase()}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Experience Level */}
                <div>
                  <h4 className="mb-3 font-medium text-gray-900">Experience Level</h4>
                  <div className="space-y-2">
                    {['ENTRY', 'MID', 'SENIOR', 'LEAD'].map((level) => (
                      <label key={level} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={filters.experienceLevel.includes(level)}
                          onChange={() => toggleFilter('experienceLevel', level)}
                          className="mr-2 rounded border-gray-300"
                        />
                        <span className="text-sm capitalize">{level.toLowerCase()}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-3">
                {/* Salary Range */}
                <div className="md:col-span-2">
                  <h4 className="mb-3 font-medium text-gray-900">Salary Range</h4>
                  <div className="flex items-center space-x-4">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.minSalary}
                      onChange={(e) => setFilters({ ...filters, minSalary: e.target.value })}
                      className="input"
                    />
                    <span className="text-gray-500">to</span>
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.maxSalary}
                      onChange={(e) => setFilters({ ...filters, maxSalary: e.target.value })}
                      className="input"
                    />
                  </div>
                </div>

                {/* Visa Sponsorship */}
                <div>
                  <h4 className="mb-3 font-medium text-gray-900">Visa Sponsorship</h4>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.visaSponsorship === true}
                      onChange={(e) =>
                        setFilters({ ...filters, visaSponsorship: e.target.checked ? true : undefined })
                      }
                      className="mr-2 rounded border-gray-300"
                    />
                    <span className="text-sm">Required</span>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {isLoading ? 'Searching...' : `${data?.data?.jobs?.length || 0} jobs found`}
          </p>
        </div>

        <div className="space-y-4">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 spinner"></div>
            </div>
          )}

          {!isLoading && data?.data?.jobs?.length === 0 && (
            <div className="card text-center py-12">
              <Briefcase className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No jobs found</h3>
              <p className="text-gray-600">Try adjusting your search criteria or filters</p>
            </div>
          )}

          {data?.data?.jobs?.map((job: any) => (
            <div key={job.id} className="card-hover">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <Link
                        to={`/jobs/${job.id}`}
                        className="text-lg font-semibold text-gray-900 hover:text-primary-600"
                      >
                        {job.title}
                      </Link>
                      {job.matchScore && (
                        <span className="ml-3 badge badge-primary">
                          <Star className="mr-1 h-3 w-3" />
                          {job.matchScore}% match
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="mt-1 font-medium text-gray-700">{job.company}</p>

                  <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-gray-600">
                    <span className="flex items-center">
                      <MapPin className="mr-1 h-4 w-4" />
                      {job.location}
                    </span>
                    <span className="flex items-center capitalize">
                      <Briefcase className="mr-1 h-4 w-4" />
                      {job.jobType?.replace('_', ' ').toLowerCase()}
                    </span>
                    {job.salary && (
                      <span className="flex items-center">
                        <DollarSign className="mr-1 h-4 w-4" />
                        {job.salary}
                      </span>
                    )}
                    {job.visaSponsorship && (
                      <span className="badge badge-success">Visa sponsorship</span>
                    )}
                  </div>

                  {job.description && (
                    <p className="mt-3 text-sm text-gray-600 line-clamp-2">
                      {job.description}
                    </p>
                  )}
                </div>

                <div className="ml-6 flex flex-col items-end space-y-2">
                  <button
                    onClick={() => job.isSaved ? handleUnsaveJob(job.id) : handleSaveJob(job.id)}
                    className={`rounded-lg p-2 transition-colors ${
                      job.isSaved
                        ? 'bg-primary-100 text-primary-700 hover:bg-primary-200'
                        : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'
                    }`}
                  >
                    <Bookmark className={`h-5 w-5 ${job.isSaved ? 'fill-current' : ''}`} />
                  </button>
                  <Link to={`/jobs/${job.id}`} className="btn btn-primary">
                    View Details
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

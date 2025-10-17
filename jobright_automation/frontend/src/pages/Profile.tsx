import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  User,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  DollarSign,
  Calendar,
  GraduationCap,
  Plus,
  X,
  Linkedin,
  Github,
  Globe,
  Save,
  Camera,
} from 'lucide-react';
import { userAPI } from '@/services/api';
import { toast } from 'sonner';

const profileSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  email: z.string().email('Invalid email address'),
  phone: z.string().optional(),
  location: z.string().optional(),
  title: z.string().optional(),
  yearsOfExperience: z.number().min(0).optional(),
  salaryMin: z.number().min(0).optional(),
  salaryMax: z.number().min(0).optional(),
  linkedin: z.string().url().optional().or(z.literal('')),
  github: z.string().url().optional().or(z.literal('')),
  portfolio: z.string().url().optional().or(z.literal('')),
});

type ProfileFormData = z.infer<typeof profileSchema>;

interface Skill {
  id: string;
  name: string;
  level?: string;
}

interface Experience {
  id: string;
  company: string;
  title: string;
  startDate: string;
  endDate?: string;
  current: boolean;
  description?: string;
}

interface Education {
  id: string;
  school: string;
  degree: string;
  field: string;
  startDate: string;
  endDate?: string;
  current: boolean;
}

export default function Profile() {
  const queryClient = useQueryClient();
  const [newSkill, setNewSkill] = useState('');
  const [skills, setSkills] = useState<Skill[]>([]);
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [education, setEducation] = useState<Education[]>([]);

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => userAPI.getFullProfile(),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
  });

  useEffect(() => {
    if (profile?.data) {
      const data = profile.data;
      reset({
        firstName: data.firstName || '',
        lastName: data.lastName || '',
        email: data.email || '',
        phone: data.phone || '',
        location: data.location || '',
        title: data.title || '',
        yearsOfExperience: data.yearsOfExperience || 0,
        salaryMin: data.salaryMin || 0,
        salaryMax: data.salaryMax || 0,
        linkedin: data.linkedin || '',
        github: data.github || '',
        portfolio: data.portfolio || '',
      });

      if (data.skills) setSkills(data.skills);
      if (data.experience) setExperiences(data.experience);
      if (data.education) setEducation(data.education);
    }
  }, [profile, reset]);

  const updateMutation = useMutation({
    mutationFn: (data: any) => userAPI.updateFullProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      toast.success('Profile updated successfully!');
    },
    onError: () => {
      toast.error('Failed to update profile');
    },
  });

  const onSubmit = (data: ProfileFormData) => {
    updateMutation.mutate({
      ...data,
      skills,
      experience: experiences,
      education,
    });
  };

  const handleAddSkill = () => {
    if (newSkill.trim()) {
      setSkills([...skills, { id: Date.now().toString(), name: newSkill.trim() }]);
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (id: string) => {
    setSkills(skills.filter((s) => s.id !== id));
  };

  const handleAddExperience = () => {
    setExperiences([
      ...experiences,
      {
        id: Date.now().toString(),
        company: '',
        title: '',
        startDate: '',
        current: false,
      },
    ]);
  };

  const handleUpdateExperience = (id: string, field: string, value: any) => {
    setExperiences(
      experiences.map((exp) => (exp.id === id ? { ...exp, [field]: value } : exp))
    );
  };

  const handleRemoveExperience = (id: string) => {
    setExperiences(experiences.filter((exp) => exp.id !== id));
  };

  const handleAddEducation = () => {
    setEducation([
      ...education,
      {
        id: Date.now().toString(),
        school: '',
        degree: '',
        field: '',
        startDate: '',
        current: false,
      },
    ]);
  };

  const handleUpdateEducation = (id: string, field: string, value: any) => {
    setEducation(
      education.map((edu) => (edu.id === id ? { ...edu, [field]: value } : edu))
    );
  };

  const handleRemoveEducation = (id: string) => {
    setEducation(education.filter((edu) => edu.id !== id));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Profile</h2>
          <p className="mt-1 text-sm text-gray-600">
            Manage your personal and professional information
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Profile Photo */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Profile Photo</h3>
          <div className="flex items-center space-x-6">
            <div className="relative">
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary-100">
                <User className="h-12 w-12 text-primary-600" />
              </div>
              <button
                type="button"
                className="absolute bottom-0 right-0 rounded-full bg-white p-2 shadow-md hover:bg-gray-50"
              >
                <Camera className="h-4 w-4 text-gray-600" />
              </button>
            </div>
            <div>
              <button type="button" className="btn btn-outline mb-2">
                Upload Photo
              </button>
              <p className="text-sm text-gray-500">
                JPG, PNG or GIF. Max size 2MB.
              </p>
            </div>
          </div>
        </div>

        {/* Basic Information */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                First Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  {...register('firstName')}
                  className="input pl-10"
                  placeholder="John"
                />
              </div>
              {errors.firstName && (
                <p className="mt-1 text-sm text-red-600">{errors.firstName.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Last Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  {...register('lastName')}
                  className="input pl-10"
                  placeholder="Doe"
                />
              </div>
              {errors.lastName && (
                <p className="mt-1 text-sm text-red-600">{errors.lastName.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  {...register('email')}
                  className="input pl-10"
                  placeholder="john@example.com"
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Phone
              </label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="tel"
                  {...register('phone')}
                  className="input pl-10"
                  placeholder="+1 (555) 123-4567"
                />
              </div>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  {...register('location')}
                  className="input pl-10"
                  placeholder="San Francisco, CA"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Professional Information */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Professional Information
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Current Title
              </label>
              <div className="relative">
                <Briefcase className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  {...register('title')}
                  className="input pl-10"
                  placeholder="Software Engineer"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Years of Experience
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="number"
                  {...register('yearsOfExperience', { valueAsNumber: true })}
                  className="input pl-10"
                  placeholder="5"
                  min="0"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Salary Range
              </label>
              <div className="flex items-center space-x-2">
                <div className="relative flex-1">
                  <DollarSign className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="number"
                    {...register('salaryMin', { valueAsNumber: true })}
                    className="input pl-10"
                    placeholder="80000"
                    min="0"
                  />
                </div>
                <span className="text-gray-500">to</span>
                <div className="relative flex-1">
                  <DollarSign className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="number"
                    {...register('salaryMax', { valueAsNumber: true })}
                    className="input pl-10"
                    placeholder="120000"
                    min="0"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Skills */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Skills</h3>
          <div className="mb-4">
            <div className="flex space-x-2">
              <input
                type="text"
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                className="input flex-1"
                placeholder="Add a skill (e.g., JavaScript, Python)"
              />
              <button
                type="button"
                onClick={handleAddSkill}
                className="btn btn-primary"
              >
                <Plus className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {skills.map((skill) => (
              <div
                key={skill.id}
                className="inline-flex items-center space-x-2 rounded-full bg-primary-100 px-3 py-1 text-sm font-medium text-primary-700"
              >
                <span>{skill.name}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveSkill(skill.id)}
                  className="rounded-full hover:bg-primary-200"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
            {skills.length === 0 && (
              <p className="text-sm text-gray-500">No skills added yet</p>
            )}
          </div>
        </div>

        {/* Experience */}
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Work Experience</h3>
            <button
              type="button"
              onClick={handleAddExperience}
              className="btn btn-outline"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Experience
            </button>
          </div>

          <div className="space-y-4">
            {experiences.map((exp, index) => (
              <div key={exp.id} className="rounded-lg border p-4">
                <div className="mb-3 flex items-start justify-between">
                  <h4 className="font-medium text-gray-900">Experience {index + 1}</h4>
                  <button
                    type="button"
                    onClick={() => handleRemoveExperience(exp.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <input
                    type="text"
                    value={exp.company}
                    onChange={(e) => handleUpdateExperience(exp.id, 'company', e.target.value)}
                    className="input"
                    placeholder="Company Name"
                  />
                  <input
                    type="text"
                    value={exp.title}
                    onChange={(e) => handleUpdateExperience(exp.id, 'title', e.target.value)}
                    className="input"
                    placeholder="Job Title"
                  />
                  <input
                    type="date"
                    value={exp.startDate}
                    onChange={(e) => handleUpdateExperience(exp.id, 'startDate', e.target.value)}
                    className="input"
                  />
                  <input
                    type="date"
                    value={exp.endDate || ''}
                    onChange={(e) => handleUpdateExperience(exp.id, 'endDate', e.target.value)}
                    className="input"
                    disabled={exp.current}
                  />
                  <label className="flex items-center md:col-span-2">
                    <input
                      type="checkbox"
                      checked={exp.current}
                      onChange={(e) => handleUpdateExperience(exp.id, 'current', e.target.checked)}
                      className="mr-2 rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">I currently work here</span>
                  </label>
                  <textarea
                    value={exp.description || ''}
                    onChange={(e) => handleUpdateExperience(exp.id, 'description', e.target.value)}
                    className="input md:col-span-2"
                    rows={3}
                    placeholder="Describe your responsibilities and achievements..."
                  />
                </div>
              </div>
            ))}

            {experiences.length === 0 && (
              <p className="text-center text-sm text-gray-500 py-4">
                No work experience added yet
              </p>
            )}
          </div>
        </div>

        {/* Education */}
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Education</h3>
            <button
              type="button"
              onClick={handleAddEducation}
              className="btn btn-outline"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Education
            </button>
          </div>

          <div className="space-y-4">
            {education.map((edu, index) => (
              <div key={edu.id} className="rounded-lg border p-4">
                <div className="mb-3 flex items-start justify-between">
                  <h4 className="font-medium text-gray-900">Education {index + 1}</h4>
                  <button
                    type="button"
                    onClick={() => handleRemoveEducation(edu.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <input
                    type="text"
                    value={edu.school}
                    onChange={(e) => handleUpdateEducation(edu.id, 'school', e.target.value)}
                    className="input"
                    placeholder="School Name"
                  />
                  <input
                    type="text"
                    value={edu.degree}
                    onChange={(e) => handleUpdateEducation(edu.id, 'degree', e.target.value)}
                    className="input"
                    placeholder="Degree (e.g., Bachelor's)"
                  />
                  <input
                    type="text"
                    value={edu.field}
                    onChange={(e) => handleUpdateEducation(edu.id, 'field', e.target.value)}
                    className="input md:col-span-2"
                    placeholder="Field of Study"
                  />
                  <input
                    type="date"
                    value={edu.startDate}
                    onChange={(e) => handleUpdateEducation(edu.id, 'startDate', e.target.value)}
                    className="input"
                  />
                  <input
                    type="date"
                    value={edu.endDate || ''}
                    onChange={(e) => handleUpdateEducation(edu.id, 'endDate', e.target.value)}
                    className="input"
                    disabled={edu.current}
                  />
                  <label className="flex items-center md:col-span-2">
                    <input
                      type="checkbox"
                      checked={edu.current}
                      onChange={(e) => handleUpdateEducation(edu.id, 'current', e.target.checked)}
                      className="mr-2 rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Currently studying</span>
                  </label>
                </div>
              </div>
            ))}

            {education.length === 0 && (
              <p className="text-center text-sm text-gray-500 py-4">
                No education added yet
              </p>
            )}
          </div>
        </div>

        {/* Social Links */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Social Links</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                LinkedIn
              </label>
              <div className="relative">
                <Linkedin className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="url"
                  {...register('linkedin')}
                  className="input pl-10"
                  placeholder="https://linkedin.com/in/yourprofile"
                />
              </div>
              {errors.linkedin && (
                <p className="mt-1 text-sm text-red-600">{errors.linkedin.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                GitHub
              </label>
              <div className="relative">
                <Github className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="url"
                  {...register('github')}
                  className="input pl-10"
                  placeholder="https://github.com/yourusername"
                />
              </div>
              {errors.github && (
                <p className="mt-1 text-sm text-red-600">{errors.github.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Portfolio Website
              </label>
              <div className="relative">
                <Globe className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="url"
                  {...register('portfolio')}
                  className="input pl-10"
                  placeholder="https://yourportfolio.com"
                />
              </div>
              {errors.portfolio && (
                <p className="mt-1 text-sm text-red-600">{errors.portfolio.message}</p>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end space-x-4">
          <button
            type="button"
            onClick={() => reset()}
            disabled={!isDirty}
            className="btn btn-outline"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={updateMutation.isPending || !isDirty}
            className="btn btn-primary"
          >
            <Save className="mr-2 h-5 w-5" />
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
}

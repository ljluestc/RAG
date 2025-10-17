import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Settings as SettingsIcon,
  Bell,
  Mail,
  Smartphone,
  Lock,
  Eye,
  EyeOff,
  CreditCard,
  Shield,
  AlertTriangle,
  Save,
  Briefcase,
  MapPin,
  DollarSign,
} from 'lucide-react';
import { toast } from 'sonner';

const passwordSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type PasswordFormData = z.infer<typeof passwordSchema>;

export default function Settings() {
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Notification preferences
  const [emailNotifications, setEmailNotifications] = useState({
    jobMatches: true,
    applicationUpdates: true,
    weeklyDigest: true,
    promotions: false,
  });

  const [smsNotifications, setSmsNotifications] = useState({
    urgentAlerts: true,
    interviewReminders: true,
  });

  const [pushNotifications, setPushNotifications] = useState({
    newMatches: true,
    messages: true,
    applicationStatus: true,
  });

  // Job preferences
  const [jobPreferences, setJobPreferences] = useState({
    preferredLocations: ['San Francisco, CA', 'Remote'],
    jobTypes: ['FULL_TIME'],
    workArrangements: ['REMOTE', 'HYBRID'],
    salaryMin: 80000,
    salaryMax: 150000,
    visaSponsorship: false,
  });

  // Privacy settings
  const [privacySettings, setPrivacySettings] = useState({
    profileVisibility: 'public',
    showSalaryExpectations: false,
    allowRecruiterContact: true,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const onPasswordSubmit = (data: PasswordFormData) => {
    // TODO: Implement password change API call
    console.log('Password change:', data);
    toast.success('Password changed successfully!');
    reset();
  };

  const handleSaveNotifications = () => {
    // TODO: Implement save API call
    console.log('Saving notifications:', { emailNotifications, smsNotifications, pushNotifications });
    toast.success('Notification preferences saved!');
  };

  const handleSaveJobPreferences = () => {
    // TODO: Implement save API call
    console.log('Saving job preferences:', jobPreferences);
    toast.success('Job preferences saved!');
  };

  const handleSavePrivacy = () => {
    // TODO: Implement save API call
    console.log('Saving privacy settings:', privacySettings);
    toast.success('Privacy settings saved!');
  };

  const handleDeleteAccount = () => {
    if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      // TODO: Implement delete account API call
      toast.error('Account deletion is not yet implemented');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <p className="mt-1 text-sm text-gray-600">
          Manage your account settings and preferences
        </p>
      </div>

      {/* Password Change */}
      <div className="card">
        <div className="mb-4 flex items-center space-x-3">
          <div className="rounded-lg bg-primary-100 p-2">
            <Lock className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Change Password</h3>
            <p className="text-sm text-gray-600">Update your password to keep your account secure</p>
          </div>
        </div>

        <form onSubmit={handleSubmit(onPasswordSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Current Password
            </label>
            <div className="relative">
              <input
                type={showCurrentPassword ? 'text' : 'password'}
                {...register('currentPassword')}
                className="input pr-10"
                placeholder="Enter current password"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showCurrentPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
            {errors.currentPassword && (
              <p className="mt-1 text-sm text-red-600">{errors.currentPassword.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              New Password
            </label>
            <div className="relative">
              <input
                type={showNewPassword ? 'text' : 'password'}
                {...register('newPassword')}
                className="input pr-10"
                placeholder="Enter new password"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showNewPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
            {errors.newPassword && (
              <p className="mt-1 text-sm text-red-600">{errors.newPassword.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirm New Password
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                {...register('confirmPassword')}
                className="input pr-10"
                placeholder="Confirm new password"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
            {errors.confirmPassword && (
              <p className="mt-1 text-sm text-red-600">{errors.confirmPassword.message}</p>
            )}
          </div>

          <div className="flex justify-end">
            <button type="submit" className="btn btn-primary">
              <Save className="mr-2 h-5 w-5" />
              Update Password
            </button>
          </div>
        </form>
      </div>

      {/* Notification Preferences */}
      <div className="card">
        <div className="mb-4 flex items-center space-x-3">
          <div className="rounded-lg bg-blue-100 p-2">
            <Bell className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Notification Preferences</h3>
            <p className="text-sm text-gray-600">Choose how you want to be notified</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Email Notifications */}
          <div>
            <div className="mb-3 flex items-center space-x-2">
              <Mail className="h-5 w-5 text-gray-500" />
              <h4 className="font-medium text-gray-900">Email Notifications</h4>
            </div>
            <div className="space-y-3 pl-7">
              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={emailNotifications.jobMatches}
                  onChange={(e) => setEmailNotifications({ ...emailNotifications, jobMatches: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Job Matches</p>
                  <p className="text-sm text-gray-500">Receive emails when new jobs match your preferences</p>
                </div>
              </label>

              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={emailNotifications.applicationUpdates}
                  onChange={(e) => setEmailNotifications({ ...emailNotifications, applicationUpdates: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Application Updates</p>
                  <p className="text-sm text-gray-500">Get notified when your application status changes</p>
                </div>
              </label>

              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={emailNotifications.weeklyDigest}
                  onChange={(e) => setEmailNotifications({ ...emailNotifications, weeklyDigest: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Weekly Digest</p>
                  <p className="text-sm text-gray-500">Weekly summary of your job search activity</p>
                </div>
              </label>

              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={emailNotifications.promotions}
                  onChange={(e) => setEmailNotifications({ ...emailNotifications, promotions: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Promotions & Tips</p>
                  <p className="text-sm text-gray-500">Career advice, promotions, and special offers</p>
                </div>
              </label>
            </div>
          </div>

          {/* SMS Notifications */}
          <div>
            <div className="mb-3 flex items-center space-x-2">
              <Smartphone className="h-5 w-5 text-gray-500" />
              <h4 className="font-medium text-gray-900">SMS Notifications</h4>
            </div>
            <div className="space-y-3 pl-7">
              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={smsNotifications.urgentAlerts}
                  onChange={(e) => setSmsNotifications({ ...smsNotifications, urgentAlerts: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Urgent Alerts</p>
                  <p className="text-sm text-gray-500">Important updates that require immediate attention</p>
                </div>
              </label>

              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={smsNotifications.interviewReminders}
                  onChange={(e) => setSmsNotifications({ ...smsNotifications, interviewReminders: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Interview Reminders</p>
                  <p className="text-sm text-gray-500">Get reminders before scheduled interviews</p>
                </div>
              </label>
            </div>
          </div>

          {/* Push Notifications */}
          <div>
            <div className="mb-3 flex items-center space-x-2">
              <Bell className="h-5 w-5 text-gray-500" />
              <h4 className="font-medium text-gray-900">Push Notifications</h4>
            </div>
            <div className="space-y-3 pl-7">
              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={pushNotifications.newMatches}
                  onChange={(e) => setPushNotifications({ ...pushNotifications, newMatches: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">New Matches</p>
                  <p className="text-sm text-gray-500">Instant notifications for high-match jobs</p>
                </div>
              </label>

              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={pushNotifications.messages}
                  onChange={(e) => setPushNotifications({ ...pushNotifications, messages: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Messages</p>
                  <p className="text-sm text-gray-500">Direct messages from recruiters</p>
                </div>
              </label>

              <label className="flex items-start">
                <input
                  type="checkbox"
                  checked={pushNotifications.applicationStatus}
                  onChange={(e) => setPushNotifications({ ...pushNotifications, applicationStatus: e.target.checked })}
                  className="mt-0.5 mr-3 rounded border-gray-300"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">Application Status</p>
                  <p className="text-sm text-gray-500">Real-time updates on your applications</p>
                </div>
              </label>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button onClick={handleSaveNotifications} className="btn btn-primary">
            <Save className="mr-2 h-5 w-5" />
            Save Preferences
          </button>
        </div>
      </div>

      {/* Job Search Preferences */}
      <div className="card">
        <div className="mb-4 flex items-center space-x-3">
          <div className="rounded-lg bg-purple-100 p-2">
            <Briefcase className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Job Search Preferences</h3>
            <p className="text-sm text-gray-600">Set your default job search criteria</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Preferred Locations
            </label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={jobPreferences.preferredLocations.join(', ')}
                onChange={(e) => setJobPreferences({ ...jobPreferences, preferredLocations: e.target.value.split(', ') })}
                className="input pl-10"
                placeholder="San Francisco, Remote, New York"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Job Types
            </label>
            <div className="grid grid-cols-2 gap-2">
              {['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP'].map((type) => (
                <label key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={jobPreferences.jobTypes.includes(type)}
                    onChange={(e) => {
                      const newTypes = e.target.checked
                        ? [...jobPreferences.jobTypes, type]
                        : jobPreferences.jobTypes.filter((t) => t !== type);
                      setJobPreferences({ ...jobPreferences, jobTypes: newTypes });
                    }}
                    className="mr-2 rounded border-gray-300"
                  />
                  <span className="text-sm capitalize">{type.replace('_', ' ').toLowerCase()}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Work Arrangements
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['REMOTE', 'HYBRID', 'ONSITE'].map((arrangement) => (
                <label key={arrangement} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={jobPreferences.workArrangements.includes(arrangement)}
                    onChange={(e) => {
                      const newArrangements = e.target.checked
                        ? [...jobPreferences.workArrangements, arrangement]
                        : jobPreferences.workArrangements.filter((a) => a !== arrangement);
                      setJobPreferences({ ...jobPreferences, workArrangements: newArrangements });
                    }}
                    className="mr-2 rounded border-gray-300"
                  />
                  <span className="text-sm capitalize">{arrangement.toLowerCase()}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Expected Salary Range
            </label>
            <div className="flex items-center space-x-2">
              <div className="relative flex-1">
                <DollarSign className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="number"
                  value={jobPreferences.salaryMin}
                  onChange={(e) => setJobPreferences({ ...jobPreferences, salaryMin: parseInt(e.target.value) })}
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
                  value={jobPreferences.salaryMax}
                  onChange={(e) => setJobPreferences({ ...jobPreferences, salaryMax: parseInt(e.target.value) })}
                  className="input pl-10"
                  placeholder="150000"
                  min="0"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={jobPreferences.visaSponsorship}
                onChange={(e) => setJobPreferences({ ...jobPreferences, visaSponsorship: e.target.checked })}
                className="mr-2 rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">Require visa sponsorship</span>
            </label>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button onClick={handleSaveJobPreferences} className="btn btn-primary">
            <Save className="mr-2 h-5 w-5" />
            Save Preferences
          </button>
        </div>
      </div>

      {/* Privacy Settings */}
      <div className="card">
        <div className="mb-4 flex items-center space-x-3">
          <div className="rounded-lg bg-green-100 p-2">
            <Shield className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Privacy Settings</h3>
            <p className="text-sm text-gray-600">Control who can see your information</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Profile Visibility
            </label>
            <select
              value={privacySettings.profileVisibility}
              onChange={(e) => setPrivacySettings({ ...privacySettings, profileVisibility: e.target.value })}
              className="input"
            >
              <option value="public">Public - Visible to everyone</option>
              <option value="recruiters">Recruiters Only - Only verified recruiters can see</option>
              <option value="private">Private - Only you can see</option>
            </select>
          </div>

          <label className="flex items-start">
            <input
              type="checkbox"
              checked={privacySettings.showSalaryExpectations}
              onChange={(e) => setPrivacySettings({ ...privacySettings, showSalaryExpectations: e.target.checked })}
              className="mt-0.5 mr-3 rounded border-gray-300"
            />
            <div>
              <p className="text-sm font-medium text-gray-900">Show Salary Expectations</p>
              <p className="text-sm text-gray-500">Display your expected salary range on your profile</p>
            </div>
          </label>

          <label className="flex items-start">
            <input
              type="checkbox"
              checked={privacySettings.allowRecruiterContact}
              onChange={(e) => setPrivacySettings({ ...privacySettings, allowRecruiterContact: e.target.checked })}
              className="mt-0.5 mr-3 rounded border-gray-300"
            />
            <div>
              <p className="text-sm font-medium text-gray-900">Allow Recruiter Contact</p>
              <p className="text-sm text-gray-500">Let recruiters reach out to you directly</p>
            </div>
          </label>
        </div>

        <div className="mt-6 flex justify-end">
          <button onClick={handleSavePrivacy} className="btn btn-primary">
            <Save className="mr-2 h-5 w-5" />
            Save Settings
          </button>
        </div>
      </div>

      {/* Subscription */}
      <div className="card">
        <div className="mb-4 flex items-center space-x-3">
          <div className="rounded-lg bg-yellow-100 p-2">
            <CreditCard className="h-5 w-5 text-yellow-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Subscription</h3>
            <p className="text-sm text-gray-600">Manage your subscription and billing</p>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-gray-900">Free Plan</p>
              <p className="text-sm text-gray-600">Limited to 10 applications per month</p>
            </div>
            <button className="btn btn-primary">
              Upgrade to Pro
            </button>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="card border-red-200 bg-red-50">
        <div className="mb-4 flex items-center space-x-3">
          <div className="rounded-lg bg-red-100 p-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Danger Zone</h3>
            <p className="text-sm text-gray-600">Irreversible actions that affect your account</p>
          </div>
        </div>

        <div className="rounded-lg border border-red-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-gray-900">Delete Account</p>
              <p className="text-sm text-gray-600">
                Permanently delete your account and all associated data
              </p>
            </div>
            <button
              onClick={handleDeleteAccount}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
            >
              Delete Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

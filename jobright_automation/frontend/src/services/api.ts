import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const { accessToken } = useAuthStore.getState();
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const { refreshToken } = useAuthStore.getState();

        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        // Try to refresh the token
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refreshToken,
        });

        const { accessToken: newAccessToken, refreshToken: newRefreshToken, user } = response.data;

        // Update tokens in store
        useAuthStore.getState().setAuth(user, newAccessToken, newRefreshToken);

        // Retry the original request with new token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  register: (email: string, password: string, firstName?: string, lastName?: string) =>
    api.post('/auth/register', { email, password, firstName, lastName }),

  logout: () => api.post('/auth/logout'),

  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }),

  resetPassword: (token: string, newPassword: string) =>
    api.post('/auth/reset-password', { token, newPassword }),
};

// Jobs API
export const jobsAPI = {
  search: (params: any) => api.get('/jobs', { params }),

  getById: (id: string) => api.get(`/jobs/${id}`),

  getRecommendations: (limit?: number) =>
    api.get('/jobs/recommendations', { params: { limit } }),

  save: (jobId: string) => api.post(`/jobs/${jobId}/save`),

  unsave: (jobId: string) => api.delete(`/jobs/${jobId}/save`),

  scrape: (platform: string, query: string, location: string) =>
    api.post('/jobs/scrape', { platform, query, location }),
};

// Applications API
export const applicationsAPI = {
  getAll: (params?: any) => api.get('/applications', { params }),

  getById: (id: string) => api.get(`/applications/${id}`),

  create: (data: any) => api.post('/applications', data),

  update: (id: string, data: any) => api.put(`/applications/${id}`, data),

  delete: (id: string) => api.delete(`/applications/${id}`),

  getStats: () => api.get('/applications/stats'),

  autoApply: (applicationId: string) =>
    api.post(`/applications/${applicationId}/auto-apply`),
};

// Resumes API
export const resumesAPI = {
  getAll: () => api.get('/resumes'),

  getById: (id: string) => api.get(`/resumes/${id}`),

  create: (data: any) => api.post('/resumes', data),

  update: (id: string, data: any) => api.put(`/resumes/${id}`, data),

  delete: (id: string) => api.delete(`/resumes/${id}`),

  getPDF: (id: string) => api.get(`/resumes/${id}/pdf`, { responseType: 'blob' }),
};

// Copilot API
export const copilotAPI = {
  getAdvice: (question: string, context?: any) =>
    api.post('/copilot/advice', { question, context }),

  optimizeResume: (resumeId: string, jobDescription: string) =>
    api.post('/copilot/optimize-resume', { resumeId, jobDescription }),

  generateCoverLetter: (jobId: string, resumeId: string) =>
    api.post('/copilot/cover-letter', { jobId, resumeId }),

  getInterviewPrep: (jobId: string) =>
    api.post('/copilot/interview-prep', { jobId }),
};

// User API
export const userAPI = {
  getProfile: () => api.get('/users/me'),

  updateProfile: (data: any) => api.put('/users/me', data),

  getFullProfile: () => api.get('/users/me/profile'),

  updateFullProfile: (data: any) => api.put('/users/me/profile', data),
};

// Networking API
export const networkingAPI = {
  getContacts: () => api.get('/networking/contacts'),

  createContact: (data: any) => api.post('/networking/contacts', data),

  updateContact: (id: string, data: any) =>
    api.put(`/networking/contacts/${id}`, data),

  deleteContact: (id: string) => api.delete(`/networking/contacts/${id}`),

  researchCompany: (company: string) =>
    api.post('/networking/research', { company }),
};

// Analytics API
export const analyticsAPI = {
  getDashboard: () => api.get('/analytics/dashboard'),

  getApplications: () => api.get('/analytics/applications'),

  getJobs: () => api.get('/analytics/jobs'),
};

// Notifications API
export const notificationsAPI = {
  getAll: () => api.get('/notifications'),

  markAsRead: (id: string) => api.put(`/notifications/${id}/read`),

  markAllAsRead: () => api.put('/notifications/read-all'),
};

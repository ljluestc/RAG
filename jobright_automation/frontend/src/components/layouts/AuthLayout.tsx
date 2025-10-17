import { Outlet } from 'react-router-dom';
import { Bot } from 'lucide-react';

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 to-secondary-600 p-12 text-white">
        <div className="flex flex-col justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur">
              <Bot className="h-7 w-7" />
            </div>
            <span className="text-2xl font-bold">JobRight Automation</span>
          </div>

          <div className="space-y-6">
            <h1 className="text-5xl font-bold leading-tight">
              Land your dream job
              <br />
              2x faster with AI
            </h1>
            <p className="text-xl text-white/90">
              Automate your job search with AI-powered matching, auto-apply, and interview prep.
            </p>

            <div className="space-y-4 pt-8">
              <div className="flex items-start space-x-3">
                <div className="mt-1 flex h-6 w-6 items-center justify-center rounded-full bg-white/20">
                  <span className="text-sm font-bold">✓</span>
                </div>
                <div>
                  <p className="font-semibold">AI Job Matching</p>
                  <p className="text-sm text-white/80">
                    Get personalized job recommendations based on your skills and preferences
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="mt-1 flex h-6 w-6 items-center justify-center rounded-full bg-white/20">
                  <span className="text-sm font-bold">✓</span>
                </div>
                <div>
                  <p className="font-semibold">Auto-Apply Automation</p>
                  <p className="text-sm text-white/80">
                    Apply to hundreds of jobs automatically with one click
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="mt-1 flex h-6 w-6 items-center justify-center rounded-full bg-white/20">
                  <span className="text-sm font-bold">✓</span>
                </div>
                <div>
                  <p className="font-semibold">Orion AI Copilot</p>
                  <p className="text-sm text-white/80">
                    Get instant career advice, resume optimization, and interview prep
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="text-sm text-white/70">
            © 2025 JobRight Automation. All rights reserved.
          </div>
        </div>
      </div>

      {/* Right side - Auth form */}
      <div className="flex flex-1 items-center justify-center bg-gray-50 p-8">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

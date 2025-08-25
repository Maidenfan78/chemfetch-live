import { redirect } from 'next/navigation';
import { supabaseServer } from '@/lib/supabase-server';
import {
  BarChart3,
  Users,
  FileText,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
} from 'lucide-react';

export default async function DashboardPage() {
  const supabase = await supabaseServer();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect('/login');
  }

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div className="bg-chemfetch-gradient rounded-2xl p-8 text-white">
        <div className="flex items-center gap-4 mb-4">
          <div className="text-4xl">🧪</div>
          <div>
            <h1 className="text-3xl font-bold mb-2">Welcome to ChemFetch Client Hub</h1>
            <p className="text-blue-100 text-lg">Chemical Safety Management Dashboard</p>
          </div>
        </div>
        <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
          <p className="text-lg mb-2">
            Logged in as: <span className="font-semibold">{user.email}</span>
          </p>
          <p className="text-blue-100">
            Access your chemical registers, SDS documents, and safety management tools.
          </p>
        </div>
      </div>

      {/* System Status Banner */}
      <div className="bg-green-50 border border-green-200 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <CheckCircle className="text-green-600" size={24} />
          <div>
            <h3 className="font-semibold text-green-800">System Status: Operational</h3>
            <p className="text-green-700 text-sm">
              All services running normally. OCR and SDS lookup available.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-chemfetch-bg-primary rounded-xl p-6 shadow-chemfetch border border-chemfetch-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-chemfetch-text-primary">Total Chemicals</h3>
            <BarChart3 size={24} className="text-chemfetch-primary" />
          </div>
          <div className="text-3xl font-bold text-chemfetch-text-primary mb-2">0</div>
          <p className="text-sm text-chemfetch-text-secondary">Registered in your system</p>
          <div className="mt-3 flex items-center text-xs text-green-600">
            <TrendingUp size={12} className="mr-1" />
            Ready to add chemicals
          </div>
        </div>

        <div className="bg-chemfetch-bg-primary rounded-xl p-6 shadow-chemfetch border border-chemfetch-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-chemfetch-text-primary">SDS Documents</h3>
            <FileText size={24} className="text-chemfetch-accent" />
          </div>
          <div className="text-3xl font-bold text-chemfetch-text-primary mb-2">0</div>
          <p className="text-sm text-chemfetch-text-secondary">Safety data sheets available</p>
          <div className="mt-3 flex items-center text-xs text-blue-600">
            <Clock size={12} className="mr-1" />
            Auto-retrieval enabled
          </div>
        </div>

        <div className="bg-chemfetch-bg-primary rounded-xl p-6 shadow-chemfetch border border-chemfetch-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-chemfetch-text-primary">Scan Time</h3>
            <TrendingUp size={24} className="text-green-500" />
          </div>
          <div className="text-3xl font-bold text-chemfetch-text-primary mb-2">~2-5s</div>
          <p className="text-sm text-chemfetch-text-secondary">Average processing time</p>
          <div className="mt-3 flex items-center text-xs text-green-600">
            <CheckCircle size={12} className="mr-1" />
            Optimal performance
          </div>
        </div>

        <div className="bg-chemfetch-bg-primary rounded-xl p-6 shadow-chemfetch border border-chemfetch-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-chemfetch-text-primary">OCR Accuracy</h3>
            <Users size={24} className="text-purple-500" />
          </div>
          <div className="text-3xl font-bold text-chemfetch-text-primary mb-2">95%+</div>
          <p className="text-sm text-chemfetch-text-secondary">Text recognition accuracy</p>
          <div className="mt-3 flex items-center text-xs text-purple-600">
            <TrendingUp size={12} className="mr-1" />
            Continuously improving
          </div>
        </div>
      </div>

      {/* Getting Started Section */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="text-amber-600" size={24} />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-amber-800 mb-2">Getting Started</h3>
            <p className="text-amber-700 mb-4">
              Your chemical register is empty. Start by adding chemicals to your system using
              barcode scanning or manual entry.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="/watchlist"
                className="inline-flex items-center px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors text-sm font-medium"
              >
                Add First Chemical →
              </a>
              <a
                href="https://chemfetch.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-4 py-2 border border-amber-600 text-amber-700 rounded-lg hover:bg-amber-100 transition-colors text-sm font-medium"
              >
                View Documentation
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Chemical Register */}
        <div className="bg-chemfetch-bg-primary rounded-xl p-6 shadow-chemfetch border border-chemfetch-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-chemfetch-primary/10 rounded-xl flex items-center justify-center">
              <BarChart3 size={24} className="text-chemfetch-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-chemfetch-text-primary">
                Chemical Register
              </h2>
              <p className="text-chemfetch-text-secondary">Manage your chemical inventory</p>
            </div>
          </div>
          <p className="text-chemfetch-text-secondary mb-6">
            View and manage all registered chemicals in your system. Track inventory, safety data,
            and compliance information with barcode scanning and OCR capabilities.
          </p>
          <div className="flex gap-3">
            <a
              href="/watchlist"
              className="inline-flex items-center px-4 py-2 bg-chemfetch-primary text-white rounded-lg hover:bg-chemfetch-primary-dark transition-colors"
            >
              View Register →
            </a>
            <button className="inline-flex items-center px-4 py-2 border border-chemfetch-border text-chemfetch-text-primary rounded-lg hover:bg-chemfetch-bg-secondary transition-colors">
              Quick Add
            </button>
          </div>
        </div>

        {/* SDS Management */}
        <div className="bg-chemfetch-bg-primary rounded-xl p-6 shadow-chemfetch border border-chemfetch-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-chemfetch-accent/10 rounded-xl flex items-center justify-center">
              <FileText size={24} className="text-chemfetch-accent" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-chemfetch-text-primary">SDS Documents</h2>
              <p className="text-chemfetch-text-secondary">Access safety data sheets</p>
            </div>
          </div>
          <p className="text-chemfetch-text-secondary mb-6">
            Access and manage Safety Data Sheets for all chemicals. Intelligent SDS discovery,
            automatic updates, and compliance tracking to ensure safety protocols are current.
          </p>
          <div className="flex gap-3">
            <a
              href="/sds"
              className="inline-flex items-center px-4 py-2 bg-chemfetch-accent text-white rounded-lg hover:bg-cyan-600 transition-colors"
            >
              View SDS →
            </a>
            <button className="inline-flex items-center px-4 py-2 border border-chemfetch-border text-chemfetch-text-primary rounded-lg hover:bg-chemfetch-bg-secondary transition-colors">
              Upload SDS
            </button>
          </div>
        </div>
      </div>

      {/* Platform Features */}
      <div className="bg-chemfetch-bg-primary rounded-2xl p-8 shadow-chemfetch border border-chemfetch-border">
        <h2 className="text-2xl font-bold text-chemfetch-text-primary mb-6">Platform Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-6">
            <div className="text-4xl mb-4">📷</div>
            <h3 className="font-semibold text-chemfetch-text-primary mb-2">Barcode Scanning</h3>
            <p className="text-chemfetch-text-secondary">
              Instant product identification through mobile barcode scanning with real-time chemical
              database lookup
            </p>
          </div>
          <div className="text-center p-6">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="font-semibold text-chemfetch-text-primary mb-2">OCR Recognition</h3>
            <p className="text-chemfetch-text-secondary">
              Advanced text extraction from product labels and documents with 95%+ accuracy for
              chemical identification
            </p>
          </div>
          <div className="text-center p-6">
            <div className="text-4xl mb-4">📋</div>
            <h3 className="font-semibold text-chemfetch-text-primary mb-2">SDS Management</h3>
            <p className="text-chemfetch-text-secondary">
              Intelligent Safety Data Sheet discovery, verification, and automatic updates for
              compliance tracking
            </p>
          </div>
        </div>
      </div>

      {/* Support Section */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
            <Users size={24} className="text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-blue-800">Need Help?</h3>
            <p className="text-blue-700">Our support team is here to assist you</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-4">
          <a
            href="mailto:info@chemfetch.com"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            Contact Support
          </a>
          <a
            href="https://chemfetch.com/privacy-policy.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-4 py-2 border border-blue-600 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors text-sm"
          >
            Privacy Policy
          </a>
        </div>
      </div>
    </div>
  );
}

// src/app/loading.tsx
export default function Loading() {
  return (
    <div className="min-h-screen bg-chemfetch-bg-secondary flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 bg-chemfetch-gradient rounded-2xl flex items-center justify-center mx-auto mb-6 animate-pulse">
          <div className="text-3xl">🧪</div>
        </div>
        <h2 className="text-xl font-semibold text-chemfetch-text-primary mb-2">
          ChemFetch Client Hub
        </h2>
        <p className="text-chemfetch-text-secondary mb-6">Loading your dashboard...</p>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-chemfetch-primary border-t-transparent"></div>
        </div>
      </div>
    </div>
  );
}

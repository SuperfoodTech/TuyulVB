const TABS = [
  {
    id: "merchant",
    label: "Merchant Dashboard",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    id: "admin",
    label: "Admin Panel",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    id: "sessions",
    label: "Session Monitor",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
      </svg>
    ),
  },
  {
    id: "logs",
    label: "Audit Logs",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ),
  },
];

export default function NavHeader({
  activeTab,
  onTabChange,
  theme,
  onToggleTheme,
  currentUser,
  onOpenLogin,
  onLogout,
  apiConnected,
  onTriggerSync,
  syncing,
}) {
  return (
    <header className="sticky top-0 z-50 border-b border-red-100 bg-white/95 shadow-[0_8px_30px_-20px_rgba(127,29,29,0.45)] backdrop-blur-xl dark:border-white/5 dark:bg-black/20 dark:shadow-none dark:backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between py-3.5 sm:py-4">
          {/* Brand Logo */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-red-600 to-red-800 shadow-lg shadow-red-900/20 dark:from-zinc-800 dark:to-zinc-950 dark:border dark:border-zinc-700 dark:shadow-none">
              <svg className="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M8.1 13.34l2.83-2.83L3.91 3.5a4.008 4.008 0 000 5.66l4.19 4.18zm6.78-1.81c1.53.71 3.68.21 5.27-1.38 1.91-1.91 2.28-4.65.81-6.12-1.46-1.46-4.2-1.1-6.12.81-1.59 1.59-2.09 3.74-1.38 5.27L3.7 19.87l1.41 1.41L12 14.41l6.88 6.88 1.41-1.41L13.41 13l1.47-1.47z" />
              </svg>
            </div>
            <div>
              <h1 className="text-base font-bold leading-tight tracking-tight text-slate-900 dark:text-white sm:text-lg">
                FoodMaster
                <span className="text-red-700 dark:text-red-400"> Auto Open/Close</span>
              </h1>
              <p className="mt-0.5 hidden text-[13px] text-slate-500 dark:text-zinc-400 sm:block">
                ShopeeFood Vercel Toggle &amp; Priority Engine
              </p>
            </div>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            {/* API Status Pill */}
            <span className={`hidden sm:inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold ${
              apiConnected
                ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400"
                : "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400"
            }`}>
              <span className={`h-1.5 w-1.5 rounded-full ${apiConnected ? "bg-emerald-500" : "bg-amber-500"}`} />
              {apiConnected ? "API Connected" : "Local Mode"}
            </span>

            {/* Sync Bot Button */}
            <button
              type="button"
              onClick={onTriggerSync}
              disabled={syncing}
              title="Pemicu Pengecekan Toko Sekarang"
              className="hidden sm:flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-red-50 hover:text-red-700 hover:border-red-200 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800 dark:hover:text-white disabled:opacity-50"
            >
              <svg className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" />
              </svg>
              {syncing ? "Syncing..." : "Sync Bot"}
            </button>

            {/* Theme Toggle */}
            <button
              type="button"
              onClick={onToggleTheme}
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-100 hover:text-slate-900 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800 dark:hover:text-white"
              title={theme === "dark" ? "Beralih ke Mode Terang" : "Beralih ke Mode Gelap"}
            >
              {theme === "dark" ? (
                <>
                  <svg className="h-4 w-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                  <span className="hidden sm:inline">Light</span>
                </>
              ) : (
                <>
                  <svg className="h-4 w-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                  <span className="hidden sm:inline">Dark</span>
                </>
              )}
            </button>

            {/* User Auth */}
            {currentUser ? (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-zinc-800">
                <span className="hidden sm:block text-xs font-semibold text-slate-700 dark:text-zinc-200 capitalize">
                  {currentUser.role}: {currentUser.name}
                </span>
                <button
                  onClick={onLogout}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-red-50 hover:text-red-700 hover:border-red-200 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenLogin}
                className="inline-flex items-center gap-1.5 rounded-xl bg-red-700 px-3.5 py-1.5 text-xs font-bold text-white shadow-md shadow-red-900/15 transition hover:bg-red-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200 dark:shadow-none"
              >
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                Masuk / Login
              </button>
            )}
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-3 sm:mx-0 sm:px-0" aria-label="Navigasi utama">
          {TABS.map((tab) => (
            <button
              type="button"
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              aria-current={activeTab === tab.id ? "page" : undefined}
              className={`
                group relative flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-[15px] font-semibold transition-all
                ${activeTab === tab.id
                  ? "bg-red-700 text-white shadow-md shadow-red-900/15 dark:bg-white dark:text-black dark:shadow-none"
                  : "text-slate-600 hover:bg-red-50 hover:text-red-700 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-white"
                }
              `}
            >
              <span className={activeTab === tab.id ? "text-white dark:text-black" : "text-slate-400 group-hover:text-red-600 dark:text-zinc-500 dark:group-hover:text-white"}>
                {tab.icon}
              </span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}

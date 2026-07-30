import React from "react";
import { Moon, Sun, Shield, Lock, Activity, Store, RefreshCw, CheckCircle, XCircle } from "lucide-react";

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
  syncing
}) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-rose-100 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md transition-colors">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        
        {/* Brand Logo & Status */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-rose-600 to-rose-500 text-white shadow-md shadow-rose-500/20">
            <Store className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                FoodMaster <span className="text-rose-600 dark:text-rose-500">Auto Open/Close</span>
              </h1>
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                apiConnected ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400" : "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400"
              }`}>
                {apiConnected ? <CheckCircle className="h-3 w-3 text-emerald-500" /> : <XCircle className="h-3 w-3 text-amber-500" />}
                {apiConnected ? "API Connected" : "Local Mode"}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              ShopeeFood Vercel Toggle & Priority Engine Automation
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1 rounded-xl bg-rose-50/70 p-1 dark:bg-slate-800/60 border border-rose-100/50 dark:border-slate-700/50">
          <button
            onClick={() => onTabChange("merchant")}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
              activeTab === "merchant"
                ? "bg-white text-rose-600 shadow-sm dark:bg-slate-900 dark:text-rose-400"
                : "text-slate-600 hover:text-rose-600 dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            <Store className="h-4 w-4" />
            Merchant Dashboard
          </button>

          <button
            onClick={() => onTabChange("admin")}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
              activeTab === "admin"
                ? "bg-white text-rose-600 shadow-sm dark:bg-slate-900 dark:text-rose-400"
                : "text-slate-600 hover:text-rose-600 dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            <Shield className="h-4 w-4" />
            Admin Panel
          </button>

          <button
            onClick={() => onTabChange("logs")}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
              activeTab === "logs"
                ? "bg-white text-rose-600 shadow-sm dark:bg-slate-900 dark:text-rose-400"
                : "text-slate-600 hover:text-rose-600 dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            <Activity className="h-4 w-4" />
            Audit Logs
          </button>
        </nav>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Force Sync Trigger Button */}
          <button
            onClick={onTriggerSync}
            disabled={syncing}
            title="Pemicu Pengecekan Toko Sekarang"
            className="hidden sm:inline-flex items-center gap-1.5 rounded-xl bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:bg-rose-950/40 dark:text-rose-300 dark:hover:bg-rose-900/60 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing..." : "Sync Bot"}
          </button>

          {/* Theme Switcher */}
          <button
            onClick={onToggleTheme}
            className="rounded-xl border border-slate-200 p-2 text-slate-600 hover:bg-slate-100 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 transition-colors"
            title="Ganti Tema Dark/Light"
          >
            {theme === "dark" ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-600" />}
          </button>

          {/* User Auth Info */}
          {currentUser ? (
            <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-slate-800">
              <div className="text-right text-xs">
                <span className="font-semibold block text-slate-800 dark:text-white capitalize">
                  {currentUser.role}: {currentUser.name}
                </span>
              </div>
              <button
                onClick={onLogout}
                className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 transition-colors"
              >
                Logout
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenLogin}
              className="inline-flex items-center gap-1.5 rounded-xl bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-rose-600/20 hover:bg-rose-700 transition-all"
            >
              <Lock className="h-3.5 w-3.5" />
              Masuk / Login
            </button>
          )}
        </div>

      </div>
    </header>
  );
}

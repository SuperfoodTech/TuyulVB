import { useState } from "react";
import StarField from "./StarField";

export default function LoginPage({ theme, onToggleTheme, onLoginSuccess }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      if (password === "admin" || password === "foodmaster2026") {
        onLoginSuccess({ role: "admin", name: "Admin FoodMaster", portal: null });
      } else {
        setError("Password Admin salah. Hubungi administrator FoodMaster.");
      }
    }, 400);
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-[#fff9f8] dark:bg-black transition-colors duration-200 px-4">
      <StarField active={theme === "dark"} />

      {/* Theme Toggle */}
      <div className="absolute top-4 right-4 z-10">
        <button
          type="button"
          onClick={onToggleTheme}
          className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-100 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
          title={theme === "dark" ? "Beralih ke Mode Terang" : "Beralih ke Mode Gelap"}
        >
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </div>

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md">
        {/* Brand Header */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-600 to-red-800 shadow-xl shadow-red-900/25 dark:from-zinc-800 dark:to-zinc-950 dark:border dark:border-zinc-700">
            <svg className="h-8 w-8 text-white" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8.1 13.34l2.83-2.83L3.91 3.5a4.008 4.008 0 000 5.66l4.19 4.18zm6.78-1.81c1.53.71 3.68.21 5.27-1.38 1.91-1.91 2.28-4.65.81-6.12-1.46-1.46-4.2-1.1-6.12.81-1.59 1.59-2.09 3.74-1.38 5.27L3.7 19.87l1.41 1.41L12 14.41l6.88 6.88 1.41-1.41L13.41 13l1.47-1.47z" />
            </svg>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
            FoodMaster Admin
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
            Auto Open &amp; Close ShopeeFood Engine
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-red-100 bg-white shadow-[0_24px_60px_-20px_rgba(127,29,29,0.35)] dark:border-zinc-800 dark:bg-zinc-950 dark:shadow-none p-6 space-y-4">
          <div className="rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 p-3 flex items-start gap-2">
            <svg className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-[12px] text-amber-800 dark:text-amber-300">
              Merchant dapat mengakses dashboard langsung melalui <strong>link khusus</strong> yang diberikan Admin.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[13px] font-semibold text-slate-600 dark:text-zinc-400 mb-1.5">
                Password Admin Internal:
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-3.5 flex items-center text-slate-400 pointer-events-none">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </span>
                <input
                  type="password"
                  placeholder="Masukkan password admin FoodMaster"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field-control pl-10"
                  autoFocus
                  autoComplete="current-password"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 p-3 flex items-center gap-2">
                <svg className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-[13px] font-semibold text-red-700 dark:text-red-400">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="primary-action w-full py-3 text-[14px] gap-2"
            >
              {isLoading ? "Memverifikasi..." : "Masuk ke Admin Panel"}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-[12px] text-slate-400 dark:text-zinc-600">
          FoodMaster Auto Open/Close &copy; {new Date().getFullYear()} &mdash; ShopeeFood Priority Engine
        </p>
      </div>
    </div>
  );
}

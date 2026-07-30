import { useState } from "react";
import StarField from "./StarField";

export default function MerchantTokenLoginPage({ theme, onToggleTheme, outletInfo, merchantStores = [], onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const expectedUsername = (outletInfo.merchant_username || outletInfo.owner_name || outletInfo.outlet_short_name || "").toLowerCase().trim();
  const expectedPassword = outletInfo.merchant_password || "foodmaster123";

  const storeCount = merchantStores.length || 1;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      const enteredUser = username.toLowerCase().trim();

      if (enteredUser === expectedUsername && password === expectedPassword) {
        onLoginSuccess({
          role: "merchant",
          name: outletInfo.owner_name || outletInfo.portal_name,
          portal: outletInfo.merchant_id,
          merchant_id: outletInfo.merchant_id
        });
      } else {
        setError("Username atau Password merchant salah. Silakan periksa kembali kredensial yang diberikan oleh Admin.");
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
        >
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-600 to-red-800 shadow-xl shadow-red-900/25 dark:from-zinc-800 dark:to-zinc-950 dark:border dark:border-zinc-700">
            <svg className="h-8 w-8 text-white" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8.1 13.34l2.83-2.83L3.91 3.5a4.008 4.008 0 000 5.66l4.19 4.18zm6.78-1.81c1.53.71 3.68.21 5.27-1.38 1.91-1.91 2.28-4.65.81-6.12-1.46-1.46-4.2-1.1-6.12.81-1.59 1.59-2.09 3.74-1.38 5.27L3.7 19.87l1.41 1.41L12 14.41l6.88 6.88 1.41-1.41L13.41 13l1.47-1.47z" />
            </svg>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white">
            FoodMaster Merchant
          </h1>
          <p className="text-xs text-slate-400 dark:text-zinc-500 mt-0.5">
            Verifikasi Keamanan Akses Akun Merchant
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-red-100 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-950 space-y-4">

          {/* Merchant ID Target Badge */}
          <div className="rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 p-3 text-left">
            <span className="text-[10px] font-bold uppercase tracking-wider text-red-700 dark:text-red-400 block">
              Akun Merchant Terverifikasi:
            </span>
            <p className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">
              {outletInfo.owner_name || outletInfo.portal_name}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-zinc-400 flex items-center gap-1 mt-0.5">
              Merchant ID: <code className="font-mono font-bold text-slate-800 dark:text-zinc-200">{outletInfo.merchant_id}</code>
              <span>&bull;</span>
              <span>{storeCount} Outlet Terdaftar</span>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-zinc-300 mb-1">
                Username Merchant:
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-3.5 flex items-center text-slate-400 pointer-events-none">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </span>
                <input
                  type="text"
                  placeholder="Masukkan username merchant"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="field-control pl-10"
                  autoFocus
                  required
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-zinc-300 mb-1">
                Password Merchant:
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-3.5 flex items-center text-slate-400 pointer-events-none">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </span>
                <input
                  type="password"
                  placeholder="Masukkan password merchant"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field-control pl-10"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 p-3 flex items-center gap-2">
                <svg className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-[12px] font-semibold text-red-700 dark:text-red-400">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="primary-action w-full py-3 text-xs gap-2"
            >
              {isLoading ? "Memverifikasi..." : "Masuk ke Dashboard Merchant"}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-[12px] text-slate-400 dark:text-zinc-600">
          FoodMaster Auto Open/Close &copy; {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}

import StarField from "./StarField";

export default function ExpiredAccessPage({ theme, onToggleTheme, reason, outletInfo }) {
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

      <div className="relative z-10 w-full max-w-md text-center">
        {/* Brand Header */}
        <div className="mb-6">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-600 to-red-800 shadow-xl shadow-red-900/25 dark:from-zinc-800 dark:to-zinc-950 dark:border dark:border-zinc-700">
            <svg className="h-8 w-8 text-white" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8.1 13.34l2.83-2.83L3.91 3.5a4.008 4.008 0 000 5.66l4.19 4.18zm6.78-1.81c1.53.71 3.68.21 5.27-1.38 1.91-1.91 2.28-4.65.81-6.12-1.46-1.46-4.2-1.1-6.12.81-1.59 1.59-2.09 3.74-1.38 5.27L3.7 19.87l1.41 1.41L12 14.41l6.88 6.88 1.41-1.41L13.41 13l1.47-1.47z" />
            </svg>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white">
            FoodMaster
          </h1>
          <p className="text-xs text-slate-400 dark:text-zinc-500 mt-0.5">
            ShopeeFood Priority Engine
          </p>
        </div>

        {/* Expired Card */}
        <div className="rounded-2xl border border-red-200 bg-white p-6 shadow-xl dark:border-red-950 dark:bg-zinc-950 space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>

          <h2 className="text-lg font-bold text-slate-900 dark:text-white">
            Akses Merchant Tidak Aktif / Masa Tenggang Habis
          </h2>

          {outletInfo && (
            <div className="rounded-xl bg-slate-50 dark:bg-zinc-900 p-3 text-left text-xs space-y-1">
              <p className="font-bold text-slate-800 dark:text-white">{outletInfo.outlet_long_name || outletInfo.portal_name}</p>
              <p className="text-slate-500 dark:text-zinc-400">Store ID: {outletInfo.store_id}</p>
              {outletInfo.subscription_end && (
                <p className="text-red-600 dark:text-red-400 font-semibold">
                  Masa Berlaku: {new Date(outletInfo.subscription_end).toLocaleDateString("id-ID")} (Expired)
                </p>
              )}
            </div>
          )}

          <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
            {reason || "Masa berlaku langganan atau link akses khusus merchant Anda telah berakhir. Silakan hubungi Admin FoodMaster untuk perpanjangan layanan Auto Open/Close ShopeeFood."}
          </p>

          <div className="pt-2">
            <a
              href="https://wa.me/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 py-3 text-xs font-bold text-white shadow-md transition-all"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l.999 1.59-1.05 3.834 3.794-.993z" />
              </svg>
              Hubungi Admin via WhatsApp
            </a>
          </div>
        </div>

        <p className="mt-6 text-[11px] text-slate-400 dark:text-zinc-600">
          FoodMaster Auto Open/Close &copy; {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}

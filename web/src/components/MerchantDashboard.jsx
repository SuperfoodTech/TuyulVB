import { useState } from "react";

export default function MerchantDashboard({ outlets, onToggleVercel, onRefresh, loading }) {
  const [selectedDuration, setSelectedDuration] = useState({});

  const handleToggleClick = (storeId, currentToggle) => {
    const duration = selectedDuration[storeId] || "full_day";
    onToggleVercel(storeId, !currentToggle, duration);
  };

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="surface-card p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">
              Dashboard Merchant ShopeeFood
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
              Kelola <strong>Vercel Toggle</strong> sebagai <em>Source of Truth</em> status operasional outlet ShopeeFood Anda.
            </p>
          </div>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="secondary-action gap-1.5 self-start sm:self-auto disabled:opacity-50"
          >
            <svg className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" />
            </svg>
            Refresh Status
          </button>
        </div>
      </div>

      {/* Outlets Grid */}
      {outlets.length === 0 ? (
        <div className="surface-card p-12 text-center">
          <svg className="mx-auto h-10 w-10 text-slate-300 dark:text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <p className="mt-3 text-sm font-semibold text-slate-500 dark:text-zinc-400">Tidak ada outlet terhubung.</p>
          <p className="text-xs text-slate-400 dark:text-zinc-500">Hubungi Admin FoodMaster untuk menambahkan outlet baru.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {outlets.map((outlet) => {
            const isSuspended = outlet.suspension_status === true || outlet.suspension_status === "Ya";
            const isSubActive = outlet.subscription_status === "Active";
            const isVercelOn = outlet.vercel_toggle === true || outlet.vercel_toggle === "ON";
            const isShopeeOn = outlet.shopee_toggle_last === true || outlet.shopee_toggle_last === "ON";

            return (
              <div
                key={outlet.store_id}
                className={`relative overflow-hidden rounded-2xl border transition-all duration-200 ${
                  isSuspended
                    ? "border-amber-200 bg-amber-50/30 dark:border-amber-900/40 dark:bg-amber-950/10"
                    : "border-red-100 bg-white shadow-[0_16px_45px_-30px_rgba(127,29,29,0.45)] dark:border-transparent dark:bg-transparent dark:shadow-none"
                }`}
              >
                {/* Status stripe */}
                <div className={`h-1 w-full ${isSuspended ? "bg-amber-500" : isVercelOn ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-700"}`} />

                <div className="p-6">
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <span className="text-[11px] font-bold text-red-700 dark:text-red-400 uppercase tracking-wider">
                        {outlet.portal_name || "FoodMaster Outlet"}
                      </span>
                      <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-0.5 leading-tight">
                        {outlet.outlet_long_name || outlet.outlet_short_name}
                      </h3>
                      <p className="text-[12px] text-slate-500 dark:text-zinc-500 mt-0.5">
                        Store ID:{" "}
                        <code className="rounded bg-red-50 px-1.5 py-0.5 font-mono text-red-700 dark:bg-zinc-800 dark:text-zinc-300">
                          {outlet.store_id}
                        </code>{" "}
                        &nbsp;|&nbsp; Merchant ID:{" "}
                        <code className="rounded bg-red-50 px-1.5 py-0.5 font-mono text-red-700 dark:bg-zinc-800 dark:text-zinc-300">
                          {outlet.merchant_id}
                        </code>
                      </p>
                    </div>

                    {/* Power Toggle */}
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <button
                        disabled={isSuspended}
                        onClick={() => handleToggleClick(outlet.store_id, isVercelOn)}
                        className={`flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-md transition-all ${
                          isSuspended
                            ? "bg-slate-200 dark:bg-zinc-800 cursor-not-allowed text-slate-400 dark:text-zinc-600"
                            : isVercelOn
                            ? "bg-emerald-500 hover:bg-emerald-600 shadow-emerald-500/30"
                            : "bg-zinc-700 hover:bg-zinc-800 dark:bg-zinc-700 dark:hover:bg-zinc-600 shadow-zinc-700/30"
                        }`}
                        title={
                          isSuspended
                            ? "Toko Ditangguhkan oleh Admin"
                            : isVercelOn
                            ? "Matikan Vercel Toggle"
                            : "Nyalakan Vercel Toggle"
                        }
                      >
                        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42A6.92 6.92 0 0119 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.28 1.09-4.3 2.58-5.42L6.17 5.17A8.932 8.932 0 002 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.73-1.22-5.18-3.17-6.83z" />
                        </svg>
                      </button>
                      <span className={`text-[10px] font-bold tracking-wider uppercase ${
                        isVercelOn ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-500 dark:text-zinc-500"
                      }`}>
                        VERCEL {isVercelOn ? "ON" : "OFF"}
                      </span>
                    </div>
                  </div>

                  {/* Duration picker (when OFF) */}
                  {!isVercelOn && !isSuspended && (
                    <div className="mt-4 rounded-xl bg-slate-50 dark:bg-zinc-900 p-3 border border-slate-100 dark:border-zinc-800">
                      <label className="block text-[11px] font-bold text-slate-600 dark:text-zinc-400 mb-1.5 uppercase tracking-wide">
                        Durasi Tutup Sementara:
                      </label>
                      <div className="grid grid-cols-4 gap-1.5">
                        {["30m", "60m", "full_day", "custom"].map((dur) => (
                          <button
                            key={dur}
                            type="button"
                            onClick={() => setSelectedDuration({ ...selectedDuration, [outlet.store_id]: dur })}
                            className={`rounded-lg py-1 text-center text-[12px] font-semibold transition-all ${
                              (selectedDuration[outlet.store_id] || "full_day") === dur
                                ? "bg-red-700 text-white dark:bg-white dark:text-black"
                                : "bg-white dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 border border-slate-200 dark:border-zinc-700 hover:border-red-200 hover:text-red-700"
                            }`}
                          >
                            {dur === "30m" ? "30 Mnt" : dur === "60m" ? "60 Mnt" : dur === "full_day" ? "Hari Ini" : "Lainnya"}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suspension Alert */}
                  {isSuspended && (
                    <div className="mt-4 flex items-start gap-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 p-3 text-amber-800 dark:text-amber-300 border border-amber-200/70 dark:border-amber-900/50 text-[12px]">
                      <svg className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <div>
                        <span className="font-bold block">Status Outlet: DITANGGUHKAN ADMIN</span>
                        <span>Alasan: {outlet.suspension_reason || "Kewajiban penangguhan FoodMaster"}. Bot akan menjaga outlet tetap TUTUP.</span>
                      </div>
                    </div>
                  )}

                  {/* Metadata grid */}
                  <div className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-[12.5px] border-t border-red-100/60 dark:border-zinc-800 pt-4">
                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block">Jam Operasional:</span>
                      <span className="font-semibold text-slate-700 dark:text-zinc-200 inline-flex items-center gap-1 mt-0.5">
                        <svg className="h-3.5 w-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {outlet.open_time || "08:00"} - {outlet.close_time || "22:00"}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block">Status ShopeePartner:</span>
                      <span className={`font-semibold inline-flex items-center gap-1 mt-0.5 ${
                        isShopeeOn ? "text-emerald-700 dark:text-emerald-400" : "text-slate-500 dark:text-zinc-500"
                      }`}>
                        {isShopeeOn ? (
                          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        ) : (
                          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        )}
                        {isShopeeOn ? "Toko Terbuka (ON)" : "Toko Tertutup (OFF)"}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block">Subscription Auto Open:</span>
                      <span className={`font-semibold inline-flex items-center gap-1 mt-0.5 ${
                        isSubActive ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400"
                      }`}>
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {outlet.subscription_package || "3 Bulan"} ({isSubActive ? "Aktif" : "Expired"})
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block">Pengecekan Bot Terakhir:</span>
                      <span className="font-medium text-slate-600 dark:text-zinc-400 mt-0.5 block">
                        {outlet.last_checked_at
                          ? new Date(outlet.last_checked_at).toLocaleTimeString("id-ID")
                          : "Baru Saja"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

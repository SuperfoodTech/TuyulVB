import { useState } from "react";
import { formatOperatingDays, formatDateID, getSubscriptionInfo, getTodayOperatingHours } from "../utils/outletUtils";
import ScheduleModal from "./ScheduleModal";

export default function MerchantDashboard({ outlets, onToggleVercel, onRefresh, loading, currentUser }) {
  // Modal state untuk "Atur Durasi Tutup Sementara"
  const [closingOutlet, setClosingOutlet] = useState(null);
  const [selectedDuration, setSelectedDuration] = useState("30m");

  // Modal state untuk "Jadwal 7 Hari"
  const [viewScheduleOutlet, setViewScheduleOutlet] = useState(null);

  const isMerchant = currentUser?.role === "merchant";

  const handleOpenCloseModal = (outlet) => {
    setSelectedDuration("30m");
    setClosingOutlet(outlet);
  };

  const handleConfirmClose = () => {
    if (!closingOutlet) return;
    onToggleVercel(closingOutlet.store_id, false, selectedDuration);
    setClosingOutlet(null);
  };

  const handleOpenOutletDirect = (storeId) => {
    onToggleVercel(storeId, true, "full_day");
  };

  return (
    <div className="space-y-6">

      {/* Header Banner */}
      <div className="surface-card p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            {isMerchant ? (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 dark:bg-red-950/30 px-2.5 py-1 text-[11px] font-bold text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50">
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    {currentUser.portal || currentUser.name}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-800 dark:text-white">
                  Outlet Saya
                </h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
                  Kelola status buka/tutup outlet ShopeeFood Anda melalui <strong>Vercel Toggle</strong>.
                </p>
              </>
            ) : (
              <>
                <h2 className="text-xl font-bold text-slate-800 dark:text-white">
                  Dashboard Semua Outlet
                  <span className="ml-2 inline-flex items-center rounded-full bg-slate-100 dark:bg-zinc-800 px-2.5 py-0.5 text-[13px] font-bold text-slate-600 dark:text-zinc-300">
                    {outlets.length}
                  </span>
                </h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
                  Kelola <strong>Vercel Toggle</strong> sebagai <em>Source of Truth</em> status operasional outlet ShopeeFood.
                </p>
              </>
            )}
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

      {/* Outlets List */}
      {outlets.length === 0 ? (
        <div className="surface-card p-12 text-center">
          <svg className="mx-auto h-10 w-10 text-slate-300 dark:text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <p className="mt-3 text-sm font-semibold text-slate-500 dark:text-zinc-400">
            {isMerchant ? `Tidak ada outlet ditemukan untuk portal ini.` : "Tidak ada outlet terhubung."}
          </p>
          <p className="text-xs text-slate-400 dark:text-zinc-500">
            {isMerchant
              ? `Pastikan portal "${currentUser?.portal}" sudah terdaftar atau hubungi Admin FoodMaster.`
              : "Hubungi Admin FoodMaster untuk menambahkan outlet baru."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {outlets.map((outlet) => {
            const isSuspended = outlet.suspension_status === true || outlet.suspension_status === "Ya";
            const isSubActive = outlet.subscription_status === "Active";
            const isVercelOn = outlet.vercel_toggle === true || outlet.vercel_toggle === "ON";
            const isShopeeOn = outlet.shopee_toggle_last === true || outlet.shopee_toggle_last === "ON";
            const subInfo = getSubscriptionInfo(outlet.subscription_end);
            const todayInfo = getTodayOperatingHours(outlet);

            return (
              <div
                key={outlet.store_id}
                className={`relative overflow-hidden rounded-2xl border transition-all duration-200 ${
                  isSuspended
                    ? "border-amber-200 bg-amber-50/30 dark:border-amber-900/40 dark:bg-amber-950/10"
                    : "border-slate-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
                }`}
              >
                {/* Header bar */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between px-6 py-4 border-b border-slate-100 dark:border-zinc-800/80 gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                      {outlet.outlet_long_name || outlet.outlet_short_name}, {outlet.portal_name || "Merchant"}
                    </h3>
                    <span className="text-slate-400 dark:text-zinc-600 font-bold">&bull;</span>
                    {isSuspended ? (
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-600 dark:text-amber-400">
                        <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                        Ditangguhkan
                      </span>
                    ) : isVercelOn ? (
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        <span className="h-2 w-2 rounded-full bg-emerald-500" />
                        Buka
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-red-500 dark:text-red-400">
                        <span className="h-2 w-2 rounded-full bg-red-500" />
                        Tutup Sementara
                      </span>
                    )}
                  </div>

                  {/* Single Action Button */}
                  <div className="shrink-0">
                    {isSuspended ? (
                      <button
                        disabled
                        className="rounded-lg border border-slate-200 bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-400 cursor-not-allowed dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-600"
                      >
                        Ditangguhkan
                      </button>
                    ) : isVercelOn ? (
                      <button
                        type="button"
                        onClick={() => handleOpenCloseModal(outlet)}
                        className="rounded-lg border border-red-400 bg-white px-4 py-2 text-xs font-semibold text-red-500 hover:bg-red-50 dark:border-red-500/60 dark:bg-transparent dark:text-red-400 dark:hover:bg-red-950/30 transition-all shadow-sm"
                      >
                        Tutup Outlet Sementara
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleOpenOutletDirect(outlet.store_id)}
                        className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 transition-all shadow-sm"
                      >
                        Buka Outlet Sekarang
                      </button>
                    )}
                  </div>
                </div>

                {/* Details Section */}
                <div className="p-6">
                  {/* Suspension Alert */}
                  {isSuspended && (
                    <div className="mb-4 flex items-start gap-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 p-3 text-amber-800 dark:text-amber-300 border border-amber-200/70 dark:border-amber-900/50 text-[12px]">
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
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[12.5px]">
                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block text-[11px] uppercase tracking-wider font-semibold">Store &amp; Merchant ID</span>
                      <span className="font-mono font-bold text-slate-800 dark:text-white block mt-0.5">
                        {outlet.store_id} / {outlet.merchant_id}
                      </span>
                    </div>

                    {/* JAM OPERASIONAL: Jam Hari Ini + Link Jadwal 7 Hari */}
                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block text-[11px] uppercase tracking-wider font-semibold">
                        Jam Operasional
                      </span>
                      <div className="mt-0.5">
                        <span className="font-bold text-slate-800 dark:text-white block">
                          Hari Ini ({todayInfo.todayName}): {todayInfo.hoursText}
                        </span>
                        <button
                          type="button"
                          onClick={() => setViewScheduleOutlet(outlet)}
                          className="text-[11.5px] font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 inline-flex items-center gap-1 transition-colors mt-0.5"
                        >
                          Lihat Jadwal 7 Hari &rsaquo;
                        </button>
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block text-[11px] uppercase tracking-wider font-semibold">Status ShopeePartner</span>
                      <span className={`font-semibold inline-flex items-center gap-1 mt-0.5 ${
                        isShopeeOn ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500 dark:text-zinc-400"
                      }`}>
                        {isShopeeOn ? "Terbuka (ON)" : "Tertutup (OFF)"}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 dark:text-zinc-500 block text-[11px] uppercase tracking-wider font-semibold">Subscription</span>
                      <span className={`font-semibold inline-flex items-center gap-1 mt-0.5 ${
                        isSubActive ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"
                      }`}>
                        {outlet.subscription_package || "3 Bulan"} ({isSubActive ? "Aktif" : "Expired"})
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* MODAL: Atur Durasi Tutup Sementara */}
      {closingOutlet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="animate-scale-up w-full max-w-2xl rounded-2xl bg-white dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 p-6 sm:p-8 shadow-2xl space-y-8">

            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Atur Durasi Tutup Sementara
              </h3>
              <button
                type="button"
                onClick={() => setClosingOutlet(null)}
                className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex flex-wrap sm:flex-nowrap items-center justify-between gap-4 py-2">
              {[
                { id: "30m", label: "30 menit" },
                { id: "60m", label: "60 menit" },
                { id: "full_day", label: "Sepanjang Hari" },
                { id: "custom", label: "Waktu Lain" },
              ].map((opt) => (
                <label
                  key={opt.id}
                  className="flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-zinc-200 cursor-pointer whitespace-nowrap select-none"
                >
                  <input
                    type="radio"
                    name="duration"
                    value={opt.id}
                    checked={selectedDuration === opt.id}
                    onChange={() => setSelectedDuration(opt.id)}
                    className="accent-[#ee4d2d] h-4 w-4 cursor-pointer"
                  />
                  <span className={selectedDuration === opt.id ? "font-bold text-slate-900 dark:text-white" : ""}>
                    {opt.label}
                  </span>
                </label>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2">
              <button
                type="button"
                onClick={() => setClosingOutlet(null)}
                className="w-full rounded-md border border-slate-300 bg-white py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 transition-all text-center"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleConfirmClose}
                className="w-full rounded-md bg-[#ee4d2d] hover:bg-[#d73d1f] py-3 text-sm font-bold text-white shadow-sm transition-all text-center"
              >
                Konfirmasi
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ScheduleModal (Jadwal 7 Hari Lengkap) */}
      {viewScheduleOutlet && (
        <ScheduleModal
          outlet={viewScheduleOutlet}
          onClose={() => setViewScheduleOutlet(null)}
        />
      )}
    </div>
  );
}

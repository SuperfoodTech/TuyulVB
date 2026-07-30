import React, { useState } from "react";
import { Power, Clock, Store, AlertTriangle, CheckCircle2, XCircle, RefreshCw, ShieldAlert, Calendar } from "lucide-react";

export default function MerchantDashboard({ outlets, onToggleVercel, onRefresh, loading }) {
  const [selectedDuration, setSelectedDuration] = useState({});

  const handleToggleClick = (storeId, currentToggle) => {
    const duration = selectedDuration[storeId] || "full_day";
    onToggleVercel(storeId, !currentToggle, duration);
  };

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="rounded-2xl border border-rose-100 dark:border-slate-800 bg-gradient-to-r from-rose-50/60 via-white to-orange-50/50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800/80 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-800 dark:text-white">
              Dashboard Merchant ShopeeFood
            </h2>
            <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
              Kelola **Vercel Toggle** sebagai *Source of Truth* status operasional outlet ShopeeFood Anda.
            </p>
          </div>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 shadow-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh Status
          </button>
        </div>
      </div>

      {/* Outlets Grid */}
      {outlets.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 p-12 text-center">
          <Store className="mx-auto h-10 w-10 text-slate-400" />
          <p className="mt-2 text-sm font-semibold text-slate-600 dark:text-slate-400">
            Tidak ada outlet terhubung.
          </p>
          <p className="text-xs text-slate-400">Hubungi Admin FoodMaster untuk menambahkan outlet baru.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {outlets.map((outlet) => {
            const isSuspended = outlet.suspension_status === true || outlet.suspension_status === "Ya";
            const isSubActive = outlet.subscription_status === "Active";
            const isVercelOn = outlet.vercel_toggle === true || outlet.vercel_toggle === "ON";
            const isShopeeOn = outlet.shopee_toggle_last === true || outlet.shopee_toggle_last === "ON";

            return (
              <div
                key={outlet.store_id}
                className={`relative overflow-hidden rounded-2xl border transition-all duration-200 shadow-sm hover:shadow-md ${
                  isSuspended
                    ? "border-amber-200 bg-amber-50/20 dark:border-amber-900/50 dark:bg-amber-950/10"
                    : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
                }`}
              >
                {/* Status Bar Indicator */}
                <div className={`h-1.5 w-full ${isSuspended ? "bg-amber-500" : isVercelOn ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-700"}`} />

                <div className="p-6">
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
                        {outlet.portal_name || "FoodMaster Outlet"}
                      </span>
                      <h3 className="text-lg font-bold text-slate-800 dark:text-white mt-0.5">
                        {outlet.outlet_long_name || outlet.outlet_short_name}
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Store ID: <code className="rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 font-mono text-slate-700 dark:text-slate-300">{outlet.store_id}</code> | Merchant ID: <code className="rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 font-mono text-slate-700 dark:text-slate-300">{outlet.merchant_id}</code>
                      </p>
                    </div>

                    {/* Vercel Toggle Master Power Button */}
                    <div className="flex flex-col items-end gap-1">
                      <button
                        disabled={isSuspended}
                        onClick={() => handleToggleClick(outlet.store_id, isVercelOn)}
                        className={`flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-md transition-all ${
                          isSuspended
                            ? "bg-slate-300 dark:bg-slate-800 cursor-not-allowed text-slate-400"
                            : isVercelOn
                            ? "bg-emerald-500 hover:bg-emerald-600 shadow-emerald-500/30"
                            : "bg-slate-700 hover:bg-slate-800 shadow-slate-700/30"
                        }`}
                        title={isSuspended ? "Toko Ditangguhkan oleh Admin" : isVercelOn ? "Matikan Vercel Toggle" : "Nyalakan Vercel Toggle"}
                      >
                        <Power className="h-6 w-6" />
                      </button>
                      <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                        Vercel {isVercelOn ? "ON" : "OFF"}
                      </span>
                    </div>
                  </div>

                  {/* Pause Duration Selection (When turning OFF) */}
                  {!isVercelOn && !isSuspended && (
                    <div className="mt-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 p-3 border border-slate-100 dark:border-slate-700/50">
                      <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1.5">
                        Pilihan Durasi Tutup Sementara:
                      </label>
                      <div className="grid grid-cols-4 gap-1.5">
                        {["30m", "60m", "full_day", "custom"].map((dur) => (
                          <button
                            key={dur}
                            type="button"
                            onClick={() => setSelectedDuration({ ...selectedDuration, [outlet.store_id]: dur })}
                            className={`rounded-lg py-1 text-center text-xs font-semibold transition-all ${
                              (selectedDuration[outlet.store_id] || "full_day") === dur
                                ? "bg-rose-600 text-white shadow-sm"
                                : "bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600"
                            }`}
                          >
                            {dur === "30m" ? "30 Menit" : dur === "60m" ? "60 Menit" : dur === "full_day" ? "Sepanjang Hari" : "Waktu Lain"}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suspension Warning Alert */}
                  {isSuspended && (
                    <div className="mt-4 flex items-start gap-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 p-3 text-amber-800 dark:text-amber-300 border border-amber-200/60 dark:border-amber-900/60 text-xs">
                      <ShieldAlert className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
                      <div>
                        <span className="font-bold block">Status Outlet: DITANGGUHKAN ADMIN</span>
                        <span>Alasan: {outlet.suspension_reason || "Kewajiban penangguhan FoodMaster"}. Bot akan menjaga outlet tetap TUTUP.</span>
                      </div>
                    </div>
                  )}

                  {/* Outlet Details Metadata (Minimum 23 fields representation) */}
                  <div className="mt-5 grid grid-cols-2 gap-3 text-xs border-t border-slate-100 dark:border-slate-800 pt-4">
                    <div>
                      <span className="text-slate-400 block">Jam Operasional:</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-300 inline-flex items-center gap-1 mt-0.5">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        {outlet.open_time || "08:00"} - {outlet.close_time || "22:00"}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 block">Status ShopeePartner:</span>
                      <span className={`font-semibold inline-flex items-center gap-1 mt-0.5 ${
                        isShopeeOn ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500"
                      }`}>
                        {isShopeeOn ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                        {isShopeeOn ? "Toko Terbuka (ON)" : "Toko Tertutup (OFF)"}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 block">Subscription Auto Open:</span>
                      <span className={`font-semibold inline-flex items-center gap-1 mt-0.5 ${
                        isSubActive ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                      }`}>
                        <Calendar className="h-3.5 w-3.5" />
                        {outlet.subscription_package || "3 Bulan"} ({isSubActive ? "Aktif" : "Expired"})
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 block">Pengecekan Bot Terakhir:</span>
                      <span className="font-medium text-slate-600 dark:text-slate-400 mt-0.5 block">
                        {outlet.last_checked_at ? new Date(outlet.last_checked_at).toLocaleTimeString("id-ID") : "Baru Saja"}
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

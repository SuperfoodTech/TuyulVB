import { useState } from "react";
import { formatOperatingDays, formatDateID, getSubscriptionInfo, getTodayOperatingHours } from "../utils/outletUtils";
import ScheduleModal from "./ScheduleModal";

export default function AdminDashboard({ outlets, onUpdateOutlet, onRefresh, loading }) {
  const [editingStoreId, setEditingStoreId] = useState(null);
  const [formData, setFormData] = useState({});
  const [viewScheduleOutlet, setViewScheduleOutlet] = useState(null);

  const handleEditClick = (outlet) => {
    setEditingStoreId(outlet.store_id);
    setFormData({
      ...outlet,
      open_time: outlet.open_time || "08:00",
      close_time: outlet.close_time || "22:00",
      operating_days: outlet.operating_days || "1,2,3,4,5,6,7",
      friday_open_time: outlet.friday_open_time || "",
      weekend_open_time: outlet.weekend_open_time || ""
    });
  };

  const handleSave = (e) => {
    e.preventDefault();
    onUpdateOutlet(formData);
    setEditingStoreId(null);
  };

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="rounded-2xl border border-red-100 bg-white p-6 shadow-[0_16px_45px_-30px_rgba(127,29,29,0.45)] dark:border-transparent dark:bg-transparent dark:shadow-none">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-red-700 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <h2 className="text-xl font-bold text-slate-800 dark:text-white">
                Admin Panel FoodMaster Internal
              </h2>
            </div>
            <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
              Kelola <strong>Status Penangguhan</strong>, <strong>Jam Operasional Master</strong>, dan <strong>Masa Aktif Subscription</strong> outlet.
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
            Refresh
          </button>
        </div>
      </div>

      {/* Outlets Table */}
      <div className="overflow-hidden rounded-2xl border border-red-100 bg-white shadow-[0_16px_45px_-30px_rgba(127,29,29,0.45)] dark:border-transparent dark:bg-transparent dark:shadow-none">
        <div className="px-5 py-4 border-b border-red-50 dark:border-zinc-800 flex justify-between items-center">
          <h3 className="font-bold text-slate-800 dark:text-white text-sm">
            Daftar Seluruh Outlet ({outlets.length})
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead className="bg-slate-50 dark:bg-zinc-900/60 text-slate-500 dark:text-zinc-400 font-semibold border-b border-slate-100 dark:border-zinc-800 text-[12px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5 rounded-l-xl">Store ID / Merchant</th>
                <th className="px-4 py-3.5">Nama Outlet / Portal</th>
                <th className="px-4 py-3.5">Jam Operasional</th>
                <th className="px-4 py-3.5">Vercel Toggle</th>
                <th className="px-4 py-3.5">Status Penangguhan</th>
                <th className="px-4 py-3.5">Subscription Auto Open</th>
                <th className="px-4 py-3.5 text-right rounded-r-xl">Aksi Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-zinc-800 text-slate-700 dark:text-zinc-300">
              {outlets.map((o) => {
                const isSusp = o.suspension_status === true || o.suspension_status === "Ya";
                const isSubActive = o.subscription_status === "Active";
                const subInfo = getSubscriptionInfo(o.subscription_end);
                const todayInfo = getTodayOperatingHours(o);

                return (
                  <tr key={o.store_id} className="hover:bg-red-50/30 dark:hover:bg-zinc-900/40 transition-colors">
                    <td className="px-4 py-3.5 font-mono">
                      <span className="font-bold block text-slate-900 dark:text-white">{o.store_id}</span>
                      <span className="text-slate-400 dark:text-zinc-500 text-[11px]">{o.merchant_id}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="font-bold block text-slate-900 dark:text-white">{o.outlet_short_name || o.outlet_long_name}</span>
                      <span className="text-slate-400 dark:text-zinc-500 text-[11px]">{o.portal_name || "FoodMaster"}</span>
                    </td>

                    {/* JAM OPERASIONAL: Hari ini + Lihat Jadwal 7 Hari */}
                    <td className="px-4 py-3.5">
                      <div className="space-y-1">
                        <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-slate-800 dark:text-zinc-200">
                          <svg className="h-3.5 w-3.5 text-red-600 dark:text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          Hari Ini ({todayInfo.todayName}): {todayInfo.hoursText}
                        </span>
                        <div>
                          <button
                            type="button"
                            onClick={() => setViewScheduleOutlet(o)}
                            className="text-[11.5px] font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 inline-flex items-center gap-1 transition-colors"
                          >
                            Lihat Jadwal 7 Hari &rsaquo;
                          </button>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        o.vercel_toggle
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                          : "bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400"
                      }`}>
                        {o.vercel_toggle ? "ON" : "OFF"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        isSusp
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300"
                          : "bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400"
                      }`}>
                        {isSusp ? "Ya (Ditangguhkan)" : "Tidak"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="space-y-1.5">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                          isSubActive
                            ? subInfo.isExpiringSoon
                              ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                              : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                            : "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400"
                        }`}>
                          {isSubActive ? (
                            subInfo.isExpiringSoon ? "⚠ Hampir Expired" : "✓ Aktif"
                          ) : (
                            "✕ Expired"
                          )}
                        </span>
                        <div className="text-[12px] font-semibold text-slate-700 dark:text-zinc-300">
                          {o.subscription_package || "3 Bulan"}
                        </div>
                        <div className="text-[11.5px] text-slate-500 dark:text-zinc-500">
                          <span>{formatDateID(o.subscription_start)}</span>
                          <span className="mx-1 text-slate-300 dark:text-zinc-600">→</span>
                          <span>{formatDateID(o.subscription_end)}</span>
                        </div>
                        {subInfo.daysLeft !== null && (
                          <div className={`text-[11px] font-bold ${
                            subInfo.isExpired
                              ? "text-red-600 dark:text-red-400"
                              : subInfo.isExpiringSoon
                              ? "text-amber-600 dark:text-amber-400"
                              : "text-slate-400 dark:text-zinc-500"
                          }`}>
                            {subInfo.isExpired
                              ? `Kadaluarsa ${Math.abs(subInfo.daysLeft)} hari lalu`
                              : `Sisa ${subInfo.daysLeft} hari`}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        onClick={() => handleEditClick(o)}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-1.5 text-[12px] font-semibold text-slate-700 dark:text-zinc-300 hover:bg-red-50 hover:text-red-700 hover:border-red-200 dark:hover:bg-zinc-800 dark:hover:text-white transition-colors"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        Edit Admin
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Admin Modal (Terdapat Pengaturan Jam Operasional Master) */}
      {editingStoreId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="animate-scale-up w-full max-w-lg rounded-2xl bg-white dark:bg-zinc-950 border border-red-100 dark:border-zinc-800 p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-red-50 dark:border-zinc-800 pb-3 sticky top-0 bg-white dark:bg-zinc-950 z-10">
              <h3 className="font-bold text-slate-800 dark:text-white">
                Pengaturan Admin: {formData.outlet_short_name}
              </h3>
              <button
                onClick={() => setEditingStoreId(null)}
                className="p-1.5 rounded-xl text-slate-400 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-4 text-[13px]">

              {/* Status Penangguhan */}
              <div className="rounded-xl bg-amber-50/60 dark:bg-amber-950/20 p-3.5 border border-amber-200/60 dark:border-amber-900/40 space-y-2">
                <label className="block font-bold text-amber-800 dark:text-amber-300">
                  Status Penangguhan (FoodMaster Internal Control):
                </label>
                <div className="flex gap-4">
                  {[
                    { value: true, label: "Ya (Tangguhkan Outlet & Paksa TUTUP)" },
                    { value: false, label: "Tidak (Cabut Penangguhan)" },
                  ].map((opt) => (
                    <label key={String(opt.value)} className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-zinc-300 cursor-pointer">
                      <input
                        type="radio"
                        name="suspension_status"
                        checked={
                          opt.value === true
                            ? formData.suspension_status === true || formData.suspension_status === "Ya"
                            : formData.suspension_status === false || formData.suspension_status === "Tidak"
                        }
                        onChange={() => setFormData({ ...formData, suspension_status: opt.value })}
                        className="text-red-700 focus:ring-red-500"
                      />
                      {opt.label}
                    </label>
                  ))}
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 dark:text-zinc-400 mb-1">Alasan Penangguhan:</label>
                  <input
                    type="text"
                    placeholder="Contoh: Kewajiban pembayaran / Merchant Churn"
                    value={formData.suspension_reason || ""}
                    onChange={(e) => setFormData({ ...formData, suspension_reason: e.target.value })}
                    className="field-control"
                  />
                </div>
              </div>

              {/* Pengaturan Jam Operasional Master */}
              <div className="rounded-xl bg-slate-50 dark:bg-zinc-900/60 p-3.5 border border-slate-200 dark:border-zinc-800 space-y-3">
                <div className="flex items-center gap-2">
                  <svg className="h-4 w-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <label className="block font-bold text-slate-800 dark:text-white">
                    Pengaturan Jam Operasional Master (Source of Truth):
                  </label>
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-zinc-400 font-semibold mb-1">
                    Hari Operasional Aktif (Format: 1,2,3,4,5,6,7):
                  </label>
                  <input
                    type="text"
                    placeholder="1,2,3,4,5,6,7 (1=Senin s/d 7=Minggu)"
                    value={formData.operating_days || "1,2,3,4,5,6,7"}
                    onChange={(e) => setFormData({ ...formData, operating_days: e.target.value })}
                    className="field-control font-mono"
                  />
                  <p className="text-[11px] text-slate-400 dark:text-zinc-500 mt-1">
                    Isikan ID hari dipisahkan koma. Ketik `1,2,3,4,5,6,7` untuk buka setiap hari.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-slate-600 dark:text-zinc-400 font-semibold mb-1">Jam Buka Standar:</label>
                    <input
                      type="text"
                      placeholder="08:00"
                      value={formData.open_time || "08:00"}
                      onChange={(e) => setFormData({ ...formData, open_time: e.target.value })}
                      className="field-control font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 dark:text-zinc-400 font-semibold mb-1">Jam Tutup Standar:</label>
                    <input
                      type="text"
                      placeholder="22:00"
                      value={formData.close_time || "22:00"}
                      onChange={(e) => setFormData({ ...formData, close_time: e.target.value })}
                      className="field-control font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-200/60 dark:border-zinc-800">
                  <div>
                    <label className="block text-slate-500 dark:text-zinc-400 text-[11.5px] mb-1">Jam Buka Jumat (Khusus Siang):</label>
                    <input
                      type="text"
                      placeholder="Misal: 13:00 (Opsional)"
                      value={formData.friday_open_time || ""}
                      onChange={(e) => setFormData({ ...formData, friday_open_time: e.target.value })}
                      className="field-control font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-500 dark:text-zinc-400 text-[11.5px] mb-1">Jam Buka Weekend (Sabtu-Minggu):</label>
                    <input
                      type="text"
                      placeholder="Misal: 07:00 (Opsional)"
                      value={formData.weekend_open_time || ""}
                      onChange={(e) => setFormData({ ...formData, weekend_open_time: e.target.value })}
                      className="field-control font-mono text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Subscription */}
              <div className="rounded-xl bg-slate-50 dark:bg-zinc-900/60 p-3.5 border border-slate-200 dark:border-zinc-800 space-y-2">
                <label className="block font-bold text-slate-800 dark:text-white">
                  Pengaturan Paket Subscription Auto Open:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-slate-500 dark:text-zinc-500 mb-1">Paket Subscription:</label>
                    <select
                      value={formData.subscription_package || "3 Bulan"}
                      onChange={(e) => setFormData({ ...formData, subscription_package: e.target.value })}
                      className="field-control"
                    >
                      <option value="3 Bulan">Paket 3 Bulan</option>
                      <option value="6 Bulan">Paket 6 Bulan (+ Bonus 1 Bln)</option>
                      <option value="12 Bulan">Paket 12 Bulan (+ Bonus 4 Bln)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-500 dark:text-zinc-500 mb-1">Status Subscription:</label>
                    <select
                      value={formData.subscription_status || "Active"}
                      onChange={(e) => setFormData({ ...formData, subscription_status: e.target.value })}
                      className="field-control"
                    >
                      <option value="Active">Active (Aktif)</option>
                      <option value="Expired">Expired (Kadaluwarsa)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800 pt-3">
                <button
                  type="button"
                  onClick={() => setEditingStoreId(null)}
                  className="secondary-action px-4 py-2 text-[13px]"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="primary-action px-4 py-2 text-[13px]"
                >
                  Simpan Perubahan Admin
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ScheduleModal (Detail 7 Hari Lengkap untuk Admin) */}
      {viewScheduleOutlet && (
        <ScheduleModal
          outlet={viewScheduleOutlet}
          onClose={() => setViewScheduleOutlet(null)}
          onUpdateOutlet={(updated) => {
            if (onUpdateOutlet) onUpdateOutlet(updated);
            setViewScheduleOutlet(updated);
          }}
        />
      )}
    </div>
  );
}

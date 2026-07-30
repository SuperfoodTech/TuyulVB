import { useState } from "react";

export default function AdminDashboard({ outlets, onUpdateOutlet, onRefresh, loading }) {
  const [editingStoreId, setEditingStoreId] = useState(null);
  const [formData, setFormData] = useState({});

  const handleEditClick = (outlet) => {
    setEditingStoreId(outlet.store_id);
    setFormData({ ...outlet });
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
              Kelola <strong>Status Penangguhan</strong>, <strong>Masa Aktif Subscription</strong>, dan pendaftaran outlet ShopeeFood.
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
                    <td className="px-4 py-3.5">
                      <span className="inline-flex items-center gap-1 font-medium">
                        <svg className="h-3.5 w-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {o.open_time || "08:00"} - {o.close_time || "22:00"}
                      </span>
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
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        isSubActive
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                          : "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400"
                      }`}>
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {o.subscription_package || "3 Bulan"} ({isSubActive ? "Aktif" : "Expired"})
                      </span>
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

      {/* Edit Admin Modal */}
      {editingStoreId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="animate-scale-up w-full max-w-lg rounded-2xl bg-white dark:bg-zinc-950 border border-red-100 dark:border-zinc-800 p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-red-50 dark:border-zinc-800 pb-3">
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
    </div>
  );
}

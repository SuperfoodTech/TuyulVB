import React, { useState } from "react";
import { Shield, Plus, Edit2, ShieldAlert, Calendar, Clock, Check, X, RefreshCw } from "lucide-react";

export default function AdminDashboard({ outlets, onUpdateOutlet, onAddOutlet, onRefresh, loading }) {
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
      
      {/* Header Banner */}
      <div className="rounded-2xl border border-rose-100 dark:border-slate-800 bg-gradient-to-r from-slate-900 via-rose-950 to-slate-900 p-6 text-white shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-rose-400" />
              <h2 className="text-xl font-bold tracking-tight">
                Admin Panel FoodMaster Internal
              </h2>
            </div>
            <p className="mt-1 text-xs sm:text-sm text-slate-300">
              Kelola **Status Penangguhan**, **Masa Aktif Subscription**, dan pendaftaran outlet ShopeeFood.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onRefresh}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-semibold text-white hover:bg-white/20 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Outlets Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
          <h3 className="font-bold text-slate-800 dark:text-white text-sm">
            Daftar Seluruh Outlet ({outlets.length})
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-100 dark:border-slate-800">
              <tr>
                <th className="p-3.5">Store ID / Merchant ID</th>
                <th className="p-3.5">Nama Outlet / Portal</th>
                <th className="p-3.5">Jam Operasional</th>
                <th className="p-3.5">Vercel Toggle</th>
                <th className="p-3.5">Status Penangguhan</th>
                <th className="p-3.5">Subscription Auto Open</th>
                <th className="p-3.5 text-right">Aksi Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
              {outlets.map((o) => {
                const isSusp = o.suspension_status === true || o.suspension_status === "Ya";
                const isSubActive = o.subscription_status === "Active";

                return (
                  <tr key={o.store_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="p-3.5 font-mono">
                      <span className="font-bold block text-slate-900 dark:text-white">{o.store_id}</span>
                      <span className="text-slate-400">{o.merchant_id}</span>
                    </td>
                    <td className="p-3.5">
                      <span className="font-bold block text-slate-900 dark:text-white">{o.outlet_short_name || o.outlet_long_name}</span>
                      <span className="text-slate-400">{o.portal_name || "FoodMaster"}</span>
                    </td>
                    <td className="p-3.5">
                      <span className="inline-flex items-center gap-1 font-medium">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        {o.open_time || "08:00"} - {o.close_time || "22:00"}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold ${
                        o.vercel_toggle ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                      }`}>
                        {o.vercel_toggle ? "ON" : "OFF"}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        isSusp ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                      }`}>
                        {isSusp ? "Ya (Ditangguhkan)" : "Tidak"}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        isSubActive ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400" : "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-400"
                      }`}>
                        <Calendar className="h-3 w-3" />
                        {o.subscription_package || "3 Bulan"} ({isSubActive ? "Aktif" : "Expired"})
                      </span>
                    </td>
                    <td className="p-3.5 text-right">
                      <button
                        onClick={() => handleEditClick(o)}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                      >
                        <Edit2 className="h-3 w-3" />
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="font-bold text-slate-800 dark:text-white">
                Pengaturan Admin: {formData.outlet_short_name}
              </h3>
              <button onClick={() => setEditingStoreId(null)} className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-4 text-xs">
              
              {/* Status Penangguhan Control */}
              <div className="rounded-xl bg-amber-50/60 dark:bg-amber-950/20 p-3 border border-amber-200/50 dark:border-amber-900/50 space-y-2">
                <label className="block font-bold text-amber-800 dark:text-amber-300">
                  Status Penangguhan (FoodMaster Internal Control):
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
                    <input
                      type="radio"
                      name="suspension_status"
                      checked={formData.suspension_status === true || formData.suspension_status === "Ya"}
                      onChange={() => setFormData({ ...formData, suspension_status: true })}
                      className="text-rose-600 focus:ring-rose-500"
                    />
                    Ya (Tangguhkan Outlet & Paksa TUTUP)
                  </label>
                  <label className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
                    <input
                      type="radio"
                      name="suspension_status"
                      checked={formData.suspension_status === false || formData.suspension_status === "Tidak"}
                      onChange={() => setFormData({ ...formData, suspension_status: false })}
                      className="text-rose-600 focus:ring-rose-500"
                    />
                    Tidak (Cabut Penangguhan)
                  </label>
                </div>
                <div>
                  <label className="block font-semibold text-slate-600 dark:text-slate-400 mb-1">
                    Alasan Penangguhan:
                  </label>
                  <input
                    type="text"
                    placeholder="Contoh: Kewajiban pembayaran / Merchant Churn"
                    value={formData.suspension_reason || ""}
                    onChange={(e) => setFormData({ ...formData, suspension_reason: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-800 dark:text-white"
                  />
                </div>
              </div>

              {/* Subscription Auto Open Control */}
              <div className="rounded-xl bg-slate-50 dark:bg-slate-800/50 p-3 border border-slate-200 dark:border-slate-700 space-y-2">
                <label className="block font-bold text-slate-800 dark:text-white">
                  Pengaturan Paket Subscription Auto Open:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-slate-500 mb-1">Paket Subscription:</label>
                    <select
                      value={formData.subscription_package || "3 Bulan"}
                      onChange={(e) => setFormData({ ...formData, subscription_package: e.target.value })}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-xs"
                    >
                      <option value="3 Bulan">Paket 3 Bulan</option>
                      <option value="6 Bulan">Paket 6 Bulan (+ Bonus 1 Bln)</option>
                      <option value="12 Bulan">Paket 12 Bulan (+ Bonus 4 Bln)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-500 mb-1">Status Subscription:</label>
                    <select
                      value={formData.subscription_status || "Active"}
                      onChange={(e) => setFormData({ ...formData, subscription_status: e.target.value })}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-xs"
                    >
                      <option value="Active">Active (Aktif)</option>
                      <option value="Expired">Expired (Kadaluwarsa)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 border-t border-slate-100 dark:border-slate-800 pt-3">
                <button
                  type="button"
                  onClick={() => setEditingStoreId(null)}
                  className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 transition-colors shadow-md shadow-rose-600/20"
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

import { useState } from "react";
import { formatDateID, getSubscriptionInfo } from "../utils/outletUtils";

export default function LinkGeneratorTab({ outlets, onUpdateOutlet, onRefresh, loading }) {
  const [copiedTokenId, setCopiedTokenId] = useState(null);
  const [copiedCredId, setCopiedCredId] = useState(null);
  const [editingStoreId, setEditingStoreId] = useState(null);
  const [formData, setFormData] = useState({});
  const [search, setSearch] = useState("");

  const getMerchantTokenLink = (outlet) => {
    const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
    const mId = outlet.merchant_id.toLowerCase();
    const token = outlet.access_token || `mcht_live_${mId}_8f9a2b`;
    return `${origin}/?merchant=${outlet.merchant_id}`;
  };

  const handleCopyLink = (outlet) => {
    const link = getMerchantTokenLink(outlet);
    navigator.clipboard.writeText(link);
    setCopiedTokenId(outlet.store_id);
    setTimeout(() => setCopiedTokenId(null), 2500);
  };

  const handleCopyCredentials = (outlet) => {
    const link = getMerchantTokenLink(outlet);
    const username = outlet.merchant_username || outlet.outlet_short_name.toLowerCase();
    const password = outlet.merchant_password || "foodmaster123";

    const text = `*AKSES DASHBOARD SHOPEEFOOD AUTO OPEN/CLOSE*\nMerchant ID: ${outlet.merchant_id}\nPortal/Nama: ${outlet.portal_name || outlet.owner_name}\nLink: ${link}\nUsername: ${username}\nPassword: ${password}`;
    navigator.clipboard.writeText(text);
    setCopiedCredId(outlet.store_id);
    setTimeout(() => setCopiedCredId(null), 2500);
  };

  const handleEditCreds = (outlet) => {
    setEditingStoreId(outlet.store_id);
    setFormData({
      ...outlet,
      merchant_username: outlet.merchant_username || outlet.outlet_short_name.toLowerCase(),
      merchant_password: outlet.merchant_password || "foodmaster123",
      access_token: outlet.access_token || `mcht_live_${outlet.merchant_id.toLowerCase()}_8f9a2b`
    });
  };

  const handleSaveCreds = (e) => {
    e.preventDefault();
    onUpdateOutlet(formData);
    setEditingStoreId(null);
  };

  const filteredOutlets = outlets.filter((o) => {
    const q = search.toLowerCase();
    return (
      (o.merchant_id || "").toLowerCase().includes(q) ||
      (o.store_id || "").toLowerCase().includes(q) ||
      (o.portal_name || "").toLowerCase().includes(q) ||
      (o.outlet_short_name || "").toLowerCase().includes(q) ||
      (o.merchant_username || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="surface-card p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 text-red-700 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">
              Link Generator &amp; Access Control per Merchant ID
            </h2>
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
            Setiap Merchant ID mendapatkan <strong>1 Link Khusus</strong> yang menampilkan seluruh outlet/toko milik merchant tersebut.
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
          Refresh Data
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <span className="absolute inset-y-0 left-3.5 flex items-center text-slate-400">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </span>
        <input
          type="text"
          placeholder="Cari Merchant ID, Store ID, nama outlet, atau portal..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="field-control pl-10"
        />
      </div>

      {/* Outlets Table */}
      <div className="overflow-hidden rounded-2xl border border-red-100 bg-white shadow-[0_16px_45px_-30px_rgba(127,29,29,0.45)] dark:border-transparent dark:bg-transparent dark:shadow-none">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead className="bg-slate-50 dark:bg-zinc-900/60 text-[12px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 border-b border-red-50 dark:border-zinc-800">
              <tr>
                <th className="px-4 py-3.5">Merchant ID &amp; Outlet</th>
                <th className="px-4 py-3.5">Username &amp; Password</th>
                <th className="px-4 py-3.5">Status Subscription</th>
                <th className="px-4 py-3.5">Link Akses (Merchant ID)</th>
                <th className="px-4 py-3.5 text-right">Aksi Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-red-50 dark:divide-zinc-800 text-slate-700 dark:text-zinc-300">
              {filteredOutlets.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-slate-400 dark:text-zinc-500">
                    Tidak ada outlet yang cocok dengan pencarian.
                  </td>
                </tr>
              ) : (
                filteredOutlets.map((o) => {
                  const subInfo = getSubscriptionInfo(o.subscription_end);
                  const isSubActive = o.subscription_status === "Active" && !subInfo.isExpired;
                  const merchantLink = getMerchantTokenLink(o);
                  const username = o.merchant_username || o.outlet_short_name.toLowerCase();
                  const password = o.merchant_password || "foodmaster123";

                  return (
                    <tr key={o.store_id} className="hover:bg-red-50/20 dark:hover:bg-zinc-900/40 transition-colors">
                      <td className="px-4 py-3.5">
                        <span className="font-mono font-bold block text-red-700 dark:text-red-400">{o.merchant_id}</span>
                        <span className="font-bold text-slate-900 dark:text-white block text-[13px]">{o.outlet_short_name || o.outlet_long_name}</span>
                        <span className="text-slate-400 dark:text-zinc-500 font-mono text-[11px]">Store ID: {o.store_id}</span>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[12px]">
                        <div>User: <span className="font-bold text-slate-800 dark:text-white">{username}</span></div>
                        <div className="text-slate-500 dark:text-zinc-400">Pass: <code className="bg-slate-100 dark:bg-zinc-800 px-1 py-0.5 rounded">{password}</code></div>
                      </td>
                      <td className="px-4 py-3.5">
                        {isSubActive ? (
                          <div>
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 px-2.5 py-0.5 text-[11px] font-bold text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50">
                              Akses Aktif (Sisa {subInfo.daysLeft} hari)
                            </span>
                            <div className="text-[11px] text-slate-400 dark:text-zinc-500 mt-0.5">
                              s/d {formatDateID(o.subscription_end)}
                            </div>
                          </div>
                        ) : (
                          <div>
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 dark:bg-red-950/30 px-2.5 py-0.5 text-[11px] font-bold text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50">
                              Akses Terkunci (Expired)
                            </span>
                            <div className="text-[11px] text-red-500 dark:text-red-400 mt-0.5">
                              Berakhir: {formatDateID(o.subscription_end)}
                            </div>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[11px]">
                        <input
                          type="text"
                          readOnly
                          value={merchantLink}
                          className="w-52 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-slate-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 truncate"
                        />
                      </td>
                      <td className="px-4 py-3.5 text-right space-x-1.5">
                        <button
                          type="button"
                          onClick={() => handleCopyCredentials(o)}
                          className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11.5px] font-semibold transition-all ${
                            copiedCredId === o.store_id
                              ? "bg-emerald-600 text-white"
                              : "bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-200 hover:bg-slate-200 dark:hover:bg-zinc-700"
                          }`}
                          title="Salin Link + Username + Password"
                        >
                          {copiedCredId === o.store_id ? "Tersalin!" : "Salin Info Login"}
                        </button>

                        <button
                          type="button"
                          onClick={() => handleCopyLink(o)}
                          className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11.5px] font-bold transition-all ${
                            copiedTokenId === o.store_id
                              ? "bg-emerald-600 text-white"
                              : "bg-red-700 text-white hover:bg-red-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
                          }`}
                        >
                          {copiedTokenId === o.store_id ? "Link Tersalin!" : "Salin Link"}
                        </button>

                        <button
                          type="button"
                          onClick={() => handleEditCreds(o)}
                          className="p-1.5 rounded-lg border border-slate-200 dark:border-zinc-700 hover:bg-red-50 dark:hover:bg-zinc-800 text-slate-600 dark:text-zinc-300"
                          title="Edit Username & Password"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Username/Password Modal */}
      {editingStoreId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="animate-scale-up w-full max-w-md rounded-2xl bg-white dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 dark:border-zinc-800 pb-3">
              <h3 className="font-bold text-slate-800 dark:text-white">
                Edit Kredensial Merchant ID: {formData.merchant_id}
              </h3>
              <button
                type="button"
                onClick={() => setEditingStoreId(null)}
                className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded-lg"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSaveCreds} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 dark:text-zinc-300 mb-1">
                  Username Merchant:
                </label>
                <input
                  type="text"
                  value={formData.merchant_username || ""}
                  onChange={(e) => setFormData({ ...formData, merchant_username: e.target.value })}
                  className="field-control"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 dark:text-zinc-300 mb-1">
                  Password Merchant:
                </label>
                <input
                  type="text"
                  value={formData.merchant_password || ""}
                  onChange={(e) => setFormData({ ...formData, merchant_password: e.target.value })}
                  className="field-control"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setEditingStoreId(null)}
                  className="secondary-action px-4 py-2 text-xs"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="primary-action px-4 py-2 text-xs"
                >
                  Simpan Kredensial
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

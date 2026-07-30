import { useState, useEffect } from "react";

export default function SessionMonitorTab({ API_BASE_URL, API_SECRET_KEY }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("all"); // all | active | missing

  const fetchSessions = () => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE_URL}/api/sessions`, {
      headers: { "X-API-Key": API_SECRET_KEY || "" }
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch sessions");
        return res.json();
      })
      .then((data) => setSessions(Array.isArray(data) ? data : []))
      .catch(() => setError("Gagal memuat status sesi browser dari backend."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSessions();
  }, [API_BASE_URL]);

  const formatTimestamp = (ts) => {
    if (!ts) return "-";
    try {
      const date = typeof ts === "number" ? new Date(ts * 1000) : new Date(ts);
      if (isNaN(date.getTime())) return String(ts);
      return date.toLocaleString("id-ID", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      });
    } catch {
      return String(ts);
    }
  };

  const filteredSessions = sessions.filter((s) => {
    const searchLower = search.toLowerCase();
    const matchSearch =
      (s.merchant_name || "").toLowerCase().includes(searchLower) ||
      (s.nama_resto_final || "").toLowerCase().includes(searchLower) ||
      (s.store_id || "").toLowerCase().includes(searchLower) ||
      (s.phone || "").toLowerCase().includes(searchLower);
    const matchType =
      filterType === "all" ||
      (filterType === "active" && s.has_session) ||
      (filterType === "missing" && !s.has_session);
    return matchSearch && matchType;
  });

  const activeCount = sessions.filter((s) => s.has_session).length;
  const missingCount = sessions.filter((s) => !s.has_session).length;

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="surface-card p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">Dashboard Sesi Login</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
            Status penyimpanan session cookie/profile per merchant ShopeeFood &amp; profil Chromium terisolasi.
          </p>
        </div>
        <button
          onClick={fetchSessions}
          disabled={loading}
          className="secondary-action gap-1.5 self-start sm:self-auto disabled:opacity-50"
        >
          <svg className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" />
          </svg>
          Refresh Data
        </button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-red-100 bg-white p-4 shadow-sm dark:border-transparent dark:bg-zinc-900/60">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400">Total Outlet</span>
          <p className="mt-1.5 text-2xl font-black text-slate-800 dark:text-white">{sessions.length}</p>
        </div>
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/30 p-4 dark:border-emerald-900/30 dark:bg-emerald-950/20">
          <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">Sesi Aktif</span>
          <p className="mt-1.5 text-2xl font-black text-emerald-800 dark:text-emerald-300">{activeCount}</p>
        </div>
        <div className="rounded-xl border border-red-100 bg-red-50/30 p-4 dark:border-red-900/30 dark:bg-red-950/20">
          <span className="text-[11px] font-bold uppercase tracking-wider text-red-700 dark:text-red-400">Sesi Kosong / Butuh Login</span>
          <p className="mt-1.5 text-2xl font-black text-red-800 dark:text-red-300">{missingCount}</p>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-4 text-sm font-semibold text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
        <div className="relative flex-1 w-full">
          <span className="absolute inset-y-0 left-3.5 flex items-center text-slate-400">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input
            type="text"
            placeholder="Cari merchant, store ID atau nomor telepon..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="field-control pl-10"
          />
        </div>
        <div className="inline-flex rounded-xl bg-slate-100 dark:bg-zinc-900 p-1 shrink-0">
          {[
            { id: "all", label: "Semua" },
            { id: "active", label: "Aktif" },
            { id: "missing", label: "Kosong" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilterType(f.id)}
              className={`rounded-lg px-3 py-1.5 text-[13px] font-bold transition-all ${
                filterType === f.id
                  ? "bg-white dark:bg-zinc-800 text-red-700 dark:text-white shadow-sm"
                  : "text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-white"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sessions Table */}
      <div className="overflow-hidden rounded-2xl border border-red-100 bg-white shadow-[0_16px_45px_-30px_rgba(127,29,29,0.45)] dark:border-transparent dark:bg-transparent dark:shadow-none">
        {loading ? (
          <div className="py-12 text-center text-slate-500 dark:text-zinc-400">
            <svg className="mx-auto h-8 w-8 animate-spin text-red-700 dark:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" />
            </svg>
            <p className="mt-3 text-sm">Memuat data sesi login...</p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="py-12 text-center text-slate-400 dark:text-zinc-500 text-sm">
            Tidak ada data merchant yang cocok dengan filter pencarian.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-red-50 dark:divide-zinc-800 text-left text-[13px]">
              <thead className="bg-slate-50 dark:bg-zinc-900/60 text-[12px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
                <tr>
                  <th className="px-4 py-3.5 rounded-l-xl">Merchant &amp; Outlet</th>
                  <th className="px-4 py-3.5">Detail Login / File Sesi</th>
                  <th className="px-4 py-3.5">Status Sesi</th>
                  <th className="px-4 py-3.5 rounded-r-xl">Terakhir Aktif</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-zinc-800 bg-white dark:bg-transparent">
                {filteredSessions.map((s, idx) => (
                  <tr key={s.id || idx} className="hover:bg-red-50/20 dark:hover:bg-zinc-900/40 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="font-bold text-slate-800 dark:text-white">
                        {s.nama_resto_final || s.merchant_name || "-"}
                      </div>
                      <div className="text-[12px] text-slate-400 dark:text-zinc-500 font-mono">{s.store_id}</div>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[12.5px] text-slate-600 dark:text-zinc-400">
                      <div>{s.phone || "-"}</div>
                      {s.session_file && (
                        <div className="mt-0.5 text-[11px] text-slate-400 dark:text-zinc-600 font-sans break-all max-w-xs">
                          {s.session_file}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      {s.has_session ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 px-2.5 py-1 text-[12px] font-bold text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          Aktif
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 dark:bg-red-950/30 px-2.5 py-1 text-[12px] font-bold text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50">
                          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                          Kosong
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-zinc-400 text-[12.5px]">
                      {formatTimestamp(s.last_active)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

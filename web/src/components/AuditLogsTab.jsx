import { useState, useEffect } from "react";

export default function AuditLogsTab({ API_BASE_URL, API_SECRET_KEY }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  const fetchLogs = () => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE_URL}/api/logs`, {
      headers: { "X-API-Key": API_SECRET_KEY || "" }
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch logs");
        return res.json();
      })
      .then((data) => setLogs(Array.isArray(data) ? data : []))
      .catch(() => setError("Gagal memuat log audit dari server SQLite."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLogs();
  }, [API_BASE_URL]);

  const filteredLogs = logs.filter((l) => {
    const q = search.toLowerCase();
    return (
      (l.store_id || "").toLowerCase().includes(q) ||
      (l.outlet_short_name || "").toLowerCase().includes(q) ||
      (l.bot_action || "").toLowerCase().includes(q) ||
      (l.status_result || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="surface-card p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 text-red-700 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">
              Audit Logs Real-Time
            </h2>
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-zinc-400">
            Riwayat tindakan bot, evaluasi prioritas, serta status sebelum &amp; sesudah eksekusi dari database SQLite <code className="rounded bg-red-50 dark:bg-zinc-800 px-1.5 py-0.5 text-[12px] text-red-700 dark:text-zinc-300">bot_logs</code>.
          </p>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="secondary-action gap-1.5 self-start sm:self-auto disabled:opacity-50"
        >
          <svg className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" />
          </svg>
          Refresh Logs
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-4 text-sm font-semibold text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <span className="absolute inset-y-0 left-3.5 flex items-center text-slate-400">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </span>
        <input
          type="text"
          placeholder="Cari store ID, nama outlet, aksi bot, atau hasil..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="field-control pl-10"
        />
      </div>

      {/* Logs Table */}
      <div className="overflow-hidden rounded-2xl border border-red-100 bg-white shadow-[0_16px_45px_-30px_rgba(127,29,29,0.45)] dark:border-transparent dark:bg-transparent dark:shadow-none">
        {loading ? (
          <div className="py-12 text-center text-slate-500 dark:text-zinc-400">
            <svg className="mx-auto h-8 w-8 animate-spin text-red-700 dark:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" />
            </svg>
            <p className="mt-3 text-sm">Memuat log audit...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-slate-50 dark:bg-zinc-900/60 text-[12px] font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 border-b border-red-50 dark:border-zinc-800">
                <tr>
                  <th className="px-4 py-3.5">ID</th>
                  <th className="px-4 py-3.5">Waktu Eksekusi</th>
                  <th className="px-4 py-3.5">Store ID / Nama</th>
                  <th className="px-4 py-3.5">Aksi Bot</th>
                  <th className="px-4 py-3.5">Sebelum</th>
                  <th className="px-4 py-3.5">Sesudah</th>
                  <th className="px-4 py-3.5">Hasil</th>
                  <th className="px-4 py-3.5">Keterangan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-red-50 dark:divide-zinc-800 text-slate-700 dark:text-zinc-300">
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-slate-400 dark:text-zinc-500">
                      Belum ada data audit log yang tercatat.
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((logItem) => {
                    const beforeStr = logItem.shopee_status_before === 1 ? "OPEN" : logItem.shopee_status_before === 0 ? "OFF" : "N/A";
                    const afterStr = logItem.shopee_status_after === 1 ? "OPEN" : logItem.shopee_status_after === 0 ? "OFF" : "N/A";
                    const isSuccess = logItem.status_result === "SUCCESS" || logItem.status_result === "SUCCESS_NO_CHANGE";

                    return (
                      <tr key={logItem.id} className="hover:bg-red-50/20 dark:hover:bg-zinc-900/40 transition-colors">
                        <td className="px-4 py-3.5 font-mono text-slate-400 dark:text-zinc-500">#{logItem.id}</td>
                        <td className="px-4 py-3.5 font-medium whitespace-nowrap text-[12.5px]">
                          {logItem.timestamp ? new Date(logItem.timestamp).toLocaleString("id-ID") : "-"}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="font-bold block text-slate-800 dark:text-white">
                            {logItem.outlet_short_name || logItem.store_id}
                          </span>
                          <span className="text-slate-400 dark:text-zinc-500 font-mono text-[11px]">{logItem.store_id}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold ${
                            logItem.bot_action === "AUTO_OPEN"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300"
                              : logItem.bot_action === "AUTO_CLOSE"
                              ? "bg-red-100 text-red-800 dark:bg-red-950/40 dark:text-red-300"
                              : "bg-slate-100 text-slate-600 dark:bg-zinc-800 dark:text-zinc-400"
                          }`}>
                            {logItem.bot_action}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 font-mono font-medium text-[12px]">{beforeStr}</td>
                        <td className="px-4 py-3.5 font-mono font-medium text-[12px]">{afterStr}</td>
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center gap-1 font-bold text-[12px] ${
                            isSuccess
                              ? "text-emerald-700 dark:text-emerald-400"
                              : "text-red-700 dark:text-red-400"
                          }`}>
                            {isSuccess ? (
                              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            ) : (
                              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            )}
                            {logItem.status_result}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-slate-500 dark:text-zinc-500 max-w-[180px] truncate text-[12px]" title={logItem.admin_info}>
                          {logItem.admin_info || "-"}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

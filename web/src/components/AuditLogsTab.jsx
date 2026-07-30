import React, { useState, useEffect } from "react";
import { Activity, RefreshCw, CheckCircle2, AlertCircle, Clock } from "lucide-react";

export default function AuditLogsTab({ API_BASE_URL, API_SECRET_KEY }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
      .then((data) => {
        setLogs(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        setError("Gagal memuat log audit dari server SQLite.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLogs();
  }, [API_BASE_URL]);

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-xl font-bold tracking-tight text-slate-800 dark:text-white">
              Audit Logs Real-Time (SQLite `bot_logs`)
            </h2>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Merekam seluruh riwayat tindakan bot, evaluasi prioritas, status sebelum & sesudah eksekusi.
          </p>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-xl bg-rose-50 px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:bg-rose-950/40 dark:text-rose-300 dark:hover:bg-rose-900/60 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Logs
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-50 dark:bg-rose-950/50 p-4 text-xs font-medium text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900">
          {error}
        </div>
      )}

      {/* Logs Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-100 dark:border-slate-800">
              <tr>
                <th className="p-3.5">ID</th>
                <th className="p-3.5">Waktu Eksekusi</th>
                <th className="p-3.5">Store ID / Nama</th>
                <th className="p-3.5">Aksi Bot</th>
                <th className="p-3.5">Status Sebelum</th>
                <th className="p-3.5">Status Sesudah</th>
                <th className="p-3.5">Hasil</th>
                <th className="p-3.5">Keterangan Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-400">
                    Belum ada data audit log yang tercatat.
                  </td>
                </tr>
              ) : (
                logs.map((logItem) => {
                  const beforeStr = logItem.shopee_status_before === 1 ? "OPEN" : logItem.shopee_status_before === 0 ? "OFF" : "N/A";
                  const afterStr = logItem.shopee_status_after === 1 ? "OPEN" : logItem.shopee_status_after === 0 ? "OFF" : "N/A";
                  const isSuccess = logItem.status_result === "SUCCESS" || logItem.status_result === "SUCCESS_NO_CHANGE";

                  return (
                    <tr key={logItem.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                      <td className="p-3.5 font-mono text-slate-400">#{logItem.id}</td>
                      <td className="p-3.5 font-medium whitespace-nowrap">
                        {logItem.timestamp ? new Date(logItem.timestamp).toLocaleString("id-ID") : "-"}
                      </td>
                      <td className="p-3.5">
                        <span className="font-bold block text-slate-800 dark:text-white">{logItem.outlet_short_name || logItem.store_id}</span>
                        <span className="text-slate-400 font-mono text-[10px]">{logItem.store_id}</span>
                      </td>
                      <td className="p-3.5">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          logItem.bot_action === "AUTO_OPEN"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                            : logItem.bot_action === "AUTO_CLOSE"
                            ? "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        }`}>
                          {logItem.bot_action}
                        </span>
                      </td>
                      <td className="p-3.5 font-mono font-medium">{beforeStr}</td>
                      <td className="p-3.5 font-mono font-medium">{afterStr}</td>
                      <td className="p-3.5">
                        <span className={`inline-flex items-center gap-1 font-bold text-[11px] ${
                          isSuccess ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                        }`}>
                          {isSuccess ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                          {logItem.status_result}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-500 max-w-xs truncate" title={logItem.admin_info}>
                        {logItem.admin_info || "-"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

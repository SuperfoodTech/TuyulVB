import React, { useState, useEffect } from "react";
import { ShieldCheck, AlertCircle, RefreshCw, Key, HardDrive, CheckCircle2 } from "lucide-react";

export default function SessionMonitorTab({ API_BASE_URL, API_SECRET_KEY }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
      .then((data) => {
        setSessions(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        setError("Gagal memuat status sesi browser dari backend.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSessions();
  }, [API_BASE_URL]);

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-xl font-bold tracking-tight text-slate-800 dark:text-white">
              Status Sesi Browser & Chromium Profile
            </h2>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Pemantau penyimpanan profil terisolasi `chromeprofile` & kesehatan sesi login ShopeePartner.
          </p>
        </div>
        <button
          onClick={fetchSessions}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-xl bg-rose-50 px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:bg-rose-950/40 dark:text-rose-300 dark:hover:bg-rose-900/60 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Session Status
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-50 dark:bg-rose-950/50 p-4 text-xs font-medium text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900">
          {error}
        </div>
      )}

      {/* Sessions Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sessions.length === 0 ? (
          <div className="col-span-full rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 p-12 text-center text-slate-400">
            Tidak ada data sesi browser yang dapat ditampilkan.
          </div>
        ) : (
          sessions.map((s, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
                  {s.platform || "ShopeeFood"}
                </span>
                <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                  s.has_session ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400" : "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-400"
                }`}>
                  {s.has_session ? <CheckCircle2 className="h-3 w-3 text-emerald-500" /> : <AlertCircle className="h-3 w-3 text-rose-500" />}
                  {s.has_session ? "Sesi Aktif" : "Belum Login"}
                </span>
              </div>

              <div>
                <h4 className="font-bold text-slate-800 dark:text-white text-sm">
                  {s.nama_resto_final || s.merchant_name}
                </h4>
                <p className="text-xs text-slate-400 font-mono">Store ID: {s.store_id}</p>
              </div>

              <div className="border-t border-slate-100 dark:border-slate-800 pt-3 text-xs space-y-1 text-slate-500 dark:text-slate-400">
                <div className="flex justify-between">
                  <span>Isolated Profile:</span>
                  <span className="font-mono text-slate-700 dark:text-slate-300">chromeprofile</span>
                </div>
                <div className="flex justify-between">
                  <span>Pengecekan Terakhir:</span>
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    {s.last_login ? new Date(s.last_login).toLocaleTimeString("id-ID") : "-"}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

    </div>
  );
}

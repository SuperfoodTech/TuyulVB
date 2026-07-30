import { getWeeklySchedule, formatOperatingDays } from "../utils/outletUtils";

export default function ScheduleModal({ outlet, onClose }) {
  if (!outlet) return null;

  const schedule = getWeeklySchedule(outlet);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="animate-scale-up w-full max-w-lg rounded-2xl bg-white dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 p-6 shadow-2xl space-y-5">

        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-100 dark:border-zinc-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </span>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Jadwal Operasional Lengkap
              </h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1">
              {outlet.outlet_long_name || outlet.outlet_short_name} &bull; {formatOperatingDays(outlet.operating_days)}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 7-Day Schedule Table */}
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-zinc-950/60 text-slate-500 dark:text-zinc-400 font-bold uppercase tracking-wider text-[11px] border-b border-slate-100 dark:border-zinc-800">
              <tr>
                <th className="px-4 py-3">Hari</th>
                <th className="px-4 py-3">Jam Operasional</th>
                <th className="px-4 py-3 text-right">Keterangan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-zinc-800/60 text-slate-700 dark:text-zinc-300">
              {schedule.map((item) => (
                <tr
                  key={item.dayId}
                  className={`transition-colors ${
                    item.isToday
                      ? "bg-red-50/60 dark:bg-red-950/20 font-bold"
                      : "hover:bg-slate-50/50 dark:hover:bg-zinc-800/30"
                  }`}
                >
                  <td className="px-4 py-3 flex items-center gap-2">
                    <span className="w-16 font-semibold">{item.name}</span>
                    {item.isToday && (
                      <span className="rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider">
                        Hari Ini
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono">
                    {item.isOperating ? (
                      <span className="text-slate-900 dark:text-white font-semibold">
                        {item.hours}
                      </span>
                    ) : (
                      <span className="text-red-500 dark:text-red-400 font-semibold">
                        {item.hours}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400 dark:text-zinc-500 text-[11px]">
                    {item.note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto rounded-xl bg-slate-900 dark:bg-white text-white dark:text-black font-bold px-5 py-2.5 text-xs hover:bg-slate-800 dark:hover:bg-zinc-200 transition-all text-center"
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
}

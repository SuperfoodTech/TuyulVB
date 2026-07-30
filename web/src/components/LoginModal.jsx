import { useState } from "react";

export default function LoginModal({ isOpen, onClose, onLoginSuccess }) {
  const [role, setRole] = useState("merchant");
  const [password, setPassword] = useState("");
  const [merchantName, setMerchantName] = useState("Merchant Foodnesia");
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    if (role === "admin") {
      if (password === "admin" || password === "foodmaster2026") {
        onLoginSuccess({ role: "admin", name: "Admin FoodMaster" });
        onClose();
      } else {
        setError("Password Admin salah. Gunakan 'admin' atau 'foodmaster2026'.");
      }
    } else {
      if (!password) {
        setError("Masukkan password dashboard merchant.");
        return;
      }
      onLoginSuccess({ role: "merchant", name: merchantName });
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="animate-scale-up w-full max-w-md rounded-2xl bg-white dark:bg-zinc-950 border border-red-100 dark:border-zinc-800 p-6 shadow-2xl">

        <div className="flex items-center justify-between border-b border-red-50 dark:border-zinc-800 pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-700 dark:bg-zinc-800 text-white">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-slate-800 dark:text-white">Login Dashboard</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Role Switcher */}
        <div className="mt-4 flex rounded-xl bg-slate-100 dark:bg-zinc-900 p-1">
          {[
            {
              id: "merchant",
              label: "Merchant",
              icon: (
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              ),
            },
            {
              id: "admin",
              label: "Admin Internal",
              icon: (
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              ),
            },
          ].map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => { setRole(r.id); setError(""); }}
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-[13px] font-semibold transition-all ${
                role === r.id
                  ? "bg-red-700 text-white shadow-sm dark:bg-white dark:text-black"
                  : "text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-white"
              }`}
            >
              {r.icon}
              {r.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {role === "merchant" && (
            <div>
              <label className="block text-[13px] font-semibold text-slate-600 dark:text-zinc-400 mb-1.5">
                Pilih Merchant / Portal:
              </label>
              <select
                value={merchantName}
                onChange={(e) => setMerchantName(e.target.value)}
                className="field-control"
              >
                <option value="Merchant Foodnesia">Foodnesia Portal</option>
                <option value="Merchant WonderFood">WonderFood Portal</option>
                <option value="Merchant Lokarasa">Lokarasa Portal</option>
              </select>
            </div>
          )}

          <div>
            <label className="block text-[13px] font-semibold text-slate-600 dark:text-zinc-400 mb-1.5">
              Kata Sandi / Password:
            </label>
            <input
              type="password"
              placeholder={role === "admin" ? "Masukkan password admin ('admin')" : "Masukkan password merchant"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field-control"
              autoFocus
            />
          </div>

          {error && (
            <p className="text-[13px] font-semibold text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-950/40 p-3 rounded-xl border border-red-100 dark:border-red-900/50">
              {error}
            </p>
          )}

          <button type="submit" className="primary-action w-full py-2.5 text-[14px]">
            Masuk Ke Dashboard
          </button>
        </form>
      </div>
    </div>
  );
}

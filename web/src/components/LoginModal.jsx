import React, { useState } from "react";
import { Lock, Shield, User, X } from "lucide-react";

export default function LoginModal({ isOpen, onClose, onLoginSuccess }) {
  const [role, setRole] = useState("merchant"); // merchant | admin
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl transition-all">
        
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-100 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400">
              <Lock className="h-4 w-4" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 dark:text-white">
              Login Dashboard
            </h3>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Role Switcher */}
        <div className="mt-4 flex rounded-xl bg-slate-100 dark:bg-slate-800 p-1">
          <button
            type="button"
            onClick={() => { setRole("merchant"); setError(""); }}
            className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all ${
              role === "merchant" ? "bg-white text-rose-600 shadow-sm dark:bg-slate-900 dark:text-rose-400" : "text-slate-500"
            }`}
          >
            <User className="h-3.5 w-3.5" />
            Merchant
          </button>
          <button
            type="button"
            onClick={() => { setRole("admin"); setError(""); }}
            className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all ${
              role === "admin" ? "bg-white text-rose-600 shadow-sm dark:bg-slate-900 dark:text-rose-400" : "text-slate-500"
            }`}
          >
            <Shield className="h-3.5 w-3.5" />
            Admin Internal
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {role === "merchant" && (
            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
                Pilih Merchant / Portal:
              </label>
              <select
                value={merchantName}
                onChange={(e) => setMerchantName(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                <option value="Merchant Foodnesia">Foodnesia Portal</option>
                <option value="Merchant WonderFood">WonderFood Portal</option>
                <option value="Merchant Lokarasa">Lokarasa Portal</option>
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
              Kata Sandi / Password:
            </label>
            <input
              type="password"
              placeholder={role === "admin" ? "Masukkan Password Admin ('admin')" : "Masukkan Password Merchant"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
          </div>

          {error && (
            <p className="text-xs font-medium text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50 p-2.5 rounded-lg">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="w-full rounded-xl bg-rose-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-rose-600/20 hover:bg-rose-700 transition-all"
          >
            Masuk Ke Dashboard
          </button>
        </form>

      </div>
    </div>
  );
}

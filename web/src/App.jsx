import { useState, useEffect } from "react";
import NavHeader from "./components/NavHeader";
import LoginPage from "./components/LoginPage";
import MerchantTokenLoginPage from "./components/MerchantTokenLoginPage";
import ExpiredAccessPage from "./components/ExpiredAccessPage";
import MerchantDashboard from "./components/MerchantDashboard";
import AdminDashboard from "./components/AdminDashboard";
import LinkGeneratorTab from "./components/LinkGeneratorTab";
import AuditLogsTab from "./components/AuditLogsTab";
import SessionMonitorTab from "./components/SessionMonitorTab";
import StarField from "./components/StarField";
import { useTheme } from "./hooks/useTheme";
import { getSubscriptionInfo } from "./utils/outletUtils";

export default function App() {
  const { theme, toggleTheme } = useTheme();

  // URL Query Parameters check (e.g. ?token=mcht_live_st1001_8f9a2b or ?merchant=ST1001)
  const [tokenParam] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      return params.get("token") || params.get("merchant") || params.get("store");
    }
    return null;
  });

  const [targetOutlet, setTargetOutlet] = useState(null);
  const [isExpired, setIsExpired] = useState(false);

  // User session
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("foodmaster_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Tab aktif (default "merchant" / semua outlet untuk admin)
  const [activeTab, setActiveTab] = useState("merchant");

  const [outlets, setOutlets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [apiConnected, setApiConnected] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const getApiBaseUrl = () => {
    if (import.meta.env.VITE_API_URL) {
      return import.meta.env.VITE_API_URL.replace(/\/+$/, "");
    }
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      if (hostname === "localhost" || hostname === "127.0.0.1") {
        return "http://localhost:18800";
      }
      return `${window.location.protocol}//${hostname}:18800`;
    }
    return "http://localhost:18800";
  };

  const API_BASE_URL = getApiBaseUrl();
  const API_SECRET_KEY = import.meta.env.VITE_API_KEY || "foodmaster-secret-api-key-2026";

  const fetchOutlets = () => {
    setLoading(true);
    fetch(`${API_BASE_URL}/api/outlets`, {
      headers: { "X-API-Key": API_SECRET_KEY }
    })
      .then((res) => {
        if (!res.ok) throw new Error("API Error");
        return res.json();
      })
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setOutlets(list);
        setApiConnected(true);
        evaluateUrlToken(list);
      })
      .catch(() => {
        setApiConnected(false);
        const fallbackList = [
          {
            store_id: "ST1001",
            merchant_id: "M101",
            owner_name: "Merchant Foodnesia",
            portal_name: "Foodnesia Portal",
            outlet_long_name: "Foodnesia Outlet Utama",
            outlet_short_name: "Foodnesia",
            merchant_username: "foodnesia",
            merchant_password: "foodnesia123",
            access_token: "mcht_live_st1001_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "6 Bulan",
            subscription_start: "2026-01-01",
            subscription_end: "2026-12-31",
            subscription_status: "Active",
            last_checked_at: new Date().toISOString()
          },
          {
            store_id: "ST1002",
            merchant_id: "M102",
            owner_name: "Merchant WonderFood",
            portal_name: "WonderFood Portal",
            outlet_long_name: "WonderFood Cabang Selatan",
            outlet_short_name: "WonderFood",
            merchant_username: "wonderfood",
            merchant_password: "wonderfood123",
            access_token: "mcht_live_st1002_8f9a2b",
            operating_days: "1,2,3,4,5",
            open_time: "09:00",
            close_time: "21:00",
            vercel_toggle: false,
            shopee_toggle_last: false,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-01-01",
            subscription_end: "2026-04-01", // Expired
            subscription_status: "Expired",
            last_checked_at: new Date().toISOString()
          },
          {
            store_id: "ST1003",
            merchant_id: "M103",
            owner_name: "Merchant Lokarasa",
            portal_name: "Lokarasa Portal",
            outlet_long_name: "Lokarasa Restoran Pusat",
            outlet_short_name: "Lokarasa",
            merchant_username: "lokarasa",
            merchant_password: "lokarasa123",
            access_token: "mcht_live_st1003_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "10:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "6 Bulan",
            subscription_start: "2026-03-01",
            subscription_end: "2026-09-01",
            subscription_status: "Active",
            last_checked_at: new Date().toISOString()
          }
        ];
        setOutlets(fallbackList);
        evaluateUrlToken(fallbackList);
      })
      .finally(() => setLoading(false));
  };

  // Evaluasi link token khusus merchant dari URL query parameter
  const evaluateUrlToken = (allOutlets) => {
    if (!tokenParam) return;

    const matched = allOutlets.find((o) => {
      const q = tokenParam.toLowerCase();
      const token = (o.access_token || "").toLowerCase();
      const storeId = o.store_id.toLowerCase();
      return token === q || storeId === q || (q.includes("st") && storeId.includes(q));
    });

    if (!matched) {
      setTargetOutlet({
        store_id: tokenParam,
        portal_name: "Unknown Outlet",
        reason: "Access Token link merchant tidak valid atau telah dicabut oleh Admin."
      });
      setIsExpired(true);
      return;
    }

    setTargetOutlet(matched);
    const subInfo = getSubscriptionInfo(matched.subscription_end);
    const expiredCheck = matched.subscription_status === "Expired" || subInfo.isExpired;
    setIsExpired(expiredCheck);
  };

  useEffect(() => {
    fetchOutlets();
  }, [tokenParam]);

  // Filtered outlets untuk Merchant View
  const visibleOutlets = currentUser?.role === "merchant"
    ? outlets.filter((o) => o.store_id === currentUser.store_id || o.store_id === currentUser.portal)
    : outlets;

  const handleToggleVercel = (storeId, newToggle, duration) => {
    setOutlets((prev) =>
      prev.map((o) => (o.store_id === storeId ? { ...o, vercel_toggle: newToggle } : o))
    );
    fetch(`${API_BASE_URL}/api/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": API_SECRET_KEY },
      body: JSON.stringify({ store_id: storeId, vercel_toggle: newToggle, duration })
    })
      .then((res) => res.json())
      .then(() => fetchOutlets())
      .catch((err) => console.error("Toggle error:", err));
  };

  const handleTriggerSync = () => {
    setSyncing(true);
    fetch(`${API_BASE_URL}/api/trigger-sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": API_SECRET_KEY },
      body: JSON.stringify({ dry_run: false })
    })
      .then((res) => res.json())
      .then(() => fetchOutlets())
      .catch((err) => console.error("Sync error:", err))
      .finally(() => setSyncing(false));
  };

  const handleUpdateOutletAdmin = (updatedOutlet) => {
    setOutlets((prev) =>
      prev.map((o) => (o.store_id === updatedOutlet.store_id ? { ...o, ...updatedOutlet } : o))
    );
  };

  const handleMerchantLoginSuccess = (user) => {
    setCurrentUser(user);
    localStorage.setItem("foodmaster_user", JSON.stringify(user));
  };

  const handleAdminLoginSuccess = (user) => {
    setCurrentUser(user);
    localStorage.setItem("foodmaster_user", JSON.stringify(user));
    setActiveTab("merchant");
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem("foodmaster_user");
    setActiveTab("merchant");
  };

  // =====================================================================
  // RENDER CASE 1: Merchant Token Link — Expired Access Page
  // =====================================================================
  if (tokenParam && isExpired && targetOutlet) {
    return (
      <ExpiredAccessPage
        theme={theme}
        onToggleTheme={toggleTheme}
        outletInfo={targetOutlet}
        reason={targetOutlet.reason}
      />
    );
  }

  // =====================================================================
  // RENDER CASE 2: Merchant Token Link — Valid Token, Needs Username/Password Login
  // =====================================================================
  if (tokenParam && !isExpired && targetOutlet && (!currentUser || currentUser.store_id !== targetOutlet.store_id)) {
    return (
      <MerchantTokenLoginPage
        theme={theme}
        onToggleTheme={toggleTheme}
        outletInfo={targetOutlet}
        onLoginSuccess={handleMerchantLoginSuccess}
      />
    );
  }

  // =====================================================================
  // RENDER CASE 3: Admin Login Page (Root without token)
  // =====================================================================
  if (!currentUser) {
    return (
      <LoginPage
        theme={theme}
        onToggleTheme={toggleTheme}
        onLoginSuccess={handleAdminLoginSuccess}
      />
    );
  }

  // =====================================================================
  // RENDER CASE 4: Authenticated Dashboard (Merchant or Admin)
  // =====================================================================
  return (
    <div className="min-h-screen bg-[#fff9f8] text-slate-900 dark:bg-black dark:text-white transition-colors duration-200">
      <StarField active={theme === "dark"} />

      <NavHeader
        activeTab={activeTab}
        onTabChange={setActiveTab}
        theme={theme}
        onToggleTheme={toggleTheme}
        currentUser={currentUser}
        onLogout={handleLogout}
        apiConnected={apiConnected}
        onTriggerSync={handleTriggerSync}
        syncing={syncing}
      />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">

        {/* MERCHANT VIEW */}
        {currentUser.role === "merchant" && (
          <MerchantDashboard
            outlets={visibleOutlets}
            onToggleVercel={handleToggleVercel}
            onRefresh={fetchOutlets}
            loading={loading}
            currentUser={currentUser}
          />
        )}

        {/* ADMIN VIEW */}
        {currentUser.role === "admin" && (
          <>
            <div className={activeTab === "merchant" ? "" : "hidden"}>
              <MerchantDashboard
                outlets={outlets}
                onToggleVercel={handleToggleVercel}
                onRefresh={fetchOutlets}
                loading={loading}
                currentUser={currentUser}
              />
            </div>
            <div className={activeTab === "links" ? "" : "hidden"}>
              <LinkGeneratorTab
                outlets={outlets}
                onUpdateOutlet={handleUpdateOutletAdmin}
                onRefresh={fetchOutlets}
                loading={loading}
              />
            </div>
            <div className={activeTab === "admin" ? "" : "hidden"}>
              <AdminDashboard
                outlets={outlets}
                onUpdateOutlet={handleUpdateOutletAdmin}
                onRefresh={fetchOutlets}
                loading={loading}
              />
            </div>
            <div className={activeTab === "sessions" ? "" : "hidden"}>
              <SessionMonitorTab
                API_BASE_URL={API_BASE_URL}
                API_SECRET_KEY={API_SECRET_KEY}
              />
            </div>
            <div className={activeTab === "logs" ? "" : "hidden"}>
              <AuditLogsTab
                API_BASE_URL={API_BASE_URL}
                API_SECRET_KEY={API_SECRET_KEY}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

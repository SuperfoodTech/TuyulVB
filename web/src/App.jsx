import React, { useState, useEffect } from "react";
import NavHeader from "./components/NavHeader";
import LoginModal from "./components/LoginModal";
import MerchantDashboard from "./components/MerchantDashboard";
import AdminDashboard from "./components/AdminDashboard";
import AuditLogsTab from "./components/AuditLogsTab";
import SessionMonitorTab from "./components/SessionMonitorTab";
import { useTheme } from "./hooks/useTheme";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState("merchant"); // merchant | admin | logs | sessions
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem("foodmaster_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [outlets, setOutlets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [apiConnected, setApiConnected] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Compute API_BASE_URL
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
        setOutlets(Array.isArray(data) ? data : []);
        setApiConnected(true);
      })
      .catch((err) => {
        console.warn("Backend API not reachable, loading fallback local outlets:", err);
        setApiConnected(false);
        // Fallback sample data if API server is offline
        setOutlets([
          {
            store_id: "ST1001",
            merchant_id: "M101",
            owner_name: "Merchant Foodnesia",
            portal_name: "Foodnesia Portal",
            outlet_long_name: "Foodnesia Outlet Utama",
            outlet_short_name: "Foodnesia",
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
            last_checked_at: new Date().isoformat()
          }
        ]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchOutlets();
  }, []);

  const handleToggleVercel = (storeId, newToggle, duration) => {
    // Optimistic UI update
    setOutlets((prev) =>
      prev.map((o) => (o.store_id === storeId ? { ...o, vercel_toggle: newToggle } : o))
    );

    fetch(`${API_BASE_URL}/api/toggle`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_SECRET_KEY
      },
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
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_SECRET_KEY
      },
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

  const handleLoginSuccess = (user) => {
    setCurrentUser(user);
    localStorage.setItem("foodmaster_user", JSON.stringify(user));
    if (user.role === "admin") {
      setActiveTab("admin");
    } else {
      setActiveTab("merchant");
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem("foodmaster_user");
    setActiveTab("merchant");
  };

  return (
    <div className="min-h-screen bg-[#fff9f8] text-slate-900 dark:bg-black dark:text-white transition-colors duration-200">
      
      {/* Navigation Header */}
      <NavHeader
        activeTab={activeTab}
        onTabChange={setActiveTab}
        theme={theme}
        onToggleTheme={toggleTheme}
        currentUser={currentUser}
        onOpenLogin={() => setIsLoginModalOpen(true)}
        onLogout={handleLogout}
        apiConnected={apiConnected}
        onTriggerSync={handleTriggerSync}
        syncing={syncing}
      />

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        
        {activeTab === "merchant" && (
          <MerchantDashboard
            outlets={outlets}
            onToggleVercel={handleToggleVercel}
            onRefresh={fetchOutlets}
            loading={loading}
          />
        )}

        {activeTab === "admin" && (
          <AdminDashboard
            outlets={outlets}
            onUpdateOutlet={handleUpdateOutletAdmin}
            onRefresh={fetchOutlets}
            loading={loading}
          />
        )}

        {activeTab === "logs" && (
          <AuditLogsTab
            API_BASE_URL={API_BASE_URL}
            API_SECRET_KEY={API_SECRET_KEY}
          />
        )}

        {activeTab === "sessions" && (
          <SessionMonitorTab
            API_BASE_URL={API_BASE_URL}
            API_SECRET_KEY={API_SECRET_KEY}
          />
        )}

      </main>

      {/* Login Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />

    </div>
  );
}

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

  // URL Query Parameters check (e.g. ?token=mcht_live_m101_8f9a2b or ?merchant=M101)
  const [tokenParam] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      return params.get("token") || params.get("merchant") || params.get("merchant_id") || params.get("store");
    }
    return null;
  });

  const [targetMerchantOutlets, setTargetMerchantOutlets] = useState([]);
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
        return "http://localhost:8000";
      }
      return `${window.location.protocol}//${hostname}:8000`;
    }
    return "http://localhost:8000";
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
            store_id: "21708900",
            merchant_id: "11511947",
            owner_name: "Fando",
            portal_name: "SuperFood",
            outlet_long_name: "Ayam Lengkuas, Ayam Warisan by Foodnesia",
            outlet_short_name: "Ayam Lengkuas F",
            merchant_username: "superfoodapp",
            merchant_password: "Master@00@",
            access_token: "mcht_live_11511947_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "09:00",
            close_time: "20:00",
            friday_open_time: "09:00",
            friday_close_time: "20:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "21897117",
            merchant_id: "14367488",
            owner_name: "Fando",
            portal_name: "WonderFood",
            outlet_long_name: "Ayam Goreng Lengkuas, Ayam Warisan by WonderFood",
            outlet_short_name: "Ayam Goreng Lengkuas W",
            merchant_username: "wonderfoodapp",
            merchant_password: "Master@00@",
            access_token: "mcht_live_14367488_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "21901580",
            merchant_id: "14384953",
            owner_name: "Fando",
            portal_name: "LOKARASA",
            outlet_long_name: "Ayam Laos Lengkuas Citraland",
            outlet_short_name: "Ayam Laos Citra D",
            merchant_username: "lokarasaapp",
            merchant_password: "Master@00@",
            access_token: "mcht_live_14384953_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "22300081",
            merchant_id: "15892383",
            owner_name: "Fando",
            portal_name: "Do Eat, Gurame Bakar",
            outlet_long_name: "Ayam Laos Lengkuas Citraland",
            outlet_short_name: "Ayam Laos Citra D",
            merchant_username: "doeatapp",
            merchant_password: "Master@00@",
            access_token: "mcht_live_15892383_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "22299060",
            merchant_id: "15892383",
            owner_name: "Fando",
            portal_name: "Do Eat, Gurame Bakar",
            outlet_long_name: "Tahu Mbledos Pandanlandung",
            outlet_short_name: "Tahu Mbledos D",
            merchant_username: "doeatapp",
            merchant_password: "Master@00@",
            access_token: "mcht_live_15892383_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: false,
            shopee_toggle_last: false,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-04-01",
            subscription_end: "2026-06-30",
            subscription_status: "Expired"
          },
          {
            store_id: "21830870",
            merchant_id: "11511947",
            owner_name: "Yolo",
            portal_name: "SuperFood",
            outlet_long_name: "Warung Nasi Rawon, Foodnesia",
            outlet_short_name: "Warung NasiRawonFoodnesia",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_11511947_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: false,
            shopee_toggle_last: false,
            suspension_status: true,
            suspension_reason: "Menunggak tagihan 3x",
            suspension_start: "2026-08-02",
            suspension_end: "2026-12-31",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "21897166",
            merchant_id: "14367488",
            owner_name: "Yolo",
            portal_name: "WonderFood",
            outlet_long_name: "Warung Lontong Sayur, WonderFood",
            outlet_short_name: "Wrg Ltg Syr Bu Sdarwati W",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_14367488_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: false,
            shopee_toggle_last: false,
            suspension_status: true,
            suspension_reason: "Menunggak tagihan 3x",
            suspension_start: "2026-08-02",
            suspension_end: "2026-12-31",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "21901629",
            merchant_id: "14384953",
            owner_name: "Yolo",
            portal_name: "LOKARASA",
            outlet_long_name: "Rawon dan Lontong Sayur, Lokarasa",
            outlet_short_name: "Wr Lontong Sudarwati L",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_14384953_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: false,
            shopee_toggle_last: false,
            suspension_status: true,
            suspension_reason: "Menunggak tagihan 3x",
            suspension_start: "2026-08-02",
            suspension_end: "2026-12-31",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "22299059",
            merchant_id: "15892383",
            owner_name: "Yolo",
            portal_name: "Do Eat, Gurame Bakar",
            outlet_long_name: "Nasi Rawon Kebonsari",
            outlet_short_name: "Nasi Rawon D",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_15892383_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: false,
            shopee_toggle_last: false,
            suspension_status: true,
            suspension_reason: "Menunggak tagihan 3x",
            suspension_start: "2026-08-02",
            suspension_end: "2026-12-31",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "22403554",
            merchant_id: "11511947",
            owner_name: "Yolo",
            portal_name: "SuperFood",
            outlet_long_name: "Sate Ayam Special 1, Foodnesia",
            outlet_short_name: "Sate Ayam Pucang F",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_11511947_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "22403325",
            merchant_id: "14367488",
            owner_name: "Yolo",
            portal_name: "WonderFood",
            outlet_long_name: "Sate Ayam 1, WonderFood",
            outlet_short_name: "Sate Ayam Kumis W",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_14367488_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "22403231",
            merchant_id: "14384953",
            owner_name: "Yolo",
            portal_name: "LOKARASA",
            outlet_long_name: "Sate Ayam Mantap 1, Lokarasa",
            outlet_short_name: "Sate Ayam Kumis L",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_14384953_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          },
          {
            store_id: "22403454",
            merchant_id: "15892383",
            owner_name: "Yolo",
            portal_name: "Do Eat, Gurame Bakar",
            outlet_long_name: "Sate Ayam Pucang",
            outlet_short_name: "Sate Ayam Pucang D",
            merchant_username: "auto7313",
            merchant_password: "Auto@7313",
            access_token: "mcht_live_15892383_8f9a2b",
            operating_days: "1,2,3,4,5,6,7",
            open_time: "08:00",
            close_time: "22:00",
            vercel_toggle: true,
            shopee_toggle_last: true,
            suspension_status: false,
            suspension_reason: "",
            subscription_package: "3 Bulan",
            subscription_start: "2026-08-01",
            subscription_end: "2026-11-01",
            subscription_status: "Active"
          }
        ];
        setOutlets(fallbackList);
        evaluateUrlToken(fallbackList);
      })
      .finally(() => setLoading(false));
  };

  // Evaluasi link token khusus merchant (berbasis Kode Unik Akses / Token)
  const evaluateUrlToken = (allOutlets) => {
    if (!tokenParam) return;

    const q = tokenParam.toLowerCase().trim();

    // Match exact store by access_token, merchant_id, or store_id
    const matchedTokenStore = allOutlets.find((o) => {
      const token = (o.access_token || "").toLowerCase();
      const mId = (o.merchant_id || "").toLowerCase();
      const storeId = (o.store_id || "").toLowerCase();
      return token === q || mId === q || storeId === q;
    });

    if (!matchedTokenStore) {
      setTargetOutlet({
        store_id: tokenParam,
        portal_name: "Unknown Merchant",
        reason: "Kode Akses Unik / Link Token Merchant tidak valid atau telah dicabut oleh Admin."
      });
      setIsExpired(true);
      return;
    }

    const targetMerchantId = matchedTokenStore.merchant_id;
    const matchedStores = allOutlets.filter(
      (o) => o.merchant_id === targetMerchantId || (o.access_token && o.access_token.toLowerCase() === q)
    );

    setTargetOutlet(matchedTokenStore);
    setTargetMerchantOutlets(matchedStores);

    // Check if ALL stores under this merchant are expired
    const allExpired = matchedStores.every((s) => {
      const subInfo = getSubscriptionInfo(s.subscription_end);
      return s.subscription_status === "Expired" || subInfo.isExpired;
    });

    setIsExpired(allExpired);
  };

  useEffect(() => {
    fetchOutlets();
    const interval = setInterval(() => {
      fetchOutlets();
    }, 5000);
    return () => clearInterval(interval);
  }, [tokenParam]);

  // Filtered outlets untuk Merchant View — Tampilkan SEMUA outlet milik Merchant ID ini!
  const visibleOutlets = currentUser?.role === "merchant"
    ? outlets.filter((o) => o.merchant_id === currentUser.merchant_id)
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
    fetch(`${API_BASE_URL}/api/outlets/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": API_SECRET_KEY },
      body: JSON.stringify(updatedOutlet)
    })
      .then((res) => res.json())
      .catch((err) => console.error("Error updating outlet:", err));
  };

  const handleMerchantLoginSuccess = (user) => {
    // Session merchant menyimpan merchant_id
    const merchantSession = {
      ...user,
      merchant_id: targetOutlet?.merchant_id
    };
    setCurrentUser(merchantSession);
    localStorage.setItem("foodmaster_user", JSON.stringify(merchantSession));
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
  // RENDER CASE 2: Merchant Token Link — Valid Merchant ID, Needs Login
  // =====================================================================
  if (tokenParam && !isExpired && targetOutlet && (!currentUser || currentUser.merchant_id !== targetOutlet.merchant_id)) {
    return (
      <MerchantTokenLoginPage
        theme={theme}
        onToggleTheme={toggleTheme}
        outletInfo={targetOutlet}
        merchantStores={targetMerchantOutlets}
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

        {/* MERCHANT VIEW — Tampilkan SEMUA toko milik Merchant ID ini */}
        {currentUser.role === "merchant" && (
          <MerchantDashboard
            outlets={visibleOutlets}
            onToggleVercel={handleToggleVercel}
            onRefresh={fetchOutlets}
            loading={loading}
            currentUser={currentUser}
            onUpdateOutlet={handleUpdateOutletAdmin}
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
                onUpdateOutlet={handleUpdateOutletAdmin}
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

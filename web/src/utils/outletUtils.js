/**
 * Helper functions untuk formatting data outlet FoodMaster
 */

const DAY_NAMES_SHORT = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];
const DAY_NAMES_FULL  = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];

/**
 * Mendapatkan ID hari ini dalam format Shopee (1=Senin, 7=Minggu)
 */
export function getTodayShopeeDayId() {
  const jsDay = new Date().getDay(); // 0 = Minggu, 1 = Senin ... 6 = Sabtu
  return jsDay === 0 ? 7 : jsDay;
}

/**
 * Mengambil nama hari ini (misal "Senin")
 */
export function getTodayName() {
  const todayId = getTodayShopeeDayId();
  return DAY_NAMES_FULL[todayId - 1];
}

/**
 * Menghasilkan jadwal operasional 7 hari lengkap per outlet.
 * Mendukung kustomisasi per hari (misal Jumat buka siang, Weekend jam weekend).
 */
export function getWeeklySchedule(outlet) {
  if (!outlet) return [];

  // Parse operating_days array (1..7)
  const activeDays = String(outlet.operating_days || "1,2,3,4,5,6,7")
    .split(",")
    .map((d) => parseInt(d.trim(), 10))
    .filter((d) => !isNaN(d));

  const todayId = getTodayShopeeDayId();

  // If custom weekly_schedule JSON exists in outlet object
  const customSchedule = outlet.weekly_schedule || {};

  return [1, 2, 3, 4, 5, 6, 7].map((dayId) => {
    const isToday = dayId === todayId;
    const dayName = DAY_NAMES_FULL[dayId - 1];

    let isOperating = activeDays.includes(dayId);
    let openTime = outlet.open_time || "08:00";
    let closeTime = outlet.close_time || "22:00";
    let note = "Normal";

    if (customSchedule[dayId]) {
      if (customSchedule[dayId].isOperating !== undefined) {
        isOperating = customSchedule[dayId].isOperating;
      }
      openTime = customSchedule[dayId].openTime || customSchedule[dayId].open || openTime;
      closeTime = customSchedule[dayId].closeTime || customSchedule[dayId].close || closeTime;
      note = customSchedule[dayId].note !== undefined ? customSchedule[dayId].note : note;
    } else if (dayId === 5) {
      // Jumat: Buka Siang / Sholat Jumat
      openTime = outlet.friday_open_time || openTime;
      closeTime = outlet.friday_close_time || closeTime;
      if (outlet.friday_open_time) note = "Jumat Siang";
    } else if (dayId === 6 || dayId === 7) {
      // Weekend: Jam Libur
      openTime = outlet.weekend_open_time || openTime;
      closeTime = outlet.weekend_close_time || closeTime;
      if (outlet.weekend_open_time) note = "Weekend";
    }

    return {
      dayId,
      name: dayName,
      shortName: DAY_NAMES_SHORT[dayId - 1],
      isToday,
      isOperating,
      openTime,
      closeTime,
      hours: isOperating ? `${openTime} – ${closeTime}` : "Libur (Tutup)",
      note: isOperating ? note : "Libur",
    };
  });
}

/**
 * Mengambil jam operasional spesifik untuk HARI INI
 */
export function getTodayOperatingHours(outlet) {
  const schedule = getWeeklySchedule(outlet);
  const todayItem = schedule.find((s) => s.isToday);
  if (!todayItem || !todayItem.isOperating) {
    return { isOperatingToday: false, hoursText: "Libur Hari Ini", todayName: getTodayName() };
  }
  return {
    isOperatingToday: true,
    hoursText: todayItem.hours,
    todayName: todayItem.name,
    note: todayItem.note,
  };
}

/**
 * Format operating_days string ke label hari yang ringkas.
 */
export function formatOperatingDays(daysStr) {
  if (!daysStr) return "Setiap Hari";
  const days = String(daysStr)
    .split(",")
    .map((d) => parseInt(d.trim(), 10))
    .filter((d) => !isNaN(d) && d >= 1 && d <= 7);

  if (days.length === 0) return "-";
  if (days.length === 7) return "Setiap Hari";

  const sorted = [...days].sort((a, b) => a - b);
  const isConsecutive = sorted.every((d, i) => i === 0 || d === sorted[i - 1] + 1);

  if (isConsecutive && sorted.length >= 3) {
    const first = DAY_NAMES_SHORT[sorted[0] - 1] || `H${sorted[0]}`;
    const last  = DAY_NAMES_SHORT[sorted[sorted.length - 1] - 1] || `H${sorted[sorted.length - 1]}`;
    return `${first} – ${last}`;
  }

  return sorted
    .map((d) => DAY_NAMES_SHORT[d - 1] || `H${d}`)
    .join(", ");
}

/**
 * Format operating_days ke daftar lengkap untuk tooltip.
 */
export function formatOperatingDaysFull(daysStr) {
  if (!daysStr) return "Setiap Hari";
  const days = String(daysStr)
    .split(",")
    .map((d) => parseInt(d.trim(), 10))
    .filter((d) => !isNaN(d) && d >= 1 && d <= 7)
    .sort((a, b) => a - b);
  if (days.length === 7) return "Setiap Hari";
  return days.map((d) => DAY_NAMES_FULL[d - 1] || `Hari ${d}`).join(", ");
}

/**
 * Format tanggal ISO ke "01 Jan 2026"
 */
export function formatDateID(dateStr) {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

/**
 * Hitung sisa hari subscription dari hari ini.
 */
export function getSubscriptionInfo(endDateStr) {
  if (!endDateStr) return { daysLeft: null, isExpired: false, isExpiringSoon: false };
  try {
    const end  = new Date(endDateStr);
    const now  = new Date();
    now.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);
    const diff = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
    return {
      daysLeft: diff,
      isExpired: diff < 0,
      isExpiringSoon: diff >= 0 && diff <= 14,
    };
  } catch {
    return { daysLeft: null, isExpired: false, isExpiringSoon: false };
  }
}

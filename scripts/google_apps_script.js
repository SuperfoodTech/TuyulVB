/**
 * ==============================================================================
 * Auto-OC Google Apps Script Webhook Engine
 * ==============================================================================
 * Skrip ini menerima request HTTP POST dari Backend Auto-OC / Web Dashboard
 * untuk memperbarui sel Google Sheets secara real-time (2-Way Sync):
 * 1. update_toggle         -> Memperbarui Status Utama (Open/Close) [Kolom O]
 * 2. update_shopee_status  -> Memperbarui Status Aktual (Open/Busy/Close) [Kolom P]
 * 3. update_outlet         -> Memperbarui Jam Operasional (Jam Buka, Jam Tutup, dll)
 * ==============================================================================
 */

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return responseJSON({ status: "error", message: "No post data received" });
    }

    var data = JSON.parse(e.postData.contents);
    var action = data.action;
    var targetStoreId = String(data.store_id || "").trim();

    if (!targetStoreId) {
      return responseJSON({ status: "error", message: "Missing store_id" });
    }

    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var dataRange = sheet.getDataRange();
    var values = dataRange.getValues();
    var headers = values[0];

    // Pemetaan nama kolom ke indeks 0-based
    var colMap = {};
    for (var j = 0; j < headers.length; j++) {
      colMap[String(headers[j]).trim().toLowerCase()] = j;
    }

    // Cari baris berdasarkan Store ID
    var targetRowIndex = -1;
    var storeIdColIndex = colMap["store id"] !== undefined ? colMap["store id"] : colMap["store_id"];
    
    // Jika header "Store ID" tidak ditemukan di baris 1, cari di semua sel
    for (var i = 1; i < values.length; i++) {
      var row = values[i];
      if (storeIdColIndex !== undefined) {
        if (String(row[storeIdColIndex]).trim() === targetStoreId) {
          targetRowIndex = i + 1; // 1-based index untuk Sheets API
          break;
        }
      } else {
        // Fallback: Pindai seluruh kolom pada baris untuk mencocokkan Store ID
        for (var c = 0; c < row.length; c++) {
          if (String(row[c]).trim() === targetStoreId) {
            targetRowIndex = i + 1;
            break;
          }
        }
        if (targetRowIndex !== -1) break;
      }
    }

    if (targetRowIndex === -1) {
      return responseJSON({ status: "error", message: "Store ID " + targetStoreId + " not found in sheet" });
    }

    // ==========================================================================
    // FX 1: SINKRONISASI VERCEL TOGGLE (STATUS UTAMA)
    // ==========================================================================
    if (action === "update_toggle") {
      var vercelToggle = data.vercel_toggle;
      var statusValue = data.status_text || (vercelToggle ? "On" : "Off");

      // Kolom O (Status Utama (Open/Close)) -> 1-based Column 15
      var mainStatusCol = colMap["status utama (open/close)"] !== undefined ? (colMap["status utama (open/close)"] + 1) : 15;
      sheet.getRange(targetRowIndex, mainStatusCol).setValue(statusValue);

      return responseJSON({
        status: "success",
        action: "update_toggle",
        store_id: targetStoreId,
        row: targetRowIndex,
        new_status: statusValue
      });
    }

    // ==========================================================================
    // FX 2: SINKRONISASI STATUS AKTUAL SHOPEE PARTNER (KOLOM P)
    // ==========================================================================
    if (action === "update_shopee_status") {
      var shopeeStatus = data.shopee_status;
      var actualValue = data.actual_status_text || (shopeeStatus ? "On" : "Off");

      // Kolom P (Status Aktual (Open/Busy/Close)) -> 1-based Column 16
      var actualStatusCol = colMap["status aktual (open/busy/close)"] !== undefined ? (colMap["status aktual (open/busy/close)"] + 1) : 16;
      sheet.getRange(targetRowIndex, actualStatusCol).setValue(actualValue);

      return responseJSON({
        status: "success",
        action: "update_shopee_status",
        store_id: targetStoreId,
        row: targetRowIndex,
        actual_status: actualValue
      });
    }

    // ==========================================================================
    // FX 3: SINKRONISASI JAM OPERASIONAL 7 HARI & ATRIBUT OUTLET
    // ==========================================================================
    if (action === "update_outlet" || action === "update_operating_hours") {
      var updates = data.updates || data;

      // Update Kolom P (Status Aktual) jika ada
      if (updates.actual_status_text || updates.shopee_toggle_last !== undefined) {
        var actualVal = updates.actual_status_text || (updates.shopee_toggle_last ? "On" : "Off");
        var actualStatusCol = colMap["status aktual (open/busy/close)"] !== undefined ? (colMap["status aktual (open/busy/close)"] + 1) : 16;
        sheet.getRange(targetRowIndex, actualStatusCol).setValue(actualVal);
      }

      // Update 7 Hari Operasional (Senin, Selasa, Rabu, Kamis, Jumat, Sabtu, Minggu) -> Kolom S - Y
      var days = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"];
      var dayHours = updates.day_operating_hours || updates.days || updates;
      for (var d = 0; d < days.length; d++) {
        var dayName = days[d];
        var dayCap = dayName.charAt(0).toUpperCase() + dayName.slice(1);
        var dayVal = dayHours[dayName] || dayHours[dayCap];
        if (dayVal !== undefined && colMap[dayName] !== undefined) {
          sheet.getRange(targetRowIndex, colMap[dayName] + 1).setValue(String(dayVal));
        }
      }

      // Update Jam Buka (jika ada)
      if (updates.open_time && colMap["jam buka"] !== undefined) {
        sheet.getRange(targetRowIndex, colMap["jam buka"] + 1).setValue(updates.open_time);
      }

      // Update Jam Tutup (jika ada)
      if (updates.close_time && colMap["jam tutup"] !== undefined) {
        sheet.getRange(targetRowIndex, colMap["jam tutup"] + 1).setValue(updates.close_time);
      }

      // Update Hari Operasional
      if (updates.operating_days && colMap["hari operasional"] !== undefined) {
        sheet.getRange(targetRowIndex, colMap["hari operasional"] + 1).setValue(updates.operating_days);
      }

      // Update Vercel Toggle jika disertakan dalam updates
      if (updates.vercel_toggle !== undefined) {
        var mainStatusCol = colMap["status utama (open/close)"] !== undefined ? (colMap["status utama (open/close)"] + 1) : 15;
        sheet.getRange(targetRowIndex, mainStatusCol).setValue(updates.vercel_toggle ? "On" : "Off");
      }

      return responseJSON({
        status: "success",
        action: action,
        store_id: targetStoreId,
        row: targetRowIndex,
        updates: updates
      });
    }

    return responseJSON({ status: "error", message: "Unknown action: " + action });

  } catch (err) {
    return responseJSON({ status: "error", message: err.toString() });
  }
}

function responseJSON(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "ok",
    service: "Auto-OC Google Apps Script Webhook Engine",
    timestamp: new Date().toISOString()
  })).setMimeType(ContentService.MimeType.JSON);
}

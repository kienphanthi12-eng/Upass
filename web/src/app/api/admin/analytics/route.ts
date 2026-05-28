import { NextRequest, NextResponse } from "next/server";
import { createAdminSupabase } from "@/lib/supabase-admin";

export async function GET(req: NextRequest) {
  try {
    const supabase = createAdminSupabase();

    // Query data from the last 30 days to calculate metrics
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoIso = thirtyDaysAgo.toISOString();

    const { data, error } = await supabase
      .from("web_analytics")
      .select("session_id, path, browser, os, device_type, created_at")
      .gte("created_at", thirtyDaysAgoIso)
      .order("created_at", { ascending: false });

    if (error) {
      console.error("Supabase query error:", error);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    const rows = data || [];
    const totalViews = rows.length;

    // Unique Visitors (unique sessions)
    const uniqueSessionIds = new Set(rows.map((r) => r.session_id));
    const uniqueVisitors = uniqueSessionIds.size;

    // Active Users (sessions in the last 5 minutes)
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    const activeSessions = new Set(
      rows
        .filter((r) => new Date(r.created_at) >= fiveMinutesAgo)
        .map((r) => r.session_id)
    );
    const activeUsers = activeSessions.size;

    // Top Pages
    const pageCounts: Record<string, number> = {};
    rows.forEach((r) => {
      pageCounts[r.path] = (pageCounts[r.path] || 0) + 1;
    });
    const topPages = Object.entries(pageCounts)
      .map(([path, views]) => ({ path, views }))
      .sort((a, b) => b.views - a.views)
      .slice(0, 10);

    // Browser Breakdown
    const browserCounts: Record<string, number> = {};
    rows.forEach((r) => {
      const b = r.browser || "Unknown";
      browserCounts[b] = (browserCounts[b] || 0) + 1;
    });
    const browsers = Object.entries(browserCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    // OS Breakdown
    const osCounts: Record<string, number> = {};
    rows.forEach((r) => {
      const o = r.os || "Unknown";
      osCounts[o] = (osCounts[o] || 0) + 1;
    });
    const os = Object.entries(osCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    // Device Breakdown
    const deviceCounts: Record<string, number> = {};
    rows.forEach((r) => {
      const d = r.device_type || "desktop";
      deviceCounts[d] = (deviceCounts[d] || 0) + 1;
    });
    const devices = Object.entries(deviceCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    // Chart Data: Last 7 Days Timeline
    const chartDataMap: Record<string, number> = {};
    // Pre-populate last 7 days with 0 views
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
      chartDataMap[dateStr] = 0;
    }

    rows.forEach((r) => {
      const rDate = new Date(r.created_at);
      const dateStr = rDate.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
      if (dateStr in chartDataMap) {
        chartDataMap[dateStr]++;
      }
    });

    const chartData = Object.entries(chartDataMap).map(([date, views]) => ({
      date,
      views,
    }));

    // Recent Logs (top 15)
    const recentLogs = rows.slice(0, 15).map((r) => ({
      path: r.path,
      browser: r.browser,
      os: r.os,
      device_type: r.device_type,
      created_at: r.created_at,
    }));

    return NextResponse.json({
      totalViews,
      uniqueVisitors,
      activeUsers,
      topPages,
      browsers,
      os,
      devices,
      chartData,
      recentLogs,
    });
  } catch (err: any) {
    console.error("Admin analytics API exception:", err);
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}

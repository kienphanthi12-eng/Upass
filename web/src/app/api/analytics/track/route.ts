import { NextRequest, NextResponse } from "next/server";
import { createAdminSupabase } from "@/lib/supabase-admin";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { path, referrer, browser, os, device_type, session_id } = body;

    if (!path || !session_id) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    // Resolve client IP address from headers
    const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim() || 
               req.headers.get("x-real-ip") || 
               "127.0.0.1";

    const supabase = createAdminSupabase();
    const { error } = await supabase.from("web_analytics").insert({
      session_id,
      path,
      referrer: referrer || null,
      browser: browser || "Unknown",
      os: os || "Unknown",
      device_type: device_type || "desktop",
      ip_address: ip,
    });

    if (error) {
      console.error("Failed to insert analytics to DB:", error);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("Analytics tracking API exception:", err);
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}

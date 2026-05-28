"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

// Simple helper to parse User-Agent client-side
function getClientSpecs() {
  if (typeof window === "undefined") {
    return { browser: "Unknown", os: "Unknown", device_type: "desktop" };
  }

  const ua = window.navigator.userAgent;
  let browser = "Unknown";
  let os = "Unknown";
  let device_type = "desktop";

  // Browser detection
  if (ua.indexOf("Firefox") > -1) browser = "Firefox";
  else if (ua.indexOf("SamsungBrowser") > -1) browser = "Samsung Browser";
  else if (ua.indexOf("Opera") > -1 || ua.indexOf("OPR") > -1) browser = "Opera";
  else if (ua.indexOf("Trident") > -1) browser = "Internet Explorer";
  else if (ua.indexOf("Edge") > -1 || ua.indexOf("Edg") > -1) browser = "Edge";
  else if (ua.indexOf("Chrome") > -1) browser = "Chrome";
  else if (ua.indexOf("Safari") > -1) browser = "Safari";

  // OS detection
  if (ua.indexOf("Windows NT 10.0") > -1) os = "Windows 10/11";
  else if (ua.indexOf("Windows NT 6.2") > -1) os = "Windows 8";
  else if (ua.indexOf("Windows NT 6.1") > -1) os = "Windows 7";
  else if (ua.indexOf("Macintosh") > -1) os = "macOS";
  else if (ua.indexOf("Android") > -1) os = "Android";
  else if (ua.indexOf("iPhone") > -1) os = "iOS (iPhone)";
  else if (ua.indexOf("iPad") > -1) os = "iOS (iPad)";
  else if (ua.indexOf("Linux") > -1) os = "Linux";

  // Device Type detection
  if (/mobi|android|iphone|ipod/i.test(ua)) {
    device_type = "mobile";
  } else if (/ipad|tablet/i.test(ua)) {
    device_type = "tablet";
  }

  return { browser, os, device_type };
}

// Simple helper to get or create session ID
function getOrCreateSessionId() {
  if (typeof window === "undefined") return "";

  let sessionId = window.sessionStorage.getItem("upass_analytics_session");
  if (!sessionId) {
    sessionId = "sess_" + Math.random().toString(36).substring(2, 15) + "_" + Date.now().toString(36);
    window.sessionStorage.setItem("upass_analytics_session", sessionId);
  }
  return sessionId;
}

export default function AnalyticsTracker() {
  const pathname = usePathname();
  const lastPathname = useRef<string | null>(null);

  useEffect(() => {
    // Prevent double tracking of the same path (e.g. strict mode twice or renders)
    if (lastPathname.current === pathname) return;
    lastPathname.current = pathname;

    const session_id = getOrCreateSessionId();
    const { browser, os, device_type } = getClientSpecs();
    const referrer = typeof document !== "undefined" ? document.referrer : "";

    fetch("/api/analytics/track", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        path: pathname,
        referrer,
        browser,
        os,
        device_type,
        session_id,
      }),
    }).catch((err) => {
      console.error("Failed to send analytics tracking update:", err);
    });
  }, [pathname]);

  return null;
}

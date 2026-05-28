"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Activity, 
  Eye, 
  Users, 
  Smartphone, 
  Monitor, 
  Laptop, 
  Compass, 
  ChevronRight, 
  RefreshCw, 
  Clock, 
  ArrowLeft 
} from "lucide-react";

interface PageViewLog {
  path: string;
  browser: string;
  os: string;
  device_type: string;
  created_at: string;
}

interface AnalyticsData {
  totalViews: number;
  uniqueVisitors: number;
  activeUsers: number;
  topPages: { path: string; views: number }[];
  browsers: { name: string; count: number }[];
  os: { name: string; count: number }[];
  devices: { name: string; count: number }[];
  chartData: { date: string; views: number }[];
  recentLogs: PageViewLog[];
}

export default function AdminDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(true);

  const fetchAnalytics = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await fetch("/api/admin/analytics");
      if (!res.ok) throw new Error("Failed to fetch analytics");
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  useEffect(() => {
    if (!isLive) return;
    const interval = setInterval(() => {
      fetchAnalytics(true);
    }, 5000);
    return () => clearInterval(interval);
  }, [isLive]);

  // Compute SVG line chart dimensions
  const renderChart = () => {
    if (!data || data.chartData.length === 0) return null;
    const chart = data.chartData;
    const width = 600;
    const height = 180;
    const padding = 20;

    const maxViews = Math.max(...chart.map((d) => d.views), 10); // min height baseline

    // Generate points
    const points = chart.map((d, index) => {
      const x = padding + (index * (width - padding * 2)) / (chart.length - 1);
      const y = height - padding - (d.views * (height - padding * 2)) / maxViews;
      return { x, y, label: d.date, value: d.views };
    });

    const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
    
    // Area D (for gradient fill under the line)
    const areaD = `${pathD} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;

    return (
      <div className="relative w-full h-[200px] mt-4">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
          <defs>
            <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
            const y = padding + ratio * (height - padding * 2);
            const val = Math.round(maxViews * (1 - ratio));
            return (
              <g key={idx} className="opacity-15">
                <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="#94a3b8" strokeDasharray="3 3" />
                <text x={4} y={y + 4} fill="#94a3b8" fontSize="8" className="font-mono">{val}</text>
              </g>
            );
          })}

          {/* Area fill */}
          <path d={areaD} fill="url(#chartGrad)" />

          {/* Line */}
          <path d={pathD} fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Data points */}
          {points.map((p, idx) => (
            <g key={idx} className="group cursor-pointer">
              <circle cx={p.x} cy={p.y} r="4" fill="#1e293b" stroke="#3b82f6" strokeWidth="2" />
              <circle cx={p.x} cy={p.y} r="8" fill="#3b82f6" className="opacity-0 group-hover:opacity-20 transition-opacity" />
              <text 
                x={p.x} 
                y={height - 2} 
                fill="#94a3b8" 
                fontSize="9" 
                textAnchor="middle" 
                className="opacity-70 font-mono"
              >
                {p.label}
              </text>
              {/* Tooltip on hover */}
              <title>{`${p.label}: ${p.value} views`}</title>
            </g>
          ))}
        </svg>
      </div>
    );
  };

  const getDeviceIcon = (device: string) => {
    switch (device) {
      case "mobile":
        return <Smartphone className="w-4 h-4 text-emerald-400" />;
      case "tablet":
        return <Laptop className="w-4 h-4 text-sky-400" />;
      default:
        return <Monitor className="w-4 h-4 text-indigo-400" />;
    }
  };

  const formatTime = (isoString: string) => {
    const d = new Date(isoString);
    return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 font-sans p-6 md:p-10">
      
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6 mb-8">
        <div>
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors">
              <ArrowLeft className="w-3.5 h-3.5" /> Quay lại
            </Link>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-300 bg-clip-text text-transparent mt-2">
            U-PASS Web Analytics
          </h1>
          <p className="text-slate-400 text-xs mt-1">Hệ thống phân tích truy cập thời gian thực</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 rounded-full px-3 py-1.5">
            <span className={`w-2 h-2 rounded-full ${isLive ? "bg-emerald-400 animate-pulse" : "bg-slate-600"}`}></span>
            <span className="text-[11px] font-medium text-slate-300">{isLive ? "Chế độ Live (5s)" : "Tắt cập nhật tự động"}</span>
            <input 
              type="checkbox" 
              checked={isLive} 
              onChange={() => setIsLive(!isLive)}
              className="ml-1 w-3 h-3 cursor-pointer accent-blue-500 rounded border-slate-800"
            />
          </div>

          <button 
            onClick={() => fetchAnalytics()}
            className="flex items-center gap-2 text-xs bg-blue-600 hover:bg-blue-500 font-semibold px-4 py-2 rounded-lg transition-all shadow-lg shadow-blue-950/20"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Tải lại
          </button>
        </div>
      </header>

      {error && (
        <div className="bg-red-950/40 border border-red-900/60 text-red-200 rounded-xl p-4 mb-6 text-sm">
          Lỗi: {error}
        </div>
      )}

      {/* Grid: 3 Main Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        
        {/* Total Page Views */}
        <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 relative overflow-hidden shadow-lg">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-600/5 blur-3xl rounded-full"></div>
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Tổng lượt xem trang</span>
            <Eye className="w-5 h-5 text-blue-400" />
          </div>
          {loading && !data ? (
            <div className="h-8 bg-slate-800/50 animate-pulse rounded-lg mt-3 w-1/2"></div>
          ) : (
            <h2 className="text-3xl font-black mt-3 font-mono text-blue-100">
              {data?.totalViews.toLocaleString("vi-VN") || 0}
            </h2>
          )}
          <p className="text-slate-500 text-[10px] mt-1">Thống kê trong vòng 30 ngày qua</p>
        </div>

        {/* Unique Visitors */}
        <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 relative overflow-hidden shadow-lg">
          <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-600/5 blur-3xl rounded-full"></div>
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Khách truy cập duy nhất</span>
            <Users className="w-5 h-5 text-indigo-400" />
          </div>
          {loading && !data ? (
            <div className="h-8 bg-slate-800/50 animate-pulse rounded-lg mt-3 w-1/2"></div>
          ) : (
            <h2 className="text-3xl font-black mt-3 font-mono text-indigo-100">
              {data?.uniqueVisitors.toLocaleString("vi-VN") || 0}
            </h2>
          )}
          <p className="text-slate-500 text-[10px] mt-1">Dựa trên mã phiên thiết bị độc lập</p>
        </div>

        {/* Active Users */}
        <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 relative overflow-hidden shadow-lg">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-600/5 blur-3xl rounded-full"></div>
          <div className="flex justify-between items-start">
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Đang hoạt động (Live)</span>
            <Activity className="w-5 h-5 text-emerald-400" />
          </div>
          {loading && !data ? (
            <div className="h-8 bg-slate-800/50 animate-pulse rounded-lg mt-3 w-1/2"></div>
          ) : (
            <h2 className="text-3xl font-black mt-3 font-mono text-emerald-100 flex items-center gap-2">
              {data?.activeUsers || 0}
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping absolute ml-2 mt-1.5"></span>
            </h2>
          )}
          <p className="text-slate-500 text-[10px] mt-1">Phiên hoạt động trong 5 phút qua</p>
        </div>

      </div>

      {/* Main Grid Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left 2 Columns: Chart and Top Pages */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Trend Chart Card */}
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-md">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-slate-300">Biểu đồ lượt xem trang (7 ngày qua)</h3>
              <Clock className="w-4 h-4 text-slate-500" />
            </div>
            {loading && !data ? (
              <div className="h-[200px] bg-slate-800/20 animate-pulse rounded-lg mt-4"></div>
            ) : (
              renderChart()
            )}
          </div>

          {/* Top Pages Table Card */}
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-md">
            <h3 className="text-sm font-bold text-slate-300 mb-4">Các trang được truy cập nhiều nhất</h3>
            {loading && !data ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-8 bg-slate-800/20 animate-pulse rounded-lg w-full"></div>
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800/80 text-slate-400 font-semibold uppercase">
                      <th className="pb-3 w-4">#</th>
                      <th className="pb-3 pl-2">Đường dẫn (Path)</th>
                      <th className="pb-3 text-right">Số lượt xem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40">
                    {data?.topPages.map((page, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                        <td className="py-3 text-slate-500 font-mono">{idx + 1}</td>
                        <td className="py-3 pl-2 font-semibold text-slate-300 font-mono truncate max-w-[200px]">
                          {page.path}
                        </td>
                        <td className="py-3 text-right font-bold font-mono text-blue-400">
                          {page.views.toLocaleString("vi-VN")}
                        </td>
                      </tr>
                    ))}
                    {(!data?.topPages || data.topPages.length === 0) && (
                      <tr>
                        <td colSpan={3} className="py-6 text-center text-slate-500">Chưa có dữ liệu trang.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>

        {/* Right 1 Column: Device Breakdown & Live Feed */}
        <div className="space-y-8">
          
          {/* Device Type Card */}
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-md">
            <h3 className="text-sm font-bold text-slate-300 mb-4">Phân bố thiết bị & Trình duyệt</h3>
            
            {loading && !data ? (
              <div className="h-[120px] bg-slate-800/20 animate-pulse rounded-lg"></div>
            ) : (
              <div className="space-y-5">
                {/* Devices */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold text-slate-500 mb-2">Loại thiết bị</h4>
                  <div className="flex gap-2 items-center">
                    {data?.devices.map((device, idx) => {
                      const total = data.devices.reduce((acc, curr) => acc + curr.count, 0) || 1;
                      const percentage = Math.round((device.count / total) * 100);
                      return (
                        <div key={idx} className="flex-1 bg-slate-950/80 border border-slate-800 rounded-xl p-3 flex flex-col items-center justify-center">
                          {getDeviceIcon(device.name)}
                          <span className="text-[10px] text-slate-400 capitalize mt-1.5">{device.name}</span>
                          <span className="text-sm font-bold mt-0.5">{percentage}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Top Browsers */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold text-slate-500 mb-2">Trình duyệt phổ biến</h4>
                  <div className="space-y-2">
                    {data?.browsers.slice(0, 3).map((browser, idx) => {
                      const total = data.browsers.reduce((acc, curr) => acc + curr.count, 0) || 1;
                      const widthPct = Math.round((browser.count / total) * 100);
                      return (
                        <div key={idx} className="text-[11px]">
                          <div className="flex justify-between text-slate-300 font-semibold mb-1">
                            <span>{browser.name}</span>
                            <span className="font-mono text-slate-400">{widthPct}%</span>
                          </div>
                          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-blue-500 rounded-full" 
                              style={{ width: `${widthPct}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Live Visitor Feed Card */}
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-bold text-slate-300">Nhật ký truy cập (Live Feed)</h3>
              <span className="text-[9px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full px-2 py-0.5 animate-pulse">Live</span>
            </div>
            
            {loading && !data ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 bg-slate-800/20 animate-pulse rounded-lg w-full"></div>
                ))}
              </div>
            ) : (
              <div className="space-y-3.5 max-h-[300px] overflow-y-auto pr-1">
                {data?.recentLogs.map((log, idx) => (
                  <div 
                    key={idx} 
                    className="bg-slate-950/60 hover:bg-slate-950 border border-slate-800/60 rounded-xl p-3 flex flex-col gap-1 transition-all"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] font-mono font-bold text-slate-200 truncate max-w-[150px]">
                        {log.path}
                      </span>
                      <span className="text-[9px] font-mono text-slate-500">{formatTime(log.created_at)}</span>
                    </div>

                    <div className="flex items-center justify-between mt-1 text-[10px] text-slate-500">
                      <div className="flex items-center gap-1.5">
                        {getDeviceIcon(log.device_type)}
                        <span className="capitalize">{log.device_type}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Compass className="w-3 h-3 text-slate-600" />
                        <span>{log.browser} ({log.os})</span>
                      </div>
                    </div>
                  </div>
                ))}
                {(!data?.recentLogs || data.recentLogs.length === 0) && (
                  <div className="text-center py-6 text-slate-500 text-xs">Chưa có lượt truy cập nào.</div>
                )}
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}

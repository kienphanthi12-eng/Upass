import { createClient } from '@supabase/supabase-js'

export function createAdminSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  
  // Nếu chưa cấu hình service role key thì fallback dùng anon key để tránh crash
  const key = (!serviceKey || serviceKey === 'your_service_role_key_here')
    ? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    : serviceKey
    
  return createClient(url, key, {
    auth: { persistSession: false },
  })
}

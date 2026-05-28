import { unzipSync } from 'fflate'

const MINERU_BASE = 'https://mineru.net/api/v4'

interface UploadInfo {
  batchId: string
  uploadUrl: string
}

export interface BatchPollResult {
  done: boolean
  state: string
  result?: MineruFileResult
  error?: string
}

interface MineruFileResult {
  state: string
  full_zip_url?: string
  zip_url?: string
  err_msg?: string
  total_pages?: number
  page_count?: number
  pages?: Array<{ markdown?: string }>
}

export async function mineruRequestUploadUrl(
  fileName: string
): Promise<UploadInfo> {
  const apiKey = process.env.MINERU_API_KEY
  if (!apiKey) throw new Error('MINERU_API_KEY not set')

  const resp = await fetch(`${MINERU_BASE}/file-urls/batch`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      files: [{ name: fileName, data_id: fileName }],
      enable_formula: true,
      enable_table: true,
      language: 'vi',
      is_ocr: true,
    }),
  })

  if (!resp.ok) throw new Error(`MinerU request_upload failed: ${resp.status}`)
  const data = await resp.json()
  if (data.code !== 0) throw new Error(`MinerU error: ${data.msg}`)

  return {
    batchId: data.data.batch_id,
    uploadUrl: data.data.file_urls[0],
  }
}

export async function mineruUploadFile(
  uploadUrl: string,
  fileBuffer: ArrayBuffer
): Promise<void> {
  const resp = await fetch(uploadUrl, {
    method: 'PUT',
    body: fileBuffer,
  })
  if (resp.status !== 200 && resp.status !== 204) {
    throw new Error(`OSS upload failed: ${resp.status}`)
  }
}

export async function mineruPollBatch(batchId: string): Promise<BatchPollResult> {
  const apiKey = process.env.MINERU_API_KEY
  if (!apiKey) throw new Error('MINERU_API_KEY not set')

  const resp = await fetch(
    `${MINERU_BASE}/extract-results/batch/${batchId}`,
    { headers: { Authorization: `Bearer ${apiKey}` } }
  )

  if (!resp.ok) throw new Error(`MinerU poll failed: ${resp.status}`)
  const data = await resp.json()
  if (data.code !== 0) throw new Error(`MinerU poll error: ${data.msg}`)

  const batchData = data.data
  const filesList: MineruFileResult[] =
    batchData.extract_result ||
    batchData.list ||
    (Array.isArray(batchData) ? batchData : [batchData])

  if (!filesList || filesList.length === 0) {
    return { done: false, state: 'waiting' }
  }

  const fileResult = filesList[0]
  const state = fileResult.state || 'unknown'

  if (state === 'done') return { done: true, state, result: fileResult }
  if (state === 'failed') return { done: true, state, error: fileResult.err_msg || 'unknown' }
  return { done: false, state }
}

export interface MineruDownloadResult {
  markdown: string
  /** Map từ tên file ảnh (vd: "abc123.jpg") → bytes */
  images: Map<string, Uint8Array>
}

export async function mineruDownloadMarkdown(result: MineruFileResult): Promise<MineruDownloadResult> {
  // Fallback: pages array (không có ZIP, không có ảnh)
  if (!result.full_zip_url && !result.zip_url) {
    const pages = result.pages || []
    if (pages.length > 0) {
      return {
        markdown: pages.map(p => p.markdown || '').filter(Boolean).join('\n\n'),
        images: new Map(),
      }
    }
    throw new Error('Không tìm thấy zip URL hoặc pages trong MinerU result')
  }

  const zipUrl = result.full_zip_url || result.zip_url!

  // Download ZIP
  const zipResp = await fetch(zipUrl)
  if (!zipResp.ok) throw new Error(`Download ZIP failed: ${zipResp.status}`)

  const zipBuffer = await zipResp.arrayBuffer()
  const uint8 = new Uint8Array(zipBuffer)

  // Extract với fflate
  const files = unzipSync(uint8)

  // Tìm file .md lớn nhất
  const mdEntries = Object.entries(files).filter(([name]) => name.endsWith('.md'))
  if (mdEntries.length === 0) throw new Error('Không có file .md trong ZIP')

  const [, mdContent] = mdEntries.reduce((max, cur) =>
    cur[1].length > max[1].length ? cur : max
  )
  const markdown = new TextDecoder('utf-8').decode(mdContent)

  // Extract tất cả ảnh từ ZIP
  const imageExts = /\.(jpg|jpeg|png|gif|webp|svg)$/i
  const images = new Map<string, Uint8Array>()
  for (const [name, data] of Object.entries(files)) {
    if (imageExts.test(name)) {
      // Chỉ lấy tên file, bỏ đường dẫn thư mục
      const basename = name.split('/').pop()!
      images.set(basename, data)
    }
  }

  return { markdown, images }
}

"""
config.py — Cấu hình toàn bộ hệ thống THPT Exam Tool
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
PDF_DIR       = Path(os.getenv("PDF_DIR", BASE_DIR / "data" / "pdfs"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", BASE_DIR / "data" / "processed"))
LOG_DIR       = Path(os.getenv("LOG_DIR", BASE_DIR / "data" / "logs"))

for d in [PDF_DIR, PROCESSED_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER','postgres')}:"
    f"{os.getenv('DB_PASSWORD','password')}@"
    f"{os.getenv('DB_HOST','localhost')}:"
    f"{os.getenv('DB_PORT','5432')}/"
    f"{os.getenv('DB_NAME','thpt_exams')}"
)

# ─── DeepSeek ─────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL    = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Model LLM riêng cho pipeline Azota (rẻ nhất). Dùng chung API key/endpoint ở trên.
# deepseek-chat không có trên endpoint Alibaba → mặc định qwen-turbo (rẻ nhất khả dụng).
AZOTA_LLM_MODEL   = os.getenv("AZOTA_LLM_MODEL", "qwen-turbo")

# ─── Scraping ─────────────────────────────────────────────────────────────────
SCRAPE_FROM_YEAR     = int(os.getenv("SCRAPE_FROM_YEAR", 2021))
DOWNLOAD_CONCURRENT  = int(os.getenv("DOWNLOAD_CONCURRENT", 3))
REQUEST_DELAY        = float(os.getenv("REQUEST_DELAY", 1.5))
MAX_RETRIES          = int(os.getenv("MAX_RETRIES", 3))

# ─── MinerU Cloud API ─────────────────────────────────────────────────────────
# Lấy token tại: https://mineru.net/apiManage/list
MINERU_API_KEY = os.getenv("MINERU_API_KEY", "")

# ─── Subjects ─────────────────────────────────────────────────────────────────
SUBJECTS = {
    "toan":        {"name": "Toán",       "code": "TOAN"},
    "vat_ly":      {"name": "Vật Lý",     "code": "LY"},
    "hoa_hoc":     {"name": "Hóa Học",    "code": "HOA"},
    "sinh_hoc":    {"name": "Sinh Học",   "code": "SINH"},
    "ngu_van":     {"name": "Ngữ Văn",    "code": "VAN"},
    "lich_su":     {"name": "Lịch Sử",    "code": "SU"},
    "dia_ly":      {"name": "Địa Lý",     "code": "DIA"},
    "gdcd":        {"name": "GDCD",       "code": "GDCD"},
    "tieng_anh":   {"name": "Tiếng Anh",  "code": "ANH"},
    "tin_hoc":     {"name": "Tin Học",    "code": "TIN"},
    "cong_nghe":   {"name": "Công Nghệ",  "code": "CN"},
}

# ─── Topics by subject ────────────────────────────────────────────────────────
TOPICS = {
    "toan": [
        "Giải tích - Hàm số",
        "Giải tích - Đạo hàm",
        "Giải tích - Tích phân",
        "Giải tích - Lũy thừa & Logarit",
        "Hình học - Hình học phẳng",
        "Hình học - Hình học không gian",
        "Hình học - Tọa độ phẳng Oxy",
        "Hình học - Tọa độ không gian Oxyz",
        "Đại số - Tổ hợp & Xác suất",
        "Đại số - Số phức",
        "Đại số - Dãy số & Cấp số",
        "Đại số - Phương trình & Bất phương trình",
    ],
    "vat_ly": [
        "Cơ học - Động học",
        "Cơ học - Động lực học",
        "Cơ học - Công & Năng lượng",
        "Cơ học - Dao động cơ",
        "Sóng cơ",
        "Điện xoay chiều",
        "Điện từ - Dao động & Sóng điện từ",
        "Quang học - Sóng ánh sáng",
        "Quang học - Lượng tử ánh sáng",
        "Vật lý hạt nhân",
        "Nhiệt học",
    ],
    "hoa_hoc": [
        "Hóa đại cương - Nguyên tử & Bảng tuần hoàn",
        "Hóa đại cương - Liên kết hóa học",
        "Hóa đại cương - Phản ứng hóa học",
        "Hóa vô cơ - Kim loại",
        "Hóa vô cơ - Phi kim",
        "Hóa vô cơ - Điện phân & Ăn mòn",
        "Hóa hữu cơ - Hydrocarbon",
        "Hóa hữu cơ - Dẫn xuất Halogen",
        "Hóa hữu cơ - Ancol & Phenol",
        "Hóa hữu cơ - Aldehyde & Ketone & Acid Carboxylic",
        "Hóa hữu cơ - Amine & Amino acid & Protein",
        "Hóa hữu cơ - Polymer",
        "Hóa hữu cơ - Carbohydrate",
    ],
    "sinh_hoc": [
        "Di truyền học - Cơ sở phân tử",
        "Di truyền học - Quy luật Mendel",
        "Di truyền học - Di truyền liên kết",
        "Di truyền học - Di truyền quần thể",
        "Di truyền học - Ứng dụng",
        "Tiến hóa",
        "Sinh thái học",
        "Sinh lý học thực vật",
        "Sinh lý học động vật",
    ],
    "tieng_anh": [
        "Ngữ pháp - Thì động từ",
        "Ngữ pháp - Câu điều kiện",
        "Ngữ pháp - Câu bị động",
        "Ngữ pháp - Mệnh đề quan hệ",
        "Từ vựng & Collocation",
        "Đọc hiểu",
        "Điền từ vào đoạn văn",
        "Viết câu",
        "Phát âm & Trọng âm",
    ],
    "ngu_van": [
        "Đọc hiểu văn bản",
        "Nghị luận xã hội",
        "Nghị luận văn học",
        "Thơ",
        "Truyện ngắn",
    ],
    "lich_su": [
        "Lịch sử Việt Nam hiện đại",
        "Lịch sử thế giới hiện đại",
        "Chiến tranh thế giới",
        "Cách mạng Việt Nam",
    ],
    "dia_ly": [
        "Địa lý tự nhiên Việt Nam",
        "Địa lý kinh tế - xã hội Việt Nam",
        "Địa lý thế giới",
        "Bản đồ & Số liệu",
    ],
    "gdcd": [
        "Pháp luật đại cương",
        "Kinh tế thị trường",
        "Đường lối cách mạng",
        "Đạo đức & Xã hội",
    ],
}

# ─── Difficulty levels ────────────────────────────────────────────────────────
DIFFICULTY_LEVELS = [
    "Nhận biết",
    "Thông hiểu",
    "Vận dụng",
    "Vận dụng cao",
]

# ─── Scraper target sites ─────────────────────────────────────────────────────
SCRAPER_SOURCES = [
    {
        "name": "ToanMath",
        "base_url": "https://toanmath.com",
        "search_path": "/de-thi-thu-thpt-mon-toan",
        "enabled": True,
    },
    {
        "name": "Tailieu.vn",
        "base_url": "https://tailieu.vn",
        "search_path": "/tim-kiem/?q={query}",
        "enabled": True,
    },
    {
        "name": "Dethi.edu.vn",
        "base_url": "https://dethi.edu.vn",
        "search_path": "/search?q={query}",
        "enabled": True,
    },
    {
        "name": "Hocmai",
        "base_url": "https://hocmai.vn",
        "search_path": "/search?q={query}",
        "enabled": True,
    },
    {
        "name": "Moet.gov.vn",
        "base_url": "https://moet.gov.vn",
        "search_path": "/search?q={query}",
        "enabled": True,
    },
]

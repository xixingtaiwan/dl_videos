# Windows Setup Guide - Video Import & Database Tool

Hướng dẫn chi tiết để cài đặt và chạy công cụ Video Import trên Windows.

---

## 📋 Yêu Cầu Hệ Thống

- **Windows 10** trở lên (64-bit)
- **RAM**: 4GB tối thiểu (8GB khuyến khích)
- **Ổ cứng**: 20GB để lưu trữ video
- **Internet**: Kết nối ổn định để tải video

---

## 🔧 Cài Đặt

### 1. Cài Đặt Python

#### Tùy chọn A: Python.org (Khuyến khích)
1. Truy cập: https://www.python.org/downloads/
2. Tải **Python 3.11** hoặc **3.12** (Windows installer)
3. Chạy installer:
   - ✅ Tick **"Add Python to PATH"** (QUAN TRỌNG!)
   - ✅ Tick **"Install pip"**
   - Chọn "Install Now"
4. Xác nhận cài đặt:
   ```cmd
   python --version
   pip --version
   ```

#### Tùy chọn B: Windows Package Manager
```cmd
winget install Python.Python.3.12
```

#### Tùy chọn C: Anaconda
1. Tải từ: https://www.anaconda.com/download/
2. Chạy installer và chọn "Add Anaconda to PATH"

---

### 2. Cài Đặt PostgreSQL (Khuyến khích) HOẶC SQLite (Mặc định)

#### **Cách A: PostgreSQL (Khuyến khích cho Production)**

1. **Tải PostgreSQL**
   - Truy cập: https://www.postgresql.org/download/windows/
   - Tải phiên bản **PostgreSQL 15** hoặc **16**

2. **Cài đặt PostgreSQL**
   - Chạy installer
   - Ghi nhớ **password** cho user `postgres`
   - Đảm bảo port **5432** được sử dụng
   - Tích chọn **pgAdmin 4** (quản lý DB UI)

3. **Xác nhận cài đặt**
   ```cmd
   psql --version
   ```

4. **Tạo Database & User**
   - Mở PowerShell hoặc Command Prompt
   - Kết nối PostgreSQL:
     ```cmd
     psql -U postgres
     ```
   - Nhập password khi được hỏi
   - Chạy các lệnh SQL:
     ```sql
     CREATE DATABASE films_db;
     CREATE USER video_user WITH PASSWORD 'your_secure_password';
     GRANT ALL PRIVILEGES ON DATABASE films_db TO video_user;
     \c films_db
     GRANT ALL ON SCHEMA public TO video_user;
     \q
     ```

5. **Cài đặt Python Driver cho PostgreSQL**
   ```cmd
   pip install psycopg2-binary
   ```

#### **Cách B: SQLite (Mặc định - Không cần cài đặt)**
SQLite đã tích hợp trong Python, không cần cài đặt riêng.

---

### 3. Clone Dự Án hoặc Tải Source Code

#### Tùy chọn A: Git (Khuyến khích)
```cmd
# Cài Git nếu chưa có
winget install Git.Git

# Clone repository
git clone <your-repo-url> C:\Projects\Download-Videos
cd C:\Projects\Download-Videos
```

#### Tùy chọn B: Tải ZIP
1. Tải file ZIP từ GitHub/GitLab
2. Giải nén vào: `C:\Projects\Download-Videos`
3. Mở Command Prompt tại thư mục này

---

### 4. Cài Đặt Python Dependencies

```cmd
# Điều hướng tới thư mục dự án
cd C:\Projects\Download-Videos

# Cài đặt các package cần thiết
pip install -r requirements.txt
```

**Nếu không có file `requirements.txt`, cài đặt thủ công:**
```cmd
pip install psycopg2-binary requests python-dotenv
```

---

### 5. Cấu Hình Dự Án

#### **Bước 1: Chỉnh Sửa `config.py`**

Mở file `config.py` bằng text editor (Notepad++, VS Code, v.v.)

```python
#!/usr/bin/env python3
"""
Configuration file for Video Import Tool - WINDOWS VERSION
Update these settings to match your setup
"""

from pathlib import Path

# Base Directory (Thay đổi đường dẫn theo máy của bạn)
BASE_DIR = Path('C:/Projects/Download-Videos')  # THAY ĐỔI ĐÂY
JSON_DIR = BASE_DIR / 'idrama'
DOWNLOAD_DIR = BASE_DIR / 'videos'

# ====================
# DATABASE CONFIGURATION
# ====================

# Option 1: SQLite (Mặc định - không cần cài đặt riêng)
USE_SQLITE = True
SQLITE_DB_PATH = BASE_DIR / 'films.db'

# Option 2: PostgreSQL (Nếu bạn đã cài PostgreSQL)
USE_SQLITE = False  # Đặt thành False để dùng PostgreSQL
DATABASE_CONFIG = {
    'host': 'localhost',           # PostgreSQL host
    'port': 5432,                  # PostgreSQL port (mặc định)
    'user': 'video_user',          # User đã tạo
    'password': 'your_secure_password',  # Password đã đặt
    'database': 'films_db',        # Database name
}

# ====================
# SCANNING CONFIGURATION
# ====================
SCAN_INTERVAL = 600  # Quét mỗi 10 phút (600 giây)
# Thay đổi thành: 300 (5 phút), 1800 (30 phút), vv.

# ====================
# LOGGING
# ====================
LOG_FILE = BASE_DIR / 'import_tool.log'

# ====================
# RETRY CONFIGURATION
# ====================
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 4]  # Chờ 2-4 giây giữa các lần thử lại

print("⚠️  CONFIGURATION CHECK:")
print(f"   Base Directory: {BASE_DIR}")
print(f"   JSON Directory: {JSON_DIR}")
print(f"   Download Directory: {DOWNLOAD_DIR}")
print(f"   Database: {'SQLite' if USE_SQLITE else 'PostgreSQL'}")
print(f"   ✓ Configuration loaded successfully!")
```

#### **Bước 2: Tạo Thư Mục Cần Thiết**

```cmd
# Trong Command Prompt, từ thư mục dự án:
mkdir idrama
mkdir videos
mkdir backups
mkdir exports
```

Hoặc tạo thủ công qua File Explorer.

---

## ▶️ Chạy Dự Án

### **1. Kiểm Tra Setup**

Trước tiên, chạy kiểm tra để đảm bảo mọi thứ được cấu hình đúng:

```cmd
python test_import.py
```

**Kết quả mong muốn:**
```
Testing JSON structure: ✓
Testing database schema: ✓
Testing file paths: ✓
3/3 tests passed ✓
```

---

### **2. Bắt Đầu Import Video**

```cmd
# Chạy công cụ import chính
python import_tool.py
```

**Hoặc chạy trong nền (background):**

#### Windows PowerShell:
```powershell
# Mở một PowerShell tab mới
Start-Process powershell -ArgumentList "-NoExit -Command python import_tool.py"
```

#### Command Prompt:
```cmd
# Chạy trong background
start python import_tool.py
```

#### Task Scheduler (Chạy tự động):
1. Mở **Task Scheduler** (tìm trong Start Menu)
2. Chọn **Create Basic Task**
3. Đặt tên: "Video Import"
4. Trigger: "Daily" hoặc "On startup"
5. Action: 
   - Program: `C:\Python\python.exe` (hoặc đường dẫn Python của bạn)
   - Arguments: `C:\Projects\Download-Videos\import_tool.py`
   - Start in: `C:\Projects\Download-Videos`

---

### **3. Theo Dõi Tiến Trình**

#### Xem Log File:
```cmd
# Mở file log (tự động cập nhật)
type import_tool.log

# Hoặc dùng PowerShell để xem real-time:
Get-Content import_tool.log -Wait
```

#### Kiểm Tra Trạng Thái Database:
```cmd
# Xem thống kê
python query_films.py stats

# Liệt kê tất cả films
python query_films.py list

# Chi tiết film cụ thể
python query_films.py details <film_id>
```

---

## 🛠️ Công Cụ Quản Lý

### **1. Query Films (Truy Vấn Database)**
```cmd
python query_films.py list          # Liệt kê tất cả films
python query_films.py stats         # Xem thống kê
python query_films.py episodes <id> # Episodes của film
python query_films.py details <id>  # Chi tiết film
```

### **2. Backup Database**
```cmd
python backup_db.py backup          # Tạo backup
python backup_db.py list            # Liệt kê backups
python backup_db.py cleanup 10      # Xóa backup cũ (giữ 10 gần nhất)
python backup_db.py stats           # Thống kê DB
```

### **3. Export Data**
```cmd
python export_db.py all json        # Export tất cả (JSON)
python export_db.py films csv       # Export films (CSV)
python export_db.py dump            # Export SQL dump
python export_db.py film <id> json  # Export film cụ thể
```

### **4. Restore Database**
```cmd
python restore_db.py list                    # Liệt kê backups
python restore_db.py restore <backup_file>   # Phục hồi từ backup
python restore_db.py restore-sql <sql_file>  # Phục hồi từ SQL dump
```

---

## 📁 Cấu Trúc Thư Mục Windows

```
C:\Projects\Download-Videos\
│
├── 🎯 CÔNG CỤ (Python Scripts)
│   ├── import_tool.py          → Công cụ chính (SQLite)
│   ├── import_tool_postgres.py → Công cụ (PostgreSQL)
│   ├── test_import.py          → Kiểm tra setup
│   ├── query_films.py          → Truy vấn database
│   ├── backup_db.py            → Quản lý backup
│   ├── export_db.py            → Xuất dữ liệu
│   └── restore_db.py           → Phục hồi database
│
├── 💾 DỮ LIỆU
│   ├── films.db                → SQLite database (tự tạo)
│   ├── idrama/                 → JSON input files
│   │   └── idrama_XXXXXXX.json
│   ├── videos/                 → Thư mục video tải về
│   │   └── idrama/
│   │       └── 100000643080/
│   │           ├── cover/
│   │           └── ep/
│   ├── backups/                → Backup database
│   └── exports/                → Dữ liệu xuất
│
├── 📝 CẤU HÌNH
│   ├── config.py               → Cấu hình chính
│   ├── window_setup.md         → Hướng dẫn này
│   └── README.md               → Tài liệu đầy đủ
│
└── 📊 LOG
    └── import_tool.log         → Log file (tự tạo)
```

---

## 🐛 Khắc Phục Sự Cố

### **Lỗi: "Python không được tìm thấy"**
```
Error: 'python' is not recognized
```
**Giải pháp:**
1. Kiểm tra Python đã thêm vào PATH
2. Thử: `python --version`
3. Nếu không work, dùng: `py --version`
4. Nếu vẫn không work, cài lại Python với tích "Add Python to PATH"

---

### **Lỗi: "No module named 'psycopg2'"**
```
ModuleNotFoundError: No module named 'psycopg2'
```
**Giải pháp (chỉ cần nếu dùng PostgreSQL):**
```cmd
pip install psycopg2-binary
```

---

### **Lỗi: "Database connection refused"**
```
Error: Could not connect to PostgreSQL server
```
**Giải pháp:**
1. Kiểm tra PostgreSQL đang chạy:
   - Mở **Services** (services.msc)
   - Tìm "postgresql-x64-XX"
   - Đảm bảo status là "Running"
2. Kiểm tra config.py có đúng:
   - Host: `localhost`
   - Port: `5432` (mặc định)
   - User/Password: Đúng không

---

### **Lỗi: "Permission denied" khi tạo thư mục**
**Giải pháp:**
1. Chạy Command Prompt **as Administrator**
2. Hoặc thay đổi quyền folder:
   - Chuột phải folder → Properties
   - Security tab → Edit → User → Full Control

---

### **Lỗi: "Database is locked"**
**Giải pháp:**
1. Tắt tất cả Python processes:
   ```cmd
   taskkill /IM python.exe /F
   ```
2. Xóa file lock (nếu có):
   - `films.db-wal`
   - `films.db-shm`
3. Chạy lại

---

### **Lỗi: "Out of memory" khi tải video**
**Giải pháp:**
1. Giảm số lượng video tải cùng lúc (edit `import_tool.py`)
2. Tăng thời gian giữa scans (edit `SCAN_INTERVAL` trong config)
3. Kiểm tra ổ cứng còn dung lượng (cần 20GB+)

---

### **Lỗi: Video tải không thành công**
**Giải pháp:**
1. Kiểm tra kết nối internet
2. Kiểm tra URLs trong JSON file hợp lệ
3. Xem log: `type import_tool.log`
4. Kiểm tra timeout (tăng MAX_RETRIES trong config)

---

## 🔒 Bảo Mật

### **Bảo Vệ PostgreSQL Password**
Nếu dùng PostgreSQL, không nên lưu password ở `config.py`:

1. **Tạo file `.env`:**
   ```
   DB_PASSWORD=your_secure_password
   DB_USER=video_user
   ```

2. **Cập nhật `config.py`:**
   ```python
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   DATABASE_CONFIG = {
       'host': 'localhost',
       'port': 5432,
       'user': os.getenv('DB_USER'),
       'password': os.getenv('DB_PASSWORD'),
       'database': 'films_db',
   }
   ```

3. **Cài `python-dotenv`:**
   ```cmd
   pip install python-dotenv
   ```

4. **Thêm vào `.gitignore`:**
   ```
   .env
   ```

---

## 📊 Performance Tips

### **Tăng tốc độ import:**
1. Tăng `SCAN_INTERVAL` nếu tải quá nhiều video:
   ```python
   SCAN_INTERVAL = 300  # Quét 5 phút một lần
   ```

2. Dùng PostgreSQL thay SQLite (PostgreSQL nhanh hơn):
   - Tham khảo POSTGRES_SETUP.md

3. Dùng SSD thay HDD (tốc độ ghi nhanh hơn)

---

## 🚀 Chạy Tự Động

### **Lựa chọn 1: Task Scheduler (Khuyến khích)**
Đã hướng dẫn ở trên.

### **Lựa chọn 2: Batch File**
Tạo file `run_import.bat`:
```batch
@echo off
cd /d C:\Projects\Download-Videos
python import_tool.py
pause
```

Chạy bằng cách double-click hoặc thêm vào startup.

### **Lựa chọn 3: PowerShell Script**
Tạo file `run_import.ps1`:
```powershell
Set-Location "C:\Projects\Download-Videos"
python import_tool.py
```

Chạy:
```powershell
powershell -ExecutionPolicy Bypass -File run_import.ps1
```

---

## 📞 Hỗ Trợ

| Vấn Đề | Giải Pháp |
|--------|----------|
| Python không chạy | Cài lại + Add to PATH |
| PostgreSQL kết nối thất bại | Kiểm tra config.py, khởi động dịch vụ |
| Video tải chậm | Kiểm tra internet, tăng timeout |
| Database bị khóa | Tắt python.exe, xóa file .db-wal |
| Hết dung lượng ổ | Kiểm tra `videos/` folder, di chuyển vào ổ khác |
| JSON file không hợp lệ | Chạy `test_import.py` để kiểm tra |

---

## ✅ Checklist Cài Đặt

- [ ] Python 3.11+ cài đặt
- [ ] Python thêm vào PATH
- [ ] PostgreSQL cài đặt (nếu chọn)
- [ ] Database & user tạo (nếu dùng PostgreSQL)
- [ ] Dự án clone/tải xuống
- [ ] Dependencies cài đặt (`pip install -r requirements.txt`)
- [ ] config.py cập nhật đường dẫn
- [ ] Thư mục `idrama`, `videos`, `backups` tạo
- [ ] `test_import.py` chạy thành công
- [ ] Thêm JSON file vào thư mục `idrama/`
- [ ] `import_tool.py` chạy

---

## 📚 Tài Liệu Thêm

- `README.md` - Hướng dẫn chi tiết đầy đủ
- `POSTGRES_SETUP.md` - Setup PostgreSQL chi tiết
- `DIRECTORY_STRUCTURE.md` - Cấu trúc thư mục
- `CHANGES_SUMMARY.md` - Lịch sử thay đổi
- `MULTI_FORMAT_SUPPORT.md` - Hỗ trợ định dạng video

---

## 🎉 Bắt Đầu

1. ✅ Cài đặt Python + PostgreSQL (tùy chọn)
2. ✅ Clone dự án
3. ✅ Chỉnh sửa `config.py`
4. ✅ Chạy `python test_import.py`
5. ✅ Thêm JSON file vào `idrama/`
6. ✅ Chạy `python import_tool.py`
7. ✅ Theo dõi `import_tool.log`

**Mọi thứ đã sẵn sàng! 🚀**

---

*Hướng dẫn này được cập nhật cho Windows 10/11 - Python 3.11+*

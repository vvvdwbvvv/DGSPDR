
# 使用指南
---

## 目錄
- [功能簡介](#功能簡介)
- [安裝指南](#安裝指南)
- [配置說明](#配置說明)
- [使用方法](#使用方法)
- [功能詳解](#功能詳解)
- [貢獻](#貢獻)
- [授權](#授權)

---

## 功能簡介

**CourseMaster** 提供以下功能模組：

- **課程資料抓取 (`course`)**：抓取課程名稱、代碼和相關資訊。
- **教師資料抓取 (`teacher`)**：抓取教師姓名、評分和統計數據。
- **課程評分抓取 (`rate`)**：抓取課程評分數據。
- **結果資料抓取 (`result`)**：抓取學期成績和其他結果。
- **全功能執行 (`all`)**：執行以上所有功能。

---

## 安裝指南

1. **複製範例配置文件**：
   複製範例配置文件 `config.toml.example` 和 `.env.example`，並填寫必要的配置信息。
   ```bash
   cp config.toml.example config.toml
   cp .env.example .env
   ```

2. **安裝依賴**：
   使用以下命令安裝 Python 所需依賴：
   ```bash
   pip install -r requirements.txt
   ```

3. **啟動測試**：
   確保所有配置和依賴正確，運行以下命令以驗證安裝：
   ```bash
   python main.py --help
   ```

---

## 配置說明

### `config.toml`

`config.toml` 用於存儲應用程序的靜態配置。以下為主要字段說明：
```toml
[general]
year = "2023"
sem = "1"
db = "database.db"  # 資料庫文件路徑

[urls]
server_url = "http://es.nccu.edu.tw/"
sem_api = "semester/"
person_api = "person/"
course_api = "course/"
trace_api = "tracing/"
teacher_schm_base_url = "http://newdoc.nccu.edu.tw/teaschm/"

[course_results]
years = ["1102", "1111", "1112", "1121"]
```

### `.env`

`.env` 文件存儲敏感數據，如用戶名和密碼：
```
USERNAME=your_username
PASSWORD=your_password
YEAR=112
SEM=1
KEY=your_secret_key
```

---

## 使用方法

執行以下命令來運行 `CourseMaster`：

### 基本命令
- **抓取課程資料**：
  ```bash
  python main.py course --db database.db --semester 1121
  ```

- **抓取教師資料**：
  ```bash
  python main.py teacher --db database.db --semester 1121
  ```

- **抓取課程評分**：
  ```bash
  python main.py rate --db database.db --semester 1121
  ```

- **抓取結果資料**：
  ```bash
  python main.py result --db database.db --semester 1121
  ```

- **執行全部功能**：
  ```bash
  python main.py all --db database.db --semester 1121
  ```

### 可選參數
| 參數          | 說明                         | 預設值           |
|---------------|------------------------------|------------------|
| `--db`        | 指定資料庫檔案路徑           | `database.db`    |
| `--semester`  | 指定學期（如 `1121`）        | `YEAR + SEM`     |
| `--delay`     | 每次請求的延遲時間（秒）     | `1.0`            |

---

## 功能詳解

1. **課程資料抓取 (`course`)**：
   - 從學校 API 中提取課程名稱、課程代碼和學分資訊，存儲於數據庫。

2. **教師資料抓取 (`teacher`)**：
   - 提取課程中對應教師的統計數據，包括評分和評價。

3. **課程評分抓取 (`rate`)**：
   - 根據課程 ID 獲取學生對課程的評分數據。

4. **結果資料抓取 (`result`)**：
   - 提取學期成績分布與結果，存儲為 CSV 文件。

5. **全功能執行 (`all`)**：
   - 順序執行上述所有功能模組。

---

## 修改

歡迎任何形式的貢獻！請遵循以下步驟：
1. Fork 本倉庫。
2. 創建您的功能分支：
   ```bash
   git checkout -b feature/YourFeature
   ```
3. 提交您的更改：
   ```bash
   git commit -m "Add YourFeature"
   ```
4. 發起 Pull Request。

---

## 授權




# DGSPDR

![Python](https://img.shields.io/badge/python-311+-blue.svg)
![Scrapy](https://img.shields.io/badge/scrapy-2.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

New scrapy in NCCU, support hierarchical search and smart complete

## Skeleton

```
DGSPDR/
├── NCCUCrawl/                    
│   ├── NCCUCrawl/
│   │   ├── spiders/
│   │   │   ├── courses_deprecated.py      
│   │   │   ├── courses_deprecated_patch.py 
│   │   │   └── teacher_deprecated.py      
│   │   ├── items.py              
│   │   ├── pipelines.py          
│   │   └── settings.py           
│   ├── test/                     
│   └── data.db                   
├── requirements.txt              
├── Makefile                     
└── README.md                    
```

## Installation

### 1. Setup

```bash
git clone <repository-url>
cd DGSPDR

pip install -r requirements.txt
pip install scrapy pytest
```

### 2. Usage

#### fetch all class
```bash
make courses
```
```bash
make courses_legacy
```

#### complete workflow
```bash
make courses_complete_it
```

#### with upsert preparation
```bash
make courses_export_upsert
```

### Prefect daily schedule

This repo includes a Prefect flow that runs a Makefile scraper target on a daily schedule.
The default target is `courses_complete_it`, which can be overridden at deployment time.
For on-premise deployments, use a local Prefect server and a process work pool.

```bash
pip install -r requirements.txt
pip install prefect

python prefect_flows/daily_scrape.py
```

To customize the schedule or target:

```bash
python - <<'PY'
from prefect_flows.daily_scrape import build_daily_deployment

deployment = build_daily_deployment(
    cron="0 3 * * *",  # 03:00 UTC daily
    timezone="UTC",
    target="courses_complete_it",
)
deployment.apply()
PY
```

#### On-premise deployment (local Prefect server)

```bash
prefect server start
```

In a new terminal:

```bash
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
prefect work-pool create --type process on-prem-pool
prefect worker start --pool on-prem-pool
```

Apply the deployment to the on-prem pool:

```bash
python - <<'PY'
from prefect_flows.daily_scrape import build_daily_deployment

deployment = build_daily_deployment(
    cron="0 2 * * *",
    timezone="UTC",
    target="courses_complete_it",
    work_pool_name="on-prem-pool",
)
deployment.apply()
PY
```

To validate the flow without running the scraper, pass `dry_run=True`.


### Hierarchical search

```python
# priority
1. 3 (dp1-dp2-dp3)   priority=100
2. 2 (dp1-dp2-∅)     priority=90
3. 1 (dp1-∅-∅)       priority=80
4. 0 (∅-∅-∅)         priority=70
```


```log
[three_level] 02-A4-P65: Total=41, Missing=1, New=1, Scheduled=0
[three_level] 01-A1-138: Total=44, Missing=6, New=6, Scheduled=0
[two_level] 02-A4-∅: Total=449, Missing=8, New=0, Scheduled=8  # 全部已在三階層找到！
[one_level] 02-∅-∅: Total=489, Missing=8, New=0, Scheduled=8   # 完美去重
```

## Stat

```log
=== Smart Hierarchical Search Statistics ===
Database existing courses: 2820
Found missing courses: 50
Successfully processed: 50
Success rate: 100.0%
Deduplication efficiency: 98.3%
API requests: 377/500 (節省 123 個請求)
```


### DB comparison

`SmartCoursesSpider` Automatically：
1. compare DB
2. recognize mssing in csv
3. hierarchichal search
4. fetch-remain

## Test

```bash
cd NCCUCrawl
python -m pytest -v

python -m pytest NCCUCrawl/test/spiders/test_courses_deprecated.py -v
```

### Data model (CourseLegacyItem)
```python
{
    "id": "1141123456789",           # 學期+課程編號
    "y": "114", "s": "1",            # 學年、學期
    "subNum": "123456789",           # 課程編號
    "name": "課程名稱",               # 中文課程名
    "nameEn": "Course Name",         # 英文課程名
    "teacher": "教師姓名",           # 中文教師名
    "teacherEn": "Teacher Name",     # 英文教師名
    "dp1": "02", "dp2": "A4", "dp3": "P15",  # 三層分類
    "point": 3.0,                    # 學分數
    "classroom": "商學院101",        # 教室
    "time": "一34",                  # 上課時間
    "kind": 1,                       # 課程類別 (1:必修 2:選修 3:群修 4:通識)
    "core": 1,                       # 核心能力 (1:是 0:否)
    "lang": "中文",                  # 授課語言
    "syllabus": "課程大綱內容...",   # 課程大綱
    "objective": "教學目標..."       # 教學目標
}
```

## Auto linting / formatting
```bash
make checkstyle
```

.PHONY: checkstyle course courses_legacy courses_complete_it courses_export_upsert teacher test_teacher test_all
# run the below script to format
# sed -i '' 's/^    /\t/g' makefile

checkstyle:
	python3 -m ruff check . --exclude test; ruff_check_status=$$?; \
	python3 -m ruff format --check . --exclude test; ruff_format_status=$$?; \
	python3 -m ruff check . --fix --exclude test; \
	python3 -m ruff format . --exclude test; \
	if [ $$ruff_check_status -ne 0 ] || [ $$ruff_format_status -ne 0 ]; then \
	    exit 1; \
	fi
courses:
	cd NCCUCrawl && \
	python3 -m scrapy crawl courses

courses_legacy:
	cd NCCUCrawl && \
	python3 -m scrapy crawl courses_deprecated

courses_complete_it:
	cd NCCUCrawl && \
	python3 -m scrapy crawl smart_courses -L INFO 

courses_export_upsert:
	cd NCCUCrawl && \
	python3 -m scrapy crawl courses_deprecated -L INFO && \
	python3 -m scrapy crawl smart_courses -L INFO && \
	sqlite3 data.db ".dump COURSE" > output.sql && \
	python3 quickfix.py

teacher:
	cd NCCUCrawl && \
	python3 -m scrapy crawl teacher_legacy -L INFO

rate_lagacy:
	cd NCCUCrawl && \
	python3 -m scrapy crawl rate_legacy -L INFO

test_all:
	cd NCCUCrawl && \
	python3 -m pytest -v -rP

test_teacher:
	cd NCCUCrawl/NCCUCrawl && \
	python3 -m pytest test/spiders/test_teacher_deprecated.py -v -rP

test_login:
	cd NCCUCrawl && \
	python3 -c "from NCCUCrawl.auth_curl import Authenticate; auth = Authenticate(); print(auth.login())"

test_token:
	cd NCCUCrawl && \
	ENCSTU="your token, which can obtain after `test_login`"
	ENC=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$ENCSTU")
	curl -X POST "https://es.nccu.edu.tw/tracing/zh-TW/$ENC/"
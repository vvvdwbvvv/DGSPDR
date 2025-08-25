.PHONY: checkstyle course
# run the below script to format
# sed -i '' 's/^    /\t/g' makefile
checkstyle:
	python3 -m ruff check . --exclude deprecated_crawl; ruff_check_status=$$?; \
	python3 -m ruff format --check . --exclude deprecated_crawl; ruff_format_status=$$?; \
	python3 -m ruff check . --fix --exclude deprecated_crawl; \
	python3 -m ruff format . --exclude deprecated_crawl; \
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
	python3 -m scrapy crawl teacher_deprecated -L INFO

test_login:
	cd NCCUCrawl && \
	python3 -c "from NCCUCrawl.auth_curl import Authenticate; auth = Authenticate(); print(auth.login())"

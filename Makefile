.PHONY: checkstyle course
# run the below script to ensure indentation correct
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

courses_smart:
	cd NCCUCrawl && \
	python3 -m scrapy crawl smart_courses -L INFO 

hotfix:
	cd NCCUCrawl && \
	python3 -m scrapy crawl smart_courses -L INFO
	sqlite3 data.db ".dump COURSE" > output.sql
	python3 quickfix.py

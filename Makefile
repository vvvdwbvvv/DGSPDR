.PHONY: checkstyle course
# run the below script to ensure indentation correct
# sed -i '' 's/^    /\t/g' makefile
checkstyle:
	python3 -m ruff check . --exclude deprecated; ruff_check_status=$$?; \
	python3 -m ruff format --check . --exclude deprecated; ruff_format_status=$$?; \
	python3 -m ruff check . --fix --exclude deprecated; \
	python3 -m ruff format . --exclude deprecated; \
	if [ $$ruff_check_status -ne 0 ] || [ $$ruff_format_status -ne 0 ]; then \
	    exit 1; \
	fi
course:
	python3 -m scrapy crawl courses
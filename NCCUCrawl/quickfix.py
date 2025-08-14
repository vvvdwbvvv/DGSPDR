# filepath: [quick_fix.py](http://_vscodecontentref_/0)
import re


def simple_unistr_fix(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    def simple_replace(match):
        unicode_string = match.group(1)

        # 處理常見的轉義序列，但不轉換換行符
        result = unicode_string
        # 將 \u000a (換行) 轉為空格，避免產生實際換行
        result = result.replace("\\u000a", " ")  # 換行改為空格
        result = result.replace("\\u000d", " ")  # 回車改為空格
        result = result.replace("\\u0009", " ")  # Tab改為空格
        result = result.replace("\\\\", "\\")  # 反斜線

        # 移除多餘的空格
        result = re.sub(r"\s+", " ", result).strip()

        # 處理 SQL 單引號
        escaped = result.replace("'", "''")
        return f"'{escaped}'"

    # 簡單的替換
    pattern = r"unistr\s*\(\s*'([^']*(?:''[^']*)*)'\s*\)"
    fixed_content = re.sub(pattern, simple_replace, content, flags=re.DOTALL)

    # 處理可能剩餘的簡單情況
    fixed_content = re.sub(r"unistr\s*\(\s*'", "'", fixed_content)
    fixed_content = re.sub(r"'\s*\)", "')", fixed_content)

    # 將 INSERT INTO 改為 INSERT OR REPLACE INTO 來處理重複記錄
    fixed_content = re.sub(
        r"\bINSERT INTO COURSE VALUES",
        "INSERT OR REPLACE INTO COURSE VALUES",
        fixed_content,
    )

    # 如果有其他表格，也一併處理
    fixed_content = re.sub(
        r"\bINSERT INTO (\w+) VALUES",
        r"INSERT OR REPLACE INTO \1 VALUES",
        fixed_content,
    )

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        f.write(fixed_content)

    print(
        "Processing complete. Changed INSERT to INSERT OR REPLACE to handle duplicates."
    )
    print(f"Output written to {output_file}")


# 使用簡單版本
simple_unistr_fix("output.sql", "output_fixed.sql")

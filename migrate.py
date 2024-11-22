import os
import sqlite3
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import logging
from psycopg2.extras import execute_values

load_dotenv()

logging.basicConfig(
    filename="logs/migrate.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)

def map_sqlite_type(sqlite_type):
    """type projection"""
    sqlite_type = sqlite_type.upper()
    if "INT" in sqlite_type:
        return "INTEGER"
    elif "CHAR" in sqlite_type or "CLOB" in sqlite_type or "TEXT" in sqlite_type:
        return "TEXT"
    elif "BLOB" in sqlite_type:
        return "BYTEA"
    elif "REAL" in sqlite_type or "FLOA" in sqlite_type or "DOUB" in sqlite_type:
        return "DOUBLE PRECISION"
    elif "NUMERIC" in sqlite_type or "DECIMAL" in sqlite_type:
        return "NUMERIC"
    else:
        return "TEXT"

def migrate_sqlite_to_postgres(sqlite_db_path, pg_conn):
    """transfer db"""
    try:
        # sqlite connect
        with sqlite3.connect(sqlite_db_path) as sqlite_conn:
            sqlite_cursor = sqlite_conn.cursor()
            # postgresql connect
            with pg_conn.cursor() as pg_cursor:
                # fetch tables
                sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = sqlite_cursor.fetchall()

                for table in tables:
                    table_name = table[0]
                    logging.info(f"start transfer: {table_name}")

                    #
                    if table_name.startswith('sqlite_'):
                        logging.info(f"skipping SQLITE MASTER : {table_name}")
                        continue

                    sqlite_cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = sqlite_cursor.fetchall()

                    sqlite_cursor.execute(f"PRAGMA index_list({table_name});")
                    indexes = sqlite_cursor.fetchall()

                    sqlite_cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                    foreign_keys = sqlite_cursor.fetchall()


                    column_definitions = []
                    primary_keys = []
                    unique_constraints = []
                    foreign_key_constraints = []

                    for column in columns:
                        col_id, col_name, col_type, notnull, default_val, pk = column
                        pg_col_type = map_sqlite_type(col_type)
                        col_def = f'"{col_name}" {pg_col_type}'

                        if notnull:
                            col_def += " NOT NULL"
                        if default_val is not None:
                            col_def += f" DEFAULT '{default_val}'"
                        column_definitions.append(col_def)

                        if pk:
                            primary_keys.append(f'"{col_name}"')

                    if primary_keys:
                        pk_def = f"PRIMARY KEY ({', '.join(primary_keys)})"
                        column_definitions.append(pk_def)

                    for fk in foreign_keys:
                        _, _, ref_table, ref_column, _, _, _ = fk
                        fk_def = f"FOREIGN KEY (\"{fk[3]}\") REFERENCES \"{ref_table}\"(\"{ref_column}\")"
                        foreign_key_constraints.append(fk_def)

                    column_definitions.extend(foreign_key_constraints)

                    create_table_query = sql.SQL(
                        f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(column_definitions)});'
                    )
                    pg_cursor.execute(create_table_query)
                    logging.info(f"表 {table_name} 創建成功（如未存在）。")

                    sqlite_cursor.execute(f'SELECT * FROM "{table_name}";')
                    rows = sqlite_cursor.fetchall()

                    if not rows:
                        logging.info(f"表 {table_name} 無數據，跳過插入。")
                        continue

                    column_names = [desc[0] for desc in sqlite_cursor.description]

                    insert_query = sql.SQL(
                        f'INSERT INTO "{table_name}" ({", ".join([f\'"{col}"\' for col in column_names])}) VALUES %s ON CONFLICT DO NOTHING;'
                    )

                    try:
                        execute_values(pg_cursor, insert_query, rows)
                        logging.info(f"成功插入表 {table_name} 的 {len(rows)} 條數據。")
                    except Exception as e:
                        logging.error(f"插入表 {table_name} 的數據時出錯: {e}")

                # 提交所有更改
                pg_conn.commit()
                logging.info("所有表遷移完成並提交。")

    except Exception as e:
        logging.error(f"遷移過程中出錯: {e}")
    finally:
        if pg_conn:
            pg_conn.close()
            logging.info("PostgreSQL 連接已關閉。")

def main():
    """主函數"""
    # 獲取環境變量
    sqlite_db_path = 'data.db'  # SQLite 數據庫路徑
    pg_dbname = os.getenv('DB_NAME')
    pg_user = os.getenv('DB_USER')
    pg_password = os.getenv('DB_PASSWORD')
    pg_host = os.getenv('DB_HOST')
    pg_port = os.getenv('DB_PORT')

    if not all([pg_dbname, pg_user, pg_password, pg_host, pg_port]):
        logging.error("PostgreSQL 連接參數不完整。請檢查 .env 文件。")
        return

    try:
        pg_conn = psycopg2.connect(
            dbname=pg_dbname,
            user=pg_user,
            password=pg_password,
            host=pg_host,
            port=pg_port
        )
        logging.info("成功連接到 PostgreSQL。")
    except psycopg2.Error as e:
        logging.error(f"連接到 PostgreSQL 時出錯: {e}")
        return

    migrate_sqlite_to_postgres(sqlite_db_path, pg_conn)

if __name__ == "__main__":
    main()
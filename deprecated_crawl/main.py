import argparse
import logging
import os
import sys

from fetch_class import fetch_classes
from fetch_teacher import fetch_teacher
from fetch_rate import fetch_rate
from fetch_result import fetch_result
import DB
import common
from user import User


def setup_logging():
    """init logging"""
    logging.basicConfig(
        filename="log.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


def setup_parser():
    """初始化命令行解析器"""
    # 全局參數解析器
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--db",
        type=str,
        default="database.db",
        help="指定資料庫檔案路徑 (預設: database.db)",
    )
    parent_parser.add_argument(
        "--semester",
        type=str,
        choices=common.All_SEMESTERS,
        nargs="*",
        default=common.All_SEMESTERS,
        help="指定要抓取的學期 (預設: ALL)",
    )
    parent_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="每次請求之間的延遲時間（秒） (預設: 1.0)",
    )

    # 主解析器
    parser = argparse.ArgumentParser(description="爬蟲主程式", parents=[parent_parser])

    # 子命令解析器
    subparsers = parser.add_subparsers(
        title="子命令",
        description="可用的功能命令",
        help="選擇需要執行的任務",
        dest="command",
    )

    # 定義子命令，繼承全局參數
    subparsers.add_parser("course", parents=[parent_parser], help="抓取課程資料")
    subparsers.add_parser("teacher", parents=[parent_parser], help="抓取教師資料")
    subparsers.add_parser("rate", parents=[parent_parser], help="抓取課程評分資料")
    subparsers.add_parser("result", parents=[parent_parser], help="抓取結果資料")
    subparsers.add_parser("all", parents=[parent_parser], help="抓取所有資料")

    return parser.parse_args()


def create_data_directory():
    dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_data")
    os.makedirs(dir_path, exist_ok=True)
    logging.info(f"Data directory ensured at {dir_path}")


def fetch_data(db, args):
    """Handle data fetching based on the command."""
    user = User()
    command_map = {
        "course": fetch_classes,
        "teacher": fetch_teacher,
        "rate": fetch_rate,
        "result": fetch_result,
        "all": lambda db, args: (
            fetch_classes(db, args),
            fetch_teacher(db, user, args),
            fetch_rate(db, args),
            fetch_result(db, args),
        ),
    }

    fetch_func = command_map.get(args.command)
    if fetch_func:
        logging.info(f"Starting task: {args.command}")
        fetch_func(db, args)
    else:
        logging.error(f"Unknown subcommand: {args.command}")
        print(f"Unknown subcommand: {args.command}")
        sys.exit(1)


def main():
    setup_logging()
    try:
        args = setup_parser()
        create_data_directory()
        db = DB.DB(args.db)

        logging.info("Program started")
        fetch_data(db, args)
        logging.info("Program ended successfully")
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        print(f"Program terminated due to an error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

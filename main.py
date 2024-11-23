import argparse
import csv
import datetime
import json
import logging
import os
import sys
from time import sleep

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from fetch_class import fetch_classes
from fetch_teacher import fetch_teacher
from fetch_rate import fetch_rate
from fetch_result import fetch_result
import DB
import common


def setup_logging():
    """init logging"""
    logging.basicConfig(
        filename="log.log",
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8"
    )


def setup_parser():
    """init parser"""
    parser = argparse.ArgumentParser(
        description="爬蟲主程式，用於抓取課程、教師、評分和結果等資料。"
    )

    parser.add_argument(
        "--db",
        type=str,
        default="database.db",
        help="指定資料庫檔案路徑 (預設: database.db)"
    )

    parser.add_argument(
        "--semester",
        type=str,
        choices=common.All_SEMESTERS,
        nargs='*',
        default=common.All_SEMESTERS,
        help="指定要抓取的學期 (預設: ALL)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="每次請求之間的延遲時間（秒） (預設: 1.0)"
    )

    subparsers = parser.add_subparsers(
        title="子命令",
        description="可用的子命令",
        help="選擇要執行的功能",
        dest="command"
    )

    # 子命令：course
    parser_course = subparsers.add_parser(
        "course",
        help="抓取課程資料"
    )

    # subcommand：teacher
    parser_teacher = subparsers.add_parser(
        "teacher",
        help="抓取教師資料"
    )

    # subcommand：rate
    parser_rate = subparsers.add_parser(
        "rate",
        help="抓取評分資料"
    )

    # subcommand：result
    parser_result = subparsers.add_parser(
        "result",
        help="抓取結果資料"
    )

    # subcommand：all
    parser_all = subparsers.add_parser(
        "all",
        help="抓取所有資料（課程、教師、評分、結果）"
    )

    return parser.parse_args()


def create_data_directory():
    dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_data")
    os.makedirs(dir_path, exist_ok=True)

def main():
    setup_logging()
    args = setup_parser()
    create_data_directory()
    db = DB.DB(args.db)

    logging.info("Program started")

    # 設定全域的延遲時間
    global DELAY
    DELAY = args.delay

    if args.command == "course":
        logging.info("Start fetching courses")
        fetch_classes(db, args)
    elif args.command == "teacher":
        logging.info("Start fetching teachers")
        fetch_teacher(db, args)
    elif args.command == "rate":
        logging.info("Start fetching rate")
        fetch_rate(db, args)
    elif args.command == "result":
        logging.info("Start fetching result")
        fetch_result(db, args)
    elif args.command == "all" or args.command is None:
        logging.info("START FETCH ALL")
        fetch_classes(db, args)
        fetch_teacher(db, args)
        fetch_rate(db, args)
        fetch_result(db, args)
    else:
        logging.error(f"unknown subcommand: {args.command}")
        print(f"unknown subcommand: {args.command}")
        sys.exit(1)

    logging.info("Program ended")


if __name__ == "__main__":
    main()

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

All_SEMESTERS =[
    "1011", "1012", "1021", "1022", "1031", "1032", "1041", "1042",
    "1051", "1052", "1061", "1062", "1071", "1072", "1081", "1082",
    "1091", "1092", "1101", "1102", "1111", "1112", "1121", "1122", "1131"
]

def setup_logging():
    """init logging"""
    logging.basicConfig(
        filename="log.log",
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",

def setup_parser():
    """Set up arg parser"""
    parser = argparse.ArgumentParser()
    parser.add_argument()
    return parser.parse_args()

def create_data_directory():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.makedirs(dir_path, "_data", exist_ok=True)

def main():
    setup_logging()
    args = setup_parser()
    create_data_directory()
    db = DB(args.db)

    if args.course:
        fetch_classes(db,args)
    else:
        print("Skipped Class Fetching")
    if args.teacher:
        fetch_teacher(db,args)
    else:
        print("Skipped Teacher Fetching")
    if args.rate:
        fetch_rate(db,args)
    else:
        print("Skipped Rate Fetching")
    if args.result:
        fetch_result(db,args)
    else:
        print("Skipped Result Fetching")


if __name__ == "__main__":
    main()

"""
============================================================
MAIN.PY — PIPELINE TÍCH HỢP TOÀN BỘ HỆ THỐNG
Phụ trách: Thành viên 5 (Trưởng nhóm - System Integrator)
============================================================
Luồng chạy (Pipeline) liên hoàn:

    Bước 1: crawl_news()   (TV1) -> data/raw_news.csv
    Bước 2: push_to_db()   (TV2) -> MySQL database "tech_news_db"
    Bước 3: clean_data()   (TV3) -> data/clean_news.csv (+ MySQL)
    Bước 4: draw_charts()  (TV4) -> outputs/charts/*.png + wordcloud

Chạy bằng terminal:
    python main.py

Hoặc chạy qua Web App (khuyên dùng để demo cho giảng viên):
    streamlit run app.py
============================================================
"""

import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules import tv1_crawler, tv2_database, tv3_cleaning, tv4_charts

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RAW_PATH = os.path.join(DATA_DIR, "raw_news.csv")
CLEAN_PATH = os.path.join(DATA_DIR, "clean_news.csv")


def step1_crawl(use_existing_csv: bool = True):
    print("\n[BƯỚC 1/4] Thu thập dữ liệu (TV1)...")
    if use_existing_csv and os.path.exists(RAW_PATH):
        print(f"  -> Đã có file {RAW_PATH}, dùng lại (bỏ qua crawl).")
        return pd.read_csv(RAW_PATH)
    try:
        articles = tv1_crawler.crawl_news()
        tv1_crawler.save_to_csv(articles)
        return pd.read_csv(RAW_PATH)
    except NotImplementedError as e:
        print(f"  [CHƯA XONG] {e}")
        return None


def step2_push_db(df: pd.DataFrame):
    print("\n[BƯỚC 2/4] Đẩy dữ liệu vào MySQL (TV2)...")
    if df is None:
        print("  -> Bỏ qua vì chưa có dữ liệu từ Bước 1.")
        return False
    try:
        return tv2_database.push_to_db(df)
    except NotImplementedError as e:
        print(f"  [CHƯA XONG] {e}")
        return False
    except ConnectionError as e:
        print(f"  [LỖI KẾT NỐI MYSQL] {e}")
        return False


def step3_clean(df: pd.DataFrame, use_existing_csv: bool = True):
    print("\n[BƯỚC 3/4] Tiền xử lý & làm sạch dữ liệu (TV3)...")
    if use_existing_csv and os.path.exists(CLEAN_PATH):
        print(f"  -> Đã có file {CLEAN_PATH}, dùng lại (bỏ qua cleaning).")
        return pd.read_csv(CLEAN_PATH)
    if df is None:
        print("  -> Bỏ qua vì chưa có dữ liệu từ Bước 1/2.")
        return None
    try:
        clean_df = tv3_cleaning.clean_data(df)
        tv3_cleaning.save_clean_csv(clean_df)
        return clean_df
    except NotImplementedError as e:
        print(f"  [CHƯA XONG] {e}")
        return None


def step4_charts(clean_df: pd.DataFrame):
    print("\n[BƯỚC 4/4] Phân tích & trực quan hóa (TV4)...")
    if clean_df is None:
        print("  -> Bỏ qua vì chưa có dữ liệu sạch.")
        return []
    try:
        return tv4_charts.draw_charts(clean_df)
    except NotImplementedError as e:
        print(f"  [CHƯA XONG] {e}")
        return []


def run_pipeline():
    print("=" * 60)
    print(" BẮT ĐẦU CHẠY PIPELINE TÍCH HỢP ")
    print("=" * 60)

    raw_df = step1_crawl()
    step2_push_db(raw_df)
    clean_df = step3_clean(raw_df)
    figs = step4_charts(clean_df)

    print("\n" + "=" * 60)
    print(" HOÀN TẤT PIPELINE ")
    print(f" Số biểu đồ tạo ra: {len(figs)}")
    print("=" * 60)
    return clean_df, figs


if __name__ == "__main__":
    run_pipeline()

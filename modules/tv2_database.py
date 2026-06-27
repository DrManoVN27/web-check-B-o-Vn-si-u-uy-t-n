"""
============================================================
THÀNH VIÊN 2 - DATABASE (MySQL: database "news_db")
============================================================
Đây là code GỐC của TV2 (file database.py): tạo database
"news_db", bảng "news" và bảng "keywords" (có khóa ngoại).
Logic tạo bảng được giữ NGUYÊN VẸN trong hàm create_tables().

Việc ĐẨY DỮ LIỆU vào bảng "news" thật ra do TV3 viết (hàm
import_to_mysql() trong data_cleaning_pipeline.py — sau khi
clean xong, TV3 tự đẩy luôn vào MySQL). Vì vậy hàm push_to_db()
ở đây gọi sang module TV3 để dùng đúng logic đẩy DB mà nhóm
đã viết, tránh viết trùng 2 lần.

CẤU HÌNH MYSQL (giữ đúng như code TV2 viết):
    host="localhost", user="root", password="09112007",
    database="news_db"
============================================================
"""

import mysql.connector
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "09112007",
    "database_name": "news_db",
}


def create_tables():
    """Logic GỐC của TV2 (file database.py), giữ nguyên 100%:
    tạo database (nếu chưa nối được vì DB chưa tồn tại thì tự tạo),
    tạo bảng news và bảng keywords."""
    # Nối trước không chỉ định database để có thể tạo nếu chưa có
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database_name']}")
    cursor.execute(f"USE {DB_CONFIG['database_name']}")

    # Tạo bảng news
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(500),
        publish_date DATE,
        author VARCHAR(100),
        content LONGTEXT,
        comments INT,
        source VARCHAR(50),
        url VARCHAR(500)
    )
    """)

    # Tạo bảng keywords
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keywords (
        keyword_id INT AUTO_INCREMENT PRIMARY KEY,
        news_id INT,
        keyword_name VARCHAR(100),
        frequency INT,
        FOREIGN KEY(news_id) REFERENCES news(id)
            ON DELETE CASCADE
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Tạo bảng thành công!")


# ─────────────────────────────────────────────
# HÀM VỎ — để app.py / main.py gọi được
# ─────────────────────────────────────────────

def push_to_db(df: pd.DataFrame) -> bool:
    """
    Hàm vỏ để Web App gọi ở Bước 2 (Đẩy vào MySQL).

    Đảm bảo database/bảng đã tồn tại (create_tables), sau đó
    đẩy dữ liệu vào bảng "news" bằng đúng logic import_to_mysql()
    mà TV3 đã viết trong data_cleaning_pipeline.py — KHÔNG viết
    lại logic đẩy DB ở đây để tránh lệch với cách TV3 đã làm.

    Args:
        df: DataFrame chứa dữ liệu bài báo (cột tiếng Việt:
            nguon, tieu_de, ngay_dang, tac_gia, noi_dung, so_binh_luan, link)

    Returns:
        bool: True nếu đẩy thành công, False nếu lỗi
    """
    try:
        create_tables()
    except mysql.connector.Error as e:
        print(f"[TV2] Lỗi khi tạo database/bảng: {e}")
        raise

    try:
        # Dùng đúng hàm import_to_mysql() mà TV3 đã viết sẵn,
        # vì đó là nơi nhóm đã định nghĩa cách map cột -> bảng "news"
        from modules import tv3_cleaning
        tv3_cleaning.import_to_mysql(df)
        return True
    except Exception as e:
        print(f"[TV2] Lỗi khi đẩy dữ liệu vào MySQL: {e}")
        raise


def read_from_db() -> pd.DataFrame:
    """Đọc lại dữ liệu từ bảng 'news' trong MySQL (database 'news_db')."""
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database_name"],
    )
    df = pd.read_sql("SELECT * FROM news", conn)
    conn.close()
    return df


if __name__ == "__main__":
    create_tables()

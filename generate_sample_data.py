"""
Script TẠO DỮ LIỆU MẪU (demo) — dùng tạm khi chưa có data thật của TV1-TV3.

Khi nhóm code xong thật, chỉ cần chạy đúng pipeline (main.py / app.py),
data thật trong MySQL sẽ tự thay thế — không cần sửa app.py.

Chạy: python generate_sample_data.py
"""

import pandas as pd
import os
import random
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

sources = ["VnExpress", "Tuổi Trẻ"]
authors = ["Minh Anh", "Hoàng Nam", "Thu Hà", "Quang Huy", "Bảo Ngọc"]

topics = [
    ("AI tạo sinh", "Công nghệ AI tiếp tục bùng nổ với nhiều mô hình mới", "ai, trí tuệ nhân tạo, chatbot, mô hình ngôn ngữ"),
    ("Chip bán dẫn", "Cuộc đua sản xuất chip ngày càng khốc liệt", "chip, bán dẫn, sản xuất, công nghệ"),
    ("Smartphone mới", "Hãng điện thoại ra mắt flagship mới", "smartphone, điện thoại, ra mắt, flagship"),
    ("Xe điện", "Thị trường xe điện Việt Nam tăng trưởng mạnh", "xe điện, pin, sạc, ô tô"),
    ("An ninh mạng", "Cảnh báo lỗ hổng bảo mật nghiêm trọng", "an ninh mạng, bảo mật, hacker, lỗ hổng"),
    ("Mạng xã hội", "Nền tảng mạng xã hội thay đổi chính sách", "mạng xã hội, chính sách, người dùng, nội dung"),
    ("Khởi nghiệp công nghệ", "Startup công nghệ Việt nhận vốn đầu tư lớn", "startup, khởi nghiệp, đầu tư, công nghệ"),
    ("Internet vạn vật", "IoT ứng dụng rộng rãi trong đời sống", "iot, internet vạn vật, thiết bị thông minh, nhà thông minh"),
]

rows = []
base_date = datetime(2026, 1, 1)
for i in range(80):
    topic, summary, keywords = random.choice(topics)
    pub_date = base_date + timedelta(days=random.randint(0, 170))
    rows.append({
        "title": f"{topic}: cập nhật mới nhất (#{i+1})",
        "summary": summary,
        "content": f"{summary}. Đây là nội dung chi tiết về {topic.lower()} với nhiều thông tin liên quan đến {keywords}.",
        "url": f"https://example-tech-news.vn/bai-viet-{i+1}",
        "source": random.choice(sources),
        "author": random.choice(authors),
        "published_date": pub_date.strftime("%Y-%m-%d"),
        "num_comments": random.randint(0, 500),
        "category": "Công nghệ",
        "keywords": keywords,
    })

df = pd.DataFrame(rows)
out_path = os.path.join(DATA_DIR, "clean_news.csv")
df.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"Đã tạo {len(df)} bài báo công nghệ mẫu tại: {out_path}")
print("Khi TV1-TV3 xong, chỉ cần chạy pipeline thật — dữ liệu thật trong MySQL sẽ thay thế file này.")

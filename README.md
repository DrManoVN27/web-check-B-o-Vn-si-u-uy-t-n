# Phân Tích Xu Hướng Tin Tức Công Nghệ Việt Nam — Đồ án nhóm

Crawl tin công nghệ từ VnExpress / Tuổi Trẻ → MySQL → Tiền xử lý & NLP
tiếng Việt → Biểu đồ & Word Cloud → Web App tìm kiếm.

## 1. Cấu trúc project

```
project/
├── app.py                  ← Web App (Streamlit) — TV5 đã code xong
├── main.py                 ← Pipeline chạy bằng terminal — TV5 đã code xong
├── database.py              ← Class Database (kết nối MySQL) — TV5 đã code xong
├── article.py                ← Class Article (đại diện 1 bài báo) — TV5 đã code xong
├── generate_sample_data.py ← Tạo data mẫu để demo (không cần khi đã có data thật)
├── requirements.txt
├── data/
│   ├── raw_news.csv        ← TV1 tạo ra (sau khi crawl xong)
│   └── clean_news.csv      ← TV3 tạo ra (sau khi clean+NLP xong) — ĐANG CÓ DATA MẪU
├── modules/
│   ├── tv1_crawler.py      ← TV1 code hàm crawl_news() ở đây
│   ├── tv2_database.py     ← TV2 code hàm push_to_db() ở đây
│   ├── tv3_cleaning.py     ← TV3 code hàm clean_data() ở đây
│   └── tv4_charts.py       ← TV4 code hàm draw_charts() ở đây
└── outputs/
    ├── charts/             ← TV4 lưu ảnh biểu đồ vào đây
    └── wordcloud/          ← TV4 lưu ảnh Word Cloud vào đây
```

## 2. Cài đặt

```bash
pip install -r requirements.txt
```

### Cài MySQL (nếu chưa có)
- Cài XAMPP (có sẵn MySQL Server + phpMyAdmin), HOẶC
- Cài MySQL Server + MySQL Workbench (icon cá heo) riêng

Mặc định code nối tới `localhost`, user `root`, không mật khẩu —
đúng cấu hình XAMPP phổ biến. Nếu MySQL của bạn khác, sửa 4 dòng
đầu trong `database.py` (HOST/USER/PASSWORD/DATABASE) hoặc set
biến môi trường `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

**Không cần tự tạo database/bảng bằng tay** — `database.py` tự
động tạo database `tech_news_db` và bảng `articles` khi chạy lần đầu.

## 3. Cách chạy

```bash
# Kiểm tra kết nối MySQL trước:
python database.py

# Chạy bằng terminal:
python main.py

# Chạy Web App (khuyên dùng để demo cho giảng viên):
streamlit run app.py
```

Trong Web App có nút **"Kiểm tra kết nối MySQL"** ở menu bên trái —
bấm để chắc app đã nối đúng MySQL trên máy bạn.

## 4. Việc của từng người (TV1–TV4)

Mỗi người **chỉ cần sửa file của mình trong `modules/`**, không cần
sửa `app.py`, `main.py`, `database.py`, `article.py`.

| Ai | File | Hàm cần code | Input | Output |
|---|---|---|---|---|
| TV1 | `modules/tv1_crawler.py` | `crawl_news()` | — | list[Article] |
| TV2 | `modules/tv2_database.py` | `push_to_db(df)` | DataFrame | True/False (ghi vào MySQL) |
| TV3 | `modules/tv3_cleaning.py` | `clean_data(df)` | DataFrame thô | DataFrame sạch + cột keywords (NLP) |
| TV4 | `modules/tv4_charts.py` | `draw_charts(df)` | DataFrame sạch | list Figure + ảnh PNG + wordcloud |

**Class có sẵn để dùng chung** (không cần tự viết lại):
- `Database` (`database.py`): quản lý kết nối MySQL
- `Article` (`article.py`): đại diện 1 bài báo, có sẵn
  `save_to_db()`, `save_many_to_db()`, `get_all()`, `search_by_keyword()`

**Cột dữ liệu chuẩn cả nhóm phải theo:**
`title, summary, content, url, source, author, published_date (YYYY-MM-DD), num_comments, category, keywords`

## 5. Test riêng từng module (không cần chờ người khác xong)

```bash
python modules/tv1_crawler.py
python modules/tv2_database.py
python modules/tv3_cleaning.py
python modules/tv4_charts.py
```

## 6. Xem dữ liệu trong MySQL Workbench

Mở MySQL Workbench (icon cá heo) → kết nối `localhost` →
database `tech_news_db` → bảng `articles` → chuột phải →
**"Select Rows - Limit 1000"** để xem toàn bộ dữ liệu đã crawl.

## 7. Lưu ý

- Hiện tại `data/clean_news.csv` đang chứa **80 bài báo công nghệ mẫu
  (giả)** để demo ô tìm kiếm, web app, MySQL ngay từ bây giờ.
- Khi TV1–TV3 code xong và chạy thật, dữ liệu thật sẽ tự thay thế —
  **không cần sửa code app.py / main.py**.
- Nếu một bước nào đó (hoặc MySQL) chưa sẵn sàng, app vẫn chạy được
  nhờ cơ chế xử lý lỗi có sẵn trong `main.py` / `app.py`.

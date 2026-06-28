# Phân Tích Xu Hướng Tin Tức Công Nghệ Việt Nam — Đồ án nhóm

Crawl tin từ VnExpress / Tuổi Trẻ → MySQL → Tiền xử lý & NLP →
Biểu đồ & Word Cloud → Web App tìm kiếm.

## 1. Cấu trúc project

```
project/
├── app.py                  ← Web App (Streamlit) — TV5
├── main.py                 ← Pipeline chạy bằng terminal — TV5
├── generate_sample_data.py ← Tạo data mẫu để demo khi chưa có data thật
├── requirements.txt
├── data/
│   ├── raw_news.csv        ← TV1 tạo ra (crawl xong)
│   └── cleaned_news.csv    ← TV3 tạo ra (clean + NLP xong)
├── modules/
│   ├── tv1_crawler.py      ← Code THẬT của TV1 (Selenium crawl Tuổi Trẻ)
│   ├── tv2_database.py     ← Code THẬT của TV2 (tạo bảng MySQL "news_db")
│   ├── tv3_cleaning.py     ← Code THẬT của TV3 (12 bước clean + import MySQL)
│   └── tv4_charts.py       ← CHƯA CÓ — đang chờ TV4 gửi code vẽ biểu đồ
└── outputs/
    ├── charts/
    └── wordcloud/
```

## 2. Cấu trúc MySQL THẬT đang dùng

- Database: **`news_db`**
- Bảng chính: **`news`** — cột: `id, title, publish_date, author, content, comments, source, url`
- Bảng phụ: **`keywords`** — cột: `keyword_id, news_id, keyword_name, frequency` (khóa ngoại tới `news.id`)
- Kết nối: `host=localhost, user=root, password=09112007`

App tự đổi tên cột (`publish_date`→`published_date`, `comments`→`num_comments`...)
khi hiển thị, không cần sửa code TV2/TV3.

## 3. Cài đặt

```bash
pip install -r requirements.txt
```

MySQL: dùng XAMPP hoặc MySQL Server + Workbench, mật khẩu root đã
đặt sẵn trong code là `09112007` — nếu máy bạn đặt mật khẩu khác,
sửa trong `modules/tv2_database.py` và `modules/tv3_cleaning.py`
(2 chỗ, dòng `password="09112007"`).

TV1 (crawler) cần Google Chrome đã cài trên máy (dùng Selenium).

## 4. Cách chạy

```bash
# Chạy Web App (khuyên dùng):
streamlit run app.py

# Hoặc chạy bằng terminal:
python main.py
```

Trong Web App có nút **"Kiểm tra kết nối MySQL"** ở menu bên trái.

## 5. Việc của từng người

| Ai | File | Trạng thái |
|---|---|---|
| TV1 | `modules/tv1_crawler.py` | ✅ Đã gán code thật (crawl Tuổi Trẻ) |
| TV2 | `modules/tv2_database.py` | ✅ Đã gán code thật (tạo bảng MySQL) |
| TV3 | `modules/tv3_cleaning.py` | ✅ Đã gán code thật (12 bước clean + import MySQL) |
| TV4 | `modules/tv4_charts.py` | ⏳ Đang chờ — gửi code khi xong, hàm cần tên `draw_charts(df)` |
| **TV5** | `app.py`, `main.py`, `requirements.txt`, `README.md` | ✅ Trưởng nhóm — Tích hợp hệ thống & Quản lý chất lượng |

**Việc cụ thể của TV5 (System Integrator & Editor):**
- Thiết kế và code **`app.py`** — Web App (Streamlit):
  - **Menu điều khiển (sidebar)**: nút kiểm tra kết nối MySQL, 4 nút
    chạy từng bước pipeline riêng lẻ (TV1→TV4), 1 nút chạy toàn bộ
    pipeline, nút tải lại dữ liệu mẫu/có sẵn, khung nhật ký chạy.
  - **Ô tìm kiếm gợi ý**: gõ 1 chữ/số/vài chữ, tự động lọc và hiện
    danh sách bài báo khớp theo tiêu đề, tóm tắt, chủ đề, từ khóa.
  - **3 tab giao diện chính**: "Tìm kiếm gợi ý", "Biểu đồ & WordCloud",
    "Dữ liệu" (xem toàn bộ bảng dữ liệu thô).
  - Bố cục `layout="wide"`, tiêu đề, icon, caption mô tả từng phần.
- Code **`main.py`** — chạy pipeline liên hoàn bằng terminal (không cần
  mở web): TV1 → TV2 → TV3 → TV4.
- Bọc code thật của TV1/TV2/TV3 thành các hàm chuẩn (`crawl_news()`,
  `push_to_db()`, `clean_data()`) để web app gọi được qua nút bấm, giữ
  nguyên 100% logic xử lý của từng người.
- Xử lý lệch cấu trúc dữ liệu giữa các module (tên cột tiếng Việt/tiếng
  Anh khác nhau, tên file CSV khác nhau) bằng lớp chuẩn hóa trong `app.py`,
  để không bắt từng người phải sửa code theo nhau.
- Deploy app lên Streamlit Community Cloud (qua GitHub) để có link
  public, ai cũng xem được không cần cài đặt gì.
- Viết tài liệu hướng dẫn (`README.md`), quản lý cấu trúc thư mục project.

Mỗi file trong `modules/` đã được giữ **nguyên 100% logic xử lý**
của từng người, chỉ thêm 1 hàm "vỏ" ở cuối file để app gọi qua nút
bấm (`crawl_news()`, `push_to_db()`, `clean_data()`, `draw_charts()`).
Nếu thành viên nào sửa lại code, chỉ cần thay phần code chính
trong file của họ, giữ nguyên tên hàm vỏ ở cuối.

## 6. Lưu ý

- App ưu tiên đọc dữ liệu từ MySQL nếu kết nối được; nếu không,
  tự rơi về đọc file `data/cleaned_news.csv` có sẵn.
- Cào dữ liệu (TV1) qua Selenium chạy khá lâu (hàng ngàn bài) —
  khi bấm nút "Thu thập dữ liệu" trên web, có thể mất nhiều thời
  gian để hoàn tất.
- Xem dữ liệu trực tiếp: mở MySQL Workbench (icon cá heo) →
  `news_db` → bảng `news` → chuột phải → "Select Rows - Limit 1000".

"""
============================================================
APP.PY — WEB APP ĐIỀU KHIỂN (Streamlit)
Phụ trách: Thành viên 5 (Trưởng nhóm - System Integrator)
============================================================
Chạy app:
    streamlit run app.py

Chức năng:
    1. Ô tìm kiếm: gõ 1 chữ / 1 số / vài chữ -> gợi ý ngay các
       bài báo công nghệ liên quan.
    2. Menu bên trái: nút bấm chạy từng bước pipeline (TV1-TV4)
       hoặc chạy toàn bộ.
    3. Nút kiểm tra kết nối MySQL (để chắc app đang nối đúng
       database mà MySQL Workbench (icon cá heo) đang mở).
    4. Khu vực hiển thị biểu đồ + Word Cloud (TV4).
============================================================
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules import tv1_crawler, tv2_database, tv3_cleaning, tv4_charts

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RAW_PATH = os.path.join(DATA_DIR, "raw_news.csv")
# Lưu ý: TV3 (data_cleaning_pipeline.py) xuất ra tên file "cleaned_news.csv"
# (có "ed"), không phải "clean_news.csv". Để khỏi phải đổi tên tay mỗi lần
# TV3 chạy lại, app ưu tiên đọc đúng tên thật này; nếu không có thì thử
# tên còn lại (phòng trường hợp đổi tên tay như trước).
CLEAN_PATH_REAL = os.path.join(DATA_DIR, "cleaned_news.csv")
CLEAN_PATH_ALT = os.path.join(DATA_DIR, "clean_news.csv")
CLEAN_PATH = CLEAN_PATH_REAL if os.path.exists(CLEAN_PATH_REAL) else CLEAN_PATH_ALT
WORDCLOUD_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "outputs", "wordcloud", "wordcloud.png"
)

st.set_page_config(
    page_title="Phân Tích Xu Hướng Tin Tức Công Nghệ VN",
    page_icon="📰",
    layout="wide",
)

# ---------- HÀM TIỆN ÍCH ----------

# Bản đồ đổi tên cột: tên cột THẬT mà nhóm đang dùng -> tên cột app cần.
# Có 2 nguồn dữ liệu thật, cột đặt tên khác nhau:
#   - File CSV của TV1/TV3 (tiếng Việt không dấu): nguon, tieu_de, ngay_dang...
#   - Bảng "news" trong MySQL của TV2/TV3 (tiếng Anh): source, title, publish_date...
# Nếu sau này đổi tên cột khác, chỉ cần sửa dict này, không cần sửa
# chỗ nào khác trong app.
COLUMN_RENAME_MAP = {
    # cột CSV tiếng Việt -> chuẩn app
    "nguon": "source",
    "tieu_de": "title",
    "ngay_dang": "published_date",
    "tac_gia": "author",
    "noi_dung": "content",
    "so_binh_luan": "num_comments",
    "link": "url",
    # cột bảng MySQL "news" (tiếng Anh, theo database.py / data_cleaning_pipeline.py của TV2-TV3)
    "publish_date": "published_date",
    "comments": "num_comments",
    # title, author, content, source, url đã đúng tên sẵn, không cần đổi
    # các cột dưới đây là cột phục vụ machine learning của TV3,
    # app không dùng tới nhưng vẫn giữ lại trong DataFrame:
    # "so_binh_luan_scaled", "nguon_encoded", "tac_gia_encoded"
}

REQUIRED_COLS = ["title", "summary", "content", "url", "source", "author",
                  "published_date", "num_comments", "category", "keywords"]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Đổi tên cột thật (tiếng Việt không dấu) sang tên app cần,
    và tự tạo các cột còn thiếu (summary, category, keywords) từ
    cột content nếu chưa có, để app không bị lỗi thiếu cột."""
    if df.empty:
        return df

    df = df.rename(columns=COLUMN_RENAME_MAP)

    # Nếu thiếu cột "summary", tự lấy 150 ký tự đầu của "content" làm tóm tắt
    if "summary" not in df.columns and "content" in df.columns:
        df["summary"] = df["content"].astype(str).str.slice(0, 150) + "..."

    # Nếu thiếu cột "category", gán cố định "Công nghệ" (đúng chủ đề đồ án)
    if "category" not in df.columns:
        df["category"] = "Công nghệ"

    # Nếu thiếu cột "keywords", để trống (tìm kiếm vẫn chạy trên các cột khác)
    if "keywords" not in df.columns:
        df["keywords"] = ""

    # Đảm bảo đủ các cột bắt buộc, thiếu cột nào thì tạo cột rỗng cho cột đó
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""

    return df


@st.cache_data
def load_articles_csv(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path)
        return normalize_columns(df)
    return pd.DataFrame(columns=REQUIRED_COLS)


def try_load_from_mysql() -> pd.DataFrame:
    """Ưu tiên đọc dữ liệu từ MySQL (bảng 'news' trong database
    'news_db', do TV2 tạo) nếu kết nối được, nếu không thì rơi về
    file CSV (mẫu hoặc đã làm sạch)."""
    try:
        df = tv2_database.read_from_db()
        if df is not None and not df.empty:
            return normalize_columns(df)
    except Exception:
        pass
    return load_articles_csv(CLEAN_PATH)


def search_articles(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    """Tìm bài báo chứa từ khóa trong title/summary/category/keywords."""
    if not keyword or df.empty:
        return df.iloc[0:0]
    kw = keyword.strip().lower()
    cols = [c for c in ["title", "summary", "category", "keywords"] if c in df.columns]
    mask = False
    for c in cols:
        col_mask = df[c].astype(str).str.lower().str.contains(kw, na=False)
        mask = col_mask if mask is False else (mask | col_mask)
    return df[mask]


def init_session_state():
    if "raw_df" not in st.session_state:
        st.session_state.raw_df = None
    if "clean_df" not in st.session_state:
        st.session_state.clean_df = load_articles_csv(CLEAN_PATH)
    if "figs" not in st.session_state:
        st.session_state.figs = []
    if "log" not in st.session_state:
        st.session_state.log = []
    if "db_status" not in st.session_state:
        st.session_state.db_status = None


def log(msg: str):
    st.session_state.log.append(msg)


init_session_state()

# ============================================================
# SIDEBAR — MENU ĐIỀU KHIỂN PIPELINE
# ============================================================
with st.sidebar:
    st.title("📋 Menu điều khiển")
    st.caption("Tích hợp 4 module: Crawl → MySQL → Clean/NLP → Chart")

    st.subheader("🔌 Kết nối MySQL")
    if st.button("Kiểm tra kết nối MySQL", use_container_width=True):
        try:
            df_check = tv2_database.read_from_db()
            st.session_state.db_status = f"✅ Kết nối OK. Database 'news_db' → bảng 'news' có {len(df_check)} bài báo."
        except Exception as e:
            st.session_state.db_status = f"❌ Chưa kết nối được MySQL: {e}"
    if st.session_state.db_status:
        st.caption(st.session_state.db_status)

    st.divider()
    st.subheader("Chạy từng bước")

    if st.button("1️⃣ Thu thập dữ liệu (TV1)", use_container_width=True):
        try:
            articles = tv1_crawler.crawl_news()
            tv1_crawler.save_to_csv(articles)
            st.session_state.raw_df = pd.read_csv(RAW_PATH)
            log("✅ TV1: Thu thập dữ liệu thành công.")
        except NotImplementedError as e:
            st.warning(f"TV1 chưa code xong: {e}")
        except Exception as e:
            st.error(f"Lỗi ở bước TV1: {e}")

    if st.button("2️⃣ Đẩy vào MySQL (TV2)", use_container_width=True):
        if st.session_state.raw_df is None:
            st.warning("Chưa có dữ liệu thô. Hãy chạy Bước 1 trước.")
        else:
            try:
                tv2_database.push_to_db(st.session_state.raw_df)
                log("✅ TV2: Đẩy MySQL thành công.")
            except NotImplementedError as e:
                st.warning(f"TV2 chưa code xong: {e}")
            except Exception as e:
                st.error(f"Lỗi kết nối/ghi MySQL: {e}")

    if st.button("3️⃣ Làm sạch & NLP (TV3)", use_container_width=True):
        if st.session_state.raw_df is None:
            st.warning("Chưa có dữ liệu thô. Hãy chạy Bước 1 trước.")
        else:
            try:
                clean_df = tv3_cleaning.clean_data(st.session_state.raw_df)
                tv3_cleaning.save_clean_csv(clean_df)
                st.session_state.clean_df = clean_df
                log("✅ TV3: Làm sạch & tách từ thành công.")
            except NotImplementedError as e:
                st.warning(f"TV3 chưa code xong: {e}")
            except Exception as e:
                st.error(f"Lỗi ở bước TV3: {e}")

    if st.button("4️⃣ Vẽ biểu đồ & WordCloud (TV4)", use_container_width=True):
        if st.session_state.clean_df is None or st.session_state.clean_df.empty:
            st.warning("Chưa có dữ liệu sạch. Hãy chạy Bước 1-3 trước (hoặc dùng data mẫu có sẵn).")
        else:
            try:
                st.session_state.figs = tv4_charts.draw_charts(st.session_state.clean_df)
                log("✅ TV4: Vẽ biểu đồ & WordCloud thành công.")
            except NotImplementedError as e:
                st.warning(f"TV4 chưa code xong: {e}")
            except Exception as e:
                st.error(f"Lỗi ở bước TV4: {e}")

    st.divider()
    run_all = st.button("▶️ CHẠY TOÀN BỘ PIPELINE", type="primary", use_container_width=True)

    st.divider()
    if st.button("🔄 Tải dữ liệu mẫu / dữ liệu sạch có sẵn", use_container_width=True):
        st.cache_data.clear()
        st.session_state.clean_df = load_articles_csv(CLEAN_PATH)
        log("ℹ️ Đã tải lại dữ liệu từ data/clean_news.csv")

    if st.session_state.log:
        st.divider()
        st.caption("Nhật ký chạy:")
        for entry in st.session_state.log[-6:]:
            st.text(entry)


if run_all:
    progress = st.progress(0, text="Đang chạy pipeline...")
    try:
        raw = tv1_crawler.crawl_news()
        tv1_crawler.save_to_csv(raw)
        st.session_state.raw_df = pd.read_csv(RAW_PATH)
    except NotImplementedError:
        st.session_state.raw_df = pd.read_csv(RAW_PATH) if os.path.exists(RAW_PATH) else None
    progress.progress(25, text="Bước 1 xong (hoặc bỏ qua) — đang đẩy MySQL...")

    if st.session_state.raw_df is not None:
        try:
            tv2_database.push_to_db(st.session_state.raw_df)
        except (NotImplementedError, Exception):
            pass
    progress.progress(50, text="Bước 2 xong (hoặc bỏ qua) — đang làm sạch & NLP...")

    if st.session_state.raw_df is not None:
        try:
            st.session_state.clean_df = tv3_cleaning.clean_data(st.session_state.raw_df)
            tv3_cleaning.save_clean_csv(st.session_state.clean_df)
        except NotImplementedError:
            st.session_state.clean_df = load_articles_csv(CLEAN_PATH)
    progress.progress(75, text="Bước 3 xong (hoặc bỏ qua) — đang vẽ biểu đồ...")

    try:
        st.session_state.figs = tv4_charts.draw_charts(st.session_state.clean_df)
    except NotImplementedError:
        st.session_state.figs = []
    progress.progress(100, text="Hoàn tất!")
    log("✅ Đã chạy toàn bộ pipeline (các bước chưa code sẽ tự bỏ qua).")


# ============================================================
# KHU VỰC CHÍNH
# ============================================================
st.title("📰 Phân Tích Xu Hướng Tin Tức Công Nghệ Việt Nam")
st.caption("VnExpress · Tuổi Trẻ — Đồ án nhóm — TV5: Tích hợp hệ thống & Quản lý chất lượng")

tab_search, tab_charts, tab_data = st.tabs(["🔎 Tìm kiếm gợi ý", "📊 Biểu đồ & WordCloud", "🗂️ Dữ liệu"])

# ---------- TAB 1: TÌM KIẾM GỢI Ý ----------
with tab_search:
    st.subheader("Tìm kiếm bài báo công nghệ")
    st.caption("Gõ 1 chữ, 1 số hoặc vài chữ — danh sách gợi ý hiện ngay bên dưới.")

    keyword = st.text_input(
        "Nhập từ khóa tìm kiếm:",
        placeholder="Ví dụ: AI, 2026, smartphone, an ninh mạng...",
        key="search_box",
    )

    df = st.session_state.clean_df if st.session_state.clean_df is not None else load_articles_csv(CLEAN_PATH)

    if df is None or df.empty:
        st.info("Chưa có dữ liệu bài báo nào. Hãy chạy pipeline ở menu bên trái hoặc dùng dữ liệu mẫu.")
    elif keyword:
        results = search_articles(df, keyword)
        st.write(f"**Tìm thấy {len(results)} bài báo khớp với '{keyword}':**")
        if results.empty:
            st.warning("Không tìm thấy bài báo phù hợp. Thử từ khóa khác.")
        else:
            for _, row in results.head(20).iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['title']}**")
                    st.caption(
                        f"📰 {row.get('source', '')} • ✍️ {row.get('author', '')} • "
                        f"📅 {row.get('published_date', '')} • 💬 {row.get('num_comments', 0)} bình luận"
                    )
                    st.write(row.get("summary", ""))
                    if pd.notna(row.get("url", None)):
                        st.markdown(f"[🔗 Xem bài báo gốc]({row['url']})")
    else:
        st.info("👆 Nhập từ khóa vào ô trên để xem gợi ý bài báo.")
        st.dataframe(df.head(10), use_container_width=True)

# ---------- TAB 2: BIỂU ĐỒ ----------
with tab_charts:
    st.subheader("Biểu đồ phân tích & Word Cloud (TV4)")
    if st.session_state.figs:
        for fig in st.session_state.figs:
            try:
                st.pyplot(fig)
            except Exception:
                st.write("Không thể hiển thị biểu đồ này.")
    else:
        st.info("Chưa có biểu đồ nào. Hãy bấm '4️⃣ Vẽ biểu đồ & WordCloud (TV4)' hoặc 'CHẠY TOÀN BỘ PIPELINE'.")

    if os.path.exists(WORDCLOUD_PATH):
        st.image(WORDCLOUD_PATH, caption="Word Cloud từ khóa công nghệ", use_container_width=True)

# ---------- TAB 3: DỮ LIỆU ----------
with tab_data:
    st.subheader("Toàn bộ dữ liệu hiện có")
    df_all = st.session_state.clean_df if st.session_state.clean_df is not None else load_articles_csv(CLEAN_PATH)
    st.dataframe(df_all, use_container_width=True)
    st.caption(f"Tổng số bài báo: {len(df_all) if df_all is not None else 0}")
    st.caption("💡 Mở MySQL Workbench (icon cá heo) → database 'news_db' → bảng 'news' để xem trực tiếp trong SQL.")

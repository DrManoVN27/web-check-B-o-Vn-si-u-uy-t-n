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

# Tìm kiếm ngữ nghĩa bằng Vector Database (ChromaDB) — bọc try/except
# vì thư viện chromadb + sentence-transformers khá nặng, có thể chưa
# cài hoặc chưa hỗ trợ trên server cloud; nếu thiếu, app vẫn chạy
# bình thường với tìm kiếm chuỗi ký tự thông thường (fallback).
try:
    import vector_search
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

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

# ============================================================
# CHẾ ĐỘ ADMIN — chỉ TV5 dùng để chạy pipeline / xem dữ liệu thô.
# Người dùng thường vào link bình thường sẽ KHÔNG thấy Menu điều
# khiển (sidebar) và tab "Dữ liệu". Để bật chế độ admin, vào app
# kèm "?admin=1" trên URL, ví dụ:
#     https://ten-app.streamlit.app/?admin=1
# hoặc lúc chạy local: http://localhost:8501/?admin=1
# ============================================================
ADMIN_MODE = st.query_params.get("admin") == "1"

if not ADMIN_MODE:
    # Ẩn hẳn sidebar khỏi giao diện (cả nút mũi tên mở sidebar)
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="collapsedControl"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
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
    except (NotImplementedError, RuntimeError):
        # Bỏ qua nếu TV1 chưa code xong, hoặc đang chạy trên server
        # cloud không có Chrome/Selenium — dùng lại data đã có sẵn.
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

if ADMIN_MODE:
    tab_search, tab_charts, tab_data = st.tabs(["🔎 Tìm kiếm gợi ý", "📊 Biểu đồ & WordCloud", "🗂️ Dữ liệu"])
else:
    tab_search, tab_charts = st.tabs(["🔎 Tìm kiếm gợi ý", "📊 Biểu đồ & WordCloud"])

# ---------- TAB 1: TÌM KIẾM GỢI Ý ----------
with tab_search:
    st.subheader("Tìm kiếm bài báo công nghệ")

    df = st.session_state.clean_df if st.session_state.clean_df is not None else load_articles_csv(CLEAN_PATH)

    # ----- Khu vực chuẩn bị Vector DB (chỉ cần làm 1 lần) -----
    if VECTOR_SEARCH_AVAILABLE:
        vector_db_ready = vector_search.collection_exists_and_has_data()
        col_a, col_b = st.columns([3, 1])
        with col_a:
            if vector_db_ready:
                st.caption("✅ Vector DB (ChromaDB) đã sẵn sàng — gõ câu mô tả, không cần đúng từ khóa.")
            else:
                st.caption("⚠️ Vector DB chưa được xây dựng lần nào. Bấm nút bên phải để xây dựng (chỉ cần 1 lần, mất vài phút với dữ liệu lớn).")
        with col_b:
            if st.button("🧠 Xây dựng Vector DB", use_container_width=True):
                if df is None or df.empty:
                    st.warning("Chưa có dữ liệu để xây dựng.")
                else:
                    with st.spinner("Đang tính embedding và lưu vào ChromaDB (có thể mất vài phút)..."):
                        try:
                            vector_search.build_vector_index(df)
                            st.success("Đã xây dựng xong Vector DB! Giờ có thể tìm kiếm theo ngữ nghĩa.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xây dựng Vector DB: {e}")
        search_mode = st.radio(
            "Kiểu tìm kiếm:",
            ["🧠 Tìm kiếm thông minh (Vector DB - hiểu nghĩa câu)", "🔤 Tìm kiếm theo từ khóa (so khớp chữ)"],
            horizontal=True,
            disabled=not vector_db_ready,
        )
    else:
        search_mode = "🔤 Tìm kiếm theo từ khóa (so khớp chữ)"
        st.caption("ℹ️ Vector DB chưa khả dụng (thiếu thư viện chromadb/sentence-transformers). Đang dùng tìm kiếm theo từ khóa.")

    if "Vector DB" in search_mode:
        st.caption("Gõ cả câu mô tả ý bạn muốn tìm — ví dụ: 'các loại thuốc bổ ích', 'tấn công mạng nguy hiểm'. Vector DB sẽ hiểu nghĩa, không cần đúng từ khóa.")
    else:
        st.caption("Gõ 1 chữ, 1 số hoặc vài chữ — tìm các bài có chứa đúng chữ đó.")

    keyword = st.text_input(
        "Nhập nội dung tìm kiếm:",
        placeholder="Ví dụ: AI, 2026, smartphone, an ninh mạng, các loại thuốc bổ ích...",
        key="search_box",
    )

    if df is None or df.empty:
        st.info("Chưa có dữ liệu bài báo nào. Hãy chạy pipeline ở menu bên trái hoặc dùng dữ liệu mẫu.")
    elif keyword:
        if "Vector DB" in search_mode and VECTOR_SEARCH_AVAILABLE and vector_search.collection_exists_and_has_data():
            try:
                with st.spinner("Đang tìm kiếm trong Vector DB..."):
                    results = vector_search.vector_search(keyword, df)
                st.write(f"**Tìm thấy {len(results)} bài báo liên quan tới '{keyword}' (theo ngữ nghĩa):**")
            except Exception as e:
                st.error(f"Lỗi tìm kiếm Vector DB: {e}. Chuyển sang tìm kiếm theo từ khóa.")
                results = search_articles(df, keyword)
        else:
            results = search_articles(df, keyword)
            st.write(f"**Tìm thấy {len(results)} bài báo khớp với '{keyword}':**")

        if results.empty:
            st.warning("Không tìm thấy bài báo phù hợp. Thử từ khóa khác.")
        else:
            for _, row in results.head(20).iterrows():
                with st.container(border=True):
                    score_text = ""
                    if "similarity_score" in row and pd.notna(row.get("similarity_score")):
                        score_text = f" • 🎯 Độ liên quan: {row['similarity_score']*100:.0f}%"
                    st.markdown(f"**{row['title']}**")
                    st.caption(
                        f"📰 {row.get('source', '')} • ✍️ {row.get('author', '')} • "
                        f"📅 {row.get('published_date', '')} • 💬 {row.get('num_comments', 0)} bình luận"
                        f"{score_text}"
                    )
                    st.write(row.get("summary", ""))
                    if pd.notna(row.get("url", None)):
                        st.markdown(f"[🔗 Xem bài báo gốc]({row['url']})")
    else:
        st.info("👆 Nhập nội dung vào ô trên để xem gợi ý bài báo.")
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

# ---------- TAB 3: DỮ LIỆU (chỉ admin) ----------
if ADMIN_MODE:
    with tab_data:
        st.subheader("Toàn bộ dữ liệu hiện có")
        df_all = st.session_state.clean_df if st.session_state.clean_df is not None else load_articles_csv(CLEAN_PATH)
        st.dataframe(df_all, use_container_width=True)
        st.caption(f"Tổng số bài báo: {len(df_all) if df_all is not None else 0}")
        st.caption("💡 Mở MySQL Workbench (icon cá heo) → database 'news_db' → bảng 'news' để xem trực tiếp trong SQL.")

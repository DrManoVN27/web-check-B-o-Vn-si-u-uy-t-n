"""
============================================================
THÀNH VIÊN 4 - PHỤ TRÁCH: PHÂN TÍCH & TRỰC QUAN HÓA
============================================================
Công cụ gợi ý (theo đề tài): pandas, matplotlib/seaborn,
wordcloud, collections.Counter.

NHIỆM VỤ:
    Viết hàm draw_charts() để:
    - Thống kê số bài viết / bình luận theo ngày, tuần, tháng
    - Vẽ biểu đồ cột: từ khóa công nghệ phổ biến nhất
    - Vẽ biểu đồ đường: xu hướng số bài theo thời gian
    - Tạo Word Cloud từ cột "keywords" (do TV3 tách từ)

QUY ĐỊNH ĐẦU VÀO:
    df: pandas.DataFrame đã làm sạch (từ TV3), có cột "keywords"

QUY ĐỊNH ĐẦU RA (BẮT BUỘC):
    - Trả về list các đối tượng Figure (matplotlib.figure.Figure),
      để web app hiển thị trực tiếp bằng st.pyplot(fig)
    - Lưu từng biểu đồ ra file PNG trong outputs/charts/
    - Lưu ảnh Word Cloud ra outputs/wordcloud/wordcloud.png

CÁCH TÍCH HỢP:
    main.py / app.py gọi: figs = draw_charts(clean_df)
============================================================
"""

import pandas as pd
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHART_DIR = os.path.join(BASE_DIR, "outputs", "charts")
WORDCLOUD_DIR = os.path.join(BASE_DIR, "outputs", "wordcloud")


def draw_charts(df: pd.DataFrame) -> list:
    """
    TODO (TV4): Viết code vẽ biểu đồ + wordcloud thật ở đây.
    Gợi ý cơ bản (xóa các dòng dưới và code lại theo ý bạn):

        import matplotlib.pyplot as plt
        from wordcloud import WordCloud

        # 1. Biểu đồ cột: top từ khóa phổ biến
        all_keywords = []
        for kw_str in df["keywords"].dropna():
            all_keywords.extend([k.strip() for k in str(kw_str).split(",")])
        top_words = Counter(all_keywords).most_common(15)

        fig1, ax1 = plt.subplots(figsize=(10, 6))
        words, counts = zip(*top_words)
        ax1.barh(words, counts)
        ax1.set_title("Top từ khóa công nghệ phổ biến")
        fig1.savefig(os.path.join(CHART_DIR, "top_keywords.png"))

        # 2. Biểu đồ đường: xu hướng số bài theo ngày
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
        daily_counts = df.groupby(df["published_date"].dt.date).size()
        daily_counts.plot(kind="line", marker="o", ax=ax2)
        ax2.set_title("Xu hướng số bài viết theo thời gian")
        fig2.savefig(os.path.join(CHART_DIR, "trend_by_date.png"))

        # 3. Word Cloud
        wc_text = " ".join(all_keywords)
        wc = WordCloud(width=800, height=400, background_color="white",
                        font_path="path/to/vietnamese_font.ttf").generate(wc_text)
        wc.to_file(os.path.join(WORDCLOUD_DIR, "wordcloud.png"))

        return [fig1, fig2]

    LƯU Ý: Word Cloud tiếng Việt cần font hỗ trợ dấu (vd: Arial,
    Noto Sans, hoặc font .ttf có Unicode tiếng Việt).

    Args:
        df: DataFrame đã làm sạch (từ TV3), có cột "keywords"

    Returns:
        list: danh sách các Figure (matplotlib)
    """
    # ----- XÓA DÒNG DƯỚI VÀ VIẾT CODE VẼ BIỂU ĐỒ THẬT TẠI ĐÂY -----
    raise NotImplementedError("TV4: Chưa code hàm draw_charts().")


if __name__ == "__main__":
    # Chạy thử: python modules/tv4_charts.py
    DATA_DIR = os.path.join(BASE_DIR, "data")
    clean_path = os.path.join(DATA_DIR, "clean_news.csv")
    os.makedirs(CHART_DIR, exist_ok=True)
    os.makedirs(WORDCLOUD_DIR, exist_ok=True)
    if os.path.exists(clean_path):
        df = pd.read_csv(clean_path)
        draw_charts(df)
    else:
        print("[TV4] Chưa có file data/clean_news.csv để test. Chạy TV1-TV3 trước.")

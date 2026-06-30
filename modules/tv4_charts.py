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
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHART_DIR = os.path.join(BASE_DIR, "outputs", "charts")
WORDCLOUD_DIR = os.path.join(BASE_DIR, "outputs", "wordcloud")


def draw_charts(df: pd.DataFrame) -> list:
    figs = []
    
    os.makedirs(CHART_DIR, exist_ok=True)
    os.makedirs(WORDCLOUD_DIR, exist_ok=True)
    
    sns.set_theme(style="whitegrid")

    # ==========================================
    # BIỂU ĐỒ 1: Biểu đồ đường 
    # ==========================================
    date_col = 'published_date' if 'published_date' in df.columns else 'ngay_dang'
    
    if date_col in df.columns:
        df_dates = df.copy()
        df_dates[date_col] = pd.to_datetime(df_dates[date_col], errors='coerce')
        daily_counts = df_dates.dropna(subset=[date_col]).groupby(df_dates[date_col].dt.date).size().reset_index(name='count')
        
        fig1, ax1 = plt.subplots(figsize=(12, 5))
        sns.lineplot(data=daily_counts, x=date_col, y='count', marker='o', color='crimson', linewidth=2.5, ax=ax1)
        ax1.set_title("Xu Hướng Số Lượng Bài Viết Theo Ngày", fontsize=14, fontweight='bold', pad=15)
        ax1.set_xlabel("Ngày Đăng")
        ax1.set_ylabel("Số lượng bài viết")
        ax1.tick_params(axis='x', rotation=45)
        fig1.tight_layout()
        
        fig1.savefig(os.path.join(CHART_DIR, "trend_by_date.png"))
        figs.append(fig1)

    # ==========================================
    # XỬ LÝ TỪ KHÓA
    # ==========================================
    all_keywords = []
    if "keywords" in df.columns:
        for kw_str in df["keywords"].dropna():
            clean_str = str(kw_str).replace('[', '').replace(']', '').replace("'", "").replace('"', '')
            all_keywords.extend([k.strip().lower() for k in clean_str.split(",") if len(k.strip()) > 1])
            
    top_words = Counter(all_keywords).most_common(15)
    
    if top_words:
        df_top = pd.DataFrame(top_words, columns=['Từ khóa', 'Tần suất'])

        # ==========================================
        # BIỂU ĐỒ 2: Biểu đồ cột 
        # ==========================================
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        sns.barplot(data=df_top, x='Từ khóa', y='Tần suất', palette='YlGnBu_r', ax=ax2)
        ax2.set_title("Top 15 Từ Khóa Công Nghệ Phổ Biến Nhất", fontsize=14, fontweight='bold', pad=15)
        ax2.set_xlabel("Từ Khóa")
        ax2.set_ylabel("Tần Suất Thực Tế")
        ax2.tick_params(axis='x', rotation=45)
        fig2.tight_layout()
        
        fig2.savefig(os.path.join(CHART_DIR, "top_keywords.png"))
        figs.append(fig2)

        # ==========================================
        # BIỂU ĐỒ 3: Word Cloud 
        # ==========================================
        wc_text = " ".join(all_keywords)
        fig3, ax3 = plt.subplots(figsize=(12, 6))
        
        wc = WordCloud(width=1200, height=600, background_color="white", 
                       colormap="ocean", prefer_horizontal=1.0, 
                       max_words=80, margin=15).generate(wc_text)
                       
        ax3.imshow(wc, interpolation="bilinear")
        ax3.axis("off")
        ax3.set_title("Đám Mây Từ Khóa - Xu Hướng Công Nghệ", fontsize=16, fontweight='bold', pad=20)
        fig3.tight_layout()
        fig3.savefig(os.path.join(WORDCLOUD_DIR, "wordcloud.png"))
        figs.append(fig3)

    return figs


if __name__ == "__main__":
    DATA_DIR = os.path.join(BASE_DIR, "data")
    clean_path = os.path.join(DATA_DIR, "clean_news.csv")
    os.makedirs(CHART_DIR, exist_ok=True)
    os.makedirs(WORDCLOUD_DIR, exist_ok=True)
    
    if os.path.exists(clean_path):
        df = pd.read_csv(clean_path)
        test_figs = draw_charts(df)
        print(f"[TV4] Đã vẽ và lưu thành công {len(test_figs)} biểu đồ vào thư mục outputs!")
    else:
        print("[TV4] Chưa có file data/clean_news.csv để test. Chạy TV1-TV3 trước.")
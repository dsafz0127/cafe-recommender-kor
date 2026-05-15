# app.py
import streamlit as st
import kakao_api
import analyzer

# -----------------------------------------------
# 🎨 페이지 설정
# -----------------------------------------------
st.set_page_config(
    page_title="카페&맛집 추천기",
    page_icon="☕",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #FFF8F0; }
    .tag {
        background-color: #FFF3E0;
        color: #E65100;
        padding: 3px 10px;
        border-radius: 10px;
        font-size: 13px;
        margin: 2px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------
# 📌 앱 제목
# -----------------------------------------------
st.title("☕ 카페 & 맛집 추천기")
st.markdown("> 🔍 카카오맵 실시간 데이터로 장소를 추천해드려요!")
st.divider()

# -----------------------------------------------
# 🔍 사이드바 검색
# -----------------------------------------------
with st.sidebar:
    st.header("🔍 검색 조건")

    search_query = st.text_input(
        "📍 지역 + 키워드",
        value="성수 카페",
        help="예: 홍대 맛집, 강남 브런치, 제주 카페"
    )

    search_btn = st.button(
        "🚀 실시간 검색",
        type="primary",
        use_container_width=True
    )

    st.divider()
    st.markdown("**💡 검색 팁**")
    st.markdown("- 성수 카페")
    st.markdown("- 홍대 브런치")
    st.markdown("- 강남 맛집")
    st.markdown("- 제주 카페")

# -----------------------------------------------
# 📊 결과 표시
# -----------------------------------------------
if search_btn:
    if not search_query.strip():
        st.warning("⚠️ 검색어를 입력해주세요!")
    else:
        with st.spinner(f"'{search_query}' 검색 중... ☕"):

            # API 호출
            places = kakao_api.search_places(search_query)

            # 분석
            df = analyzer.analyze_data(places)

        if df.empty:
            st.error("❌ 검색 결과가 없어요. 키워드를 바꿔보세요.")
        else:
            # 상단 요약
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📍 찾은 장소", f"{len(df)}곳")
            with col2:
                st.metric("🏆 1등 장소", df.iloc[0]['place_name'])
            with col3:
                s_count = len(df[df['grade'] == "⭐ S등급 (강추)"])
                st.metric("🌟 S등급", f"{s_count}곳")

            st.divider()
            st.subheader(f"📋 추천 결과 ({len(df)}곳)")

            # 카드 출력
            for _, row in df.iterrows():
                with st.container():
                    col_info, col_score = st.columns([4, 1])

                    with col_info:
                        # 장소명
                        st.markdown(f"### {row['place_name']}")

                        # 기본 정보
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.caption(f"📂 {row['category_name']}")
                        with c2:
                            st.caption(f"📍 {row['address_name']}")
                        with c3:
                            if row['phone']:
                                st.caption(f"📞 {row['phone']}")

                        # 카카오맵 링크
                        st.markdown(f"🔗 [카카오맵에서 보기]({row['place_url']})")

                        # 태그
                        if row['purpose_tags']:
                            tags_html = " ".join([
                                f'<span class="tag">{t}</span>'
                                for t in row['purpose_tags']
                            ])
                            st.markdown(tags_html, unsafe_allow_html=True)

                    with col_score:
                        st.markdown(
                            f"""
                            <div style='text-align:center; padding:15px;
                            background:#FF6B35; border-radius:15px; color:white;'>
                                <div style='font-size:36px; font-weight:bold;'>
                                    {row['quality_score']}
                                </div>
                                <div style='font-size:12px;'>품질 점수</div>
                                <div style='font-size:12px; margin-top:5px;'>
                                    {row['grade']}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                st.divider()

else:
    # 처음 화면
    st.info("👈 왼쪽에서 검색어를 입력하고 검색 버튼을 눌러보세요!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### ☕ 카페 탐방")
        st.markdown("성수, 홍대, 연남동...")
    with col2:
        st.markdown("### 🍝 맛집 탐방")
        st.markdown("강남, 이태원, 을지로...")
    with col3:
        st.markdown("### 🗺️ 전국 어디든")
        st.markdown("제주, 부산, 전주...")

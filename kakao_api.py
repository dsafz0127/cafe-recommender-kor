# kakao_api.py
import requests

# ✅ secrets.py에서 키 가져오기
try:
    from secrets import KAKAO_API_KEY  # 로컬 환경
except:
    import streamlit as st
    KAKAO_API_KEY = st.secrets["KAKAO_API_KEY"]  # 배포 환경

def search_places(query):
    """카카오맵 장소 검색 API"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }

    params = {
        "query": query,
        "size": 15,
        "sort": "accuracy"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )
        print("응답 코드:", response.status_code)
        response.raise_for_status()
        data = response.json()
        return data.get('documents', [])

    except Exception as e:
        print(f"API 오류: {e}")
        return []
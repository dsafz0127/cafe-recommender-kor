import requests
import streamlit as st


def _load_key(key_name):
    try:
        import config
        val = getattr(config, key_name, "")
        if val and str(val).strip():
            return str(val).strip()
    except ImportError:
        pass
    try:
        val = st.secrets.get(key_name, "")
        if val and str(val).strip():
            return str(val).strip()
    except Exception:
        pass
    return ""


KAKAO_API_KEY = _load_key("KAKAO_API_KEY")


def search_places(query, page=1, size=15):
    if not KAKAO_API_KEY:
        return {"documents": [], "meta": {}, "error": "카카오 REST API 키가 설정되지 않았습니다."}

    url     = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params  = {
        "query": query,
        "size":  min(size, 15),
        "page":  min(max(page, 1), 45),
        "sort":  "accuracy",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {"documents": data.get("documents", []), "meta": data.get("meta", {}), "error": None}

        status = response.status_code
        if status == 401:
            return {"documents": [], "meta": {}, "error": "인증 실패. REST API 키를 확인해주세요."}
        elif status == 400:
            return {"documents": [], "meta": {}, "error": "검색 요청이 올바르지 않습니다."}
        elif status == 429:
            return {"documents": [], "meta": {}, "error": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."}
        else:
            return {"documents": [], "meta": {}, "error": f"서버 오류 (HTTP {status})"}

    except requests.Timeout:
        return {"documents": [], "meta": {}, "error": "서버 응답 시간 초과."}
    except requests.ConnectionError:
        return {"documents": [], "meta": {}, "error": "인터넷 연결을 확인해주세요."}
    except Exception as e:
        return {"documents": [], "meta": {}, "error": f"오류: {str(e)}"}


def search_places_multi(query, total_size=15):
    all_docs = []
    page = 1
    max_pages = 45

    while len(all_docs) < total_size and page <= max_pages:
        result = search_places(query, page=page, size=15)

        if result["error"]:
            meta_info = {
                "total_count": len(all_docs),
                "requested_size": total_size,
                "fetched_count": len(all_docs),
                "pages_fetched": page - 1 if page > 1 else 0,
                "is_truncated": False,
                "warning": result["error"]
            }
            return {
                "documents": all_docs[:total_size],
                "meta": meta_info,
                "error": None
            }

        docs = result["documents"]
        if not docs:
            break
        all_docs.extend(docs)

        meta = result.get("meta", {})
        is_end = meta.get("is_end", True)

        if is_end:
            break
        page += 1

    result_docs = all_docs[:total_size]
    meta_info = {
        "total_count": len(all_docs),
        "requested_size": total_size,
        "fetched_count": len(result_docs),
        "pages_fetched": page,
        "is_truncated": (len(all_docs) > total_size) or (not is_end and page <= max_pages)
    }

    return {
        "documents": result_docs,
        "meta": meta_info,
        "error": None
    }
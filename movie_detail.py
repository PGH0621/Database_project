import sqlite3
import requests
import xml.etree.ElementTree as ET
import time

API_KEY = "2a0ea954af173fd3754ab841729022de"
DB = "moviesM.db"

# =========================
# DB 연결
# =========================
conn = sqlite3.connect(DB)
cur = conn.cursor()

# =========================
# 상세정보 테이블 생성
# =========================
cur.execute("""
CREATE TABLE IF NOT EXISTS movie_info (
    movieCd TEXT PRIMARY KEY,
    movieNm TEXT,
    movieNmEn TEXT,
    showTm TEXT,
    prdtYear TEXT,
    openDt TEXT,
    nations TEXT,
    genres TEXT,
    directors TEXT,
    actors TEXT,
    audits TEXT,
    companys TEXT
)
""")

# =========================
# movies 테이블에서 movieCd 목록 수집
# =========================
movie_codes = [
    row[0] for row in cur.execute(
        "SELECT DISTINCT movieCd FROM movies"
    ).fetchall()
]

print(f"🎬 수집 대상 영화 수: {len(movie_codes)}")

# =========================
# 영화 상세정보 수집
# =========================
for idx, movieCd in enumerate(movie_codes, 1):
    url = (
        "http://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/"
        f"searchMovieInfo.xml?key={API_KEY}&movieCd={movieCd}"
    )

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[ERROR] {movieCd} 요청 실패:", e)
        continue

    root = ET.fromstring(r.content)
    info = root.find("movieInfo")

    if info is None:
        print(f"[SKIP] {movieCd} 정보 없음")
        continue

    def get_text(parent, path):
        el = parent.find(path)
        return el.text if el is not None else ""

    movieNm = get_text(info, "movieNm")
    movieNmEn = get_text(info, "movieNmEn")
    showTm = get_text(info, "showTm")
    prdtYear = get_text(info, "prdtYear")
    openDt = get_text(info, "openDt")

    nations = ", ".join(
        [n.find("nationNm").text for n in info.findall("nations/nation")]
    )

    genres = ", ".join(
        [g.find("genreNm").text for g in info.findall("genres/genre")]
    )

    directors = ", ".join(
        [d.find("peopleNm").text for d in info.findall("directors/director")]
    )

    actors = ", ".join(
        [a.find("peopleNm").text for a in info.findall("actors/actor")[:10]]
    )

    audits = ", ".join(
        [a.find("watchGradeNm").text for a in info.findall("audits/audit")]
    )

    companys = ", ".join(
        [c.find("companyNm").text for c in info.findall("companys/company")]
    )

    cur.execute("""
        INSERT OR REPLACE INTO movie_info
        (movieCd, movieNm, movieNmEn, showTm, prdtYear, openDt,
         nations, genres, directors, actors, audits, companys)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        movieCd, movieNm, movieNmEn, showTm, prdtYear, openDt,
        nations, genres, directors, actors, audits, companys
    ))

    print(f"[{idx}/{len(movie_codes)}] 저장 완료: {movieNm}")

    time.sleep(0.2)  # API 과부하 방지

conn.commit()
conn.close()

print("✅ 영화 상세정보 수집 완료")

import sqlite3
import requests
from datetime import datetime, timedelta

API_KEY = "2a0ea954af173fd3754ab841729022de"
DB = "moviesM.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 테이블 초기화
cur.execute("DROP TABLE IF EXISTS movies")

cur.execute("""
CREATE TABLE movies (
    movieCd TEXT,
    movieNm TEXT,
    rank TEXT,
    audiCnt TEXT,
    audiAcc TEXT,
    salesAmt TEXT,
    salesAcc TEXT,
    targetDt TEXT,
    PRIMARY KEY (movieCd, targetDt)
)
""")

# 최근 3개월 (90일)
dates = [(datetime.today() - timedelta(days=i)).strftime("%Y%m%d") for i in range(90)]

for targetDt in dates:
    url = (
        "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/"
        f"searchDailyBoxOfficeList.json?key={API_KEY}&targetDt={targetDt}"
    )

    r = requests.get(url).json()
    data = r.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

    if not data:
        print(f"{targetDt} 데이터 없음")
        continue

    for m in data:
        cur.execute("""
            INSERT OR REPLACE INTO movies
            (movieCd, movieNm, rank, audiCnt, audiAcc, salesAmt, salesAcc, targetDt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["movieCd"],
            m["movieNm"],
            m["rank"],
            m["audiCnt"],
            m["audiAcc"],
            m["salesAmt"],
            m["salesAcc"],
            targetDt
        ))

    print(f"{targetDt} 저장 완료")

conn.commit()
conn.close()
print("✅ DB 수집 완료")

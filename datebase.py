import sqlite3
import requests
from datetime import datetime, timedelta

API_KEY = "2a0ea954af173fd3754ab841729022de"
DB = "moviesM.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 날짜 리스트 (최근 30일)
dates = [(datetime.today() - timedelta(days=i)).strftime("%Y%m%d") for i in range(30)]

for targetDt in dates:
    url = ("http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/"
           f"searchDailyBoxOfficeList.json?key={API_KEY}&targetDt={targetDt}")

    json = requests.get(url).json()

    # 데이터 없는 날짜 패스
    if "boxOfficeResult" not in json or "dailyBoxOfficeList" not in json["boxOfficeResult"]:
        print(f"{targetDt}: 데이터 없음 → 건너뜀")
        continue

    data = json["boxOfficeResult"]["dailyBoxOfficeList"]
    if not data:
        print(f"{targetDt}: 영화 목록 없음 → 건너뜀")
        continue

    # 컬럼 생성 (첫 실행 시)
    columns = list(data[0].keys())
    sql_columns = ", ".join([f'"{c}" TEXT' for c in columns])
    cur.execute(f'CREATE TABLE IF NOT EXISTS movies ({sql_columns});')

    # 누락된 컬럼 자동 확장
    existing_cols = [row[1] for row in cur.execute("PRAGMA table_info(movies)").fetchall()]
    for col in columns:
        if col not in existing_cols:
            cur.execute(f'ALTER TABLE movies ADD COLUMN "{col}" TEXT;')

    # 데이터 INSERT
    for movie in data:
        movie_values = [movie.get(col, None) for col in columns]
        placeholders = ", ".join(["?"] * len(columns))
        cur.execute(f'''
            INSERT OR REPLACE INTO movies ({",".join(columns)})
            VALUES ({placeholders})
        ''', movie_values)

    print(f"{targetDt} 저장 완료")

conn.commit()
conn.close()
print("\n최근 30일 데이터 모두 저장 완료 (API → SQLite)")

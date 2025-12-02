import os
import sqlite3
import requests
from flask import Flask, render_template

app = Flask(__name__)
DB = "moviesM.db"
API_KEY = "2a0ea954af173fd3754ab841729022de"

@app.route("/")
def home():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ==== 1) 일간 박스오피스 (DB) ====
    try:
        rows = cur.execute("SELECT * FROM movies BY rank ASC").fetchall()
    except:
        rows = cur.execute("SELECT * FROM movies").fetchall()

    daily_list = [dict(r) for r in rows]
    conn.close()

    # ==== 2) 주간 박스오피스 (API 실시간) ====
    weekly_url = (
        "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/"
        f"searchWeeklyBoxOfficeList.json?key={API_KEY}&targetDt=20251116"
    )
    json = requests.get(weekly_url).json()
    weekly_data = json["boxOfficeResult"]["weeklyBoxOfficeList"]

    # 포스터 매핑 (일간)
    for m in daily_list:
        code = m.get("movieCd", "")
        m["poster"] = "default.png"
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            path = f"static/posters/{code}{ext}"
            if os.path.exists(path):
                m["poster"] = code + ext
                break

    # 포스터 매핑 (주간)
    for w in weekly_data:
        code = w.get("movieCd", "")
        w["poster"] = "default.png"
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            path = f"static/posters/{code}{ext}"
            if os.path.exists(path):
                w["poster"] = code + ext
                break

    return render_template("newflix_html.html",
                           movies=daily_list,
                           weekly=weekly_data)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)

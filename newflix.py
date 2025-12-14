import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, abort

app = Flask(__name__)
DB = "moviesM.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def attach_poster(items):
    for m in items:
        code = m.get("movieCd", "")
        m["poster"] = "default.png"
        for ext in [".jpg", ".png", ".jpeg", ".webp"]:
            if os.path.exists(f"static/posters/{code}{ext}"):
                m["poster"] = code + ext
                break

@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor()

    latest_dt = cur.execute(
        "SELECT MAX(targetDt) AS dt FROM movies"
    ).fetchone()["dt"]

    default_year = latest_dt[:4]
    default_month = latest_dt[4:6]

    year = request.args.get("year", default_year)
    month = request.args.get("month", default_month)
    only_new = request.args.get("only_new", "0") == "1"

    yyyymm = f"{year}{month}"

    # --- 신규 콘텐츠 (최근 30일, 최초 등장 기준) ---
    start_dt = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")

    new_rows = cur.execute("""
        SELECT m.*
        FROM movies m
        JOIN (
            SELECT movieCd, MIN(targetDt) AS firstDt
            FROM movies
            GROUP BY movieCd
        ) f ON m.movieCd = f.movieCd
        WHERE f.firstDt >= ?
          AND m.targetDt = f.firstDt
        ORDER BY f.firstDt DESC
    """, (start_dt,)).fetchall()

    new_contents = [dict(r) for r in new_rows]

    # --- 월별 박스오피스 (신규 전용 모드면 조회 X) ---
    movies = []
    if not only_new:
        rows = cur.execute("""
            SELECT *
            FROM movies
            WHERE substr(targetDt,1,6) = ?
              AND targetDt = (
                  SELECT MAX(targetDt)
                  FROM movies
                  WHERE substr(targetDt,1,6) = ?
              )
            ORDER BY CAST(rank AS INTEGER) ASC
        """, (yyyymm, yyyymm)).fetchall()
        movies = [dict(r) for r in rows]

    conn.close()

    attach_poster(new_contents)
    attach_poster(movies)

    # NEW 배지 여부
    new_codes = {n["movieCd"] for n in new_contents}
    for m in movies:
        m["is_new"] = m["movieCd"] in new_codes

    return render_template(
        "newflix_html.html",
        movies=movies,
        new_contents=new_contents,
        selected_year=year,
        selected_month=month,
        only_new=only_new
    )

@app.route("/movie/<movieCd>")
def detail(movieCd):
    conn = get_db()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT *
        FROM movies
        WHERE movieCd = ?
        ORDER BY targetDt DESC
    """, (movieCd,)).fetchall()

    if not rows:
        abort(404)

    movie = dict(rows[0])
    history = [dict(r) for r in rows]

    conn.close()

    attach_poster([movie])

    return render_template(
        "detail.html",
        movie=movie,
        history=history
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)

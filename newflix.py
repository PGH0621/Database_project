import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, abort

app = Flask(__name__)
DB = "moviesM.db"

# =========================
# DB 연결
# =========================
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# =========================
# 포스터 연결
# =========================
def attach_poster(items):
    for m in items:
        code = m.get("movieCd", "")
        m["poster"] = "default.png"
        for ext in [".jpg", ".png", ".jpeg", ".webp"]:
            if os.path.exists(f"static/posters/{code}{ext}"):
                m["poster"] = code + ext
                break

# =========================
# 메인 페이지
# =========================
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

    country = request.args.get("country")
    audience = request.args.get("audience")
    genre = request.args.get("genre")

    filter_active = any([only_new, country, audience, genre])

    yyyymm = f"{year}{month}"

    cutoff_date = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    # 신규 콘텐츠
    new_rows = cur.execute("""
        SELECT m.*
        FROM movies m
        JOIN (
            SELECT movieCd, MAX(targetDt) AS latestDt
            FROM movies
            GROUP BY movieCd
        ) t
          ON m.movieCd = t.movieCd
         AND m.targetDt = t.latestDt
        WHERE m.openDt >= ?
        ORDER BY m.openDt DESC
    """, (cutoff_date,)).fetchall()

    new_contents = [dict(r) for r in new_rows]

    # 필터 결과
    filter_results = []
    if filter_active:
        sql = """
            SELECT m.*, i.genres, i.nations
            FROM movies m
            JOIN (
                SELECT movieCd, MAX(targetDt) AS latestDt
                FROM movies
                GROUP BY movieCd
            ) t
              ON m.movieCd = t.movieCd
             AND m.targetDt = t.latestDt
            LEFT JOIN movie_info i ON m.movieCd = i.movieCd
            WHERE 1=1
        """
        params = []

        if only_new:
            sql += " AND m.openDt >= ?"
            params.append(cutoff_date)

        if country == "korea":
            sql += " AND i.nations LIKE '%한국%'"
        elif country == "foreign":
            sql += " AND i.nations NOT LIKE '%한국%'"

        if audience == "100":
            sql += " AND CAST(m.audiAcc AS INTEGER) >= 1000000"
        elif audience == "500":
            sql += " AND CAST(m.audiAcc AS INTEGER) >= 5000000"

        if genre:
            sql += " AND i.genres LIKE ?"
            params.append(f"%{genre}%")

        rows = cur.execute(sql, params).fetchall()
        filter_results = [dict(r) for r in rows]

    movies = []
    if not filter_active:
        rows = cur.execute("""
            SELECT *
            FROM movies
            WHERE substr(targetDt,1,6)=?
              AND targetDt=(
                SELECT MAX(targetDt)
                FROM movies
                WHERE substr(targetDt,1,6)=?
              )
            ORDER BY CAST(rank AS INTEGER)
        """, (yyyymm, yyyymm)).fetchall()
        movies = [dict(r) for r in rows]

    conn.close()

    attach_poster(new_contents)
    attach_poster(movies)
    attach_poster(filter_results)

    new_codes = {n["movieCd"] for n in new_contents}
    for m in movies:
        m["is_new"] = m["movieCd"] in new_codes

    return render_template(
        "newflix_html.html",
        movies=movies,
        new_contents=new_contents,
        filter_results=filter_results,
        filter_active=filter_active,
        selected_year=year,
        selected_month=month,
        only_new=only_new,
        country=country,
        audience=audience,
        genre=genre
    )

# =========================
# 전체 영화 보기
# =========================
@app.route("/all")
def all_movies():
    conn = get_db()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT m.*
        FROM movies m
        JOIN (
            SELECT movieCd, MAX(targetDt) AS latestDt
            FROM movies
            GROUP BY movieCd
        ) t
          ON m.movieCd = t.movieCd
         AND m.targetDt = t.latestDt
        ORDER BY m.movieNm
    """).fetchall()

    movies = [dict(r) for r in rows]
    conn.close()

    attach_poster(movies)

    return render_template("all_movies.html", movies=movies)

# =========================
# 상세 페이지
# =========================
@app.route("/movie/<movieCd>")
def detail(movieCd):
    conn = get_db()
    cur = conn.cursor()

    movie_row = cur.execute("""
        SELECT *
        FROM movies
        WHERE movieCd = ?
        ORDER BY targetDt DESC
        LIMIT 1
    """, (movieCd,)).fetchone()

    if not movie_row:
        abort(404)

    movie = dict(movie_row)

    info_row = cur.execute("""
        SELECT *
        FROM movie_info
        WHERE movieCd = ?
    """, (movieCd,)).fetchone()

    info = dict(info_row) if info_row else {}

    conn.close()

    attach_poster([movie])

    return render_template(
        "detail.html",
        movie=movie,
        info=info
    )
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)

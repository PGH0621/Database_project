import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, abort, redirect

app = Flask(__name__)

# =========================
# DB 경로 (권장: 절대경로)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "moviesM.db")

# =========================
# 임시 사용자 (과제용)
# =========================
CURRENT_USER_ID = 1   # 박근호

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

    # =========================
    # 신규 콘텐츠
    # =========================
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

    # =========================
    # 🔹 내가 찜한 영화
    # =========================
    fav_rows = cur.execute("""
        SELECT m.*
        FROM favorites f
        JOIN movies m
          ON f.movieCd = m.movieCd
        JOIN (
            SELECT movieCd, MAX(targetDt) AS latestDt
            FROM movies
            GROUP BY movieCd
        ) t
          ON m.movieCd = t.movieCd
         AND m.targetDt = t.latestDt
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    """, (CURRENT_USER_ID,)).fetchall()

    favorite_movies = [dict(r) for r in fav_rows]

    # =========================
    # 필터 결과
    # =========================
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

    # =========================
    # 월별 박스오피스
    # =========================
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

    # 포스터 연결
    attach_poster(new_contents)
    attach_poster(movies)
    attach_poster(filter_results)
    attach_poster(favorite_movies)

    new_codes = {n["movieCd"] for n in new_contents}
    for m in movies:
        m["is_new"] = m["movieCd"] in new_codes

    return render_template(
        "newflix_html.html",
        movies=movies,
        new_contents=new_contents,
        favorite_movies=favorite_movies,   # ✅ 추가
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
# 영화 상세 페이지
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

    # 🔹 찜 여부
    fav = cur.execute("""
        SELECT 1 FROM favorites
        WHERE user_id = ? AND movieCd = ?
    """, (CURRENT_USER_ID, movieCd)).fetchone()
    is_favorite = fav is not None

    # 🔹 시청 기록 여부 + 시간
    watch = cur.execute("""
        SELECT watched_sec
        FROM watch_history
        WHERE user_id = ? AND movieCd = ?
    """, (CURRENT_USER_ID, movieCd)).fetchone()

    has_watch_history = watch is not None
    watched_sec = watch["watched_sec"] if watch else 0

    conn.close()
    attach_poster([movie])

    return render_template(
        "detail.html",
        movie=movie,
        info=info,
        is_favorite=is_favorite,
        has_watch_history=has_watch_history,
        watched_sec=watched_sec
    )


# =========================
# 찜하기
# =========================
# =========================
# 찜하기 / 찜 취소 (토글)
# =========================
@app.route("/favorite/<movieCd>", methods=["POST"])
def toggle_favorite(movieCd):
    conn = get_db()
    cur = conn.cursor()

    # 이미 찜했는지 확인
    fav = cur.execute("""
        SELECT 1 FROM favorites
        WHERE user_id = ? AND movieCd = ?
    """, (CURRENT_USER_ID, movieCd)).fetchone()

    if fav:
        # 이미 찜 → 취소
        cur.execute("""
            DELETE FROM favorites
            WHERE user_id = ? AND movieCd = ?
        """, (CURRENT_USER_ID, movieCd))
    else:
        # 찜 안 함 → 추가
        cur.execute("""
            INSERT INTO favorites (user_id, movieCd)
            VALUES (?, ?)
        """, (CURRENT_USER_ID, movieCd))

    conn.commit()
    conn.close()

    return redirect(f"/movie/{movieCd}")
@app.route("/watch_time/<movieCd>")
def get_watch_time(movieCd):
    conn = get_db()
    cur = conn.cursor()

    row = cur.execute("""
        SELECT watched_sec
        FROM watch_history
        WHERE user_id = ? AND movieCd = ?
    """, (CURRENT_USER_ID, movieCd)).fetchone()

    conn.close()

    return {
        "watched_sec": row["watched_sec"] if row else 0
    }
@app.route("/watch_time/<movieCd>", methods=["POST"])
def save_watch_time(movieCd):
    watched_sec = request.json.get("watched_sec", 0)

    conn = get_db()
    cur = conn.cursor()

    # 🔹 영화명 조회 (최신 데이터 기준)
    movie_row = cur.execute("""
        SELECT movieNm
        FROM movies
        WHERE movieCd = ?
        ORDER BY targetDt DESC
        LIMIT 1
    """, (movieCd,)).fetchone()

    movieNm = movie_row["movieNm"] if movie_row else ""

    # 🔹 시청 기록 저장 (movieNm 포함)
    cur.execute("""
        INSERT INTO watch_history
        (user_id, movieCd, movieNm, watched_sec, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, movieCd)
        DO UPDATE SET
            watched_sec = excluded.watched_sec,
            movieNm = excluded.movieNm,
            updated_at = CURRENT_TIMESTAMP
    """, (
        CURRENT_USER_ID,
        movieCd,
        movieNm,
        watched_sec
    ))

    conn.commit()
    conn.close()

    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)

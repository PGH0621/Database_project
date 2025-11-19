import os
import requests
from flask import Flask, render_template

app = Flask(__name__)

API_KEY = "2a0ea954af173fd3754ab841729022de"  # KOBIS 서비스 키

@app.route("/")
def home():
    url = (
        "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/"
        f"searchDailyBoxOfficeList.json?key={API_KEY}&targetDt=20251118"
    )
    response = requests.get(url)
    data = response.json()
    movie_list = data["boxOfficeResult"]["dailyBoxOfficeList"]

    # 🎬 영화 고유 코드(movieCd) 기반 포스터 파일 매칭
    for m in movie_list:
        code = m["movieCd"]   # 예: "20198452"
        m["poster"] = "default.png"  # 기본 이미지 (없을 때)

        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            file_path = f"static/posters/{code}{ext}"
            if os.path.exists(file_path):
                m["poster"] = code + ext
                break

    return render_template("newflix_html.html", movies=movie_list)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)

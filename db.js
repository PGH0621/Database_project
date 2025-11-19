const API_KEY = "2a0ea954af173fd3754ab841729022de";
const targetDate = "20251117";  // 예: YYYYMMDD 형식
const url = `https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key=${API_KEY}&targetDt=${targetDate}`;

fetch(url)
  .then(res => res.json())
  .then(data => {
    console.log("응답 데이터:", data);
    const list = data.boxOfficeResult.dailyBoxOfficeList;
    list.forEach(movie => {
      console.log(movie.movieNm, movie.audiCnt);
    });
  })
  .catch(err => {
    console.error("API 호출 오류:", err);
  });

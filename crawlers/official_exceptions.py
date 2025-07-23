import requests
from bs4 import BeautifulSoup

def crawl():
    url = "https://docs.python.org/3/library/exceptions.html"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "lxml")
    print("official_exceptions crawl 함수 호출됨")
    results = []
    # dt 태그는 예외 이름, dd 태그는 설명
    dts = soup.find_all("dt")
    for dt in dts:
        title = dt.get_text().strip()
        dd = dt.find_next_sibling("dd")
        description = dd.get_text().strip() if dd else ""
        if "Error" in title or "Exception" in title:
            results.append({
                "title": title,
                "description": description,
                "source": "official_exceptions"
            })
    return results

import requests
from bs4 import BeautifulSoup

def crawl():
    url = "https://rollbar.com/blog/python-errors-and-how-to-handle-them/"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "lxml")
    print("rollbar crawl 함수 호출됨")
    results = []
    for h in soup.select("h2, h3"):
        title = h.get_text(strip=True)
        desc = h.find_next("p")
        desc_text = desc.get_text(strip=True) if desc else ""
        if "error" in title.lower():
            results.append({
                "title": title,
                "description": desc_text,
                "source": "rollbar.com"
            })
    return results

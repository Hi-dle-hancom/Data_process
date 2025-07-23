import requests
from bs4 import BeautifulSoup

def crawl():
    url = "https://betterstack.com/community/guides/scaling-python/python-errors/"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "lxml")
    print("betterstack3 crawl 함수 호출됨")
    results = []
    for block in soup.select("h2"):
        title = block.get_text(strip=True)
        desc = block.find_next("p")
        desc_text = desc.get_text(strip=True) if desc else ""
        if "error" not in title.lower():
            continue
        results.append({
            "title": title,
            "description": desc_text,
            "source": "betterstack.com"
        })
    return results
import importlib
import crawlers.betterstack3 as betterstack3

importlib.reload(betterstack3)
print("crawl 함수 있음?", hasattr(betterstack3, "crawl"))
import requests
from bs4 import BeautifulSoup

url = "https://pokharamun.gov.np/notices"
html = requests.get(url).text
soup = BeautifulSoup(html, "html.parser")

notices = soup.select(".notice-title")
for n in notices:
    print(n.text)

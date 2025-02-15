import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def http_get(url):
    # HTTP GET 요청
    headers = {
        "User-Agent": "junghae2017@gmail.com"
    }
    response = requests.get(url, headers=headers)
    return response


def crowl(name):
    print("한경 뉴스 수집중...")
    news_dict = {}
    # 한경 뉴스 검색 URL
    url = f"https://search.hankyung.com/search/news?query={quote(name)}&sort=DATE%2FDESC%2CRANK%2FDESC&period=ALL&area=title&exact=&include=&except="

    response = http_get(url)

    # 요청 성공 여부 확인
    if response.status_code == 200:
        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')

        # 뉴스 제목 및 링크 요소 선택
        news_items = soup.select("#content > div.left_cont > div > div.section.hk_news > div > ul > li > div > a")

        # 각 뉴스에서 제목과 링크 추출
        for item,num in zip(news_items,range(len(news_items))):
            title_element = item.select_one("em.tit")
            link = item.get('href')

            if title_element and link:
                title = title_element.get_text(strip=True)

                # 각 뉴스 링크에 대한 요청을 보냄
                article_response = http_get(link)

                if article_response.status_code == 200:
                    # 새로운 페이지에서 본문 내용 추출
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')
                    contents = article_soup.select_one("#articletxt")

                    if contents:
                        content_text = contents.get_text(strip=True)
                        news_dict[title] = content_text
                    else:
                        print("본문을 찾을 수 없습니다.\n")
                else:
                    print(f"뉴스 페이지에 접속할 수 없습니다. 상태 코드: {article_response.status_code}\n")

    else:
        print("한경 뉴스에 접속할 수 없습니다. 상태 코드:", response.status_code)

    return news_dict




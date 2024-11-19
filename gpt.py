import base64
import requests
from openai import OpenAI

def base64_image(name):
    # Function to encode the imageA
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Path to your image
    image_path = f"img/chart_{name}.png"

    # Getting the base64 string
    base64_image = encode_image(image_path)
    return base64_image


class CompanyAnalyzer:

    def __init__(self, news_dict, name, n):
        self._news_dict = news_dict
        self._titles = news_dict.keys()
        self._name = name
        self.analysis_result = self.get_n(n)

    def get_n(self, n):

        top_titles = Prompt(
            f"내가지금부터 너가 분석해야할 주식인 {self._name}종목의 최신 뉴스 제목을 줄거야."
            f"너가 판단하기에 너가 투자하기전에 가장 중요해보이는 뉴스 제목 {n}개를 뽑아줘."
            f"너가 선택한 뉴스제목 {n}개를 그대로 문자열로 출력하고 각각 뉴스제목 사이 줄바꿈해줘. 매우 중요해 너 출력값들은 /n(줄바꿈 한개) 으로만 구분됙 해야해. 너가 입력받은 뉴스제목 문자열을 하나도 바꾸지 말고 그대로 출력해야해."
            f"예를 들어 [김남길·서경덕, 광복절 맞아 '조선민족대동단' 알린다] 이 대괄호 안의 문자열이 뉴스제목이면 너도 김남길·서경덕, 광복절 맞아 '조선민족대동단' 알린다 를 그대로 출력해줘") \
            .text(str('\n'.join(self._titles))) \
            .get_response() \
            .split('\n')
        return self.analysis_news(top_titles)

    def analysis_news(self,top_titles):

        content = ''

        for title in top_titles:
            try:
                title = title.strip()
                content += f"[{title}:{self._news_dict[title]}]"
            except :
                pass

        opinion = Prompt(
            """
            당신은 전설적인 주식 분석 전문가입니다. 사용자가 주식 차트와 중요한 관련 뉴스 데이터를 제공하면, 
            그 차트와 뉴스를 철저히 분석하여 환경분석,시장상황,최근 이슈,사람들의 심리적 상태,기술적 지표, 트렌드, 그리고 리스크를 고려한 종합적인 
            매매 전략을 제시해야 합니다. 당신은 주식이 확실한 상승 방향성을 보일 때만 매수를 추천해야합니다.
            현재 시점에서 매수, 매도, 관망 중 하나의 행동을 추천해 주십시오.
            """).image(base64_image(self._name)).text(content).get_response()
        return opinion




class Prompt:
    def __init__(self, system):
        self._system = system
        self.content = []

    def text(self, text):
        if not isinstance(text, str):
            raise TypeError()

        self.content.append({
            "type": "text",
            "text": text
        })
        return self

    def image(self, image):
        if not isinstance(image, str):
            raise TypeError()

        self.content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image}"
            }
        })
        return self

    def get_response(self):

        client = OpenAI(
            api_key="your_api_key"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": self._system
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": self.content
                }
            ]
        )

        # try:

        text = response.choices[0].message.content
        return text
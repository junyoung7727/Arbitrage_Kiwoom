# 1. 데이터 수집 및 저장

from MySQL import SqlConnect

# 2. 차트 시각화
import Visualizer
# 3. 뉴스 수집
import crowler
import gpt
print("------------------------------------------------------------------------------------")
stock_name = input('종목을 입력해주세요')
Visualizer.Setting(stock_name)
news_dict = crowler.crowl(stock_name)
text = gpt.CompanyAnalyzer(news_dict,stock_name,3)
print(text.analysis_result)



# text, opinion = gpt.analysis_news(news_dict,stock_name)
# print(text)
# if opinion == '0':
#     cj_order = kiwoom.send_order("buy", "0012", 0, "001040", 1, 123000, 0, order_no="")
# elif opinion == '1':
#     print("Cj 판매")
# elif opinion == '2':
#     print("cj 관망중")
from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
import math

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()
        self.tr_event_loop = QEventLoop()
        self.tr_data = []
        self.spot_prices = {}
        self.future_prices = {}
        self.spot_future_pairs = {}
        self.expiration_dates = {}
        self.dividend_yields = {}
        self.spot_future_match = {}
        self.get_future_interest_rate('005930')

        # Initialize arbitrage parameters
        self.transaction_cost = 0   # Transaction cost per trade (set to 0 for simplicity)
        self.quantity = 1           # Quantity of shares/contracts to trade

        # Get spot-future pairs
        print('starting kiwoom')
        self.spot_future_pairs = self.get_all_futures_info()
        print(self.spot_future_match)
        # Get dividend yields for all spot codes

        spot_codes = list(self.spot_future_pairs.keys())
        future_codes = [info['future_code'] for info in self.spot_future_pairs.values()]

        print(len(future_codes), len(spot_codes))
        self.register_real_time_data_spot(spot_codes)
        self.register_real_time_data_future(future_codes)

    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.OnReceiveMsg.connect(self._on_receive_msg)
        self.OnReceiveChejanData.connect(self._on_receive_chejan)
        self.OnReceiveRealData.connect(self._receive_real_data)

    def _login_slot(self, err_code):
        if err_code == 0:
            print("Connected!")
        else:
            print("Not Connected...")
        self.login_event_loop.exit()

    def _comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def get_account_number(self):
        account_list = self.dynamicCall("GetLoginInfo(QString)", "ACCLIST")
        account_number = account_list.split(';')[0]
        print(f"계좌번호: {account_number}")
        return account_number

    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        print(f"OnReceiveMsg - Screen: {screen_no}, RQName: {rqname}, TRCode: {trcode}, Message: {msg}")

    def _on_receive_chejan(self, gubun, item_cnt, fid_list):
        print(f"OnReceiveChejan - 구분: {gubun}, 아이템개수: {item_cnt}, FID리스트: {fid_list}")
        for fid in fid_list.split(";"):
            data = self.dynamicCall("GetChejanData(int)", int(fid))
            print(f"FID {fid}: {data}")

    def get_comm_data(self, trcode, record, index, item):
        return self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, record, index, item)

    def on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        if rqname == "opt50001_req_days_remaining":
            expiration_date = self.get_comm_data(trcode, rqname, 0, "잔존일수").strip()
            self.expiration_dates[self.current_future_code] = int(expiration_date)

        elif rqname == "opt50001_future_interest_rate":
            self.interest_rate = self.get_comm_data(trcode, rqname, 0, "이자율").strip()

        elif rqname == "opt10001_req_divid":
            # 주당 배당금 가져오기
            dividend = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "배당수익률").strip()
            if dividend:
                dividend_yield = float(dividend)
            else:
                dividend_yield = 0.0

            # 주식 코드 가져오기
            code = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "종목코드").strip()

            # 배당수익률 저장
            self.dividend_yields[code] = dividend_yield / 100  # 퍼센트 값을 소수로 변환
            print(self.dividend_yields[code])

        self.tr_event_loop.exit()

    def _receive_real_data(self, s_code, real_type, real_data):
        print(f"Received real data: s_code={s_code}, real_type={real_type}")
        if real_type == "주식체결":
            current_price = abs(int(self.dynamicCall("GetCommRealData(QString, int)", s_code, 10).strip()))
            bid_price = abs(int(self.dynamicCall("GetCommRealData(QString, int)", s_code, 27).strip()))
            ask_price = abs(int(self.dynamicCall("GetCommRealData(QString, int)", s_code, 28).strip()))
            self.spot_prices[s_code] = {'bid': bid_price, 'ask': ask_price, 'current': current_price}
            # Check arbitrage opportunity
            #print(f"checking {s_code}")
            #self.check_arbitrage_opportunity(s_code)

        elif real_type == '주식선물호가잔량':

            #current_price = abs(int(self.dynamicCall("GetCommRealData(QString, int)", s_code, 10).strip()))  # 현재가
            ask = abs(int(self.dynamicCall("GetCommRealData(QString, int)", s_code, 28).strip())) # 최유리 매도 호가
            bid = abs(int(self.dynamicCall("GetCommRealData(QString, int)", s_code, 27).strip()))  # 최유리 매수 호가

            self.future_prices[s_code] = {'bid': bid, 'ask': ask}
            #print(f"종목 코드: {s_code}, 선물 시세 데이터: {self.future_prices[s_code]}")
            self.check_arbitrage_opportunity(s_code)

    def calculate_theoretical_future_price(self, spot_price, r, q, T):
        return spot_price * math.exp((r - q) * T)

    def get_future_interest_rate(self, future_code):
        self.current_future_code = future_code
        #self.dynamicCall("SetInputValue(QString, QString)", "종목코드", future_code)
        #self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt50001", "opt50001_future_interest_rate", 0,"5001")
        #self.tr_event_loop = QEventLoop()
        #self.tr_event_loop.exec_()
        return 0.035 #self.interest_rate

    def get_future_expiration_date(self, future_code):
        if future_code in self.expiration_dates:
            return self.expiration_dates[future_code]
        self.current_future_code = future_code
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", future_code)
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt50001_req_days_remaining", "opt50001", 0, "5002")
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()
        return self.expiration_dates.get(future_code, None)

    def get_dividend_yield(self, code):
        """
        주식 종목의 배당수익률을 TR로 가져오는 함수.
        Kiwoom API의 opt10001 TR을 사용하여 배당수익률을 가져옴.
        """
        if code in self.dividend_yields:
            return self.dividend_yields[code]
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10001_req_divid", "opt10001", 0, "2000")
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()
        return self.dividend_yields.get(code, 0.0)

    def check_arbitrage_opportunity(self, code):
        try:
            #print(f"Checking arbitrage opportunity for: {code}")

            # Find matching pair for the given code (either spot or future)
            if code in self.spot_future_pairs:
                spot_code = code
                matching_pair = self.spot_future_pairs[spot_code]
                future_code = matching_pair['future_code']
            elif code in self.spot_future_match:
                future_code = code
                spot_code = self.spot_future_match[future_code]
                matching_pair = self.spot_future_pairs[spot_code]
            else:
                print(f"No matching pair found for code: {code}")
                return

            # Check if both spot and future prices are available
            spot_price_info = self.spot_prices.get(spot_code)
            future_price_info = self.future_prices.get(future_code)

            if spot_price_info is not None and future_price_info is not None:
                self.execute_arbitrage(matching_pair, spot_price_info, future_price_info, spot_code, future_code)
            else:
                print(f"Spot or future prices not available for {code}")
                return
        except Exception as e:
            print(f'error: {e}')

    def execute_arbitrage(self, pair, spot_price_info, future_price_info, spot_code, future_code):
        spot_bid = spot_price_info['bid']
        spot_ask = spot_price_info['ask']
        #spot_current = spot_price_info['current']

        future_bid = future_price_info['bid']
        future_ask = future_price_info['ask']
        #future_current = future_price_info['current']

        # Get or calculate expiration date
        expiration_date = pair.get('expiration_date')
        if not expiration_date:
            expiration_date = self.get_future_expiration_date(future_code)
            pair['expiration_date'] = expiration_date

        days_to_expiration = self.get_future_expiration_date(future_code)
        T = days_to_expiration / 365.0

        # Get dividend yield
        dividend_yield = self.get_dividend_yield(spot_code)

        risk_free_rate = self.get_future_interest_rate(future_code)

        # Calculate theoretical future prices
        theoretical_buy_price = self.calculate_theoretical_future_price(spot_ask, risk_free_rate, dividend_yield, T)
        theoretical_sell_price = self.calculate_theoretical_future_price(spot_bid, risk_free_rate, dividend_yield, T)

        # Calculate arbitrage opportunities
        buy_arbitrage = future_ask - theoretical_buy_price  # 매수차익 = 선물매수가 - 선물매수이론가
        sell_arbitrage = theoretical_sell_price - future_bid  # 매도차익 = 선물매도이론가 - 선물매도가

        #print(f"종목코드: {spot_code}, 매수차익: {buy_arbitrage}, 매도차익: {sell_arbitrage}")

        # Define thresholds for executing arbitrage
        threshold = 0  # Adjust this value based on transaction costs and desired profit

        # Check for arbitrage opportunities
        if buy_arbitrage > threshold:
            print(f"매수차익거래 기회 발견: 선물 매수가({future_ask}) - 선물매수이론가({theoretical_buy_price}) = {buy_arbitrage}")
            # Execute buy arbitrage: Buy spot at ask price, sell future at bid price
            self.place_order('buy_spot', spot_code, spot_ask)
            self.place_order('sell_future', future_code, future_bid)
        elif sell_arbitrage > threshold:
            print(f"매도차익거래 기회 발견: 선물매도이론가({theoretical_sell_price}) - 선물 매도가({future_bid}) = {sell_arbitrage}")
            # Execute sell arbitrage: Sell spot at bid price, buy future at ask price
            self.place_order('sell_spot', spot_code, spot_bid)
            self.place_order('buy_future', future_code, future_ask)
        else:
            pass  # No arbitrage opportunity

    def place_order(self, order_type, code, price):
        quantity = self.quantity
        if order_type == 'buy_spot':
            self.send_order('buy', code, price, quantity)
        elif order_type == 'sell_spot':
            self.send_order('sell', code, price, quantity)
        elif order_type == 'buy_future':
            self.send_order_future('buy', code, price, quantity)
        elif order_type == 'sell_future':
            self.send_order_future('sell', code, price, quantity)

    def send_order(self, order_type, code, price, quantity):
        rqname = "자동매매주문"
        screen_no = "6000"
        acc_no = self.account_number
        order_type_dict = {'buy': 1, 'sell': 2}
        nOrderType = order_type_dict[order_type]
        hoga = "00"  # 지정가
        order_no = ""
        res = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                               [rqname, screen_no, acc_no, nOrderType, code, quantity, price, hoga, order_no])
        if res == 0:
            print(f"주식 주문 성공: {order_type} {code} 수량:{quantity} 가격:{price}")
        else:
            print(f"주식 주문 실패: {order_type} {code} 수량:{quantity} 가격:{price} 에러코드:{res}")

    def send_order_future(self, order_type, code, price, quantity):
        rqname = "자동매매선물주문"
        screen_no = "7000"
        acc_no = self.account_number
        order_type_dict = {'buy': 1, 'sell': 2}
        nOrderType = order_type_dict[order_type]
        hoga = "00"  # 지정가
        order_no = ""
        res = self.dynamicCall("SendOrderFO(QString, QString, QString, int, QString, int, QString, QString, QString)",
                               [rqname, screen_no, acc_no, nOrderType, code, quantity, str(price), order_no, hoga])
        if res == 0:
            print(f"선물 주문 성공: {order_type} {code} 수량:{quantity} 가격:{price}")
        else:
            print(f"선물 주문 실패: {order_type} {code} 수량:{quantity} 가격:{price} 에러코드:{res}")

    def register_real_time_data_spot(self, codes):
        fid_list = "10;27;28"  # 현재가;매수최우선호가;매도최우선호가
        real_type = "0"  # 0: 추가 등록
        screen_no = "6001"
        codes_string = ';'.join(codes)
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_no, '005930', fid_list, real_type)
        print(f"실시간 데이터 등록 완료(주식): {codes_string}")

    def register_real_time_data_future(self, codes):
        fid_list = "10;15;13;16;20;27;28;31;32;33"  # 현재가;매수최우선호가;매도최우선호가
        real_type = "0"  # 0: 추가 등록
        screen_no = "6002"
        codes_string = ';'.join(codes[:10])
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_no, '111VB000', fid_list, real_type)
        print(f"실시간 데이터 등록 완료(선물): {codes_string}")


    def get_sfo_basis_asset_list(self):
        # 주식선물 기초자산 코드 리스트 가져오기
        codes = self.dynamicCall("GetSFOBasisAssetList()")
        code_list = codes.strip().split(';') if codes else []
        return code_list

    def get_futures_code_list(self, base_asset_code):
        # 기초자산 코드에 해당하는 선물 종목 리스트 가져오기
        codes = self.dynamicCall("GetSFutureList(QString)", base_asset_code)
        code_list = codes.strip().split('|') if codes else []
        return code_list

    def get_all_futures_info(self):
        # 모든 개별주식선물 종목 정보 가져오기
        basis_asset_list = self.get_sfo_basis_asset_list()
        futures_info = {}
        spot_info = []
        for item in basis_asset_list:
            if not item:
                continue
            code_name_pair = item.strip().split('|')
            if len(code_name_pair) != 2:
                continue
            spot_code = code_name_pair[0]
            spot_name = code_name_pair[1].strip()
            spot_info.append((spot_code, spot_name))

        # 선물 종목 리스트 가져오기
        all_future_code = self.get_futures_code_list('')
        # 1. '|'로 항목을 나누기
        items = all_future_code

        # 2. 각 항목을 '^'로 나눠서 종목 코드와 상품명 분리
        for item in items:
            parts = item.split('^')
            if len(parts) >= 2:
                future_code = parts[0].strip()  # 종목 코드
                product = parts[1].strip()  # 상품명

                # 선물 종목인 경우 (상품명에 'F'가 포함된 경우)
                if 'F' in product:
                    # 'F' 이전의 기초자산 이름을 추출
                    asset_name = product.split('F')[0].strip()

                    # spot_info와 매칭되는 기초자산 찾기
                    found = False  # 매칭이 되었는지 확인하는 플래그
                    for spot_code, spot_name in spot_info:
                        # 기초자산 이름이 일치하는지 확인 (대소문자 무시하고 공백 제거)
                        if spot_name.lower() == asset_name.lower():
                            # futures_info에 추가
                            futures_info[spot_code[3:9]] = {
                                'spot_name': spot_name,
                                'future_code': future_code,
                                'interest_rates': 0.035  # 기본 이자율 설정
                            }
                            self.spot_future_match[future_code] = spot_code
                            found = True  # 매칭되었음을 표시
                            break  # 매칭이 되었으면 더 이상 asset_pair 반복문을 진행할 필요 없음

                    # 매칭이 되면 다음 item으로 넘어감
                    if found:
                        continue
        # 최종적으로 futures_info 반환
        print(futures_info)
        return futures_info


class KiwoomApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.kiwoom = Kiwoom()  # Kiwoom API 클래스 연결

        #Timer to update the table periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)
        self.timer.start(5000)  # 5초마다 업데이트

    def init_ui(self):
        self.setWindowTitle("Arbitrage Information")
        self.setGeometry(100, 100, 1200, 600)

        # Create a QTableWidget to display the data
        self.table_widget = QTableWidget(self)
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(14)
        self.table_widget.setHorizontalHeaderLabels([
            "종목명", "현물매도호가", "현물매수호가", "주식선물매도가",
            "주식선물매수가", "이자율", "배당", "잔존일수(영업일)",
            "주식선물매도이론가", "주식선물매수이론가", "선물매도차익",
            "선물매수차익", "매도차익수익률", "매수차익수익률"
        ])
        self.setCentralWidget(self.table_widget)

    def update_table(self):
        try:
            # 테이블 행 수 설정
            self.table_widget.setRowCount(len(self.kiwoom.spot_future_pairs))
            #print(self.kiwoom.spot_future_pairs)
            for row, (spot_code, pair) in enumerate(self.kiwoom.spot_future_pairs.items()):
                future_code = pair['future_code']

                # 가격 정보 가져오기 (현물 및 선물)
                spot_price_info = self.kiwoom.spot_prices.get(spot_code, {'bid': 0, 'ask': 0, 'current': 0})
                future_price_info = self.kiwoom.future_prices.get(future_code, {'bid': 0, 'ask': 0, 'current': 0})

                # days_to_expiration이 문자열일 경우 숫자로 변환
                days_to_expiration = self.kiwoom.get_future_expiration_date(future_code)
                if isinstance(days_to_expiration, str):
                    try:
                        days_to_expiration = int(days_to_expiration)
                    except ValueError:
                        days_to_expiration = 0  # 변환 실패 시 기본값 0으로 설정

                # 배당수익률 가져오기
                dividend_yield = self.kiwoom.dividend_yields.get(spot_code, 0.0)

                # 무위험 이자율 가져오기
                risk_free_rate = self.kiwoom.get_future_interest_rate(future_code)

                # 이론 선물 가격 계산
                T = days_to_expiration / 365.0
                theoretical_sell_price = self.kiwoom.calculate_theoretical_future_price(
                    spot_price_info['ask'], risk_free_rate, dividend_yield, T
                )
                theoretical_buy_price = self.kiwoom.calculate_theoretical_future_price(
                    spot_price_info['bid'], risk_free_rate, dividend_yield, T
                )

                # 차익 계산
                sell_arbitrage = theoretical_sell_price - future_price_info['bid']
                buy_arbitrage = future_price_info['ask'] - theoretical_buy_price

                # 값 출력 (디버깅용)
                """
                print(f"종목명: {pair['spot_name']}")
                print(f"현물매도호가: {spot_price_info['ask']}, 현물매수호가: {spot_price_info['bid']}")
                print(f"선물매도호가: {future_price_info['ask']}, 선물매수호가: {future_price_info['bid']}")
                print(f"이자율: {risk_free_rate}, 배당수익률: {dividend_yield}")
                print(f"잔존일수: {days_to_expiration}")
                print(f"선물매도차익: {sell_arbitrage}, 선물매수차익: {buy_arbitrage}")
                """

                # 테이블에 값 넣기
                self.table_widget.setItem(row, 0, QTableWidgetItem(pair['spot_name']))
                self.table_widget.setItem(row, 1, QTableWidgetItem(str(spot_price_info['ask'])))
                self.table_widget.setItem(row, 2, QTableWidgetItem(str(spot_price_info['bid'])))
                self.table_widget.setItem(row, 3, QTableWidgetItem(str(future_price_info['ask'])))
                self.table_widget.setItem(row, 4, QTableWidgetItem(str(future_price_info['bid'])))
                self.table_widget.setItem(row, 5, QTableWidgetItem(str(risk_free_rate)))
                self.table_widget.setItem(row, 6, QTableWidgetItem(str(dividend_yield)))
                self.table_widget.setItem(row, 7, QTableWidgetItem(str(days_to_expiration)))
                self.table_widget.setItem(row, 8, QTableWidgetItem(str(theoretical_sell_price)))
                self.table_widget.setItem(row, 9, QTableWidgetItem(str(theoretical_buy_price)))
                self.table_widget.setItem(row, 10, QTableWidgetItem(str(sell_arbitrage)))
                self.table_widget.setItem(row, 11, QTableWidgetItem(str(buy_arbitrage)))

        except Exception as e:
            print(f"Error in update_table: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KiwoomApp()
    window.show()
    sys.exit(app.exec_())

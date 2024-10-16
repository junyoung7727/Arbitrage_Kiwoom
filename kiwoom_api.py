from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
import time
import pandas as pd
import fid
from fid import FID_CODES, get_fid
from datetime import datetime
# 필요한 모듈들을 가져옵니다.

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()
        self.tr_event_loop = QEventLoop()
        self.universe_realtime_transaction_info = []
        self.tr_data = None

    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.OnReceiveMsg.connect(self._on_receive_msg)
        self.OnReceiveChejanData.connect(self._on_receive_chejan)
        self.OnReceiveRealData.connect(self._receive_real_data)  # 이벤트 연결 확인

    def set_real_reg(self, str_screen_no, str_code_list, str_fid_list, str_opt_type):
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", str_screen_no, str_code_list, str_fid_list,
                         str_opt_type)
        time.sleep(1)

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

    def get_code_list_stock_market(self, market_type):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_type)
        code_list = code_list.split(';')[:-1]
        return code_list

    def get_code_name(self, code):
        name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return name

    def _receive_real_data(self, s_code, real_type, real_data):
        if real_type == "주식시세":
            current_price = self.dynamicCall("GetCommRealData(QString, int)", s_code, 10)
            current_price = abs(int(current_price.strip()))
            print(f"[현물] 종목코드: {s_code}, 실시간 현재가: {current_price}")
            # 선물 종목과 매칭하여 차익거래 로직 구현 가능

        elif real_type == "선물시세":
            current_price = self.dynamicCall("GetCommRealData(QString, int)", s_code, 10)
            current_price = abs(int(current_price.strip()))
            print(f"[선물] 종목코드: {s_code}, 실시간 현재가: {current_price}")
            # 현물 종목과 매칭하여 차익거래 로직 구현 가능

    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        print(f"OnReceiveMsg - Screen: {screen_no}, RQName: {rqname}, TRCode: {trcode}, Message: {msg}")

    def _on_receive_chejan(self, gubun, cnt, fid_list):
        print(f"OnReceiveChejan - 구분: {gubun}, 개수: {cnt}, FID리스트: {fid_list}")

        for fid in fid_list.split(";"):
            code = self.dynamicCall("GetChejanData(int)", "9001")[1:]
            data = self.dynamicCall("GetChejanData(int)", fid).lstrip("+").lstrip("-")
            if data.isdigit():
                data = int(data)
            name = FID_CODES.get(fid, "Unknown FID")
            print(f'{name} : {data}')

    def get_comm_data(self, trcode, record, index, item):
        return self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, record, index, item)

    def on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        print(f"OnReceiveTrData - Screen: {screen_no}, RQName: {rqname}, TRCode: {trcode}, Next: {next}")
        cnt = self.dynamicCall("GetRepeatCnt(QString,QString)", trcode, rqname)

        if next == "2":
            self.isnext = True  # 조회할 페이지가 남으면 2
        else:
            self.isnext = False

        if rqname == "opt10081":
            total = []
            for i in range(cnt):
                date = self.get_comm_data(trcode, rqname, i, "일자").strip()
                open_price = int(self.get_comm_data(trcode, rqname, i, "시가").strip())
                high = int(self.get_comm_data(trcode, rqname, i, "고가").strip())
                low = int(self.get_comm_data(trcode, rqname, i, "저가").strip())
                close = int(self.get_comm_data(trcode, rqname, i, "현재가").strip())
                volume = int(self.get_comm_data(trcode, rqname, i, "거래량").strip())
                total.append([date, open_price, high, low, close, volume])
            self.tr_data = total

        elif rqname == "opw00001":
            deposit = self.dynamicCall("GetCommData(QString, QString, int,QString)", trcode, rqname, 0, "주문가능금액")
            self.tr_data = int(deposit)

        elif rqname == "opw00018":
            balance_data = []
            for i in range(cnt):
                code = self.get_comm_data(trcode, rqname, i, "종목번호").strip()
                code = code[1:]  # 종목번호 앞에 있는 'A' 제거
                name = self.get_comm_data(trcode, rqname, i, "종목명").strip()
                quantity = int(self.get_comm_data(trcode, rqname, i, "보유수량").strip())
                purchase_price = int(self.get_comm_data(trcode, rqname, i, "매입가").strip())
                current_price = int(self.get_comm_data(trcode, rqname, i, "현재가").strip())
                eval_profit_loss = int(self.get_comm_data(trcode, rqname, i, "평가손익").strip())
                yield_ratio = float(self.get_comm_data(trcode, rqname, i, "수익률(%)").strip())

                balance_data.append([code, name, quantity, purchase_price, current_price, eval_profit_loss, yield_ratio])

            self.tr_data = balance_data

        elif rqname == "opt10001_req":
            price = self.dynamicCall("GetCommData(QString, QString, QString, int, QString)", trcode, "", rqname, 0,
                                     "현재가")
            self.current_price = abs(int(price.strip()))
            self.tr_event_loop.exit()

        elif rqname == "opt50001_req_bid_ask":
            self.bid_price = abs(
                int(self.dynamicCall("GetCommData(QString, QString, QString, int, QString)", trcode, "", rqname, 0,
                                     "매수최우선호가").strip()))
            self.ask_price = abs(
                int(self.dynamicCall("GetCommData(QString, QString, QString, int, QString)", trcode, "", rqname, 0,
                                     "매도최우선호가").strip()))
            self.tr_event_loop.exit()

        elif rqname == "opt10004_req":
            self.spot_bid_price = abs(
                int(self.dynamicCall("GetCommData(QString, QString, QString, int, QString)", trcode, "", rqname, 0,
                                     "매수최우선호가").strip()))
            self.spot_ask_price = abs(
                int(self.dynamicCall("GetCommData(QString, QString, QString, int, QString)", trcode, "", rqname, 0,
                                     "매도최우선호가").strip()))
            self.tr_event_loop.exit()

        elif rqname == "get_sfuture_list":
            codes = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, "", rqname, 0,
                                     "종목코드")
            self.tr_data = codes.split(';')

        elif rqname == "opt50001_req_days_remaining":
            self.expiration_date = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0,
                                                    "잔존일수")
            self.expiration_date = self.expiration_date.strip()

        elif rqname == "opt50001_req_price":
            price = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "현재가")
            self.current_price = abs(int(price.strip()))

        # TR 요청에 대한 이벤트 루프 종료
        self.tr_event_loop.exit()


    def get_sfo_basis_asset_list(self):
        # 주식선물 기초자산 코드 리스트 가져오기
        codes = self.dynamicCall("GetSFOBasisAssetList()")
        code_list = codes.strip().split(';') if codes else []
        return code_list

    def get_futures_code_list(self, base_asset_code):
        # 기초자산 코드에 해당하는 선물 종목 리스트 가져오기
        codes = self.dynamicCall("GetSFutureList(QString)", base_asset_code)
        code_list = codes.strip().split('^') if codes else []
        return codes

    def get_all_futures_info(self):
        # 모든 개별주식선물 종목 정보 가져오기
        basis_asset_list = self.get_sfo_basis_asset_list()
        futures_info = []

        for item in basis_asset_list:
            if not item:
                continue
            code_name_pair = item.strip().split('|')
            if len(code_name_pair) != 2:
                continue
            base_asset_code, base_asset_name = code_name_pair
            # 선물 종목 리스트 가져오기
            all_future_code = self.get_futures_code_list('')
            # 1. '|'로 항목을 나누기
            items = all_future_code.split('|')

            # 2. 각 항목을 '^'로 나눠서 종목 코드와 상품명 분리
            for item in items:
                parts = item.split('^')
                if len(parts) >= 2:
                    code = parts[0].strip()  # 종목 코드
                    product = parts[1].strip()  # 상품명

                if 'F' in product:
                    futures_info.append({
                        'base_asset_code': base_asset_code,
                        'base_asset_name': base_asset_name,
                        'future_code': code
                    })
        return futures_info

    def get_future_expiration_date(self, future_code):
        # 선물 종목의 만기일 가져오기
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", future_code)
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt50001_req_days_remaining", "opt50001", 0, "1001")
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()
        return self.expiration_date

    def get_current_price(self, code, code_type):
        # 현재가 가져오기 (code_type: 'spot' 또는 'future')
        if code_type == 'spot':
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10001_req", "opt10001", 0, "1002")
        elif code_type == 'future':
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt50001_req_price", "opt50001", 0, "1003")
        self.tr_event_loop = QEventLoop()

        self.tr_event_loop.exec_()
        return self.current_price

    def register_real_time_data(self, codes):
        # 실시간 데이터 등록
        fid_list = "10"  # 현재가
        real_type = 0  # 0: 추가 등록
        screen_no = "2000"
        codes_string = ';'.join(codes)
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_no, codes_string, fid_list,
                         str(real_type))
        print(f"실시간 데이터 등록 완료: {codes_string}")

    def calculate_days_to_expiration(self, expiration_date):
        # 만기일까지 남은 일수 계산
        expiration_datetime = datetime.strptime(expiration_date, '%Y%m%d')
        today = datetime.today()
        days_to_expiration = (expiration_datetime - today).days
        return days_to_expiration

if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()


    futures_info = kiwoom.get_all_futures_info()
    print(futures_info)

    app.exec_()

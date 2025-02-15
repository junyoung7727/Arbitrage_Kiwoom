import numpy as np
from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
import time
import pandas as pd
import MySQL
import os
import talib
sys.path.insert(0, os.path.abspath("C:\\Users\\jungh\\PycharmProjects\\Quant_Model"))
from MySQL import SqlConnect

sql = SqlConnect()


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()
        self.tr_event_loop = QEventLoop()
        self.universe_realtime_transaction_info = []

    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.OnReceiveMsg.connect(self._on_receive_msg)
        self.OnReceiveRealData.connect(self._on_receive_real_data)

    def set_real_reg(self, str_screen_no, str_code_list, str_fid_list, str_opt_type):
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", str_screen_no, str_code_list, str_fid_list,str_opt_type)
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
        account_list = self.dynamicCall("GetLoginInfo(QString)","ACCLIST")
        account_number = account_list.split(';')[0]
        print(account_number)
        return account_number

    def get_code_name(self, code):
        name = self.dynamicCall("GetMasterCodeName(QString)",code)
        return name
    def _on_receive_real_data(self, s_code, real_type, real_data):
        if real_type == "장시작시간":
            pass
        elif real_type == "주식체결":
            pass

    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        print(screen_no, rqname, trcode, msg)

    def get_code_list_stock_market(self, market_type):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_type)
        code_list = code_list.split(';')[:-1]
        return code_list

    def on_receive_tr_data(self,screen_no,rqname,trcode,record_name,next,v1,v2,v3,v4):
        print(screen_no,rqname,trcode,record_name,next)
        cnt = self.dynamicCall("GetRepeatCnt(QString,QString)",trcode,rqname)

        if next == "2":
            self.isnext = True #조회할 페이지가 남으면 2
        else:
            self.isnext = False

        if rqname == "opt10081":
            total = []
            for i in range(cnt):
                date = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "일자").strip()
                open = int(
                    self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "시가").strip())
                high = int(
                    self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "고가").strip())
                low = int(
                    self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "저가").strip())
                close = int(
                    self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가").strip())
                volume = int(
                    self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "거래량").strip())
                total.append([date, open, high, low, close, volume])
            self.tr_data = total
            time.sleep(1)

            self.tr_event_loop.exit()

    def get_kroea_stock_list(self):
        # 코스피 주식 코드 가져오기
        kospi_list = self.get_code_list_stock_market("0")
        # 코스닥 주식 코드 가져오기
        kosdaq_list = self.get_code_list_stock_market("10")

        return kospi_list, kosdaq_list

    def get_price(self, code):
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081", "opt10081", 0, "0020")
        self.tr_event_loop.exec_()

        total = self.tr_data

        while self.isnext:
            time.sleep(0.4)
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081", "opt10081", 2, "0020")
            self.tr_event_loop.exec_()
            total += self.tr_data
            time.sleep(0.1)


        df = pd.DataFrame(total, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df = df.drop_duplicates()
        df = df.sort_index()
        return df

    def collect_data_job(self):
        app = QApplication(sys.argv)
        kiwoom = Kiwoom()
        sql_connecter = MySQL.SqlConnect()

        kospi_list,kosdaq_list = kiwoom.get_kroea_stock_list()
        krx_code = kospi_list + kosdaq_list


        print(sql_connecter.update_status_table())
        while sql_connecter.update_status_table() == False:
            try:
                cnt = int(os.getenv('CRAWLING_COUNT', '0'))
                existing_table = sql_connecter.get_all_table_names()
                existing_table = [item.upper() for item in existing_table]
                krx_code = set(krx_code) - set(existing_table)
                print(len(krx_code))
                for code in krx_code:
                    print(cnt)
                    cnt += 1
                    time.sleep(0.5)
                    df = kiwoom.get_price(code)
                    print(f"Updating data for: {kiwoom.get_code_name(code)}")
                    sql_connecter.table_setting(df, code)

                    if cnt >= 200:
                        # Restart the application
                        print("Processed 30 items. Restarting application...")
                        os.environ['CRAWLING_COUNT'] = str(cnt)  # Set environment variable for next start
                        time.sleep(0.5)
                        os.execv(sys.executable, ['python'] + sys.argv)

            except Exception as e:
                print(f"An error occurred: {e}")
                # Optionally log the error or perform other error handling here
                time.sleep(5)  # Short delay before retrying

            app.exec_()

class PutExtraData():
    def technical(self, stock_code):

        # Load stock data (assumed to be stored in the database or fetched from an API)
        self.stock_data = sql.fetch_data(stock_code)  # Example function to get stock data
        print(self.stock_data)
        # Extract necessary columns from stock_data
        close = self.stock_data['close'].values.astype(float)
        high = self.stock_data['high'].values.astype(float)
        low = self.stock_data['low'].values.astype(float)
        volume = self.stock_data['volume'].values.astype(float)

        # Define the list of indicators to calculate (excluding the ones mentioned as excluded)
        indicator_list = ['MFI', 'ADI', 'OBV', 'CMF', 'FI', 'EOM', 'EMV', 'VPT', 'NVI', 'PVO', 'ATR',
            'BollingerBands', 'KeltnerChannel', 'SMA', 'EMA', 'MACD', 'ADX', 'Di+', 'Di-',
            'VortexIndicator', 'RSI', 'StochasticRSI', 'TSI', 'UltimateOscillator',
            'StochasticOscillator', 'WilliamsR', 'AwesomeOscillator', 'KAMA', 'ROC', 'PPO'
        ]

        # Iterate through the indicators and calculate them using talib

        for indicator in indicator_list:
            print(indicator)
            if indicator == 'ATR':
                atr = talib.ATR(high, low, close, timeperiod=14)
                self.add_indicator_to_db(stock_code, 'ATR', atr)

            elif indicator == 'RSI':
                rsi = talib.RSI(close, timeperiod=14)
                self.add_indicator_to_db(stock_code, 'RSI', rsi)

            elif indicator == 'MFI':
                mfi = talib.MFI(high, low, close, volume, timeperiod=14)
                self.add_indicator_to_db(stock_code, 'MFI', mfi)

            elif indicator == 'OBV':
                obv = talib.OBV(close, volume)
                self.add_indicator_to_db(stock_code, 'OBV', obv)

            elif indicator == 'MACD':
                macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                self.add_indicator_to_db(stock_code, 'MACD', macd)
                self.add_indicator_to_db(stock_code, 'MACD_signal', macdsignal)
                self.add_indicator_to_db(stock_code, 'MACD_hist', macdhist)


                # Continue with the other indicators...

    def add_indicator_to_db(self, stock_code, column_name, data):
        """Helper function to add calculated indicator data to the database."""
        # Ensure the column exists in the table, create it if not
        sql.add_table_column(stock_code, column_name, 'float')

        # Convert the data to a pandas Series if it's not already
        if not isinstance(data, pd.Series):
            data = pd.Series(data, index=self.stock_data['date'])

        # Ensure the index of the Series matches the 'date' format in the table
        if not pd.api.types.is_string_dtype(data.index):
            data.index = data.index.strftime('%Y%m%d')

        # Update the database with the new column data
        sql.batch_update_table_from_series(stock_code, column_name, data)


a = PutExtraData()
a.technical('005880')

from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtCore import QEventLoop
import sys

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._create_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()

    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)
        self.OnReceiveTrData.connect(self._on_receive_tr_data)

    def _login_slot(self, err_code):
        if err_code == 0:
            print("로그인 성공")
        else:
            print("로그인 실패")
        self.login_event_loop.exit()

    def _comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def request_hoga_data(self, code):
        """선물 호가 데이터를 요청"""
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        rqname = "선물호가요청"
        trcode = "opt50004"
        screen_no = "1000"
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, 0, screen_no)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, prev_next, unused1, unused2, unused3,
                            unused4):
        if rqname == "선물호가요청":
            # 매수/매도 호가 가져오기
            bid_prices = []
            ask_prices = []
            for i in range(1, 11):
                bid_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, "", 0,
                                             f"매수호가{i}").strip()
                ask_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, "", 0,
                                             f"매도호가{i}").strip()
                bid_prices.append(bid_price)
                ask_prices.append(ask_price)

            # 호가 출력
            print("매수 호가:", bid_prices)
            print("매도 호가:", ask_prices)
            self.tr_event_loop.exit()

class HogaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.kiwoom = Kiwoom()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("호가 데이터 요청")
        self.setGeometry(300, 300, 300, 200)

        # 버튼 및 텍스트 출력 영역
        self.button = QPushButton("호가 데이터 가져오기", self)
        self.button.clicked.connect(self.get_hoga_data)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.text_edit)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def get_hoga_data(self):
        """삼성전자 선물 호가 데이터 요청"""
        code = "1B3VC000"  # 삼성전자 선물 종목 코드 (정확한 코드를 사용해야 합니다)
        self.kiwoom.request_hoga_data(code)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    hoga_app = HogaApp()
    hoga_app.show()
    sys.exit(app.exec_())

import sys
import threading
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QTextEdit, QLineEdit, QHBoxLayout
from PyQt5.QtCore import pyqtSlot, Qt
from testcase import AlpacaAPI, OptionAnalyzer, OrderManager, ContractInfo

class TradingBotGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.bot_thread = None
        self.bot_running = False
        self.symbol = "GDX"  # Default symbol
        self.trading_bot = TradingBot([self.symbol], self.log_message)

    def initUI(self):
        layout = QVBoxLayout()

        # Horizontal layout for buttons and symbol input
        top_layout = QHBoxLayout()

        self.symbol_input = QLineEdit(self)
        self.symbol_input.setPlaceholderText("Enter Symbol (e.g., GDX)")
        self.symbol_input.setFixedWidth(150)
        top_layout.addWidget(self.symbol_input)

        self.start_button = QPushButton('Start', self)
        self.start_button.setFixedWidth(80)
        self.start_button.clicked.connect(self.start_bot)
        top_layout.addWidget(self.start_button)

        self.stop_button = QPushButton('Stop', self)
        self.stop_button.setFixedWidth(80)
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        top_layout.addWidget(self.stop_button)

        layout.addLayout(top_layout)

        self.status_label = QLabel('Status: Not Running', self)
        layout.addWidget(self.status_label)

        # Grid layout for the quadrants
        grid = QGridLayout()

        self.output_text_1 = QTextEdit(self)
        self.output_text_1.setReadOnly(True)
        self.output_text_1.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.output_text_1.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        grid.addWidget(self.output_text_1, 0, 0)

        self.output_text_2 = QTextEdit(self)
        self.output_text_2.setReadOnly(True)
        self.output_text_2.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.output_text_2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        grid.addWidget(self.output_text_2, 0, 1)

        self.output_text_3 = QTextEdit(self)
        self.output_text_3.setReadOnly(True)
        self.output_text_3.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.output_text_3.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        grid.addWidget(self.output_text_3, 1, 0)

        self.output_text_4 = QTextEdit(self)
        self.output_text_4.setReadOnly(True)
        self.output_text_4.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.output_text_4.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        grid.addWidget(self.output_text_4, 1, 1)

        layout.addLayout(grid)

        self.setLayout(layout)
        self.setWindowTitle('Trading Bot Control Panel')
        self.setGeometry(300, 300, 600, 400)

    @pyqtSlot()
    def start_bot(self):
        symbol = self.symbol_input.text().strip()
        if symbol:
            self.symbol = symbol.upper()
            self.trading_bot.symbols = [self.symbol]

        if not self.bot_running:
            self.bot_running = True
            self.status_label.setText(f'Status: Running for {self.symbol}')
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            # Start the bot in a separate thread
            self.bot_thread = threading.Thread(target=self.run_bot)
            self.bot_thread.start()

    @pyqtSlot()
    def stop_bot(self):
        if self.bot_running:
            self.bot_running = False
            self.status_label.setText('Status: Stopping...')
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def run_bot(self):
        try:
            self.trading_bot.run()
        except Exception as e:
            self.log_message(f"Error: {str(e)}", quadrant=1)
        finally:
            self.bot_running = False
            self.status_label.setText('Status: Not Running')
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def log_message(self, message, quadrant=1):
        if quadrant == 1:
            self.output_text_1.append(message)
            self.output_text_1.verticalScrollBar().setValue(self.output_text_1.verticalScrollBar().maximum())
        elif quadrant == 2:
            self.output_text_2.append(message)
            self.output_text_2.verticalScrollBar().setValue(self.output_text_2.verticalScrollBar().maximum())
        elif quadrant == 3:
            self.output_text_3.append(message)
            self.output_text_3.verticalScrollBar().setValue(self.output_text_3.verticalScrollBar().maximum())
        elif quadrant == 4:
            self.output_text_4.append(message)
            self.output_text_4.verticalScrollBar().setValue(self.output_text_4.verticalScrollBar().maximum())

class TradingBot:
    def __init__(self, symbols, log_func=None):
        self.alpaca_api = AlpacaAPI("PKRNHCONZVDSHM8HML9P", "2vFNJyqJ4AglXtDkmaoTwOp7RlDBJi8ttEa46iMC")
        self.contract_info = ContractInfo(self.alpaca_api)
        self.option_analyzer = OptionAnalyzer(self.alpaca_api, self.contract_info)
        self.order_manager = OrderManager(self.alpaca_api)
        self.symbols = symbols
        self.log_func = log_func

    def run(self):
        while True:
            for symbol in self.symbols:
                try:
                    # Analyze options for the current symbol
                    current_price = self.option_analyzer.analyze_options(symbol)

                    # Process each identified opportunity
                    for opportunity in self.option_analyzer.opportunities:
                        stock_symbol, option_symbol, formatted_symbol, bid_price, ask_price, current_price, profit = opportunity
                        
                        # Place order for the stock
                        order_response1 = self.order_manager.place_order(stock_symbol, 100, current_price)
                        # Log order response
                        if self.log_func:
                            self.log_func(f"Order response:\n{json.dumps(order_response1, indent=4)}", quadrant=1)

                        # Place order for the option
                        order_response = self.order_manager.place_order(option_symbol, 1, ask_price)
                        # Log order response
                        if self.log_func:
                            self.log_func(f"Order response:\n{json.dumps(order_response, indent=4)}", quadrant=2)

                        # Exercise the option after 30 seconds
                        threading.Thread(target=self.delayed_exercise, args=(option_symbol,)).start()
                        
                    # Log the found opportunities
                    if self.log_func:
                        for opportunity in self.option_analyzer.opportunities:
                            stock_symbol, option_symbol, formatted_symbol, bid_price, ask_price, current_price, profit = opportunity
                            self.log_func(f"Opportunity: {symbol} {formatted_symbol} Profit: {profit}", quadrant=3)
                except Exception as e:
                    if self.log_func:
                        self.log_func(f"Error processing {symbol}: {e}", quadrant=4)
                    continue

    def delayed_exercise(self, option_symbol):
        time.sleep(30)
        exercise_response = self.order_manager.exercise_option(option_symbol)
        if self.log_func:
            self.log_func(f"Exercise response:\n{json.dumps(exercise_response, indent=4)}", quadrant=4)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = TradingBotGUI()
    gui.show()
    sys.exit(app.exec_())

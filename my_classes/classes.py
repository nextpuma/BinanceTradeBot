from binance.client import Client
import sqlite3
import math


class Database:
    def __init__(self):
        """
        Connects to trade_bot.db database. Initializes cursor. If user_data and
        trade_data tables do not exist, they are created.
        """
        self.conn = sqlite3.connect('trade_bot.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS user_data (username TEXT, password TEXT,
                                                                api_key TEXT, secret_key TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS trade_data (datetime DATE, asset TEXT, 
                                                                 trade_size TEXT, trade_entry TEXT, 
                                                                 trade_exit TEXT, gain_percent TEXT)''')

    def create_user(self, username, password_hash, api_key, secret_key):
        """
        Stores user data into user_data table.

        :param username:
        :param password_hash:
        :param api_key:
        :param secret_key:
        :return:
        """
        self.c.execute('''INSERT INTO user_data VALUES(:username, :password, :api_key, :secret_key)''',
                       {'username': username, 'password': password_hash,
                        'api_key': api_key, 'secret_key': secret_key})
        self.conn.commit()

    def get_user_data(self, username):
        """
        Retrieves all data from specific username. Returns the first
        match found, since duplicate usernames cannot exist.

        :param username:
        :return:
        """
        self.c.execute('SELECT * FROM user_data WHERE username=?', (username,))
        return self.c.fetchone()

    def log_trade(self, datetime, asset, trade_size, entry_price, exit_price, gain):
        """
        Logs trade date into trade_data table.

        :param datetime:
        :param asset:
        :param trade_size:
        :param entry_price:
        :param exit_price:
        :param gain:
        :return:
        """
        self.c.execute('''INSERT INTO trade_data VALUES(:datetime, :asset, :trade_size, :trade_entry,
                        :trade_exit, :gain_percent)''', {'datetime': datetime, 'asset': asset,
                                                         'trade_size': trade_size, 'trade_entry': entry_price,
                                                         'trade_exit': exit_price, 'gain_percent': gain})
        self.conn.commit()


class Bot:
    def __init__(self):
        """
        Initializes bot with no asset and trade_amount values
        set to None.
        """
        self.asset = None
        self.trade_amount = None

    def connect(self, api_key, secret_key):
        """
        Uses the provided api and secret key to
        connect to user's binance account

        :param api_key:
        :param secret_key:
        :return:
        """
        self.client = Client(api_key, secret_key)

    def setup_params(self, asset, trade_amount, interval):
        """
        Sets the trading asset, trade amount and chart time interval

        :param asset:
        :param trade_amount:
        :param interval:
        :return:
        """
        self.asset = asset
        self.trade_amount = trade_amount
        self.time_interval = interval

    def check_params(self):
        """
        Does a boolean check to see if trade parameters have been set

        :return:
        """
        if self.asset and self.trade_amount:
            return True

    def get_btc_balance(self):
        """
        Retrieves the current user's bitcoin balance

        :return:
        """
        btc_balance = self.client.get_asset_balance(asset='BTC')

        return float(btc_balance['free'])

    def find_ticker(self, selected_ticker):
        """
        Retrieves all tickers from exchange, loops through them.
        If the user's desired asset symbol is found, True will
        be returned. If not, False will be returned.

        :param selected_ticker:
        :return:
        """
        all_tickers = self.client.get_all_tickers()
        ticker_found = False

        for ticker in all_tickers:
            if selected_ticker == ticker['symbol']:
                ticker_found = True

        return ticker_found

    def get_klines(self, limit_):
        """
        Selects appropriate kline interval from dictionary based on parameter, reverses
        the order since oldest candles are retrieved first, and data is returned in a list.

        :param limit_:
        :return:
        """
        kline_intervals = {'15m': Client.KLINE_INTERVAL_15MINUTE, '30m': Client.KLINE_INTERVAL_30MINUTE,
                           '1H': Client.KLINE_INTERVAL_1HOUR, '2H': Client.KLINE_INTERVAL_2HOUR,
                           '4H': Client.KLINE_INTERVAL_4HOUR, '6H': Client.KLINE_INTERVAL_6HOUR,
                           '12H': Client.KLINE_INTERVAL_12HOUR, '1D': Client.KLINE_INTERVAL_1DAY}

        klines = self.client.get_klines(symbol=self.asset,
                                        interval=kline_intervals[self.time_interval],
                                        limit=limit_)
        klines.reverse()
        return klines

    def get_bbands(self):
        """
        Calculates the upper and lower bollinger bands. First retrieves appropriate
        klines. Gathers the last 20 closes. Calculates the simple moving average.
        Squares each of the last 20 closes into new list. Then calculates the
        standard deviation. From there it is able to calculate the upper and lower
        bollinger bands.

        :return:
        """
        klines = self.get_klines(25)

        last_20_closes = [float(klines[i][4]) for i in range(20)]
        simple_ma = sum(last_20_closes) / 20
        squared_list = [(close - simple_ma)**2 for close in last_20_closes]

        standard_deviation = math.sqrt(sum(squared_list) / 20)
        lower_band = round(simple_ma - (standard_deviation * 2), 8)

        # calculate upper band (not used currently)
        # upper_band = simple_ma + (standard_deviation * 2)

        return lower_band

    def place_market_buy(self, current_price):
        """
        Takes the user's set trade amount, and divides by the current
        asset price to determine amount of asset to buy. Then commits
        a market buy order.

        :param current_price:
        :return:
        """
        self.amount = int((self.trade_amount / current_price))
        self.client.order_market_buy(symbol=self.asset,
                                     quantity=self.amount)

    def place_market_sell(self):
        """
        Places a market sell order.

        :return:
        """
        self.client.order_market_sell(symbol=self.asset,
                                      quantity=self.amount)

    def get_current_asset_price(self):
        """
        Retrieves the currently traded asset price.

        :return:
        """
        klines = self.get_klines(1)
        current_price = float(klines[0][4])
        return current_price

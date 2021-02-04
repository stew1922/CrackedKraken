import os
import json
import requests, urllib
from dotenv import load_dotenv
import hmac, base64, hashlib
import time
import json
import requests
import pandas as pd
import websocket

# load the .env file that your Kraken keys are stored in (must be at or above this library level)
load_dotenv()

class PublicKraken:

    def __init__(self):
        self = self

    def get_server_time(self, unix=True):
        # display Kraken's server time
        # input unix=True (default) returns the unix timestamp
        # input unix=False returns the rfc 1123 time format DAY, DD MON YYYY hh:mm:ss GMT
            # ex.: Sat, 16 Jan 21 22:23:36 +0000
        '''
        args:
            *Optional: 'unix=True' will return a unix timestamp, while 'unix=False' will return the time in rfc 1123 format.  
                - Default is set to unix=True.
        '''
        
        url = 'https://api.kraken.com/0/public/Time'
        res = requests.post(url).json()

        if not res['error']:
            if unix == True:
                return res['result']['unixtime']
            else:
                return res['result']['rfc1123']
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_system_status(self):
        
        # display the current status from Kraken
            # returns a list of [status, time]
        # Possible statuses:
            # 'online' = fully functional
            # 'cancel_only' = existing orders can be cancelled, new orders cannot be placed
            # 'post_only' = existing orders can be cancelled, ONLY new post limit orders can be placed
            # 'limit_only' = existing orders can be cancelled, ONLY new limit orders can be placed
        '''
        returns:
            - A list of [status, time]
        '''

        url = 'https://api.kraken.com/0/public/SystemStatus'
        res = requests.get(url).json()

        if not res['error']:
            return [res['result']['status'], res['result']['timestamp']]
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def make_api_data(self, asset=None, aclass=None, trades=None, userref=None, start=None, end=None, ofs=None, closetime=None, type=None, txid=None, consolidation=None, docalcs=None, pair=None, fee_info=None, ordertype=None, price=None, price2=None, volume=None, leverage=None, oflags=None, starttm=None, expiretm=None, validate=None, since=None, info=None):
        # simple function that will create the 'data' dictionary that will be used to pass information into any api calls
        data = {arg: value for arg, value in locals().items() if arg != 'endpoint' and arg != 'url' and arg != 'method' and value is not None and value != False}

        return data

    def name_converter(self, asset):
        # Function that converts asset names into Kraken compatible names.
        # Kraken uses the X-ISO4217-A3 system to name their assets.
        # See https://github.com/globalcitizen/x-iso4217-a3 for more info
        # this will mainly be used as a helper function within other functions to minimize naming convention errors
        '''
        args:
            - Any Kraken ticker or common ticker symbol, i.e.- 'btc', 'XBT', etc.

        returns:
            - The valid Kraken X-ISO4217-A3 ticker.
        '''

        url = 'https://api.kraken.com/0/public/Assets'
        res = requests.get(url).json()
        asset = asset.upper()

        if not res['error']:
            cryptos = {}
            for crypto in res['result']:
                if asset==crypto:
                    return crypto
                else:
                    cryptos[crypto] = res['result'][crypto]['altname']

            cryptoskeys = list(cryptos.keys())
            cryptosvals = list(cryptos.values())

            if asset == 'btc' or asset == 'BTC':
                return 'XXBT'
            elif asset in cryptosvals:
                pos = cryptosvals.index(asset)
                kraken_name = cryptoskeys[pos]
                return kraken_name
                
            else:
                raise Exception({'naming_error': f'Error Message: {asset} is not a name Kraken recognizes.  Use "get_asset_info" without passing an asset into the function to get a full list of Kraken recongized assets.'})

        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def pair_matching(self, trading_pair):
        # takes in wsname or altname and returns the Kraken pair name
        # this will mainly be used as a helper function within other functions to minimize naming convention errors
        '''
        args:
            - 'trading-pair' = any pair name, i.e.- 'ethusd', 'XETHZUS', 'eth/USD', etc

        returns:
            - A valid Kraken recognized trading pair
        '''

        url = 'https://api.kraken.com/0/public/AssetPairs'
        res = requests.get(url).json()
        
        if not res['error']:
            if trading_pair.upper() == 'BTCUSD':
                return 'XXBTZUSD'
                
            # check to see if 'trading_pair' is a list or not
            if type(trading_pair) == list:
                # check to see if each 'trading_pair' is already a valid Kraken pair
                new_pairs = []
                for coin in trading_pair:
                    coin = coin.upper()
                    if coin in res['result']:
                        new_pairs.append(coin)
                    else:
                        # create a dictionary with all the trading pair/wsname pairs
                        wsdict = {}
                        for pair in res['result']:
                            # some pairs do not have a wsname, so we want to skip those
                            try:
                                wsdict[pair] = res['result'][pair]['wsname']
                            except KeyError: continue

                        # create a list for the keys and values of the wsdict
                        wsdictkeys = list(wsdict.keys())
                        wsdictvals = list(wsdict.values())

                        # create a dictionary of the trading pair/altname pairs
                        altdict = {}
                        for pair in res['result']:
                            altdict[pair] = res['result'][pair]['altname']

                        # create a list for the keys and the valuses of altdict
                        altdictkeys = list(altdict.keys())
                        altdictvals = list(altdict.values())

                        # if 'coin' is a wsname, then return the Kraken pair name and add to the pair list
                        if coin in wsdictvals:
                            pos = wsdictvals.index(coin)
                            item = wsdictkeys[pos]
                            new_pairs.append(item)
                        # if 'coin' is an altname, then return the Kraken pair name and add to the pair list
                        elif coin in altdictvals:
                            pos = altdictvals.index(coin)
                            item = altdictkeys[pos]
                            new_pairs.append(item)
                        # otherwise throw an error
                        else:
                            raise Exception({'naming_error': f'Error Message: {coin} is not a recognized trading pair by Kraken.'})

                return new_pairs

            # if it is not a list, perform the same logic and return the single Kraken pair
            else:
                trading_pair = trading_pair.upper()
                # check to see if 'trading_pair' is already a valid Kraken pair
                if trading_pair in res['result']:
                    return trading_pair
                else:
                    # create a dictionary with all the trading pair/wsname pairs
                    wsdict = {}
                    for pair in res['result']:
                        # some pairs do not have a wsname, so we want to skip those
                        try:
                            wsdict[pair] = res['result'][pair]['wsname']
                        except KeyError: continue

                    # create a list for the keys and values of the wsdict
                    wsdictkeys = list(wsdict.keys())
                    wsdictvals = list(wsdict.values())

                    # create a dictionary of the trading pair/altname pairs
                    altdict = {}
                    for pair in res['result']:
                        altdict[pair] = res['result'][pair]['altname']

                    # create a list for the keys and the valuses of altdict
                    altdictkeys = list(altdict.keys())
                    altdictvals = list(altdict.values())

                    # if 'trading_pair' is a wsname, then return the Kraken pair name
                    if trading_pair in wsdictvals:
                        pos = wsdictvals.index(trading_pair)
                        return wsdictkeys[pos]
                    # if 'trading_pair' is an altname, then return the Kraken pair name
                    elif trading_pair in altdictvals:
                        pos = altdictvals.index(trading_pair)
                        return altdictkeys[pos]
                    # otherwise throw an error
                    else:
                        raise Exception({'naming_error': f'Error Message: {trading_pair} is not a recognized trading pair by Kraken.'})
        
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_asset_pairs(self):
        '''
        returns:
            - A list of all available asset trading pairs from Kraken
        '''

        url = 'https://api.kraken.com/0/public/AssetPairs'

        message = requests.post(url).json()

        if not message['error']:
            assetpairs = []
            for assetpair in message['result']:
                assetpairs.append(assetpair)
            return assetpairs
        else:
            raise Exception({'kraken_error': f'Error Message: {message["error"]}'})

    def get_pair_info(self, pair=None, info='info'):
        '''
        args:
            *Optional: a valid Kraken trading pair, wsname or altname.  Use 'get_asset_pairs' for a list of pairs that are available.
                - Default is to return ALL available pairs.
            *Optional: info to be returned
                - Default is to return ALL available info.
                - Other options include: 'leverage', 'fees', 'margin'

        returns:
            - If a pair and info has been specified, this function will return a dictionary of data for that pair/info.
            - Otherwise all pairs/info will be returned in a dictonary with the pair names as the keys (see below for structure)
        ---------------------------------------------------------------------------------------------
        <pair_name> = pair name
            altname = alternate pair name
            wsname = WebSocket pair name (if available)
            aclass_base = asset class of base component
            base = asset id of base component
            aclass_quote = asset class of quote component
            quote = asset id of quote component
            lot = volume lot size
            pair_decimals = scaling decimal places for pair
            lot_decimals = scaling decimal places for volume
            lot_multiplier = amount to multiply lot volume by to get currency volume
            leverage_buy = array of leverage amounts available when buying
            leverage_sell = array of leverage amounts available when selling
            fees = fee schedule array in [volume, percent fee] tuples
            fees_maker = maker fee schedule array in [volume, percent fee] tuples (if on maker/taker)
            fee_volume_currency = volume discount currency
            margin_call = margin call level
            margin_stop = stop-out/liquidation margin level
            ordermin = minimum order volume for pair
        '''

        url = 'https://api.kraken.com/0/public/AssetPairs'

        # if a pair ha been provided, convert the pair name to a valid Kraken traing pair format
        if pair != None:
            pair = self.pair_matching(pair)

        # if pair and/or info is passed as an argument send that in the API request package
        if pair != None and info != 'info':
            data = PrivateKraken().make_api_data(pair=pair, info=info)
        elif pair != None and info == 'info':
            data = PrivateKraken().make_api_data(pair=pair)
        elif pair == None and info != 'info':
            data = PrivateKraken().make_api_data(info=info)
        else:
            data = {}

        # send and receive the API request
        message = requests.post(url, data=data).json()

        # return the result
        if not message['error']:
            return message['result']
        else:
            raise Exception({'kraken_error': f'Error Message: {message["error"]}'})

    def get_asset_info(self, asset=None):
            # find all the info for a certain asset
            # info includes:
                # 'altname' = alternative name, ie: XETH --> ETH
                # 'aclass' = asset class (currency, futures, etc.)
                # 'decimals' = scaling decimal places for record keeping
                # 'display_decimals' = scaling decimal places for output display
            '''
            args:
                *Optional: 'asset' is the asset to return data for
                    - Default is set to 'None' which will return all assets on Kraken.

            returns:
                - A dictionary of asset info.
            '''

            url = 'https://api.kraken.com/0/public/Assets'
            res = requests.get(url).json()

            if not res['error']:
                if asset != None:
                    asset = asset.upper()
                    try: 
                        return res['result'][asset]

                    except KeyError: 
                        return self.name_converter(asset)

                else:
                    return res['result']
                
            else:
                raise Exception({'kraken_error': f'Error Message: {res["error"]}'})

    def get_fees(self, pair, maker_taker=None, volume=None):
        # return a dictionary of a dictionary of the fees associated with the provided pair
        # {'taker': {volume1: fee1, volume2: fee2}, 'maker': {volume1: fee1, volume2: fee2}}
        # if your monthly volume is equal to OR more than the listed volume, then the associated fee is your fee in percent
        '''
        args:
            - Valid trading pair's Kraken name, wsname or alternative name. 
                * Optional: 'maker_taker' which can be either 'maker' or 'taker'.  If neither are provided, both fee tiers are returned.
                    - Default is set to 'None'
                * Optional: 'volume' which is the user's volume in $.  If none is provided, all tiers are returned.
                    - Default is set to 'None'
                
        returns:
            - A dictionary of taker and maker fee tiers.  Volume is given in $ amount and fees are given in percents.
        ''' 

        url = 'https://api.kraken.com/0/public/AssetPairs'
        res = requests.get(url).json()

        pair = self.pair_matching(pair)

        if not res['error']:
            fees = {}

            # get the taker fees and fill the taker dictionary and add it to the fees dictionary
            taker_fees_array = res['result'][pair]['fees']
            takerdict = {}
            for fee in taker_fees_array:
                takerdict[fee[0]] = fee[1]
            fees['taker'] = takerdict

            # get the maker fees and fill the maker dictionary and add it to the fees dictionary
            maker_fees_arrary = res['result'][pair]['fees_maker']
            makerdict = {}
            for fee in maker_fees_arrary:
                makerdict[fee[0]] = fee[1]
            fees['maker'] = makerdict

            # check to see if either the maker_taker argument or the volume argument is provided and return the corresponding dictionary(ies)

            if volume == None:
                if maker_taker == None:
                    fees = fees
                if maker_taker == 'maker':
                    fees = fees['maker']
                elif maker_taker == 'taker':
                    fees = fees['taker']
                else:
                    fees = fees
            
            if volume != None:
                for vol in fees['maker']:
                    if volume >= vol:
                        volume_tier = vol
                if maker_taker == None:
                    fees_vol = {}
                    fees_vol['taker'] = fees['taker'][volume_tier]
                    fees_vol['maker'] = fees['maker'][volume_tier]
                    fees = fees_vol
                if maker_taker == 'maker':
                    fees = fees['maker'][volume_tier]
                elif maker_taker == 'taker':
                    fees = fees['taker'][volume_tier]
                else:
                    fees = fees
                    
            return fees

        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_pair_trade_data(self, pair):
        # returns all the trade info for the given pair
            # altname = alternate pair name
            # wsname = WebSocket pair name (if available)
            # aclass_base = asset class of base component
            # base = asset id of base component
            # aclass_quote = asset class of quote component
            # quote = asset id of quote component
            # lot = volume lot size
            # pair_decimals = scaling decimal places for pair
            # lot_decimals = scaling decimal places for volume
            # lot_multiplier = amount to multiply lot volume by to get currency volume
            # leverage_buy = array of leverage amounts available when buying
            # leverage_sell = array of leverage amounts available when selling
            # fees = fee schedule array in [volume, percent fee] tuples
            # fees_maker = maker fee schedule array in [volume, percent fee] tuples (if on maker/taker)
            # fee_volume_currency = volume discount currency
            # margin_call = margin call level
            # margin_stop = stop-out/liquidation margin level
            # ordermin = minimum order volume for pair
        '''
        args:
            - Valid trading pair's Kraken name, wsname or alternative name.
        returns:
            - A dictionary of trade data for the given pair.
        ''' 

        url = 'https://api.kraken.com/0/public/AssetPairs'
        res = requests.get(url).json()

        pair = self.pair_matching(pair)

        if not res['error']:
            return res['result'][pair]
        else:
            raise Exception(f"Error Message: {res['error']}")

    def get_ticker_info(self, pair):
        # returns the current order book level one for a given pair, or list of pairs
            # NOTICE: it appears that, for the time being, the Kraken API only returns the alphabetically last pair data when passing a list of pairs as an argument
        '''
        args:
            - Valid trading pair's Kraken name, wsname or alternative name.
        returns:
            - A dicitonary of dictionaries of ticker data: ask, bid, last trade, volume, volume weighted average price, number of trades, low, high, open
        '''
        url = 'https://api.kraken.com/0/public/Ticker'
        pair = self.pair_matching(pair)
        params = {'pair': pair}
        res = requests.get(url, params).json()
        
        if not res['error']:
            return res['result']
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_ohlc(self, pair, interval=None, since=None):
        # returns the last 720 iterations of periods that you feed it, i.e.- default is minutes, so you would recieve the last 720 minutes. If you input 'D' you would get the last 720 days on a daily timescale.
        '''
        args:
            - Valid Kraken trading pair name, wsname, or alternative name.
                * Optional: 'interval' which is the time frame interval (can take string or int -- for the 1 minute interval, you can enter either '1' or 'min').
                * Optional: 'since' which is the unix timestamp from which to start the data pull (Kraken limits you to 720 previous iterations)
        returns: 
            - A dictionary of a dictionaries with the format: 
                {timestamp1: 
                    {open: open1, 
                    high: high1, 
                    low: low1, 
                    close: close1, 
                    vwap: vwap1, 
                    volume: volume1, 
                    count: count1}, 
                timestamp2: 
                    {open: open2, 
                    high: high2, 
                    low: low2, 
                    close: close2, 
                    vwap: vwap2, 
                    volume: volume2, 
                    count: count2}}
        '''
        interval_dict = {
            'MIN': 1,
            '1H': 60,
            '4H': 240,
            'D': 1440,
            'W': 10080,
            '15D': 21600
        }

        if type(interval) == int:
            if interval not in interval_dict.values():
                raise Exception({'input_error': f'{interval} not a valid input.  Only 1, 60, 240, 1440, 10080, or 21600 accepted as integers.'})
            interval = interval
        elif interval==None:
            interval = None
        else:
            if interval not in interval_dict.keys():
                raise Exception({'input_error': f'{interval} not a valid input.  Only "min", "1h", "4h", "D", "W" and "15D" accepted as strings.'})
            interval = interval_dict[interval.upper()]
        
        url = 'https://api.kraken.com/0/public/OHLC'
        pair = self.pair_matching(pair)

        if interval==None and since==None:
            params = {
                'pair': pair
            }

        elif interval==None:
            params = {
                'pair': pair,
                'since': since
            }

        elif since==None:
            params = {
                'pair': pair,
                'interval': interval
            }
        else:
            params = {
                'pair': pair,
                'interval': interval,
                'since': since
            }

        res = requests.get(url, params).json()
        if not res['error']:
            # the response comes back as a list of lists of strings, so we need to put in to a dictionary to put into a dataframe
            converter_dict = {}

            data = res['result'][pair]
            for row in data:
                converter_dict[row[0]] = {
                'open': float(row[1]),
                'high': float(row[2]),
                'low': float(row[3]),
                'close': float(row[4]),
                'vwap': float(row[5]),
                'volume': float(row[6]),
                'count': float(row[7])
            }

            return converter_dict
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_ohlc_dataframe(self, pair, interval=None, since=None):
        # similar to get_ohlc, except returns a dataframe instead of a dictionary of dictionaries
        '''
        Similar to 'get_ohlc', except returns a dataframe instead of a dictionary of dictionaries.
        
        args:
            - Valid Kraken trading pair name, wsname, or alternative name.
                * Optional: 'interval' which is the time frame interval.
                    - Default is set to 'None' and returns a 1 minute interval (?)
                * Optional: 'since' which is the unix timestamp from which to start the data pull (Kraken limits you to 720 iterations)
                    - Default is set to 'None' and returns the previous 720 interations

        returns: 
            - A pandas dataframe with a datetime index and columns 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
        '''
        
        data = self.get_ohlc(pair, interval, since)

        df = pd.DataFrame(data).T
        df.index = pd.to_datetime(df.index, unit='s')

        return df

    def get_order_book(self, pair, count=None):
        # function that will return a dictionary of dictionaries of the asks and bids
        '''
        args:
         - Valid trading pair's Kraken name, wsname or alternative name.
            * Optional: 'count' which is the maximium number of bids/asks.  
                - By default set to 'None' which returns all bids/asks.

        returns: 
            - A dictionary of dictionaries of bids and asks.
        '''

        pair = self.pair_matching(pair)

        url = 'https://api.kraken.com/0/public/Depth'
        if count==None:
            params = {
                'pair': pair
            }
        else:
            params = {
                'pair': pair,
                'count': count
            }
        
        res = requests.get(url, params).json()

        if not res['error']:
            return res['result'][pair]
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_asks(self, pair, count=None):
        # returns only the asks for a selected pair
        '''
        args:
            - Valid trading pair's Kraken name, wsname or alternative name.
                *Optional: 'count' which is the maximum number of asks to return.
                    - Default is set to 'None' which returns all asks.

        returns: 
            - A list of list of each ask -- [[price, volume, timestamp]]
        '''
        pair = self.pair_matching(pair)

        asks = self.get_order_book(pair, count)

        return asks['asks']

    def get_bids(self, pair, count=None):
        # returns only the bids for a selected pair
        '''
        args:
            - Valid trading pair's Kraken name, wsname or alternative name.
                * Optional: 'count' which is the maximum number of bids to return.
                    - By Default, set to 'None' which returns all bids

        -Returns: a list of list of each bid -- [[price, volume, timestamp]]
        '''
        pair = self.pair_matching(pair)

        bids = self.get_order_book(pair, count)

        return bids['bids']

    def get_current_bid(self, pair):
        # returns the current bid for a selected pair
        '''
        args:
            - Valid trading pair's Kraken name, wsname or alternative name.

        returns: 
            - A list of current bid info -- [price, volume, timestamp]
        '''
        pair = self.pair_matching(pair)

        bid = self.get_order_book(pair)

        return bid['bids'][0]

    def get_current_ask(self, pair):
        # returns the current bid for a selected pair
        '''
        args:
            - Valid trading pair's Kraken name, wsname or alternative name.

        returns: 
            - A list of current ask info -- [price, volume, timestamp]
        '''
        pair = self.pair_matching(pair)

        ask = self.get_order_book(pair)

        return ask['asks'][0]

    def get_leverage_data(self, pair, type):
        '''
        args:
            - pair = the trading pair to lookup leverage information for
            - type = whether it is buy-side or sell-side leverage (i.e.- long or short)

        returns: 
            - A list of all available leverage options for that asset.
        '''

        leverage = self.get_pair_trade_data(pair)[f'leverage_{type}']

        return leverage

    def get_historical_data(self, pair, start_time=None):

        '''
        args:
            - pair = trading pair to pull historical data for.
                *Optional: start_time = time from which to begin pulling historical data
                    - By default, set to 'None' and returns the previous 720 trades
                    - start_time = 0 is a special case that will pull trade history from the genesis of trading that asset on Kraken.
        returns:
            - A pandas dataframe of every trade.
        '''
        # if start_time = 0, then the function will pull all history since the genesis trade on Kraken
            # beware, this is A LOT of data.  To download all ETHUSD trades would take over 30 hours due to API rate limitations
        # start_time must be in str format

        # be sure 'pair' is a Kraken recognized trading pair, i.e.- XETHZUSD
        pair = self.pair_matching(pair)

        # subscribe to the 'Trades' endpoint
        url = 'https://api.kraken.com/0/public/Trades'

        # if start_time==None, then pull the default which is the most recent 1000 trades, otherwise pull in trades since the start_time
            # caveat: the API only allows you to pull in 1000 trades at a time, so if you want more than that you will have to loop through function using the previous 1000 trades' most recent trade as the new start_time
        data = self.make_api_data(pair=pair, since=start_time)  

        message = requests.post(url, data).json()

        if not message['error']:
            # put the initial results in a dataframe
            hist = pd.DataFrame(message['result'][pair], columns=['price', 'volume', 'timestamp', 'buy/sell', 'ordertype', 'misc'])
            # be sure the timestamp is in datetime format and then make it the index
            hist['datetime'] = pd.to_datetime(hist.timestamp, unit='s')
            hist.timestamp.astype('float')
            hist.set_index(hist.timestamp, inplace=True)
            hist.drop(columns=['timestamp'], inplace=True)
            if start_time==None:
                return hist
            else:

                # for Public Kraken API calls, you get a maximum of 15 calls (which is increased by 1 every 3 seconds until 15 is refilled again)
                max_calls = 15
                call_add_rate = 3
                last_time = message['result']['last']
                
                # since we already called the API once in the message call, we need to start our counter at 14 (plus this builds in a little leeway to guarantee we don't break the rules)
                call_count = max_calls - 1
                init_time = str(format(time.time() * 1000000000, '0.0f'))
                call_time = time.time()

                # start the loop until we pass the code initialization time
                while float(last_time) <= float(init_time):
                    # first check to see if more than 3 seconds have passed and add time back to 'call_count' if so, otherwise subtract one from the 'call_count'
                    if (time.time() - call_add_rate) >= call_time:
                        call_time = time.time()
                        call_count += 1
                    else:
                        call_count -= 1

                    # if the 'call_count' is greater than 0, then make the call, otherwise wait enough time for the call count to reload
                    if call_count > 0:
                        # create a new data packet with 'since' updated to the 'last_time'
                        data = self.make_api_data(pair=pair, since=last_time)

                        # put the returned message into a dataframe exactly the same as above
                        message = requests.post(url, data).json()

                        if not message['error']:
                            hist2 = pd.DataFrame(message['result'][pair], columns=['price', 'volume', 'timestamp', 'buy/sell', 'ordertype', 'misc']) 
                            hist2.timestamp.astype('float')
                            hist2['datetime'] = pd.to_datetime(hist2.timestamp, unit='s')
                            hist2.set_index(hist2.timestamp, inplace=True)
                            hist2.drop(columns=['timestamp'], inplace=True)

                            # append to the existing dataframe
                            hist = hist.append(hist2)

                            # reset 'last_time'
                            last_time = message['result']['last']
                        else:
                            raise Exception({'kraken_error': f'Error Message: {message["error"]}'})
                        
                    # wait until the 'call_count' resets
                    else:
                        call_count = max_calls
                        for i in range(0, max_calls * call_add_rate):
                            time.sleep(1)
                return hist
        
        else:
            raise Exception({'kraken_error': f'Error Message: {message["error"]}'})

    def guarantee_online(self):
        '''
        This is a function that will run an infinite loop until the server is 'online' and fully operational
        '''

        # this function will check to see if the Kraken server is in 'online' mode, otherwise it will wait 3 seconds and then try again
        # the 3 second wait will ensure you do not exceed your API call limits
        is_online = self.get_system_status()

        while is_online[0] != 'online':
            print(f'System is in {is_online[0]} mode.  Time checked is {is_online[1]}')
            time.sleep(3)
            is_online = self.get_system_status()

    def guarantee_operational(self):
        '''
        This is a function that will run an infinte loop until the server is operational, even if it is limited.
            *WARNING: this function does not guarantee all order types.  If you need to place an order (especially a market order) utilize the 'guarantee_online' function
        '''
        # this function will check to see if the Kraken server is in an operational mode (either 'online' or 'post_only' or 'limit_only'), otherwise it will wait 3 seconds and then try again
        # the 3 second wait will ensure you do not exceed your API call limits
        is_operational = self.get_system_status()

        while is_operational[0] != 'online' or is_operational != 'post_only' or is_operational != 'limit_only':
            print(f'System is in {is_operational[0]} mode.  Time checked is {is_operational[1]}')
            time.sleep(3)
            is_operational = self.get_system_status()

    def guarantee_cancel(self):
        '''
        This is a function that will run an infinte loop until the server is in a cancelable state.
            *WARNING: this will not guarantee a mode that allows order placing, rather it only guarantees order cancelling.
        '''
        # this function will check to see if the Kraken server is in a cancel mode (either 'online' or 'post_only' or 'limit_only' or 'cancel_only'), otherwise it will wait 3 seconds and then try again
        # the 3 second wait will ensure you do not exceed your API call limits
        is_cancellable = self.get_system_status()

        while is_cancellable[0] == 'maintenance':
            print(f'System is in {is_cancellable[0]} mode.  Time checked is {is_cancellable[1]}')
            time.sleep(3)
            is_cancellable = self.get_system_status()

class PrivateKraken:

    def __init__(self):
        self = self

        # set an api key variable that will be used to authenticate your account
        krakenapi = os.getenv('kraken_api')
        krakenprivatekey = os.getenv('kraken_private_key')

        self.krakenapi = krakenapi
        self.krakenprivatekey = krakenprivatekey

    def authenticate(self, endpoint, data):
        # this will mostly be used as a helper function for the other private functions
        # this function will authenticate any API calls
        # takes in the endpoint information  the user wishes to access - Balance, TradeBalance, etc.
        # takes in the optional/required data from the desired endpoint information lookup as a dictionary of items.

        '''
        args:
            - Endpoint information you wish to access along with a dictionary of required/optional data to include in the api call.  See Kraken API 
        documentation for further information.

        returns:
            - Data corresponding with the chosen endpoint information.
        '''

        url = 'https://api.kraken.com/0/private/' + endpoint
        method = '/0/private/' + endpoint

        nonce = str(int(time.time() * 1000))

        data['nonce'] = nonce

        api_data = urllib.parse.urlencode(data)

        api_nonce = (nonce + api_data).encode()
        message = method.encode() + hashlib.sha256(api_nonce).digest()

        hmac_encode = hmac.new(base64.b64decode(self.krakenprivatekey), message, hashlib.sha512)
        api_signature = base64.b64encode(hmac_encode.digest())

        params = {
            'API-Key': self.krakenapi,
            'API-Sign': api_signature
        }
        res = requests.post(url, headers=params, data=data).json()

        if not res['error']:
            return res['result']
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_balance(self, asset=None):
        # returns to the user the balance of all accounts in Kraken
        '''
        args:
            *Optional: 'asset' = the asset the user wishes to recieve Account Balance information about.  
                - Default is set to 'None' which returns all balances.

        returns: 
            - A single dictionary of assets and their balances.
        '''
        data = PublicKraken().make_api_data(asset=asset)

        # be sure that (if supplied) the asset is in the Kraken recognized variant
        try:
            data['asset'] = PublicKraken().name_converter(data['asset'])
            asset = data['asset']
        except KeyError: data = data

        message = self.authenticate('Balance', data)

        if asset is not None:
            return message[asset]
        else:
            return message

    def get_trade_balance(self, asset='ZUSD', aclass='currency'):
        # returns a user's trade balance for a given asset, USD is default
            # Note: you can also choose the class of asset ('aclass'), but Kraken currently (1.17.2021) only has currency, 
            # so currency is the default option and likely does not need to be changed.
        '''
        args:
            *Optional: 'asset' = asset used to return balance for.
                - By default, asset class is set to 'currency'.  Kraken currently (01.17.2021) only lists currecies, so this should not be changed.
            *Optional: 'aclass' = asset class to return balance for.
                - By default, asset is set to 'ZUSD'.  Takes either the offical Kraken name, wsname or alternative name.

        returns: 
            - A dictionary of trade balance information:
                eb = equivalent balance (combined balance of all currencies)
                tb = trade balance (combined balance of all equity currencies)
                m = margin amount of open positions
                n = unrealized net profit/loss of open positions
                c = cost basis of open positions
                v = current floating valuation of open positions
                e = equity = trade balance + unrealized net profit/loss
                mf = free margin = equity - initial margin (maximum margin available to open new positions)
                ml = margin level = (equity / initial margin) * 100
        '''

        asset = PublicKraken().name_converter(asset)

        data = PublicKraken().make_api_data(asset=asset, aclass=aclass)

        message = self.authenticate('TradeBalance', data)

        return message

    def get_open_orders(self, trades=None, userref=None):
        '''
        args:
            *Optional: trades = True or False, determines whether to include trades in output.
                - By default, set to 'False'.
            *Optioinal: userref = a user reference id and can be used to restrict orders to that particular userref.
                - By default, set to 'None' and returns all orders

        returns: 
            - A dictionary of open order information with the Transaction ID as the key.  It is empty if there are no open orders.
        ------------------------------------------------------------------------------------------------------------------------
            refid = Referral order transaction id that created this order
                userref = user reference id
                status = status of order:
                    pending = order pending book entry
                    open = open order
                    closed = closed order
                    canceled = order canceled
                    expired = order expired
                opentm = unix timestamp of when order was placed
                starttm = unix timestamp of order start time (or 0 if not set)
                expiretm = unix timestamp of order end time (or 0 if not set)
                descr = order description info
                    pair = asset pair
                    type = type of order (buy/sell)
                    ordertype = order type (See Add standard order)
                    price = primary price
                    price2 = secondary price
                    leverage = amount of leverage
                    order = order description
                    close = conditional close order description (if conditional close set)
                vol = volume of order (base currency unless viqc set in oflags)
                vol_exec = volume executed (base currency unless viqc set in oflags)
                cost = total cost (quote currency unless unless viqc set in oflags)
                fee = total fee (quote currency)
                price = average price (quote currency unless viqc set in oflags)
                stopprice = stop price (quote currency, for trailing stops)
                limitprice = triggered limit price (quote currency, when limit based order type triggered)
                misc = comma delimited list of miscellaneous info
                    stopped = triggered by stop price
                    touched = triggered by touch price
                    liquidated = liquidation
                    partial = partial fill
                oflags = comma delimited list of order flags
                    viqc = volume in quote currency
                    fcib = prefer fee in base currency (default if selling)
                    fciq = prefer fee in quote currency (default if buying)
                    nompp = no market price protection
                trades = array of trade ids related to order (if trades info requested and data available)
        '''

        # build the dictionary for the required/optional items to be sent in the API request
        data = PublicKraken().make_api_data(trades=trades, userref=userref)

        message = self.authenticate('OpenOrders', data)

        return message['open']

    def get_closed_orders(self, trades=None, userref=None, start=None, end=None, ofs=None, closetime=None):
        '''
        -args: 
            * Optional: trades, userrf, start, end, ofs or closetime.
                - By default, all optional inputs are set to None.

        -returns: 
            * A of closed order information with the Transaction ID as the key.  It is empty if there are no closed orders.
        -----------------------------------------------------------------------------------------------------------------------------
            refid = Referral order transaction id that created this order
                userref = user reference id
                status = status of order:
                    pending = order pending book entry
                    open = open order
                    closed = closed order
                    canceled = order canceled
                    expired = order expired
                opentm = unix timestamp of when order was placed
                starttm = unix timestamp of order start time (or 0 if not set)
                expiretm = unix timestamp of order end time (or 0 if not set)
                descr = order description info
                    pair = asset pair
                    type = type of order (buy/sell)
                    ordertype = order type (See Add standard order)
                    price = primary price
                    price2 = secondary price
                    leverage = amount of leverage
                    order = order description
                    close = conditional close order description (if conditional close set)
                vol = volume of order (base currency unless viqc set in oflags)
                vol_exec = volume executed (base currency unless viqc set in oflags)
                cost = total cost (quote currency unless unless viqc set in oflags)
                fee = total fee (quote currency)
                price = average price (quote currency unless viqc set in oflags)
                stopprice = stop price (quote currency, for trailing stops)
                limitprice = triggered limit price (quote currency, when limit based order type triggered)
                misc = comma delimited list of miscellaneous info
                    stopped = triggered by stop price
                    touched = triggered by touch price
                    liquidated = liquidation
                    partial = partial fill
                oflags = comma delimited list of order flags
                    viqc = volume in quote currency
                    fcib = prefer fee in base currency (default if selling)
                    fciq = prefer fee in quote currency (default if buying)
                    nompp = no market price protection
                trades = array of trade ids related to order (if trades info requested and data available)
        '''
        
        data = PublicKraken().make_api_data(trades=trades, userref=userref, start=start, end=end, ofs=ofs, closetime=closetime)

        message = self.authenticate('ClosedOrders', data)

        return message['closed']

    def get_trade_history(self, type='all', trades=None, start=None, end=None, ofs=None):
        '''
        -args: 
            * Optional: type, trades, start, end, ofs
                ** type takes only one of the following arguments (set to 'all' by default):
                    --'any position'
                    --'closed position'
                    --'closing position'
                    --'no position'
        -returns: 
            - A dictionary with the transaction id as the key.  
        -------------------------------------------------------------------------------
        returned array data:
            ordertxid = order responsible for execution of trade
            pair = asset pair
            time = unix timestamp of trade
            type = type of order (buy/sell)
            ordertype = order type
            price = average price order was executed at (quote currency)
            cost = total cost of order (quote currency)
            fee = total fee (quote currency)
            vol = volume (base currency)
            margin = initial margin (quote currency)
            misc = comma delimited list of miscellaneous info
                closing = trade closes all or part of a position

        **Additionally, if the trade opened a position, the following fields are also present in the trade info:
            posstatus = position status (open/closed)
            cprice = average price of closed portion of position (quote currency)
            ccost = total cost of closed portion of position (quote currency)
            cfee = total fee of closed portion of position (quote currency)
            cvol = total fee of closed portion of position (quote currency)
            cmargin = total margin freed in closed portion of position (quote currency)
            net = net profit/loss of closed portion of position (quote currency, quote currency scale)
            trades = list of closing trades for position (if available)
        '''
        
        data = PublicKraken().make_api_data(type=type, trades=trades, start=start, end=end, ofs=ofs)

        message = self.authenticate('TradesHistory', data)

        return message['trades']

    def get_open_positions(self, txid=None, docalcs=False, consolidation=None):
        # pretty self explanatory on this one
        '''
        args:
            * Optional: txid = transaction id to return
                - By default, set to 'None'
            * Optional: docalcs = True or False, if True then the returned data will include profit/loss calculations for the 'net' value
                - By default, set to 'False'
            * Optional: consolidated = if set to 'market' then the returned data will be consolidate into one position for each market
                - I.e. - if you have open 3 ETH positions and 5 BTC positons, 'market' will return only two positions- one for your average ETH and one for your average BTC
                - By default, set to 'None'.

        returns: 
            - A dictionary with txid as the key of open margin positions.
        -------------------------------------------------------------------------
            <position_txid> = open position info
                ordertxid = order responsible for execution of trade
                pair = asset pair
                time = unix timestamp of trade
                type = type of order used to open position (buy/sell)
                ordertype = order type used to open position
                cost = opening cost of position (quote currency unless viqc set in oflags)
                fee = opening fee of position (quote currency)
                vol = position volume (base currency unless viqc set in oflags)
                vol_closed = position volume closed (base currency unless viqc set in oflags)
                margin = initial margin (quote currency)
                value = current value of remaining position (if docalcs requested.  quote currency)
                net = unrealized profit/loss of remaining position (if docalcs requested.  quote currency, quote currency scale)
                misc = comma delimited list of miscellaneous info
                oflags = comma delimited list of order flags
                    viqc = volume in quote currency
        '''

        data = PublicKraken().make_api_data(txid=txid, docalcs=docalcs, consolidation=consolidation)
            
        message = self.authenticate('OpenPositions', data)

        return message

    def get_fee_volume(self, pair=None, fee_info=True):
        '''
        args:
            * Optional: pairs = if a pair, or list of pairs, is provided, then only fee data will be provided for those.
                - By default, set to 'None' which will return ALL fee volume data
            * Optional: fee_info = True or False, when set to True will return the fee information along with user's trade volume
                - By default, set to True
                **NOTICE: it appears this functionality is not working with Kraken right now.  Investigating as to why 'True' does not return fee info.  For now, will have to use the public method 'get_fees' in conjunction with the volume amount returned here.

        returns: 
            - A dictionary with volume and fee information.
        --------------------------------------------------------------------
            currency = volume currency
                volume = current discount volume
                fees = array of asset pairs and fee tier info (if requested)
                    fee = current fee in percent
                    minfee = minimum fee for pair (if not fixed fee)
                    maxfee = maximum fee for pair (if not fixed fee)
                    nextfee = next tier's fee for pair (if not fixed fee.  nil if at lowest fee tier)
                    nextvolume = volume level of next tier (if not fixed fee.  nil if at lowest fee tier)
                    tiervolume = volume level of current tier (if not fixed fee.  nil if at lowest fee tier)
                fees_maker = array of asset pairs and maker fee tier info (if requested) for any pairs on maker/taker schedule
                    fee = current fee in percent
                    minfee = minimum fee for pair (if not fixed fee)
                    maxfee = maximum fee for pair (if not fixed fee)
                    nextfee = next tier's fee for pair (if not fixed fee.  nil if at lowest fee tier)
                    nextvolume = volume level of next tier (if not fixed fee.  nil if at lowest fee tier)
                    tiervolume = volume level of current tier (if not fixed fee.  nil if at lowest fee tier)
        '''

        data = PublicKraken().make_api_data(pair=pair, fee_info=fee_info)

        message = self.authenticate('TradeVolume', data)

        return message

    def add_standard_order(self, pair, side, volume, ordertype='market', price=None, price2=None, leverage=None, oflags=None, start_time=0, expire_time=0, userref=None, validate=False):
        # creates an order for Kraken
            # either buy or sell (as side)
            # market, limit, stop-loss, take-profift, stop-loss-limit, take-profit-limit, settle-position
                # for limit orders, price = limit sell price
                # for stop-loss and take-profit orders, price = price at which a market order will be triggered
                # for stop-loss-limit and take-profit-limit, price = trigger price for the limit order and price2 = the limit order price.
            # oflag options include (entered in a comma delimited list): fcib = prefer fee in base currency, fciq = prefer fee in quote currency, nompp = no market price protection, post = post only order (only available with type = 'limit')
            # validate = True, validates inputs only - does not submit order to exchange
        # this will be used as teh backbone for most of our order functions
        '''
        args: 
            - pair = pair to trade
            - side = side of order ('buy' or 'sell')
            - volume = amount of currency to trade
                * Optional: ordertype =
                    - By default, set to 'market'.  Others include 'stop-loss', 'take-profit', 'stop-loss-limit', 'take-profit-limit', 'settle-position'
                * Optional: price = price at which to transact, if not market order.  If market order, the order will fill at the best available price
                * Optional: price2 = second price used for limit orders
                * Optional: leverage = amount of leverage to use
                    - see the PublicKraken method 'get_leverage_data' for various leverage options
                * Optional: oflags = list of order flags: 'fcib', 'fciq', 'nompp', 'post'
                * Optional: start_time = scheduled time to start the order, unix timestamp
                    - can use '+<timestamp>' to specify a time from the current time
                * Optional: expire_time = scheduled time to cancel the order, unix timestamp
                    - can use '+<timestamp>' to specify a time from the current time
                * Optional: userref = user reference id, 32-bit signed number
                * Optional: validate = True or False, when set to True will only test the inputs with Kraken's API, but will not send the order through
                    - By default, set to 'False'
        
        returns: 
            - Trade confirmation message from Kraken.
        -------------------------------------------------------------------------

        Notes:
            * You can use relative pricing except for trailing stops.  For example, you can order +1 or -1 for positive or negative $1 from the current price (if market order, consider the bid/ask side you wish to be one and adjust accordingly).
            * You can also use '#' ahead to either add or subtract depending on the bid/ask side of the order.
            * You can also suffix a % to signify the relative pricing as a percent. For example: -5%, +2%
            * If ordering with leverage, '0' can be used to automatically fill the volume needed to close out your position.
        -------------------------------------------------------------------------

        Input details:
            pair = asset pair
            type = type of order (buy/sell)
            ordertype = order type:
                market
                limit (price = limit price)
                stop-loss (price = stop loss price)
                take-profit (price = take profit price)
                stop-loss-limit (price = stop loss trigger price, price2 = triggered limit price)
                take-profit-limit (price = take profit trigger price, price2 = triggered limit price)
                settle-position
            price = price (optional.  dependent upon ordertype)
            price2 = secondary price (optional.  dependent upon ordertype)
            volume = order volume in lots
            leverage = amount of leverage desired (optional.  default = none)
            oflags = comma delimited list of order flags (optional):
                fcib = prefer fee in base currency
                fciq = prefer fee in quote currency
                nompp = no market price protection
                post = post only order (available when ordertype = limit)
            starttm = scheduled start time (optional):
                0 = now (default)
                +<n> = schedule start time <n> seconds from now
                <n> = unix timestamp of start time
            expiretm = expiration time (optional):
                0 = no expiration (default)
                +<n> = expire <n> seconds from now
                <n> = unix timestamp of expiration time
            userref = user reference id.  32-bit signed number.  (optional)
            validate = validate inputs only.  do not submit order (optional)
        
            optional closing order to add to system when order gets filled:
                close[ordertype] = order type
                close[price] = price
                close[price2] = secondary price
        '''
        if volume == None or volume == 0:
            raise Exception({'input_error':'Must enter in a volume for the trade'})

        if pair == None:
            raise Exception({'input_error':'Must enter in a valid trading pair for the trade'})
        else:
            pair = PublicKraken().pair_matching(pair)

        if side != 'buy' and side != 'sell':
            raise Exception({'input_error':"'side' must be either 'buy' or 'sell'"})


        data = PublicKraken().make_api_data(
            pair=pair, 
            type=side, 
            ordertype=ordertype, 
            price=price, 
            price2=price2, 
            volume=volume, 
            leverage=leverage, 
            oflags=oflags, 
            starttm=start_time, 
            expiretm=expire_time, 
            userref=userref, 
            validate=validate
        )

        message = self.authenticate('AddOrder', data)

        return message

    def market_buy(self, pair, volume, price=None, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
        # allows for a quick market buy (notice, 'side' is not an input option, but is automatically included as 'buy' as part of the data packet sent to the API)
        '''
        args: 
            - pair = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
            - volume = the lot size of the purchase.
                * Optional: price = the price at which to transact the market order
                * Optional: leverage = how much leverage to use.  See the Kraken documentation or PublicKraken.get_pair_info() for more information on a specific asset
                * Optional: oflags = fcib, fciq, nompp, post
                * Optional: start_time
                * Optional: expire_time
                * Optional: userref
                * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
        
        returns:
            - Order confirmation message
        '''
        # be sure servers are in full operational mode
        status = PublicKraken().get_system_status()
        if status[0] != 'online':
            raise Exception({'server_error':f'Server is in {status[0]} mode'})

        message = self.add_standard_order(
            pair=pair, 
            side='buy', 
            price=price, 
            ordertype='market', 
            volume=volume, 
            leverage=leverage, 
            oflags=oflags, 
            start_time=start_time, 
            expire_time=expire_time, 
            userref=userref, 
            validate=validate
        )

        return message

    def market_sell(self, pair, volume, price=None, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
        # allows for a quick market sell (notice, 'side' is not an input option, but is automatically included as 'sell' as part of the data packet sent to the API)
        '''
        args: 
            - pair = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
            - volume = the lot size of the purchase.
                * Optional: price = the price at which to transact the market order
                * Optional: leverage = how much leverage to use.  See the Kraken documentation or PublicKraken.get_pair_info() for more information on a specific asset
                * Optional: oflags = fcib, fciq, nompp, post
                * Optional: start_time
                * Optional: expire_time
                * Optional: userref
                * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
        
        returns:
            - Order confirmation message
        '''
        # be sure servers are in full operational mode
        status = PublicKraken().get_system_status()
        if status[0] != 'online':
            raise Exception({'server_error':f'Server is in {status[0]} mode'})

        message = self.add_standard_order(
            pair=pair, 
            side='sell', 
            price=price, 
            ordertype='market', 
            volume=volume, 
            leverage=leverage, 
            oflags=oflags, 
            start_time=start_time, 
            expire_time=expire_time, 
            userref=userref, 
            validate=validate
        )

        return message

    def limit_buy(self, pair, volume, price, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
        # allows for a quick limit buy (notice, 'buy' is not an input option, but is automatically included as 'buy' as part of the data packet sent to the API)
        '''
        args: 
            - pair = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
            - volume = the lot size of the purchase.
                * Optional: price = the price at which to transact the market order
                * Optional: leverage = how much leverage to use.  See the Kraken documentation or PublicKraken.get_pair_info() for more information on a specific asset
                * Optional: oflags = fcib, fciq, nompp, post
                * Optional: start_time
                * Optional: expire_time
                * Optional: userref
                * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
        
        returns:
            - Order confirmation message
        '''
        # be sure servers are in a limit order operational mode
        status = PublicKraken().get_system_status()
        if status[0] == 'maintenance' or status[0] == 'cancel_only':
            raise Exception({'server_error':f'Server is in {status[0]} mode'})

        message = self.add_standard_order(
            pair=pair, 
            side='buy', 
            price=price, 
            ordertype='limit', 
            volume=volume, 
            leverage=leverage, 
            oflags=oflags, 
            start_time=start_time, 
            expire_time=expire_time, 
            userref=userref, 
            validate=validate
        )

        return message

    def limit_sell(self, pair, volume, price, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
        # allows for a quick limit sell (notice, 'sell' is not an input option, but is automatically included as 'sell' as part of the data packet sent to the API)
        '''
        args: 
            - pair = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
            - volume = the lot size of the purchase.
                * Optional: price = the price at which to transact the market order
                * Optional: leverage = how much leverage to use.  See the Kraken documentation or PublicKraken.get_pair_info() for more information on a specific asset
                * Optional: oflags = fcib, fciq, nompp, post
                * Optional: start_time
                * Optional: expire_time
                * Optional: userref
                * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
        
        returns:
            - Order confirmation message
        '''
        # be sure servers are in a limit order operational mode
        status = PublicKraken().get_system_status()
        if status[0] == 'maintenance' or status[0] == 'cancel_only':
            raise Exception({'server_error':f'Server is in {status[0]} mode'})

        message = self.add_standard_order(
            pair=pair, 
            side='sell', 
            price=price, 
            ordertype='limit', 
            volume=volume, 
            leverage=leverage, 
            oflags=oflags, 
            start_time=start_time, 
            expire_time=expire_time, 
            userref=userref, 
            validate=validate
        )

        return message

    def cancel_single_order(self, txid):
        '''
        args:
            - 'txid' = transaction id of order to be cancelled

        returns:
            - Cancelled order message
        '''
        # be sure the system is in a cancelable state
        PublicKraken().guarantee_cancel()

        data = PublicKraken().make_api_data(txid=txid)

        message = self.authenticate('CancelOrder', data)

        return message

    def cancel_all_orders(self):
        '''
        Cancels ALL open orders.

        returns:
            - Cancelled order message
        '''
        # be sure the servers allow cancel orders
        PublicKraken().guarantee_cancel()

        data = PublicKraken().make_api_data()

        message = self.authenticate('CancelAll', data)

        return message

class KrakenWS:

    def __init__(self):
        self = self
    
    def get_ws_token(self):
        '''
        returns:
            - An authenticated websocket token
            * NOTICE: if not used, the token will expire within 15 minutes and a new token will have to be requested
        '''
        # will return the wwebsockets token that is needed for all ws function calls

        # create an empty 'data' dictionary since there are no fields to pass through
        data = {}

        # use the private function 'authenticate' to request a token from the REST API
        token = PrivateKraken().authenticate('GetWebSocketsToken', data)['token']

        # return the token
        return token

    def ws_name(self, pair):
        '''
        args:
            - pair = any trading pair name/names, i.e.- 'ethusd', ['btcusd', 'XMR/USD'], 'XXBTZUSD'
        
        returns:
            - wsname of specified trading pair/pairs
        '''
        # takes in any name and returns the wsname
            # can take a list (for multiple pairs) or a single string
        # this will mainly be used as a helper function within other functions to minimize naming convention errors
        
        url = 'https://api.kraken.com/0/public/AssetPairs'
        res = requests.get(url).json()

        # instantiate the list we will return from this funtion (if given a list), along with the naming classification dictionaries we will need.
        ws_names = []
        wsdict = {}
        altdict = {}

        # as long as Kraken is not returning an error, start the logic on converting the names to wsnames
        if not res['error']:
            # populate the wsdict and altdict with the wsnames and alternative names and then create a list of the key/value pairs so that we can index them later
            for coin in res['result']:
                try:
                    wsdict[coin] = res['result'][coin]['wsname']
                except KeyError: continue

            for coin in res['result']:
                try:
                    altdict[coin] = res['result'][coin]['altname']
                except KeyError: continue
            
            # don't actually need the keys for wsdict here, since the value is what we are trying to return any how.  
            wsdictvals = list(wsdict.values())

            altdictkeys = list(altdict.keys())
            altdictvals = list(altdict.values())

            # first thing to check is if the entered pair data is a list or not, if it is a list, return a list
            if type(pair) == list:
                for coin in pair:
                    coin = coin.upper()
                    # since BTC/USD is a common form people will use, but Kraken does not recognize, we will need to make a manual case for this one
                    if coin=='BTCUSD' or coin=='BTC/USD':
                        ws_names.append('XBT/USD')
                    # if the name entered is already in the Kraken trading format (i.e.- 'XETHZUSD') then return the wsname for it, otherwise we need to find the match
                    elif coin in res['result']:
                        ws_names.append(res['result'][coin]['wsname'])
                    else:
                        # if the name already exists in the wsname dictionary values, then the name is already in wsname format and we will add that to the list to return
                        if coin in wsdictvals:
                            ws_names.append(coin)
                        # otherwise, if the name is an alternative name we need to convert it to the wsname
                        elif coin in altdictvals:
                            pos = altdictvals.index(coin)
                            kname = altdictkeys[pos]
                            ws_names.append(wsdict[kname])
                        else:
                            raise Exception(f'Error Message: {coin} is not a recognized trading pair by Kraken.')
                            
                return ws_names

                # if the entered pair is not a list, then return a string following the same logic from above (just returning the values instead of adding them to a list)
            else:
                pair = pair.upper()

                if pair=='BTCUSD' or pair=='BTC/USD':
                    return 'XBT/USD'

                elif pair in res['result']:
                    return res['result'][pair]['wsname']
                else:

                    if pair in wsdictvals:
                        return pair

                    elif pair in altdictvals:
                        pos = altdictvals.index(pair)
                        kname = altdictkeys[pos]
                        return wsdict[kname]
                    else:
                        raise Exception(f'Error Message: {pair} is not a recognized trading pair by Kraken.')

        # if Kraken returns an error, then have the function return it as well
        else:
            raise Exception(res['error'])

    def ws_ticker(self, pair, reqid=None):
        '''
        args:
            -pair: valid Kraken trading pair, alternative name or wsname
        
        returns:
            -Dictionary of websocket data (see Kraken Websocket docs for full data definitioins)
        '''

        # create a function that will open a websockets connection to the Kraken websocket API and pull in the 'ticker' channel
        # this is a bunch of info about a ticker that comes in - if more specific data is needed, it is suggested to look at the other channels:
            # OHLC
            # Trades
            # Spread
            # Book

        # first, be sure the servers are online or at least in post_only mode
        PublicKraken().guarantee_online()

        # initiate our connection
        ws = websocket.create_connection('wss://ws.kraken.com/')

        # be sure 'pair' is in wsname format
        pair = self.ws_name(pair)

        # be sure 'pair' is a list
        if type(pair)==list:
            pair = pair
        else:
            pair = [pair]

        # create the payload to be sent to the websocket API
        if reqid==None:
            payload = json.dumps({
                'event': 'subscribe',
                'pair': pair,
                'subscription': {
                    'name': 'ticker'
                }           
            })
        else:
            payload = json.dumps({
                'event': 'subscribe',
                'pair': pair,
                'reqid': reqid,
                'subscription': {
                    'name': 'ticker'
                }
            })

        # send our packet along
        ws.send(payload)

        # loop through the returned data
        while True:
            trade_data = json.loads(ws.recv())

            return trade_data

        ws.close()


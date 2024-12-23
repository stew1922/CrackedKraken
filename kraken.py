# This is where all the Kraken API/websocket calls are located.  Do not modify unless you are fixing a bug.

import os
import json
import requests, urllib
from dotenv import load_dotenv
import hmac, base64, hashlib
import time
import pandas as pd
import websocket
import sqlite3
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import sys
import math

# load the .env file that your Kraken keys are stored in (must be at or above this library level)
load_dotenv()


class PublicKraken:
    '''
    Takes 'asset' which is either a single currency (i.e.- ETH, XETH, usd, etc.) or a trading pair (i.e.- ETHUSD, btcusd, LTC/eth, etc.).
    Can be a single entry, or a list of entries.
    '''

    def __init__(self, asset=None):
        self.asset = asset

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
        res = requests.get(url).json()

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
            return ['kraken_error', f"Error Message: {res['error']}"]

    def make_api_data(self, asset=None, aclass=None, trades=None, userref=None, start=None, end=None, ofs=None, closetime=None, type=None, txid=None, consolidation=None, docalcs=None, pair=None, fee_info=None, ordertype=None, price=None, price2=None, volume=None, leverage=None, oflags=None, starttm=None, expiretm=None, validate=None, since=None, info=None, activity=None, nonce=None):
        # simple function that will create the 'data' dictionary that will be used to pass information into any api calls
        # will be used only as a helper function and doesn't really need to be called on its own.
        # if you write any new functions, the inputs must be added as an argument to this function with a default value of 'None'
            # as long as the argument value is 'None' the data will not be included in the data package, only once the argument value is something other than 'None'
            # IF anyone has a better idea on how to handle this so that the argument list for this function is not as long, please make a fork and pull request with your solution (or let me know)
        data = {arg: value for arg, value in locals().items() if arg != 'endpoint' and arg != 'url' and arg != 'method' and value is not None and value is not False}

        return data

    def quote_order_min(self, currency=None):
        # returns the minimum order amounts for the different quote currencies: USD, EUR, AUD and GBP
        
        # first create a dictionary with the different quote currencies and their minimums
        quote_min = {}
        quote_min['ZUSD'] = 5
        quote_min['ZAUD'] = 5
        quote_min['ZGBP'] = 5
        quote_min['ZEUR'] = 5

        if self.asset == None:
            if currency == None:
                pass
            else:
                currency = currency
        else:
            currency = self.asset

        # match the input to the right dictionary entry
        if currency == None and self.asset == None:
            return quote_min
        else:
            return quote_min[f'{PublicKraken(currency).name_converter()}']

    def name_converter(self):
        # Function that converts asset names into Kraken compatible names.
        # Kraken uses the X-ISO4217-A3 system to name their assets.
        # See https://github.com/globalcitizen/x-iso4217-a3 for more info
        # this will mainly be used as a helper function within other functions to minimize naming convention errors
        '''
        returns:
            - The valid Kraken X-ISO4217-A3 ticker.
        '''
        if self.asset is None:
            raise Exception(f'No asset provided to PublicKraken instantiation.  Please provide an asset.')

        asset = self.asset

        # define the assets being requested
        if type(asset) == list:
            asset = [item.upper() for item in asset]
            request_assets = str()
            count = 0
            for assets in asset:
                count += 1
                if count == 1:
                    request_assets = assets
                else:
                    request_assets += ("," + assets)
        else:
            request_assets = asset.upper()
            asset = [asset.upper()]

        # make the request
        url = 'https://api.kraken.com/0/public/Assets'
        params = {
            'asset': request_assets
        }
        res = requests.get(url, params).json()

        # parse the data
        kraken_names = []
        if not res['error']:
            cryptos = {}
            for crypto in res['result']:
                if asset==crypto:
                    return crypto
                else:
                    cryptos[crypto] = res['result'][crypto]['altname']

            cryptoskeys = list(cryptos.keys())
            cryptosvals = list(cryptos.values())

            for assets in asset:
                if assets == 'BTC':
                    kraken_names.append('XXBT')
                elif assets == 'DOGE':
                    kraken_names.append('XXDG')
                elif assets in cryptosvals:
                    pos = cryptosvals.index(assets)
                    kraken_name = cryptoskeys[pos]
                    kraken_names.append(kraken_name)
                elif assets in cryptoskeys:
                    kraken_name = assets
                    kraken_names.append(kraken_name)
                else:
                    print(f'WARNING: {assets} is not a name Kraken recognizes.  Use "get_asset_info" without passing an asset into the function to get a full list of Kraken recongized assets.')
                
            return kraken_names

        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def pair_matching(self):
        # takes in wsname or altname and returns the Kraken pair name
        # this will mainly be used as a helper function within other functions to minimize naming convention errors
        '''
        returns:
            - A valid Kraken recognized trading pair
        '''
        if self.asset is None:
            raise Exception(f'No asset provided to PublicKraken instantiation.  Please provide an asset.')

        # convert asset to list if not already
        if type(self.asset) == list:
            trading_pair = self.asset
        else:
            trading_pair = [self.asset]
        
        # be sure all items in the list are in upper case
        trading_pair = [item.upper() for item in trading_pair]
        
        # create a string to pass as the requested pairs to the API
        count = 0
        for pair in trading_pair:
            count = 1
            if count == 1:
                request_pair = pair
            else:
                request_pair += ("," + pair)

        # make the API request
        url = 'https://api.kraken.com/0/public/AssetPairs'
        params = {
            'pair': request_pair
        }
        res = requests.get(url).json()

        # parse the data
        if not res['error']:
            # check to see if each 'trading_pair' is already a valid Kraken pair
            new_pairs = []
            for coin in trading_pair:
                coin = coin.upper()
                if coin == 'BTCUSD' or coin == 'BTC/USD':
                    new_pairs.append('XXBTZUSD')
                elif coin == 'DOGEUSD' or coin == 'DOGE/USD':
                    new_pairs.append('XDGUSD')
                elif coin in res['result']:
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

                    # create a list for the keys and the values of altdict
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

        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_asset_pairs(self):
        '''
        returns:
            - A list of all available asset trading pairs from Kraken
        '''

        url = 'https://api.kraken.com/0/public/AssetPairs'

        message = requests.get(url).json()

        if not message['error']:
            assetpairs = []
            for assetpair in message['result']:
                assetpairs.append(assetpair)
            return assetpairs
        else:
            raise Exception({'kraken_error': f'Error Message: {message["error"]}'})

    def get_wsname(self):
        # function that will return the wsname of Kraken trading pair (if it exists)
        '''
        returns:
            - wsname/list of wsnames of asset(s) provided in PublicKraken instantiation
        '''
        pair = PublicKraken(self.asset).pair_matching()
        count = 0
        for pairs in pair:
            count += 1
            if count == 1:
                request_pair = pairs
            else:
                request_pair += ("," + pairs)
        
        url = 'https://api.kraken.com/0/public/AssetPairs'
        params = {
            'pair': request_pair
        }
        message = requests.get(url, params).json()

        wsname = []
        for crypto in pair:
            wsname.append(message['result'][crypto]['wsname'])

        return wsname

    def get_asset_common_name(self):
        # function that will return the common name of Kraken asset (if it exists)
        '''
        returns:
            - common name/list of common names of asset(s) provided in PublicKraken instantiation
        '''
        
        asset = PublicKraken(self.asset).name_converter()
        count = 0
        for assets in asset:
            count += 1
            if count == 1:
                request_assets = assets
            else:
                request_assets += ("," + assets)


        url = 'https://api.kraken.com/0/public/Assets'
        params = {
            'asset': request_assets
        }
        message = requests.get(url, params).json()


        common_name = []
        if type(asset) == list:
            for crypto in asset:
                if crypto == 'XXBT':
                    common_name.append('BTC')
                elif crypto == 'XXDG':
                    common_name.append('DOGE')
                else:
                    common_name.append(message['result'][crypto]['altname'])
        
        else:
            if asset == 'XXBT':
                common_name = 'BTC'
            elif asset == 'XXDG':
                common_name = 'DOGE'
            else:
                common_name = message['result'][asset]['altname']

        return common_name

    def get_pair_common_name(self):
        # function that will return the common name of Kraken trading pair (if it exists)
        '''
        returns:
            - wsname/list of wsnames of asset(s) provided in PublicKraken instantiation
        '''
        
        pair = PublicKraken(self.asset).pair_matching()
        count = 0
        for pairs in pair:
            count += 1
            if count == 1:
                request_pair = pairs
            else:
                request_pair += ("," + pairs)
        
        url = 'https://api.kraken.com/0/public/AssetPairs'
        params = {
            'pair': request_pair
        }
        message = requests.get(url, params).json()


        wsname = []
        for crypto in pair:
            if crypto == 'XXBTZUSD':
                wsname.append('BTC/USD')
            elif crypto == 'XXDGZUSD':
                wsname.append('DOGE/USD')
            else:
                wsname.append(message['result'][crypto]['wsname'])

        return wsname

    def get_pair_info(self, info='info'):
        '''
        args:
            *Optional: info = information to be returned
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
            pair_decimals = scaling decimal places for pair
            cost_decimals = scaling decimal places for cost
            lot_decimals = scaling decimal places for volume
            lot_multiplier = amount to multiply lot volume by to get currency volume
            leverage_buy = array of leverage amounts available when buying
            leverage_sell = array of leverage amounts available when selling
            fees = fee schedule array in [volume, percent fee] dictionary
            fees_maker = maker fee schedule array in [volume, percent fee] dictionary (if on maker/taker)
            fee_volume_currency = volume discount currency
            margin_call = margin call level
            margin_stop = stop-out/liquidation margin level
            ordermin = minimum order volume for pair
            costmin = minimum order cost (in terms of quote currency)
            tick_size = minimum increment between valid price levels
            status = status of asset, possible values: 'online', 'cancel_only', 'post_only', 'limit_only', 'reduce_only'
            long_position_limit = maximum long margin position size (in terms of base currency)
            short_position_limit = maximum short margin position size (in terms of base currency)
        '''
        
        # if a pair has been provided, convert the pair name to a valid Kraken traing pair format
        if self.asset != None:
            pair = self.pair_matching()
        else:
            pair = self.asset

        url = 'https://api.kraken.com/0/public/AssetPairs'

        # the 'pair' name or list must be a string when sent as part of the request
        pair_string = str()
        if type(pair) == None:
            pass
        elif type(pair) == list:
            for crypto in pair:
                pair_string += ',' + crypto
            pair_string = pair_string[1:]
        
        else:
            pair_string = str(pair)

        # if pair and/or info is passed as an argument send that in the API request package
        if pair != None and info != 'info':
            data = self.make_api_data(pair=pair_string, info=info)
        elif pair != None and info == 'info':
            data = self.make_api_data(pair=pair_string)
        elif pair == None and info != 'info':
            data = self.make_api_data(info=info)
        else:
            data = {}

        # send and receive the API request
        message = requests.get(url, data=data).json()
        
        # return the result
        if not message['error']:
            if pair == None or len(pair) > 1:
                return message['result']
            else:
                return message['result'][pair[0]]
        else:
            raise Exception({'kraken_error': f'Error Message: {message["error"]}'})

    def get_asset_info(self):
            # find all the info for a certain asset
            # info includes:
                # 'altname' = alternative name, ie: XETH --> ETH
                # 'aclass' = asset class (currency, futures, etc.)
                # 'decimals' = scaling decimal places for record keeping
                # 'display_decimals' = scaling decimal places for output display
                # 'collateral_value' = valuation as margin collateral (if applicable)
                # 'status' = status of asset, possible values: 'enabled', 'deposit_only', 'withdrawal_only', 'funding_temporarily_disabled'
            '''
            returns:
                - A dictionary of asset info.
            '''

            if type(self.asset) == list:
                asset = self.asset
            elif self.asset == None:
                asset = self.asset
            else:
                asset = [self.asset]

            if asset != None:
                asset = [item.upper() for item in asset]
                count = 0
                for assets in asset:
                    count += 1
                    if count == 1:
                        request_asset = assets
                    else:
                        request_asset += ("," + assets)
            else:
                request_asset = None

            url = 'https://api.kraken.com/0/public/Assets'
            params = {
                'asset': request_asset
            }
            res = requests.get(url, params).json()
            
            asset_dict = {}
            if not res['error']:
                if asset == None:
                    return res['result']
                else:
                    for name in res['result']:
                        output = PublicKraken(name).name_converter()
                        asset_dict[output[0]] = res['result'][name]
            else:
                raise Exception({'kraken_error': f'Error Message: {res["error"]}'})
            
            return asset_dict

    def get_fees(self, maker_taker=None, volume=None):
        # return a dictionary of a dictionary of the fees associated with the provided pair
        # {'taker': {volume1: fee1, volume2: fee2}, 'maker': {volume1: fee1, volume2: fee2}}
        # if your monthly volume is equal to OR more than the listed volume, then the associated fee is your fee in percent
        '''
        args:
            * Optional: 'maker_taker' which can be either 'maker' or 'taker'.  If neither are provided, both fee tiers are returned.
                - Default is set to 'None'
            * Optional: 'volume' which is the user's volume in $.  If none is provided, all tiers are returned.
                - Default is set to 'None'
                
        returns:
            - A dictionary of taker and maker fee tiers.  Volume is given in $ amount and fees are given in percents.
        ''' 

        url = 'https://api.kraken.com/0/public/AssetPairs'
        res = requests.get(url).json()

        pair = self.pair_matching()[0]

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

    def get_ticker_info(self, pair=None, info=None):
        # returns the current order book level one for a given pair
            # NOTICE: this endpoint can only take one pair...if the pair is left blank (in the instanciation of the PublicKraken() class, then
            # this function will return ALL tradeable assets on Kraken)
        '''
        args:
            - OPTIONAL: info = info to return
                *options include current ask, current bid, last trade (aka current price), volume, 24 hour vwap, 24 hour trade count, 24 hour low, 24 hour high, today's open
        returns:
            - A dicitonary ticker data: 
                a = current ask: [price, whloe lot volume, lot volume]
                b = current bid: [price, whloe lot volume, lot volume]
                c = last trade: [price, lot volume]
                v = volume: [today, last 24 hours]
                p = volume weighted price: [today, last 24 hours]
                t = number of trades: [today, last 24 hours]
                l = low: [today, last 24 hours]
                h = high: [today, last 24 hours]
                o = opening price: [today]
        '''
        info_dict = {'ask': 'a',
                     'bid': 'b',
                     'current': 'c',
                     'volume': 'v',
                     'vwap': 'p',
                     'trades': 't',
                     'low': 'l',
                     'high': 'h',
                     'open': 'o'
                     }

        url = 'https://api.kraken.com/0/public/Ticker'
        if pair is not None:
            pair = PublicKraken(pair).pair_matching()
        elif self.asset is not None:
            pair = self.pair_matching()
        
        params = {'pair': pair}
        res = requests.get(url, params).json()
        
        if not res['error']:
            if info is not None:
                return res['result'][pair[0]][info_dict[info]]
            else:
                return res['result']
        else:
            raise Exception({'kraken_error': f"Error Message: {res['error']}"})

    def get_ohlc(self, interval=None, since=None):
        # returns the last 720 iterations of periods that you feed it, i.e.- default is minutes, so you would recieve the last 720 minutes. If you input 'D' you would get the last 720 days on a daily timescale.
        # if more data is needed, utilize the ohlc_df function in data.py
        '''
        args:
            * Optional: 'interval' which is the time frame interval (can take string or int -- for the 1 minute interval, you can enter either '1' or 'min').
            * Optional: 'since' which is the unix timestamp from which to start the data pull (Kraken limits you to 720 iterations)
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
        pair = self.pair_matching()[0]

        params = {
            'pair': pair,
            'interval': interval,
            'since': since}

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

    def get_ohlc_dataframe(self, interval=None, since=None):
        # similar to get_ohlc, except returns a dataframe instead of a dictionary of dictionaries
        '''
        Similar to 'get_ohlc', except returns a dataframe instead of a dictionary of dictionaries.
            Note: if more data is needed, utilized the ohlcv_df() function on data.py
        
        args:
            * Optional: 'interval' which is the time frame interval.
                - Default is set to 'None' and returns a 1 minute interval
            * Optional: 'since' which is the unix timestamp from which to start the data pull (Kraken limits you to 720 iterations)
                - Default is set to 'None' and returns the next 720 interations

        returns: 
            - A pandas dataframe with a timestamp index and columns 'date', 'open', 'high', 'low', 'close', 'volume', 'trade_count', 'vwap'
        '''
        
        data = self.get_ohlc(interval, since)

        df = pd.DataFrame(data).T
        df['date'] = pd.to_datetime(df.index, unit='s')

        df.rename(columns={'count':'trade_count'}, inplace=True)
        
        df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'trade_count', 'vwap']]

        return df

    def get_order_book(self, count=None):
        # function that will return a dictionary of dictionaries of the asks and bids
        '''
        * Optional: 'count' which is the maximium number of bids/asks.  
            - By default set to 'None' which returns all bids/asks.

        returns: 
            - A dictionary of dictionaries of bids and asks.
        '''

        pair = self.pair_matching()[0]

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

    def get_asks(self, count=None):
        # returns only the asks for a selected pair
        '''
        args:
            *Optional: 'count' which is the maximum number of asks to return.
                - Default is set to 'None' which returns all asks.

        returns: 
            - A list of list of each ask -- [[price, volume, timestamp]]
        '''
        asks = self.get_order_book(count)

        return asks['asks']

    def get_bids(self, count=None):
        # returns only the bids for a selected pair
        '''
        args:
            * Optional: 'count' which is the maximum number of bids to return.
                - By Default, set to 'None' which returns all bids

        -Returns: a list of list of each bid -- [[price, volume, timestamp]]
        '''
        bids = self.get_order_book(count)

        return bids['bids']

    def get_current_bid(self):
        # returns the current bid for a selected pair
        '''
        returns: 
            - A list of current bid info -- [price, volume, timestamp]
        '''
        bid = self.get_order_book()

        return bid['bids'][0]

    def get_current_ask(self):
        # returns the current bid for a selected pair
        '''
        returns: 
            - A list of current ask info -- [price, volume, timestamp]
        '''
        ask = self.get_order_book()

        return ask['asks'][0]

    def get_leverage_data(self, side=None):
        '''
        args:
            *Optional: side = whether it is buy-side or sell-side leverage (i.e.- long or short)
                - Default is set to None and returns both buy and sell side leverage

        returns: 
            - A dictionary or list of all available leverage position sizes for that asset.
                i.e. - {'buy': [2, 3, 4, 5], 'sell': [2, 3, 4, 5]}
        '''
        if side == None:
            leverage = {'buy': self.get_pair_info()['leverage_buy'], 'sell': self.get_pair_info()['leverage_buy']}
        else:
            leverage = self.get_pair_info()[f'leverage_{side}']

        return leverage

    def get_historical_data(self, start_time=None):

        '''
        args:
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
        pair = self.pair_matching()

        # subscribe to the 'Trades' endpoint
        url = 'https://api.kraken.com/0/public/Trades'

        # if start_time==None, then pull the default which is the most recent 1000 trades, otherwise pull in trades since the start_time
            # caveat: the API only allows you to pull in 1000 trades at a time, so if you want more than that you will have to loop through function using the previous 1000 trades' most recent trade as the new start_time
        data = self.make_api_data(pair=pair, since=start_time)  

        message = requests.get(url, data).json()

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
                        message = requests.get(url, data).json()

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
                        time.sleep(max_calls * call_add_rate)
                        call_count = max_calls - 1
                return hist
        
        else:
            raise Exception({'kraken_error': f'Error Message: {message["error"]}'})

    def guarantee_online(self):
        '''
        This is a function that will run an infinite loop until the server is 'online' and fully operational
        '''

        # this function will check to see if the Kraken server is in 'online' mode, otherwise it will wait 4 seconds and then try again
        # the 4 second wait will ensure you do not exceed your API call limits
        is_online = self.get_system_status()

        while is_online[0] != 'online':
            if is_online[0] == 'kraken_error':
                print(f'Kraken Servers are unresponsive.  {is_online[1]}')
                time.sleep(4)
            else:
                print(f'Kraken Servers are in {is_online[0]} mode.  Time checked is {is_online[1]}')
                time.sleep(4)
            
            is_online = self.get_system_status()

    def guarantee_limit(self):
        '''
        This is a function that will run an infinte loop until the server allows at least limit orders.
            *WARNING: this function does not guarantee all order types.  If you need to place an order (especially a market order) utilize the 'guarantee_online' function
        '''
        # this function will check to see if the Kraken server is in an operational mode (either 'online' or 'post_only' or 'limit_only'), otherwise it will wait 4 seconds and then try again
        # the 4 second wait will ensure you do not exceed your API call limits
        is_limit = self.get_system_status()

        while is_limit[0] != 'online' or is_limit != 'post_only' or is_limit != 'limit_only':
            if is_limit[0] == 'kraken_error':
                print(f'Kraken Servers are unresponsive.  {is_limit[1]}')
                time.sleep(4)
            else:
                print(f'Kraken Servers are in {is_limit[0]} mode.  Time checked is {is_limit[1]}')
                time.sleep(4)
                is_limit = self.get_system_status()

            is_limit = self.get_system_status()

    def guarantee_cancel(self):
        '''
        This is a function that will run an infinte loop until the server is in a cancelable state.
            *WARNING: this will not guarantee a mode that allows order placing, rather it only guarantees order cancelling.
        '''
        # this function will check to see if the Kraken server is in a cancel mode (either 'online' or 'post_only' or 'limit_only' or 'cancel_only'), otherwise it will wait 4 seconds and then try again
        # the 4 second wait will ensure you do not exceed your API call limits
        is_cancellable = self.get_system_status()

        while is_cancellable[0] == 'maintenance' or is_cancellable[0] == 'kraken_error':
            if is_cancellable[0] == 'kraken_error':
                print(f'Kraken Servers are unresponsive.  {is_cancellable[1]}')
                time.sleep(4)
            else:
                print(f'Kraken Servers are in {is_cancellable[0]} mode.  Time checked is {is_cancellable[1]}')
                time.sleep(4)
                is_cancellable = self.get_system_status()
            
            is_cancellable = self.get_system_status()

    def guarantee_operational(self):
        '''
        This is a function that will run an infinte loop until the server is in a operational state.
            *WARNING: this will not guarantee a mode that allows order placing, rather it only guarantees that the server is responsive.
        '''
        # this function will check to see if the Kraken server is in a cancel mode (either 'online' or 'post_only' or 'limit_only' or 'cancel_only'), otherwise it will wait 4 seconds and then try again
        # the 4 second wait will ensure you do not exceed your API call limits
        is_operational = self.get_system_status()

        while is_operational[0] == 'kraken_error':
            if is_operational[0] == 'kraken_error':
                print(f'Kraken Servers are unresponsive.  {is_operational[1]}')
                time.sleep(4)
            else:
                print(f'Kraken Servers are in {is_operational[0]} mode.  Time checked is {is_operational[1]}')
                time.sleep(4)
                is_operational = self.get_system_status()
            
            is_operational = self.get_system_status()


class PrivateKraken:

    def __init__(self, asset=None, userref=None):
        '''
        Args:
            - *Optional: asset = asset to hold as an argument for any method
            - *Optional: userref = the user reference id to pull data for
        '''
        self.asset = asset

        # userref can be used to define different "sub accounts", much like portfolios on Coinbase.  This is only useful for different bots to trade on different strategies at the same time
        # Not required
        self.userref = userref

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

        nonce = str(int(1000 * time.time()))
        data['nonce'] = nonce

        postdata = urllib.parse.urlencode(data)
        encoded = (nonce + postdata).encode()
        message = method.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(self.krakenprivatekey), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())

        headers = {
            'API-Key': self.krakenapi,
            'API-Sign': sigdigest.decode()
        }
        res = requests.post(url, headers=headers, data=data).json()

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
        # be sure that (if supplied) the asset is in the Kraken recognized variant
        if asset == None and self.asset != None:
            asset = self.asset

        if asset is not None:
            asset = PublicKraken(asset).name_converter()

        data = PublicKraken().make_api_data()

        message = self.authenticate('Balance', data)

        if asset is not None:
            return message[asset[0]]
        else:
            return message

    def get_trade_balance(self, currency='ZUSD'):
        # returns a user's total balance available in a given currency, USD is default
            # Note: you can also choose the class of asset ('aclass'), but Kraken currently (1.17.2021) only has currency, 
            # so currency is the default option and likely does not need to be changed.
        '''
        args:
            *Optional: 'currency' = currency the data is returned as.
                - By default, currency is set to 'ZUSD'.  Takes either the offical Kraken name, wsname or alternative name.
            *Optional: 'aclass' = asset class to return balance for.
                - By default, asset class is set to 'currency'.  Kraken currently (01.17.2021) only lists currecies, so this should not be changed.

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
        
        asset = PublicKraken(currency).get_asset_common_name()[0]

        data = PublicKraken().make_api_data(asset=asset)

        message = self.authenticate('TradeBalance', data)

        return message

    def get_open_orders(self, trades=None):
        '''
        args:
            *Optional: trades = True or False, determines whether to include trades in output.
                - By default, set to 'False'.

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
        data = PublicKraken().make_api_data(trades=trades, userref=self.userref)

        message = self.authenticate('OpenOrders', data)

        return message['open']

    def get_closed_orders(self, trades=None, start=None, end=None, ofs=None, closetime=None):
        '''
        -args: 
            * Optional: trades, start, end, ofs or closetime.
                - By default, all optional inputs are set to None.

        -returns: 
            * A dictionary of closed order information with the Transaction ID as the key.  It is empty if there are no closed orders.
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
        
        data = PublicKraken().make_api_data(trades=trades, userref=self.userref, start=start, end=end, ofs=ofs, closetime=closetime)

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
        # pretty self explanatory on this one - open margin positions
        '''
        args:
            * Optional: txid = transaction id to return
                - By default, set to 'None'
            * Optional: docalcs = True or False, if True then the returned data will include profit/loss calculations for the 'net' value
                - By default, set to 'False'
            * Optional: consolidation = if set to 'market' then the returned data will be consolidated into one position for each market
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

        if not message:
            return message
        else:
            if consolidation == 'market':
                return message[0]
            else:
                return message

    def get_trade_volume_info(self, fee_info=True):
        '''
        args:
            * Optional: fee_info = True or False, when set to True will return the fee information along with user's trade volume
                - By default, set to True
                **NOTICE: it appears this functionality is not working with Kraken right now.  Investigating as to why 'False' returns everything.

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
        pair = PublicKraken(self.asset).pair_matching()

        # if multiple pairs being passed, must put it in a string to send to the API
        if len(pair) > 1:
            pair = ','.join(pair)
        else:
            pair = pair[0]

        data = PublicKraken().make_api_data(pair=pair, fee_info=fee_info)

        message = self.authenticate('TradeVolume', data)

        return message

    def get_user_fees(self, schedule, pair=None):
        '''
        args:
            - schedule = either 'maker' or 'taker'
            * Optional: pair = the trading pair to return user maker fees, if provided overides instantiation pair
                - By default, set to None

        returns: 
            - the maker fee for the given trading pair
        '''
        if pair != None:
            pair = pair
        else:
            pair = self.asset

        pair = PublicKraken(pair).pair_matching()

        # if multiple pairs being passed, must put it in a string to send to the API
        if len(pair) > 1:
            pair_str = ','.join(pair)
        else:
            pair_str = pair[0]

        data = PublicKraken().make_api_data(pair=pair_str)

        trade_volume_info = self.authenticate('TradeVolume', data)

        fee_dict = {}
        for pair in pair:
            # if the pair is not on a maker/taker system, then only the taker fee will be returned
            if schedule == 'maker':
                if not trade_volume_info['fees_maker']:
                    user_fee = trade_volume_info['fees'][pair]['fee']
                else:
                    user_fee = trade_volume_info['fees_maker'][pair]['fee']
            elif schedule == 'taker':
                user_fee = trade_volume_info['fees'][pair]['fee']
            else:
                raise Exception("input_error:'schedule' provided must be either 'taker' or 'maker'")
            
            fee_dict[pair] = float(user_fee)

        return fee_dict

    def add_standard_order(self, side, volume=None, ordertype='market', price=None, price2=None, leverage=None, oflags=None, start_time=0, expire_time=0, validate=False):
        # creates an order for Kraken
            # either buy or sell (as side)
            # market, limit, stop-loss, take-profift, stop-loss-limit, take-profit-limit, settle-position
                # for limit orders, price = limit sell price
                # for stop-loss and take-profit orders, price = price at which a market order will be triggered
                # for stop-loss-limit and take-profit-limit, price = trigger price for the limit order and price2 = the limit order price.
            # oflag options include (entered in a comma delimited list): fcib = prefer fee in base currency, fciq = prefer fee in quote currency, nompp = no market price protection, post = post only order (only available with type = 'limit')
            # validate = True, validates inputs only - does not submit order to exchange
        # this will be used as the backbone for most of our order functions
        '''
        args: 
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
        pair = PublicKraken(self.asset).pair_matching()[0]
        
        if volume != None and float(volume) < 0:
            raise Exception({'input_error':'Must enter in a positive volume for the trade'})

        if side != 'buy' and side != 'sell':
            raise Exception({'input_error':"'side' must be either 'buy' or 'sell'"})

        data = PublicKraken().make_api_data(
            userref = self.userref, 
            ordertype = ordertype, 
            type = side, 
            volume = volume, 
            pair = pair, 
            price = price, 
            price2 = price2, 
            leverage = leverage, 
            oflags = oflags, 
            starttm = start_time, 
            expiretm = expire_time, 
            validate = validate
        )
 
        message = self.authenticate('AddOrder', data)

        return message

    def market_buy(self, volume=None, leverage=None, oflags=None, start_time=None, expire_time=None, validate=False):
        # allows for a quick market buy (notice, 'side' is not an input option, but is automatically included as 'buy' as part of the data packet sent to the API)
        '''
        args: 
            - volume = the lot size of the purchase
                * Default volume is given in base currency...if using quote currency oflag "viqc" MUST be used
            * Optional: leverage = how much leverage to use.  See the Kraken documentation or PublicKraken().get_pair_info() for more information on a specific asset
            * DEPRECATED Optional: max_slippage = maximum slippage to allow when using 'quote_amount' -- provided as a number (i.e.: 1% slippage == 0.01)
            * Optional: oflags = fcib, fciq, nompp, post, viqc (supposedly this works now?)
            * Optional: start_time
            * Optional: expire_time
            * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
        
        returns:
            - Order confirmation message
        '''
        # be sure servers are in full operational mode
        PublicKraken().guarantee_online()

        # pull in the pair info for the pair being traded
        pair_info = PublicKraken(self.asset).get_pair_info()

        # define the quote currency and the base currency and their maximum decimals
        quote = pair_info['quote']
        base = pair_info['base']

        # check to see if your order size is large enough (Kraken employs size limits so you can do very small txns)
        base_min = float(pair_info['ordermin'])
        quote_min = float(pair_info['costmin'])

        if oflags != 'viqc':
            if volume < base_min:
                raise Exception(f"Attempted {base} volume is smaller than Kraken limits.  Please increase the {base} volume and try again.")
        else:
            if volume < quote_min:
                raise Exception(f"Attempted {quote} amount is smaller than Kraken limits.  Please increase the {quote} amount and try again")
            
        message = PrivateKraken(self.asset).add_standard_order(
            side='buy', 
            ordertype='market', 
            volume=str(volume), 
            leverage=leverage, 
            oflags=oflags, 
            start_time=start_time, 
            expire_time=expire_time, 
            validate=validate
        )
        print(message)
        print(f'Purchased Volume = {volume}{"USD" if oflags=="viqc" else "ETH"}')

    def market_sell(self, volume=None, quote_amount=None, leverage=None, max_slippage=None, oflags=None, start_time=None, expire_time=None, validate=False):
        #***BIG NOTICE: using 'quote_amount' is not ready yet and may return inconsistent results.  Unless you feel like gambling, use 'volume' only for now.
        
        # allows for a quick market sell (notice, 'side' is not an input option, but is automatically included as 'sell' as part of the data packet sent to the API)
        '''
        args: 
            - volume = the lot size of the purchase
            - quote_amount = amount in quote currency to purchase (this cannot be given if 'volume' is also given)
            * Optional: leverage = how much leverage to use.  See the Kraken documentation or PublicKraken.get_pair_info() for more information on a specific asset
            * Optional: max_slippage = maximum slippage to allow when using 'quote_amount' -- provided as a number (i.e.: 1% slippage == 0.01)
            * Optional: oflags = fcib, fciq, nompp, post
            * Optional: start_time
            * Optional: expire_time
            * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
        
        returns:
            - Order confirmation message
        '''
        # be sure servers are in full operational mode
        PublicKraken().guarantee_online()

        # pull in the pair info for the pair being traded
        pair_info = PublicKraken(self.asset).get_pair_info()

        # define the quote currency and the base currency and their maximum decimals
        quote = pair_info['quote']
        base = pair_info['base']

        quote_decimals = pair_info['pair_decimals']
        base_decimals = pair_info['lot_decimals']

        # check to see if your order size is large enough (Kraken employs size limits so you can do very small txns)
        base_min = float(pair_info['ordermin'])
        quote_min = float(pair_info['costmin'])

        if volume != None:
            if float(volume) < base_min:
                raise Exception(f"Attempted {base} volume is smaller than Kraken limits.  Please increase the {base} volume and try again.")

        if quote_amount is not None:
            if float(quote_amount) < quote_min:
                raise Exception(f"Attempted {quote} amount is smaller than Kraken limits.  Please increase the {quote} amount and try again")
            
        # if both volume and quote_amount are given, throw an Exception as this could cause an error if they are conflicting
        if volume != None and quote_amount != None:
            raise Exception("Both 'volume' and 'quote_currency' cannot be specified.  Please choose only one and try again.")
            
        # if no volume is provided and a quote amount is, then loop through the order book until no quote amount is left
        elif volume == None and quote_amount != None:
            # create a loop that goes through the order book until there is no quote_amount left
            quote_amount_left = float(quote_amount)
                
            initial_bid = float(PublicKraken(self.asset).get_current_bid()[0])

            trade_count = 0

            while quote_amount_left >= quote_min:
                # first pull in the current bid -- good thing I was smart enough to make a function for this already!  :)
                trade_count += 1

                current_bid = PublicKraken(self.asset).get_current_bid()

                bid_price = float(current_bid[0])
                
                # make sure we haven't exceeded max_slippage (if present), if so, end the loop by setting quote_amount_left to 0
                slippage = abs(((bid_price - initial_bid) / initial_bid))
                if max_slippage != None:
                    if slippage > max_slippage:
                        quote_amount_left = 0
                        print('max slippage reached')
                        break

                bid_volume = float(current_bid[1])
                bid_value = bid_price * bid_volume

                # choose an order_volume that can be supported by the quote_amount_left
                if bid_value >= quote_amount_left:
                    order_volume = Math.round_down((quote_amount_left / bid_price), base_decimals) * 0.99
                else:
                    order_volume = bid_volume * 0.99

                # create the market order using the order_volume
                message = PrivateKraken(self.asset).add_standard_order(
                    side='sell', 
                    ordertype='market', 
                    volume=str(order_volume), 
                    leverage=leverage, 
                    oflags=oflags, 
                    start_time=start_time, 
                    expire_time=expire_time, 
                    validate=validate
                )

                print(message)

                # if the current order reduces the 'quote_amount_left' to less than $10 USD, then we need to end the loop 
                trade_volume = float(message['descr']['order'].split()[1])

                quote_amount_left -= (trade_volume * bid_price)
                quote_amount_left = Math.round_down(quote_amount_left, quote_decimals)
                
                print(f'Asset Price: ${Math.round_down(bid_price, 2)}, Total Volume on the Bid: {Math.round_down(bid_volume, 2)}, Total Value on the Bid: ${Math.round_down(bid_value, 2)}')    
                print(f'Quote Amount Spent: ${bid_value if bid_value <= quote_amount_left else (Math.round_down(order_volume * bid_price, 2))}, Quote Amount Left: ${quote_amount_left}, Number of Trades: {trade_count}')
                print()
            
        # otherwise make a standard market order with the asset volume
        else:
            message = PrivateKraken(self.asset).add_standard_order(
                side='sell', 
                ordertype='market', 
                volume=str(volume), 
                leverage=leverage, 
                oflags=oflags, 
                start_time=start_time, 
                expire_time=expire_time, 
                validate=validate
            )

        print(message)

    def limit_buy(self, volume, price, leverage=None, oflags=None, start_time=None, expire_time=None, validate=False):
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
                * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
        
        returns:
            - Order confirmation message
        '''
        # be sure servers are in a limit order operational mode
        status = PublicKraken().get_system_status()
        if status[0] == 'maintenance' or status[0] == 'cancel_only':
            raise Exception({'server_error':f'Server is in {status[0]} mode'})

        message = self.add_standard_order( 
            side='buy', 
            price=price, 
            ordertype='limit', 
            volume=volume, 
            leverage=leverage, 
            oflags=oflags, 
            start_time=start_time, 
            expire_time=expire_time,
            validate=validate
        )

        return message

    def limit_sell(self, volume, price, leverage=None, oflags=None, start_time=None, expire_time=None, validate=False):
        # allows for a quick limit sell (notice, 'sell' is not an input option, but is automatically included as 'sell' as part of the data packet sent to the API)
        '''
        args: 
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
            side='sell', 
            price=price, 
            ordertype='limit', 
            volume=volume, 
            leverage=leverage, 
            oflags=oflags, 
            start_time=start_time, 
            expire_time=expire_time, 
            validate=validate
        )

        return message

    def close_short_position(self, volume=None, oflags=None, start_time=None, expire_time=None, validate=False):
        # allows for you to close open leveraged short positions
        '''
        args:
            * Optional: volume = volume, in lots, that you wish to close, default = volume of entire open position
            * Optional: oflags = fcib, fciq, nompp, post
            * Optional: start_time
            * Optional: expire_time
            * Optional: userref
            * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.

        returns:
            - Order confirmation message
        '''
        pair = PublicKraken(self.asset).pair_matching()[0]
  
        if type(pair) == list:
            raise Exception({'input_error': 'Can only send one asset order at a time.'})
        
        # create a dictionary we can use to return all the messages to
        orders = {}

        # use a for loop to close multiple positions individually
        for position in self.get_open_positions():
            if self.get_open_positions()[position]['type'] == 'sell':
                order_id = PrivateKraken('ethusd').get_open_positions()[position]['ordertxid']
        
                # find the leverage level to use
                leverage = PrivateKraken().get_closed_orders()[order_id]['descr']['leverage'][0]

                # if no volume supplied, close the entire position
                # if any of the position has already been closed, then you need to subtract it out from the total
                if volume==None:
                    if float(self.get_open_positions()[position]['vol_closed']) > 0:
                        volume = float(self.get_open_positions()[position]['vol']) - float(self.get_open_positions()[position]['vol_closed'])
                    else:
                        volume = float(self.get_open_positions()[position]['vol'])

                orders[position] = self.market_buy(
                    volume=volume,
                    leverage=leverage,
                    validate=validate
                )

        return orders

    def close_long_position(self, volume=None, oflags=None, start_time=None, expire_time=None, validate=False):
        # allows for you to close open leveraged long positions
        '''
        args:
            * Optional: volume = volume, in lots, that you wish to close
            * Optional: oflags = fcib, fciq, nompp, post
            * Optional: start_time
            * Optional: expire_time
            * Optional: userref
            * Optional: validate = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.

        returns:
            - Order confirmation message
        '''
        pair = PublicKraken(self.asset).pair_matching()
  
        if type(pair) == list:
            raise Exception({'input error': 'Can only send one asset order at a time.'})

        # create a dictionary we can use to return all the messages to
        orders = {}

        # use a for loop to close multiple positions individually
        for position in self.get_open_positions():
            if self.get_open_positions()[position]['type'] == 'buy':
                order_id = PrivateKraken('ethusd').get_open_positions()[position]['ordertxid']
        
                # find the leverage level to use
                leverage = PrivateKraken().get_closed_orders()[order_id]['descr']['leverage'][0]

                # if no volume supplied, close the entire position
                # if any of the position has already been closed, then you need to subtract it out from the total
                if volume==None:
                    if float(self.get_open_positions()[position]['vol_closed']) > 0:
                        volume = float(self.get_open_positions()[position]['vol']) - float(self.get_open_positions()[position]['vol_closed'])
                    else:
                        volume = float(self.get_open_positions()[position]['vol'])

                orders[position] = self.market_sell(
                    volume=volume,
                    leverage=leverage,
                    validate=validate
                )

        return orders

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

    def get_ledger_info(self, aclass='currency', activity=None, start=None, end=None, ofs=None):

        if self.asset != None:
            asset = PublicKraken(self.asset).pair_matching()
        else:
            asset = self.asset

        data = PublicKraken().make_api_data(
            aclass = aclass,
            asset = asset,
            type = activity,
            start = start,
            end = end,
            ofs = ofs
        )       

        message = self.authenticate('Ledgers', data)

        return message


class KrakenWS:

    def __init__(self, asset=None):
        self.asset = asset
    
    def ping_pong(auth):
        # wrapper function to be sure server is responsive before sending any traffic
        '''
        args:
            - auth = Authenticated websocket (True) or non-Authenticated (False)
        '''
        def wrapper(*args, **kwargs):
            if auth == True:
                ws = websocket.create_connection('wss://ws-auth.kraken.com')
            else:
                ws = websocket.create_connection('wss://ws.kraken.com')
            
            payload = {
                'event': 'ping'
            }

            ws.send(json.dumps(payload))

            # start an infinite loop until the server returns a 'pong'
            i = True
            while i == True:
                ping = json.loads(ws.recv())
                print('yes')
                # once 'pong' is recieved, then kill the loop and allow function to occur
                if ping['event'] == 'pong':
                    i = False
        return wrapper

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

    def ws_name(self):
        '''        
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

        pair = self.asset

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

    def ws_ticker(self, reqid=None):
        '''        
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
        pair = self.ws_name()

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

            print(trade_data)

        ws.close()

    def ws_trade(self, reqid=None):
        '''        
        returns:
            -Dictionary of websocket data (see Kraken Websocket docs for full data definitioins)
        '''

        # create a function that will open a websockets connection to the Kraken websocket API and pull in the 'trade' channel

        # first, be sure the servers are online or at least in post_only mode
        PublicKraken().guarantee_online()

        # initiate our connection
        ws = websocket.create_connection('wss://ws.kraken.com/')

        # be sure 'pair' is in wsname format
        pair = self.ws_name()

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
                    'name': 'trade'
                }           
            })
        else:
            payload = json.dumps({
                'event': 'subscribe',
                'pair': pair,
                'reqid': reqid,
                'subscription': {
                    'name': 'trade'
                }
            })

        # send our packet along
        ws.send(payload)

        # loop through the returned data
        while True:
            trade_data = json.loads(ws.recv())

            print(trade_data)

        ws.close()

    def ws_ohlc(self, interval, display=True, reqid=None):
        '''      
        args: \n
            -'interval' = this is the interval for which the ohlc data will be built (in minutes)
        returns: \n
            - A dictionary of ohlc items:\n
                -'current_time' = time of most recent trade
                -'end_time' = time when the current interval will end
                -'open' = opening price of the current interval
                -'high' = highest price of the current interval
                -'low' = lowest price of the current interval
                -'close' = closing price of the current interval (a.k.a.: the current price)
                -'vwap' = volume weighted average price of the current interval
                -'volume' = volume of traded asset in the current interval
                -'count' = number of trades within the current interval
        '''

        # create a function that will open a websockets connection to the Kraken websocket API and pull in the 'ohlc' channel

        # first, be sure the servers are online or at least in post_only mode
        PublicKraken().guarantee_online()

        # initiate our connection
        ws = websocket.create_connection('wss://ws.kraken.com/')

        # be sure 'pair' is in wsname format
        pair = self.ws_name()

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
                    'name': 'ohlc',
                    'interval': interval
                }           
            })
        else:
            payload = json.dumps({
                'event': 'subscribe',
                'pair': pair,
                'reqid': reqid,
                'subscription': {
                    'name': 'ohlc',
                    'interval': interval
                }
            })

        # send our packet along
        ws.send(payload)

        # loop through the returned data
        while True:
            trade_data = json.loads(ws.recv())

            # if there is data, put it in a dictionary
            
            if type(trade_data) == list:
                ohlc_data = {}
                ohlc_data = {'current_time': trade_data[1][0],
                            'end_time': trade_data[1][1],
                            'open': trade_data[1][2],
                            'high': trade_data[1][3],
                            'low': trade_data[1][4],
                            'close': trade_data[1][5],
                            'vwap': trade_data[1][6],
                            'volume': trade_data[1][7],
                            'count': trade_data[1][8],
                            'ohlc_interval': interval
                            }
            
                if display == True:
                    print(ohlc_data)

        ws.close()

    def guarantee_no_open_order(self, order_id=None):
        # this function will connect to the websocket and pause any logic from running until either there are no open orders,
        # or the order_id that is provided is no longer open
        # see https://support.kraken.com/hc/en-us/articles/360034499452-WebSocket-API-private-feeds-openOrders for more info

        # create the websocket token needed for authenticated access
        token = self.get_ws_token()

        # connect to the authenticated websocket
        ws = websocket.create_connection('wss://ws-auth.kraken.com/')

        # subscribe to the open orders authenticated websocket endpoint
        payload = json.dumps({
            'event': 'subscribe',
            'subscription': {
                'name': 'openOrders',
                'token': token
            }
        })

        # send the packet data to Kraken websocket
        ws.send(payload)

        # recieve the connection and subscription message, if no message raise an Exception
        if not json.loads(ws.recv()):
            raise Exception({'websocket_error': 'Error Message: Could not connect to channel'})

        if not json.loads(ws.recv()):
            raise Exception({'websocket_error': 'Error Message: Could not subscribe to channel'})

        # loop through the responses until either: A) there are no open orders or, B) the provided order_id is no longer open
        # instantiate initial loop condition and a list for tracking order_ids and dictionary for tracking order_status
        loop = 1
        list_of_orders = []
        order_status = {}
        while loop == 1:
            
            # save the response as a variable to call later on
            orders = json.loads(ws.recv())

            # if there are no orders initially, end the loop and close the websocket
            if type(orders) == dict and orders['event'] == 'heartbeat':
                continue
            elif not orders[0]:
                loop = 0
            
            # create a list of the order_ids to reference later
            if type(orders) == list:
                for order_data in orders[0]:
                    for order in order_data:
                        list_of_orders.append(order)

            # track the status of each order_id in a dictionary
            if type(orders) == list:
                for order_data in orders[0]:
                    for order in list_of_orders:
                        try:
                            order_status[order] = order_data[order]['status']
                        except: KeyError
            
            # remove closed orders from order_status dictionary and list_of_orders
            if len(order_status) > 0:
                for order in list_of_orders:
                    if order_status[order] != 'open':
                        order_status.pop(order)
                        while order in list_of_orders:
                            list_of_orders.remove(order)

            # end the loop and close the websocket if the either A) order_id == None AND the order_status dictionary is empty, or
            # B) the order_status dictionary does not contain the order_id
            if order_id != None:
                if order_id not in order_status:
                    loop = 0
            elif not order_status:
                loop = 0
        
        ws.close()    


class KrakenData:

    def __init__(self, asset=None):
        self.asset = asset
    
    def create_kraken_db(self, folder_path, db_path, db_name='kraken_historical_trades'):
        # this function will create a sqlite database from the Kraken downloadable data found at:
            # https://support.kraken.com/hc/en-us/articles/360047543791-Downloadable-historical-market-data-time-and-sales-
        # folder_path is the folder that you download and save these files in
        # db_path is where you want the databse to be created and stored.
        # Beware - if you use the entire dataset, the trade history will be around 40 GB and takes about 15-30 minutes to run and 
            # will only get bigger every quarter (at least at the time of this writing - 12/7/2022)
        # Once this initial database is created, it is recommended to run KrakenData().update_db() immediately after.  This will
            # bring the database up to date with current trades - however, there could be a lot of data needing to be updated so it 
            # could potentially take a very long time (like a day or two if the database is created toward the end of the quarter - the Kraken REST API is rate 
            # limited and therefore very little data can be pulled down at one time...there is no way around this, trust me, I have emailed Kraken extensively 
            # about this).
        '''
        args:
            - folder_path = directory path where Kraken historical data is stored
            - db_path = directory path where the database will be created and stored
            * Optional: db_name = name of the database that will be created, default name is 'trade_historical_data.db'

        creates:
            - sqlite database
        '''
        # create a list of all the available data files from Kraken. These will be used for the tables in the sqlite db.
        table_list = os.listdir(folder_path)

        # connect to the db, if it doesn't exist it will be created.
        conn = sqlite3.connect(Path(f'{db_path}/{db_name}.db'))

        # read in the .csv files as a pandas dataframe and then send to the newly created db
        # use tqdm library to display a progress bar
        pbar = tqdm(table_list)
        for table in pbar:
            pbar.set_description(f'Current Asset: {table}   Overall Progress: ')
            df = pd.read_csv(
                Path(f'{folder_path}/{table}'),
                delimiter=',',
                names=['timestamp', 'price', 'volume'])
            
            df.set_index('timestamp', inplace=True, )
            
            df.to_sql(f'{table.replace(".csv", "")}', conn, if_exists='replace')

        # close the connection after the tables are built
        conn.close()

    def ohlcv_df(self, interval, db_path, start_time=None, end_time=None, last=None, include_last_period=True):
        # takes a crypto trading pair and time interval and returns an multiindex OHLC dataframe
        pair = []
        if type(self.asset) != list:
            assets = [self.asset]
        else:
            assets = self.asset
            
        for asset in PublicKraken(assets).pair_matching():
            pair.append(PublicKraken(asset).get_pair_info()['altname'])

        interval_dict = {
            'D': 86400,
            'H': 3600,
            'HR': 3600,
            'M': 60,
            'MIN': 60,
            'S': 1,
            'SEC': 1,
            'W': 604800,
            'MO': 2628002.88,
            'MON': 2628002.88
        }
        
        # if the 'last' argument is passed, set the start_time for that interval period
        # need to parse 'interval' out to figure out what the units are (i.e.- '1D' needs to read as 86400 seconds)
        if last != None:
            end_time = None
            interval_length = str()
            interval_unit = str()
            
            count = 0
            for let in interval:
                count += 1 
                try:
                    int(let)
                    interval_length += let
                    interval_length = interval_length
                except:
                    if count == 1:
                        interval_length = 1
                    if let == " ":
                        continue
                    else:
                        interval_unit += let
                        interval_unit = interval_unit.upper()

            interval_length = int(interval_length)

            start_time = pd.to_datetime(time.time() - (last * interval_length * interval_dict[interval_unit]), unit='s')


        # start a counter and loop through the different assets, creating a query to send to the db
        count = 0

        for crypto in pair:
            break_loop = 0
            count += 1

            # create the connection to the sqlite db
            conn = sqlite3.connect(db_path)

            # make a placeholder "start" to reference later in the code
            start = 0

            # create the query to send to sql
            if start_time != None and end_time == None:
                start = int(datetime.timestamp(pd.to_datetime(start_time, utc=True)))
                query = f'SELECT * FROM "{str(crypto)}" WHERE timestamp >= {start}'

            elif start_time == None and end_time != None:
                end = int(datetime.timestamp(pd.to_datetime(end_time, utc=True)))
                query = f'SELECT * FROM "{str(crypto)}" WHERE timestamp <= {end}'

            elif start_time != None and end_time != None:
                start = int(datetime.timestamp(pd.to_datetime(start_time, utc=True)))
                end = int(datetime.timestamp(pd.to_datetime(end_time, utc=True)))
                query = f'SELECT * FROM "{str(crypto)}" WHERE timestamp >= {start} AND timestamp <= {end}'

            else:
                query = f'SELECT * FROM "{str(crypto)}"'

            # check to make sure that there was trade activity in the time period chosen for any particular crypto
            # if not, it needs to be skipped as the resample will throw an error on a blank df
            last_trade_time = datetime.timestamp(pd.to_datetime(KrakenData(crypto).trades_df(db_path=db_path,).iloc[-1].date, utc=True))

            if last_trade_time < start:
                # if there is only one crypto being analyzed, then we must gracefully throw an error because the ohlcv won't be created
                # if len(pair) <= 1:
                #     raise Exception(f'{crypto} has no trade activity since {start_time} and therefore cannot create an OHLCV.  Please try a different asset or a different start time')
                    
                print(f'WARNING: {crypto} not included in dataframe since there have been no trades since {start_time}')
                break_loop = 1
                continue

            try:
                crypto = pd.read_sql(query, conn, index_col='timestamp')
                conn.close()

            except Exception as e:
                conn.close()
                raise e

            # format the ohlcv df
            crypto['date'] = pd.to_datetime(crypto.index, unit='s')
            crypto = crypto[['date', 'price', 'volume']]
            crypto = crypto.resample(interval, on='date').agg({'price': 'ohlc', 'volume':'sum', 'date':'count'})
            crypto.columns = crypto.columns.droplevel()
            crypto.columns = pd.MultiIndex.from_product([[pair[count-1]], crypto.columns])
            crypto.rename(columns={'date':'trade_count'}, inplace=True)

            if count == 1:
                ohlcv = crypto
            else:
                ohlcv = ohlcv.merge(crypto, on='date', how='outer').sort_index()
        
        if break_loop == 1:
            None
        elif include_last_period == True:
            return ohlcv
        else:
            return ohlcv[:-1]

    def trades_df(self, db_path, pair=None, start_time=None):
        # takes a crypto trading pair and returns an trades dataframe on a tick by tick basis
        # the trade timestamp is set as the index, however there is a date column to help with sorting
        if pair == None:
            pair = PublicKraken(self.asset).pair_matching()
            pair = PublicKraken(pair).get_pair_info()['altname']
        else:
            pair = PublicKraken(pair).pair_matching()
            pair = PublicKraken(pair).get_pair_info()['altname']

        # establish a sqlite3 connection to the database provided by db_path
        conn = sqlite3.connect(db_path)

        if start_time is not None:
            start_time = int(datetime.timestamp(pd.to_datetime(start_time, utc=True)))
            query = f'SELECT * FROM "{str(pair)}" WHERE timestamp >= {start_time}'
        else:
            query = f'SELECT * FROM "{str(pair)}"'        

        data = pd.read_sql(query, conn, index_col='timestamp')

        conn.close()

        data['date'] = pd.to_datetime(data.index, unit='s')

        data = data[['date', 'price', 'volume']]

        return data

    def update_db(self, db_path):

        conn = sqlite3.connect(db_path)
        
        # pull in all the available pairs on Kraken (unless just one asset is provided in instantiation of KrakenData)
        if self.asset != None:
            pair_list = PublicKraken(self.asset).pair_matching()
        else:
            pair_list = PublicKraken().get_asset_pairs()
            for pair in  pair_list:
                if '.d' in pair:
                    pair_list.remove(pair)

        # we need to initiate a new call time.  this is to help track the number of Kraken API calls - for every three seconds after this, we add 1 more call to the call counter
        call_time = time.time()

        # loop through all the pairs and update the missing data from the sqlite database
        pbar = tqdm(pair_list)
        for pair in pbar:

            # Find the table name to update, which is the pair's altname (if you used the .create_kraken_db() function above).
            table_name = str(PublicKraken(pair).get_pair_info()['altname'])
            
            pbar.set_description(f'Current Asset: {table_name}   Overall Progress: ')

            # use a try/except to skip over the data that might not have any current data and create a new table if one doesn't exist yet
            try:
                df = self.trades_df(db_path, pair=pair)

                # last_time must be unix time with nanosecond resolution (default is second resolution)
                try:
                    # if the table is empty, there will be an error with calculating last_time below
                    last_time  = int(df.iloc[-1].name * 1000000000)
                    time_init = int(df.iloc[-1].name)
                except:
                    # if the table is empty, then just set last_time to 0 and time_init to the earliest time for that asset
                    last_time = 0
                    time_init = PublicKraken(pair).get_ohlc_dataframe('D', since=0).index[0]


            except:
                df = pd.DataFrame(columns=['timestamp', 'price', 'volume'])
                df.set_index('timestamp', inplace=True)
                table_create = f'CREATE TABLE "{table_name}" ("timestamp" INTEGER,"price" REAL,"volume" REAL)'
                cur = conn.cursor()
                cur.execute(table_create)
                time_init = PublicKraken(pair).get_ohlc_dataframe('D', since=0).index[0]
                last_time = 0
                df_length = 'new'
                

            # for Public Kraken API calls, you get a maximum of 15 calls (which is increased by 1 every 3 seconds until 15 is refilled again)
            max_calls = 15
            call_add_rate = 3 # 3 = 1 call every 3 seconds
            
            # since we already called the API twice in the message call, we need to start our counter at 13 (plus this builds in a little leeway to guarantee we don't break the rules)
            call_count = max_calls - 2

            # since we only get back the last 1000 trades, if the length of the df is less than 1000 then we are up to date and we must track this length for the upcoming 'while' loop
            df_length = len(df)

            while df_length >= 1000 or df_length == 'new':
                # first check to see if more than 3 seconds have passed and add time back to 'call_count' if so, otherwise subtract one from the 'call_count'
                if (time.time() - call_add_rate) > call_time:
                    call_time = time.time()
                    call_count += 1
                else:
                    call_count -= 1

                # if the 'call_count' is greater than 0, then make the call, otherwise wait enough time for the call count to reload
                if call_count > 0:
                    # subscribe to the 'Trades' endpoint and make a new dataframe
                    url = 'https://api.kraken.com/0/public/Trades'
                    data = PublicKraken().make_api_data(pair=pair, since=last_time)
                    message = requests.post(url, data).json()
                    call_count -= 1 # reduce the call counter after making the request
                    try:
                        message
                    except TimeoutError as t:
                        print('Connection Issue:', t)
                        continue

                    if not message['error']:
                        df2 = pd.DataFrame(message['result'][pair], columns=['price', 'volume', 'timestamp', 'buy/sell', 'ordertype', 'misc', 'trade_id'])
                        df2.set_index('timestamp', inplace=True)
                        df2 = df2[['price', 'volume']]
                    elif message['error'] == ['EService:Unavailable'] or message['error'] == ['EService:Busy'] or message['error'] == ['EGeneral:Internal error']:
                        print("Server connection issue...retrying...")
                        PublicKraken().guarantee_cancel()
                    else:
                        raise Exception({'kraken_error': f'Error Message: {message["error"]}'})
                    
                    # send the new dataframe to the sqlite3 database
                    df2.to_sql(table_name, conn, if_exists='append')   

                    # update df_length to see if it is time to exit the loop
                    df_length = len(df2)

                    # set the last_time parameters for tracking purposes
                    last_time = int(message['result']['last'])
                    last_date = pd.to_datetime((last_time / 1000000000), unit='s')
                
                # else, wait until the 'call_count' resets
                else:
                    # reset call count (set to 14 just build in some safety that you don't accidentally get to 15)
                    call_count = max_calls - 1
                    # wait for the appropriate time for the Kraken counter to reset
                    time.sleep(max_calls * call_add_rate)

                # update the asset progress tracker based on the amount of time from the last data point to now.
                if df_length < 1000:
                    asset_progress = 1
                else:
                    time_now = int(time.time())
                    init_time_diff = time_now - time_init
                    current_time_diff = time_now - int((last_time / 1000000000))
                    asset_progress = 1 - (current_time_diff / init_time_diff)
                
                # print of progress tracking  
                barLength = 30
                status = ""
                if asset_progress >= 1:
                    asset_progress == 1, status == 'Done...', "\r\n"
                block = int(round(barLength * asset_progress))
                text = "\r{} [{}] {:.0f}% {} {}".format(f'{table_name} Progress: ', "#" * block + "-" * (barLength - block), round(asset_progress * 100, 0), status, format(last_date, '%Y-%m-%d'))        
                sys.stdout.write(text)
                sys.stdout.flush()

        conn.close()


class Math:

    def __init__(self, asset=None):
        self.asset = asset

    def round_down(number, decimals):
        number = float(number)
        multiplier = 10 ** decimals
        return math.floor(number * multiplier) / multiplier

    def round_up(number, decimals):
        number = float(number)
        multiplier = 10 ** decimals
        return math.ceil(number * multiplier) / multiplier
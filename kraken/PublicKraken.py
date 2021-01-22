import json
import requests
import pandas as pd

def get_server_time(unix=True):
    # display Kraken's server time
    # input unix=True (default) returns the unix timestamp
    # input unix=False returns the rfc 1123 time format DAY, DD MON YYYY hh:mm:ss GMT
        # ex.: Sat, 16 Jan 21 22:23:36 +0000
    '''
    'unix=True' will return a unix timestamp, while 'unix=False' will return the time in rfc 1123 format.
    '''
    
    url = 'https://api.kraken.com/0/public/Time'
    res = requests.post(url).json()

    if not res['error']:
        if unix == True:
            return res['result']['unixtime']
        else:
            return res['result']['rfc1123']
    else:
        print(f"Error Message: {res['error']}")

def get_system_status():
    # display the current status from Kraken
        # returns a list of [status, time]
    # Possible statuses:
        # 'online' = fully functional
        # 'cancel_only' = existing orders can be cancelled, new orders cannot be placed
        # 'post_only' = existing orders can be cancelled, ONLY new post limit orders can be placed
        # 'limit_only' = existing orders can be cancelled, ONLY new limit orders can be placed
    '''
    -Returns a list, [status, time]
    '''

    url = 'https://api.kraken.com/0/public/SystemStatus'
    res = requests.get(url).json()

    if not res['error']:
        return [res['result']['status'], res['result']['timestamp']]
    else:
        print(f"Error Message: {res['error']}")

def name_converter(asset):
    # Function that converts asset names into Kraken compatible names.
    # Kraken uses the X-ISO4217-A3 system to name their assets.
    # See https://github.com/globalcitizen/x-iso4217-a3 for more info
    # this will mainly be used as a helper function within other functions to minimize naming convention errors
    '''
    -Takes in an asset name and returns the equivalent Kraken recongized name to the user/program.
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
            raise Exception(f'Error Message: {asset} is not a name Kraken recognizes.  Use "get_asset_info" without passing an asset into the function to get a full list of Kraken recongized assets.')

    else:
        raise Exception(f"Error Message: {res['error']}")

def pair_matching(trading_pair):
    # takes in wsname or altname and returns the Kraken pair name
    # this will mainly be used as a helper function within other functions to minimize naming convention errors
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
                        raise Exception(f'Error Message: {coin} is not a recognized trading pair by Kraken.')

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
                    raise Exception({'error': f'Error Message: {trading_pair} is not a recognized trading pair by Kraken.'})
    
    else:
        raise Exception(f"Error Message: {res['error']}")

def get_asset_info(asset=None):
        # find all the info for a certain asset
        # info includes:
            # 'altname' = alternative name, ie: XETH --> ETH
            # 'aclass' = asset class (currency, futures, etc.)
            # 'decimals' = scaling decimal places for record keeping
            # 'display_decimals' = scaling decimal places for output display
        '''
        -Returns ALL assets unless 'asset' is specified.
        '''

        url = 'https://api.kraken.com/0/public/Assets'
        res = requests.get(url).json()

        if not res['error']:
            if asset != None:
                asset = asset.upper()
                try: 
                    return res['result'][asset]

                except KeyError: 
                    return name_suggestion(asset)

            else:
                return res['result']
            
        else:
            raise Exception(f"Error Message: {res['error']}")

def get_fees(pair, maker_taker=None, volume=None):
    # return a dictionary of a dictionary of the fees associated with the provided pair
    # {'taker': {volume1: fee1, volume2: fee2}, 'maker': {volume1: fee1, volume2: fee2}}
    # if your monthly volume is equal to OR more than the listed volume, then the associated fee is your fee in percent
    '''
    Input a valid trading pair's Kraken name, wsname or alternative name and get back a dictionary of taker and maker fee tiers.  Volume is given in $ amount and fees are given in percents.
    * Optionally, takes argument 'maker_taker' which can be either 'maker' or 'taker'.  If neither are provided, both fee tiers are returned.
    * Optionally, takes argument 'volume' which is the user's volume in $.  If none is provided, all tiers are returned.
    ''' 

    url = 'https://api.kraken.com/0/public/AssetPairs'
    res = requests.get(url).json()

    pair = pair_matching(pair)

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
        raise Exception( f"Error Message: {res['error']}")

def get_pair_trade_data(pair):
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
    Input a valid trading pair's Kraken name, wsname or alternative name and get back a dictionary of trade data for the given pair.
    ''' 

    url = 'https://api.kraken.com/0/public/AssetPairs'
    res = requests.get(url).json()

    pair = pair_matching(pair)

    if not res['error']:
        return res['result'][pair]
    else:
        raise Exception(f"Error Message: {res['error']}")

def get_ticker_info(pair):
    # returns the current order book level one for a given pair, or list of pairs
        # NOTICE: it appears that, for the time being, the Kraken API only returns the alphabetically last pair data when passing a list of pairs as an argument
    '''
    -Input a valid trading pair's Kraken name, wsname or alternative name.
    -Return an array of arrays of ticker data: ask, bid, last trade, volume, volume weighted average price, number of trades, low, high, open
    '''
    url = 'https://api.kraken.com/0/public/Ticker'
    pair = pair_matching(pair)
    params = {'pair': pair}
    res = requests.get(url, params).json()
    
    if not res['error']:
        return res['result']
    else:
        raise Exception( f"Error Message: {res['error']}")

def get_ohlc(pair, interval=None, since=None):
    # returns the last 720 iterations of periods that you feed it, i.e.- default is minutes, so you would recieve the last 720 minutes. If you input 'D' you would get the last 720 days on a daily timescale.
    '''
    -Inputs: valid Kraken trading pair name, wsname, or alternative name.
        * Optionally, takes 'interval' which is the time frame interval (can take string or int -- for the 1 minute interval, you can enter either '1' or 'min').
        * Optionally, takes 'since' which is the unix timestamp from which to start the data pull (Kraken limits you to 720 iterations)
    -Returns: a dictionary of a dictionaries with the format: 
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
            raise Exception(f'{interval} not a valid input.  Only 1, 60, 240, 1440, 10080, or 21600 accepted as integers.')
        interval = interval
    elif interval==None:
        interval = None
    else:
        if interval not in interval_dict.keys():
            raise Exception(f'{interval} not a valid input.  Only "min", "1h", "4h", "D", "W" and "15D" accepted as strings.')
        interval = interval_dict[interval.upper()]
    
    url = 'https://api.kraken.com/0/public/OHLC'
    pair = pair_matching(pair)
    if 'Error Message' in pair:
        return pair
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
        raise Exception(f"Error Message: {res['error']}")

def get_ohlc_dataframe(pair, interval=None, since=None):
    # similar to get_ohlc, except returns a dataframe instead of a dictionary of dictionaries
    '''
    Similar to 'get_ohlc', except returns a dataframe instead of a dictionary of dictionaries.
    -Inputs: valid Kraken trading pair name, wsname, or alternative name.
        * Optionally, takes 'interval' which is the time frame interval.
        * Optionally, takes 'since' which is the unix timestamp from which to start the data pull (Kraken limits you to 720 iterations)
    -Returns: pandas dataframe with a datetime index and columns 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
    '''
    
    data = get_ohlc(pair, interval, since)
    if 'Error Message' in data:
        raise Exception(data)

    df = pd.DataFrame(data).T
    df.index = pd.to_datetime(df.index, unit='s')

    return df

def get_order_book(pair, count=None):
    # function that will return a dictionary of dictionaries of the asks and bids
    '''
    -Inputs: valid trading pair's Kraken name, wsname or alternative name.
        * Optionally, input 'count' which is the maximium number of bids/asks.  By default, all bids/asks are returned.
    -Returns: dictionary of dictionaries of bids and asks.
    '''

    pair = pair_matching(pair)

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
        raise Exception(f"Error Message: {res['error']}")

def get_asks(pair, count=None):
    # returns only the asks for a selected pair
    '''
    -Inputs: valid trading pair's Kraken name, wsname or alternative name.
        * Optionally, takes 'count' which is the maximum number of asks to return.
    -Returns: a list of list of each ask -- [[price, volume, timestamp]]
    '''
    pair = pair_matching(pair)

    asks = get_order_book(pair, count)

    return asks['asks']

def get_bids(pair, count=None):
    # returns only the bids for a selected pair
    '''
    -Inputs: valid trading pair's Kraken name, wsname or alternative name.
        * Optionally, takes 'count' which is the maximum number of asks to return.
    -Returns: a list of list of each bid -- [[price, volume, timestamp]]
    '''
    pair = pair_matching(pair)

    bids = get_order_book(pair, count)

    return bids['bids']

def get_current_bid(pair):
    # returns the current bid for a selected pair
    '''
    -Inputs: valid trading pair's Kraken name, wsname or alternative name.
    -Returns: a list of current bid info -- [price, volume, timestamp]
    '''
    pair = pair_matching(pair)

    bid = get_order_book(pair)

    return bid['bids'][0]

def get_current_ask(pair):
    # returns the current bid for a selected pair
    '''
    -Inputs: valid trading pair's Kraken name, wsname or alternative name.
    -Returns: a list of current ask info -- [price, volume, timestamp]
    '''
    pair = pair_matching(pair)
    
    ask = get_order_book(pair)

    return ask['asks'][0]

def get_leverage_data(pair, type):
    '''
    -Inputs: pair and type
        * Pair is the asset trading pair to lookup leverage information for.
        * type is whether it is buy-side or sell-side leverage.
    -Returns: a list of all available leverage options for that asset.
    '''

    leverage = get_pair_trade_data(pair)[f'leverage_{type}']

    return leverage



import os
import json
import requests, urllib
from dotenv import load_dotenv
import hmac, base64, hashlib
import time
from . import PublicKraken

# load the .env file that your Kraken keys are stored in (must be at or above this library level)
load_dotenv()

# set an api key variable that will be used to authenticate your account
krakenapi = os.getenv('kraken_api')
krakenprivatekey = os.getenv('kraken_private_key')

def make_api_data(asset=None, aclass=None, trades=None, userref=None, start=None, end=None, ofs=None, closetime=None, type=None, txid=None, consolidation=None, docalcs=None, pair=None, fee_info=None, ordertype=None, price=None, price2=None, volume=None, leverage=None, oflags=None, starttm=None, expiretm=None, validate=None):
    # simple function that will create the 'data' dictionary that will be used to pass information into our api call
    data = {arg: value for arg, value in locals().items() if arg != 'account_info' and arg != 'url' and arg != 'method' and value is not None and value != False}

    return data

def authenticate(account_info, data):
    # this will mostly be used as a helper function for the other private functions
    # this function will authenticate any API calls
    # takes in the account information  the user wishes to access - Balance, TradeBalance, etc.
    # takes in the optional/required data from the desired account information lookup as a dictionary of items.

    '''
    -Inputs: account information you wish to access along with a dictionary of required/optional data to include in the api call.  See Kraken API 
    documentation for further information.
    -Returns: data corresponding with the chosen account information.
    '''

    url = 'https://api.kraken.com/0/private/' + account_info
    method = '/0/private/' + account_info

    nonce = str(int(time.time() * 1000))

    data['nonce'] = nonce

    api_data = urllib.parse.urlencode(data)

    api_nonce = (nonce + api_data).encode()
    message = method.encode() + hashlib.sha256(api_nonce).digest()

    hmac_encode = hmac.new(base64.b64decode(krakenprivatekey), message, hashlib.sha512)
    api_signature = base64.b64encode(hmac_encode.digest())

    params = {
        'API-Key': krakenapi,
        'API-Sign': api_signature
    }
    res = requests.post(url, headers=params, data=data).json()

    if not res['error']:
        return res['result']
    else:
        raise Exception(res['error'])

def get_balance(asset=None):
    # returns to the user the balance of all accounts in Kraken
    '''
    -Inputs: optionally takes 'asset' which is the asset the user wishes to recieve Account Balance information about.  Default returns all balances.
    -Returns: A single dictionary of assets and their balances.
    '''
    data = make_api_data(asset=asset)

    # be sure that (if supplied) the asset is in the Kraken recognized variant
    try:
        data['asset'] = PublicKraken.name_converter(data['asset'])
        asset = data['asset']
    except KeyError: data = data

    message = authenticate('Balance', data)

    if asset is not None:
        return message[asset]
    else:
        return message

def get_trade_balance(asset='ZUSD', aclass='currency'):
    # returns a user's trade balance for a given asset, USD is default
        # Note: you can also choose the class of asset ('aclass'), but Kraken currently (1.17.2021) only has currency, 
        # so currency is the default option and likely does not need to be changed.
    '''
    -Inputs: Optionally takes base asset used to determine balance and asset class.
        * By default, asset class is set to 'currency'.  Kraken currently (01.17.2021) only lists currecies, so this is not likely needed to be changed.
        * By default, asset is set to 'ZUSD'.  Takes either the offical Kraken name, wsname or alternative name.
    -Returns: A dictionary of trade balance information:
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

    asset = PublicKraken.name_converter(asset)

    data = make_api_data(asset=asset, aclass=aclass)

    message = authenticate('TradeBalance', data)

    return message

def get_open_orders(trades=None, userref=None):
    '''
    -Inputs: Optionally accepts trades and userrf.
        * trades determines whether or not to include trades in output.  By default it is set to False.
        * userref will restrict the results to a giver user reference id.  By default usrref=None.
    -Returns: An array of open order information with the Transaction ID as the key.  It is empty if there are no open orders.
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
    data = make_api_data(trades=trades, userref=userref)

    message = authenticate('OpenOrders', data)

    return message['open']

def get_closed_orders(trades=None, userref=None, start=None, end=None, ofs=None, closetime=None):
    '''
    -Input: Optionally takes trades, userrf, start, end, ofs or closetime.
        * By default, all optional inputs are set to None.
    -Returns: An array of closed order information with the Transaction ID as the key.  It is empty if there are no closed orders.
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
    
    data = make_api_data(trades=trades, userref=userref, start=start, end=end, ofs=ofs, closetime=closetime)

    message = authenticate('ClosedOrders', data)

    return message['closed']

def get_trade_history(type='all', trades=None, start=None, end=None, ofs=None):
    '''
    -Inputs: Optionally takes type, trades, start, end, ofs
        * type takes the following arguments (set to 'all' by default):
            --'any position'
            --'closed position'
            --'closing position'
            --'no position'
    -Returns: An array with the transaction id as the key.  
    -------------------------------------------------------------------------------
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
    
    data = make_api_data(type=type, trades=trades, start=start, end=end, ofs=ofs)

    message = authenticate('TradesHistory', data)

    return message['trades']

def get_open_positions(txid=None, docalcs=False, consolidation=None):
    # pretty self explanatory on this one
    '''
    -Inputs: Optionally takes 'txid', 'docalcs', and 'consolidated'.
        * By default, all inputs are set to None.
        * docalcs=True will include profit/loss calculations for the 'net' value in the returned array.
        * 'consolidation' will consolidate the position data around a specific market.  Takes a valid trading pair's Kraken name, wsname or alternative name.
            **NOTICE: the documentation is not clear on 'consolidation' and it doesn't seem to be functioning.  Best not to use for now.
    -Returns: An array with txid as the key of open margin positions.
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
    data = make_api_data(txid=txid, docalcs=docalcs, consolidation=consolidation, market=market)
        
    message = authenticate('OpenPositions', data)

    return message

def get_fee_volume(pair=None, fee_info=None):
    '''
    -Inputs: Optionally takes pairs and fee_info.
        * fee_info=True will return fee information along with the trade volume.  By default it is set to False.
            **NOTICE: it appears this functionality is not working with Kraken right now.  Investigating as to why 'True' does not return fee info.  For now, will have to use the public method 'get_fees' in conjunction with the volume amount returned here.
    - Returns: An array with volume and fee information.
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

    data = make_api_data(pair=pair, fee_info=fee_info)

    message = authenticate('TradeVolume', data)

    return message

def add_standard_order(pair, side, volume=None, ordertype='market', price=None, price2=None, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
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
    -Inputs: 
        * Required: pair to trade, side of order ('buy' or 'sell') and volume in lot size
        * Optional: ordertype, price (if not market order), price2, leverage, oflags, start_time, expire_time, userref, validate
            * NOTICE: -ordertype is, by default, set to market.
                      -validate is, by default, set to False.  validate=True will only test the inputs with Kraken's API, but will not send the order through.
    -Returns: the trade confirmation message from Kraken.
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
        raise Exception(f'Must enter in a volume for the trade')

    if pair == None:
        raise Exception('Must enter in a valid trading pair for the trade')
    else:
        pair = PublicKraken.pair_matching(pair)

    if side != 'buy' and side != 'sell':
        raise Exception("'side' must be either 'buy' or 'sell'")


    data = make_api_data(
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

    message = authenticate('AddOrder', data)

    return message

def market_buy(pair, volume, price=None, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
    # allows for a quick market buy (notice, 'side' is not an input option, but is automatically included as 'buy' as part of the data packet sent to the API)
    '''
    -Inputs: 
        * Required: 'pair' = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
                    'volume' = the lot size of the purchase.
        * Optional: 'price' = the price at which to transact the market order
                    'leverage' = how much leverage to use.  See the Kraken documentation or PublicKraken.get_asset_info() for more information on a specific asset
                    'oflags' = fcib, fciq, nompp, post
                    'start_time'
                    'expire_time'
                    'userref'
                    'validate' = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
    -Outputs: order confirmation message
    '''

    message = add_standard_order(
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

def market_sell(pair, volume, price=None, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
    # allows for a quick market sell (notice, 'side' is not an input option, but is automatically included as 'sell' as part of the data packet sent to the API)
    '''
    -Inputs: 
        * Required: 'pair' = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
                    'volume' = the lot size of the purchase.
        * Optional: 'price' = the price at which to transact the market order
                    'leverage' = how much leverage to use.  See the Kraken documentation or PublicKraken.get_asset_info() for more information on a specific asset
                    'oflags' = fcib, fciq, nompp, post
                    'start_time'
                    'expire_time'
                    'userref'
                    'validate' = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
    -Outputs: order confirmation message
    '''

    message = add_standard_order(
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

def limit_buy(pair, volume, price, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
    # allows for a quick limit buy (notice, 'buy' is not an input option, but is automatically included as 'buy' as part of the data packet sent to the API)
    '''
    -Inputs: 
        * Required: 'pair' = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
                    'volume' = the lot size of the purchase.
                    'price' = limit price of the order.
        * Optional: 'leverage' = how much leverage to use.  See the Kraken documentation or PublicKraken.get_asset_info() for more information on a specific asset
                    'oflags' = fcib, fciq, nompp, post
                    'start_time'
                    'expire_time'
                    'userref'
                    'validate' = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
    -Outputs: order confirmation message
    '''

    message = add_standard_order(
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

def limit_sell(pair, volume, price, leverage=None, oflags=None, start_time=None, expire_time=None, userref=None, validate=False):
    # allows for a quick limit sell (notice, 'sell' is not an input option, but is automatically included as 'sell' as part of the data packet sent to the API)
    '''
    -Inputs: 
        * Required: 'pair' = the valid Kraken trading pair name, or common name. (i.e.- 'ethusd' or 'ETH/USD' or 'XETHZUSD')
                    'volume' = the lot size of the purchase.
                    'price' = limit price of the order.
        * Optional: 'leverage' = how much leverage to use.  See the Kraken documentation or PublicKraken.get_asset_info() for more information on a specific asset
                    'oflags' = fcib, fciq, nompp, post
                    'start_time'
                    'expire_time'
                    'userref'
                    'validate' = False by default.  When 'True' will not send order to Kraken, but will check the parameters and return a successful message.
    -Outputs: order confirmation message
    '''

    message = add_standard_order(
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

def cancel_single_order(txid):

    data = make_api_data(txid=txid)

    message = authenticate('CancelOrder', data)

    return message

def cancel_all_orders():

    data = make_api_data()

    message = authenticate('CancelAll', data)

    return message




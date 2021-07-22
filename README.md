# CrackedKraken
Repository for using Kraken's Public and Private APIs  
Current version = v0.3.3

## Table of Contents
* [Updates](#Updates)
* [Classes](#Classes)
* [Example Code](#Example-Code)
* [References](#References)

## Updates:
* 07/22/2021 - realeased v0.3.3
   * release notes:
      * Updated the market orders to be more flexible:
         * Can now input amount of quote currency desired to be purchased rather than just the volume of the asset (beware: this could potentially lead to multiple trades being filled in order to use up all the quote currency specified).
         * Can now input `max_slippage` as an argument which will stop the market order from executing once the slippage has been reached.  This is only useful when utilizing the quote amount.

      * Added a status bar to some of the data update functions to better help the user understand what stage the update is in.

      * Added a `Math()` class to make some commonly used functions available. 

* 04/08/2021 - released v0.3.2
    * release notes:
        * Added new methods to `PublicKraken()` class:
            * `.get_common_name()` which returns the wsname of the instantiated asset except for XXBTZUSD which is BTC/USD
            * `.get_wsname()` which returns the wsname of the instantiated asset
        * Kraken started using the wsname in some REST API calls, so the methods that rely on that have been updated
        * Added new method to `KrakenWS()`:
            * `.guarantee_no_open_orders()` which will pause your execution code until there are no open orders left on your account.  This will prevent any 'no available funds' errors if trying to place a new order immediately after closing the existing position. 

* 02/27/2021 - released v0.3.1
   * release notes:
      * Added functionality to `PrivateKraken()` class:
         * can now instantiate the class with 'userref' as an argument
         * added `.close_short_position()` and `.close_long_position()` methods
      * continued to clean up certain functions and grammar mistakes
      * `KrakenData().update_db()` now includes a check to be sure the Kraken servers are online
      * Still developing `KrakenWS()` class

* 02/16/2021 - released v0.3.0
    * release notes:
        * added KrakenData class
            * can create and update sqlite databases with entire trading history from Kraken
            * can utilize that trading history to build OHLCV pandas dataframes
        * refactored PublicKraken, PrivateKraken and KrakenWS to more efficiently call methods for desired assets

* 02/02/2021 - released v0.2.0
    * release notes:
        * Refactored and Cleaned the code base
        * Got rid of different .py files for PrivateKraken, PublicKraken and KrakenWS and combined them all in one
        * Created 3 classes - PublicKraken, PrivateKraken and KrakenWS
        * KrakenWS is still under development

## Classes -- ***Full documentation coming soon***
#### - PublicKraken
* get_status
* get_asset_info  
  
  
#### - PrivateKraken
    Must have your private and public keys from Kraken saved in a .env file as the following:
        - kraken_api="<PUBLIC KRAKEN KEY>"
        - kraken_private_key="<PRIVATE KRAKEN KEY>"  
    The .env file MUST be in the same directory as this code base, or above it as the code utilizes load_dotenv() to read the file.  
* get_balance  
  

#### - KrakenWS
    ***NOTE: the websocket portion is still in development***

#### - KrakenData


## Example Code
#### Creating an OHLC dataframe
    from kraken import PublicKraken
    eth_df = PublicKraken('ethusd').get_ohlc_dataframe()
    
    
    - NOTE: this will only return the most recent 720 time frames, to get more history utilize the following code:  

    # first go to the Historical Kraken trades website and download all files (or just the assets you wish to track): "https://support.kraken.com/hc/en-us/articles/360047543791-Downloadable-historical-market-data-time-and-sales-"   

    from kraken import KrakenData
    folder_path = 'C:/folder_path'     # this is the folder or directory where the downloaded Kraken history is saved.
    db_path = 'C:/db_path'     # this is the folder/location you would like the database to be saved - you will need upwards of 15 GB of space.

    KrakenData().create_kraken_db(folder_path, db_path)


    # now that the database has been created, you can create any timed interval OHLCV dataframe you like.  Below, the sample creates a daily df:

    eth_df = KrakenData('ethusd').ohlcv_df('1D', db_path)
    
    -NOTE: It is advisable to use the KrakenData().update_db() function to keep the database up-to-date as Kraken only release trading data on a quarterly basis.
    
#### Pulling in trade history:  
    from kraken import PrivateKraken
    trade_history = PrivateKraken().get_trade_history(type='closed position')

## References
* [Kraken REST API Documentation](https://www.kraken.com/en-us/features/api#example-api-code)
* [Kraken Websocket Documentation](https://docs.kraken.com/websockets/)
* Historical Kraken [OHLC](https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-OHLCVT-Open-High-Low-Close-Volume-Trades-data) and historical [trades](https://support.kraken.com/hc/en-us/articles/360047543791-Downloadable-historical-market-data-time-and-sales-) data


# CrackedKraken
Repository for using Kraken's Public and Private APIs  
Current version = v0.3.0

## Table of Contents
* [Updates](#Updates)
* [Classes](#Classes)
* [Example Code](#Example-Code)
* [References](#References)

## Updates:
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


    # first go to the Historical Kraken trades website and download all files: "https://support.kraken.com/hc/en-us/articles/360047543791-Downloadable-historical-market-data-time-and-sales-"   

    from kraken import KrakenData
    folder_path = 'C:/folder_path'     # this is the folder or directory where the downloaded Kraken history is saved.
    db_path = 'C:/db_path'     # this is the folder/location you would like the database to be saved - you will need around 12 GB of space.

    KrakenData().create_kraken_db(folder_path, db_path)


    # now that the database has been created, you can create any timed interval OHLCV dataframe you like.  Below, the sample creates a daily df:

    eth_df = KrakenData('ethusd').ohlcv_df('1D', db_path)

#### Pulling in trade history:  
    from kraken import PrivateKraken
    trade_history = PrivateKraken().get_trade_history(type='closed position')

## References
* [Kraken REST API Documentation](https://www.kraken.com/en-us/features/api#example-api-code)
* [Kraken Websocket Documentation](https://docs.kraken.com/websockets/)
* Historical Kraken [OHLC](https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-OHLCVT-Open-High-Low-Close-Volume-Trades-data) and historical [trades](https://support.kraken.com/hc/en-us/articles/360047543791-Downloadable-historical-market-data-time-and-sales-) data


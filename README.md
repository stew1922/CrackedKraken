# CrackedKraken
Repository for using Kraken's Public and Private APIs  
Current version = v0.2.0

## Table of Contents
* [Updates](#Updates)
* [Classes](#Classes)
* [Example Code](#Example-Code)
* [References](#References)

## Updates:
   * 02/02/2021 - released v0.2.0
      * release notes:
         * Refactored and Cleaned the code base
         * Got rid of different .py files for PrivateKraken, PublicKraken and KrakenWS and combined them all in one
         * Created 3 classes - PublicKraken, PrivateKraken and KrakenWS
         * KrakenWS is still under development

## Classes -- ***Full documentation coming soon***
### PublicKraken

* PrivateKraken - handles all the private API calls
    * must have your private and public keys from Kraken saved in a .env file as the following:
        * kraken_api="PUBLIC KRAKEN KEY"
        * kraken_private_key="PRIVATE KRAKEN KEY"  
      (Where the string inside the quotes are your keys)
    * The .env file must be in the same directory as this code base, or above.  
* KrakenWS - handles the websocket connection
    * ***NOTE: the websocket portion is still in development***


## Example Code
#### Creating an OHLC dataframe
    from kraken import PublicKraken
    eth_df = PublicKraken().get_ohlc_dataframe('ethusd')

#### Pulling in trade history:  
    from kraken import PrivateKraken
    trade_history = PrivateKraken().get_trade_history(type='closed position')

## References
* [Kraken REST API Documentation](https://www.kraken.com/en-us/features/api#example-api-code)
* [Kraken Websocket Documentation](https://docs.kraken.com/websockets/)
* Historical Kraken [OHLC](https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-OHLCVT-Open-High-Low-Close-Volume-Trades-data) and historical [trades](https://support.kraken.com/hc/en-us/articles/360047543791-Downloadable-historical-market-data-time-and-sales-) data


# CrackedKraken
Repository for using Kraken's Public and Private APIs  
Current version = v0.2.0

## Updates:
   * 02/02/2021 - released v0.2.0
      * release notes:
         * Refactored and Cleaned the code base
         * Got rid of different .py files for PrivateKraken, PublicKraken and KrakenWS and combined them all in one
         * Created 3 classes - PublicKraken, PrivateKraken and KrakenWS
         * KrakenWS is still under development

## Classes
* PublicKraken - handles all the public API calls
* PrivateKraken - handles all the private API calls
    * must have your private and public keys from Kraken saved in a .env file as the following:
        * kraken_api="PUBLIC KRAKEN KEY"
        * kraken_private_key="PRIVATE KRAKEN KEY"  
      (Where the string inside the quotes are your keys)
    * The .env file must be in the same directory as this code base, or above.  
* KrakenWS - handles the websocket connection
    * ***NOTE: the websocket portion is still in development***

Example code:

* Creating an OHLC dataframe:  
`from kraken import PublicKraken`  
`eth_df = PublicKraken().get_ohlc_dataframe('ethusd')`  

* Pulling in trade history:  
`from kraken import PrivateKraken`  
`trade_history = PrivateKraken().get_trade_history(type='closed position')`  


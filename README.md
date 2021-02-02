# CrackedKraken
Repository for using Kraken's Public and Private APIs

## Classes
* PublicKraken - handles all the public API calls
* PrivateKraken - handles all the private API calls
    * must have your private and public keys from Kraken saved in a .env file as the following:
        * kraken_api="PUBLIC KRAKEN KEY"
        * kraken_private_key="PRIVATE KRAKEN KEY"
* KrakenWS - handles the websocket connection
    * ***NOTE: the websocket portion is still in development***

Example code:

* Creating an OHLC dataframe:  
`from kraken import PublicKraken`  
`eth_df = PublicKraken().get_ohlc_dataframe('ethusd')`  

* Pulling in trade history:  
`from kraken import PrivateKraken`  
`trade_history = PrivateKraken().get_trade_history(type='closed position')`  


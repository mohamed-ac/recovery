from logger import get_logger
logger = get_logger(__name__)
import yfinance as yf
import pandas as pd
from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
from twelvedata import TDClient

load_dotenv()
api_key = os.getenv("TWELVE_DATA_API_KEY")


class DataProvider(ABC):
       
    @abstractmethod
    def get_data(self,ticker,start,end) -> pd.DataFrame:
        pass
    
    
class YFinanceProvider(DataProvider):
    @staticmethod
    def _normalize(df:pd.DataFrame) -> pd.DataFrame:
        """enleve le multi index """
        return df.droplevel(1, axis=1)

    def __init__(self):
        self.provider_name = "yfinance" 

    def get_data(self,ticker,start,end) -> pd.DataFrame:
        cache_path = f"cache/{ticker}_{start}_{end}.pkl"
        #print(cache_path)
        
        if os.path.exists(cache_path):
            logger.info(f"loading from cache: {cache_path}")
            return pd.read_pickle(cache_path)

        try:
            logger.info(f"retrieving OHLC data "
                        f"for {ticker}"
                        f"from {start} to {end} ({self.provider_name})")
            df = yf.download(ticker, start, end , interval="1d")
            if df.empty:
                raise ValueError("empty data")      
            
            os.makedirs("cache", exist_ok=True)
            self._normalize(df).to_pickle(cache_path)
            logger.info(f"data cached : {cache_path}")
            
            return self._normalize(df)
        
        except Exception as e:
            logger.error(e)
            raise



class TwelveDataProvider(DataProvider):
    def __init__(self):
        self.provider_name = "twelvedata"
        self.client = TDClient(apikey=api_key)
    
    def get_data(self, ticker, start, end, interval="1h") -> pd.DataFrame:
        try:
            logger.info(f"retrieving {interval} data for {ticker} ({self.provider_name})")
            ts = self.client.time_series(
                symbol=ticker,
                interval=interval,
                start_date=start,
                end_date=end,
                outputsize=5000
            ).as_pandas()
            if ts.empty:
                raise ValueError("empty data")
            ts = ts.sort_index(ascending=True)
            return ts
        except Exception as e:
            logger.error(e)
            raise



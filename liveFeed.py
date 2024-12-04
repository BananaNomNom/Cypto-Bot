import cbpro
import time
import pandas as pd
import sqlalchemy
import datetime

class WebsocketFeed(cbpro.WebsocketClient):
    def on_open(self):
        self.url = "wss://ws-feed.pro.coinbase.com/"
        self.products = 'LTC-USD'
        self.message_count = 0
        self.databaseName = ''
        
    def on_message(self, msg):
        if 'price' in msg and 'type' in msg:
            frame = createFrame(msg)
            frame.to_sql(self.databaseName, engine, if_exists='append', index=False)
            self.message_count += 1
            time.sleep(1)

    def on_close(self):
        print("-- End Connection --")

def createFrame(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:, ['product_id','time','price']]
    df. columns = ['Symbol', 'Time', 'Price']
    df.Price = df.Price.astype(float)
    df.Time = pd.to_datetime(df.Time)
    return df

engine = sqlalchemy.create_engine('sqlite:///CoinStream.db')
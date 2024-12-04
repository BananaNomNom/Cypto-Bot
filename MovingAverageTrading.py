import cbpro

import pandas as pd
import numpy as np

import time
import datetime as DT

client = cbpro.PublicClient()
coinID = 'LTC-USD'
ST = 12
LT = 26

#modifies liveFeed's class for use in this program
from liveFeed import WebsocketFeed
class newWSF(WebsocketFeed):
    def on_message(self, msg):
        if 'price' in msg and 'type' in msg:
            self.frame = createFrame(msg)
            self.message_count += 1
            time.sleep(1)

wsClient = newWSF(products=coinID, channels=['ticker'])
wsClient.start()

#creats a dataframe of the msg provided taking it as only Time, Symbol, and Price
def createFrame(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:, ['product_id','time','price']]
    df. columns = ['Symbol', 'Time', 'Price']
    df.Price = df.Price.astype(float)
    df.Time = pd.to_datetime(df.Time)
    return df

#gets Historical Values of a crypto coin over the LT number of days.
def getHistoricals(symbol):

    #gets current time from API server
    tmptime = client.get_time()
    
    #converts the epoch time taken from tmptime to LT days earlier while also turning it into ISO format
    startTime = DT.datetime.utcfromtimestamp(tmptime.get('epoch') - (86400*LT)).isoformat()

    #just converts the tmptime to UTC time of the day before
    endTime = DT.datetime.utcfromtimestamp(tmptime.get('epoch')- 86400).isoformat()
    
    #request the historaical rates of a given product starting at startTime and ending at endTime with a granulairty of 1 day
    df = pd.DataFrame(client.get_product_historic_rates(product_id=symbol, start=startTime, end=endTime, granularity=86400))
    
    #manipulates the 5th column (the closes column) into then calculating a short term and long term data
    closes = pd.DataFrame(df[4])
    
    #reverses the dataframe and resets the indexs
    closes = closes.iloc[::-1]
    closes = closes.reset_index(drop=True)

    #renames the column and then makes a rolling sum for the short term and long term
    closes.columns = ['Close']
    closes['ST'] = closes.Close.rolling(ST-1).sum()
    closes['LT'] = closes.Close.rolling(LT-1).sum()

    closes.dropna(inplace=True)
    return closes

#get the live Moving average
def liveSMA(hist, live):
    liveST = (hist['ST'].values + live.Price.values) / ST
    liveLT = (hist['LT'].values + live.Price.values) / LT
    return liveST, liveLT

#main strategy
def strat(coin, qty, SL_limit, open_position = False):
    f = open('balance.txt', 'r')
    smallLoan = float(f.readline())
    f.close()

    fee = 0.005
    historicals = getHistoricals(coinID)
    while True:
        frame = wsClient.frame
        livest, livelt = liveSMA(historicals, wsClient.frame)
        #buying crypto at the crossover of the moving averages
        if livest > livelt and not open_position:
            if smallLoan < frame.Price[0]:
                break

            print('I bought at $' + str(frame.Price[0]))
            buyprice = float(frame.Price[0])
            transPrice = float(frame.Price[0]*qty+(frame.Price[0]*qty*fee))
            temptime = client.get_time()

            log = ('I bought ' +str(qty)+ ' ' +coinID+ ' at ' +str(client.get_time().get('iso'))+ 
            '\nPrice at time of trade: $' +str(frame.Price[0])+ 
            '\nTotal Price of Buy: $' +str(transPrice)+ 
            '\nBalance: $' + str(smallLoan-(transPrice-(transPrice*fee)))+ '\n~~~~~~~~~~~~~~~~~~~~\n')
            smallLoan = smallLoan-(transPrice-(transPrice*fee))


            f = open('log.txt', 'a')
            f.write(log)
            f.close()
            open_position = True

        #selling bought Crypto
        if open_position:
            if frame.Price[0] < buyprice * SL_limit or frame.Price[0] > buyprice * 1.02:
                sellprice = float(frame.Price[0]*qty)
                sellprice = float(sellprice - (sellprice*fee))
                print('I sold at $' + str(frame.Price[0]))

                log = ('I sold ' +str(qty)+ ' ' +coinID+ ' at ' +str(client.get_time().get('iso'))+ 
                '\nPrice at time of trade: $' +str(frame.Price[0])+ 
                '\nTotal Price of sell: $' +str(sellprice)+ 
                '\nBalance: $' + str(smallLoan+(sellprice-(sellprice*fee)))+ '\n~~~~~~~~~~~~~~~~~~~~\n')
                smallLoan = smallLoan+(sellprice-(sellprice*fee))

                f = open('log.txt', 'a')
                f.write(log)
                f.close()

                break

    f = open('balance.txt', 'w')
    f.write(str(smallLoan))
    f.close()

while True:
    strat(coinID, 2, 0.98)
    time.sleep(30)

wsClient.close()
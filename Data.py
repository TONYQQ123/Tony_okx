import okx.PublicData as PublicData
import time
import okx.MarketData as MarketData
import json

def get_data(symbol,api,trade_type):
    try:
        return data(symbol,api,trade_type)
    except:
        print("Update Price Failed!")
        time.sleep(2)
        return data(symbol,api,trade_type)

def data(symbol,api,trade_type):
    marketDataAPI = api
    result = marketDataAPI.get_ticker(instId=symbol)
    if result['code']!='0':
        print('取得資料失敗')
        # print('錯誤: ',result,'幣: ',symbol)
        return None
    result=result['data'][0]
    instType = result['instType']
    instId = result['instId']
    last = result['last']
    lastSz = result['lastSz']
    askPx = result['askPx']
    askSz = result['askSz']
    bidPx = result['bidPx']
    bidSz = result['bidSz']
    open24h = result['open24h']
    high24h = result['high24h']
    low24h = result['low24h']
    volCcy24h = result['volCcy24h']
    vol24h = result['vol24h']
    ts = result['ts']
    sodUtc0 = result['sodUtc0']
    sodUtc8 = result['sodUtc8']

    data={'symbol':instId,'price':last,'size':lastSz,'timestamp':ts}
    # print(data)
    return data

if __name__=='__main__':
    with open('settings.json','r') as file:
        setting=json.load(file)
    api = MarketData.MarketAPI(setting['FLAG'])
    print(get_data('TRX-USDT-SWAP',api,'SWAP'))
    # Doge=api.get_ticker(instId='DOGE-USDT-SWAP')
    # Dot=api.get_tickers(instType='SWAP',uly='DOT-USDT')
    # BTC=api.get_tickers(instType='SWAP',uly='BTC-USDT')
    # ada=api.get_tickers(instType='SWAP',uly='ADA-USDT')

    # print('DOGE Data: ',Doge,'\n\n')
    # print('DOT Data: ',Dot,'\n\n')
    # print('BTC Data: ',BTC,'\n\n')
    # print('ADA Data: ',ada,'\n\n')
    



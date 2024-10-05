import okx.Trade as Trade
import json
import time

def place_limit(api,orders)->None:
    for order in orders:
        if order['size']==0:
            # print(order)
            # print('無法下單')
            continue
        result=api.place_order(
            instId=order['symbol'],
            tdMode="cross",
            side=order['side'],
            ordType="limit",
            posSide='net',
            px=order['price'],
            sz=str(order['size'])
        )
        a=order['size']
        # print(a)
        if result['code']=='0':
            pass
            # print(order)
            print('下單成功')
        else:
            # print(order)
            # print(a)
            print('下單失敗',result)
    
def cancel_allOrders(api)->None:
    orders=api.get_order_list()
    orders=orders['data']
    i=0
    for order in orders:
        i+=1
        if i==20:
            time.sleep(3)
            i=0
        a=order['instId']
        b=order['ordId']
        c=order['clOrdId']
        response=api.cancel_order(a,b,c)
        if response['code'] == '0':
            print("订单取消成功！")
        else:
            # print("取消订单时出错：", response['msg'])
            print("取消订单时出错")

def cancel_allPosition(trade_api,account_api)->None:
    positions = account_api.get_positions()
    positions=positions['data']
    i=0
    for position in positions:
        i+=1
        if i==20:
            time.sleep(3)
            i=0
        instId = position['instId']
        mgnMode = position['mgnMode']
        response = trade_api.close_positions(instId, mgnMode)
    # if response['code'] == '0':
    #     pass
    #     # print(f"成功关闭仓位：{instId}")
    # else:
    #     # print(f"关闭仓位失败：{instId}，错误信息：{response['msg']}")
    #     pass

def cancel_and_unwind_all(trade_api,account_api)->None:
    cancel_allOrders(trade_api)
    cancel_allPosition(trade_api,account_api)



if __name__=='__main__':
    with open('settings.json','r') as file:
        setting=json.load(file)
    api=Trade.TradeAPI(setting['api_key'], setting['api_secret'],setting["password"], False,setting['FLAG'])
    result=api.place_order(
            instId='BTC-USDT-SWAP',
            tdMode="cross",
            side='buy',
            posSide='net',
            ordType="limit",
            px='66000.396',
            sz='5'
        )
    print(result)
    # BNB sz:2 4u
    # PEPE sz:0.1 4u
    # ETH sz:0.5 6u
    # AVAX sz:5 5u
    # BCH sz: 4 5u
    # DOT sz:20 4u
    # LINK sz:1 5u
    # SOL sz:1 4.5u
    # UNI sz:1 3.5u
    # BTC sz:5 6.5u




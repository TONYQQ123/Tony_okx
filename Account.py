import json
import okx.Account as Account
import time
class Blance:
    currence={}
    total=0

    def __init__(self,data) -> None:
        if data is not None:
            self.total=data['data'][0].get('totalEq',0)
            for currency_data in data['data']:
                for detail in currency_data.get('details', []):
                    coin=detail.get('ccy')
                    if coin=='USDT':
                        balance = detail.get('availBal')
                        self.currence[coin]=balance

class MyAccount:
    def __init__(self,setting) -> None:
        self.account_api= Account.AccountAPI(setting['api_key'], setting['api_secret'],setting["password"], False,setting['FLAG'])
        result = self.account_api.get_account_balance()
        if result is not None:
            self.balance=Blance(result)
        else:
            print('Get balance failed!')
            self.balance=None
        self.inventory=None
        self.risk_alert=setting['risk_alert']
        self.flag=setting['FLAG']
        self.inital_capital=setting['inital_capital']

    def update_inventory(self,market):
        for m in market:
            result=self.get_inventory(m,type)
            if result is not None:
                self.inventory[m] =result
        self.latest_filled=time.time()
    
    def get_inventory(self,symbol,trade_type)->float:
        temp = self.account_api.get_positions(instType=trade_type, instId=symbol)
        print(temp)
        if temp['code']=='0':
            if temp['data']==[]:
                return 0
            temp=temp['data'][0]
            if temp==[]:
                return 0
            posSide=temp.get('PosSide')
            if posSide==None:
                print('還無交易過')
                return 0
            pos=temp['pos']
            if posSide=='net':
                return float(pos)
            elif posSide=='short':
                return float(pos)*-1
        else:
            print('取得inventory失敗: ',temp,trade_type,symbol)
            return None
    
    def get_balance(self,symbol):
        if symbol is not None:
            return float(self.balance.currence[symbol])
        return self.balance.currence
    


if __name__=='__main__':
    with open('settings.json','r') as file:
        setting=json.load(file)
    a=MyAccount(setting)
    s=a.get_inventory('ETH-USDT-SWAP','SWAP')
    print(s)
    

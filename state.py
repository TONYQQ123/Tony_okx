import Data
import time
from datetime import datetime, timezone, timedelta
import queue
from Account import MyAccount

class State:
    def __init__(self,symbol,strategy_config) -> None:
        self.symbol=symbol
        self.price=None
        self.last_close=None
        self.interval=0.2
        self.timestamp=None
        try:
            self.create_vec()
            self.create_state()
        except Exception as e:
            print('錯誤State')
        self.config=strategy_config

    def update_data(self,data_api,trade_type):
        self.last_close=self.price
        data= Data.get_data(self.symbol,data_api,trade_type)
        if data is not None:
            self.price=float(data['price'])
            # print(f"Updated price for {self.symbol}: {self.price}")
            self.timestamp=datetime.fromtimestamp(int(data['timestamp'])/1000)
        else:
            pass
            # print(f"Updated {self.symbol} Failed!")
    
    def create_state(self):
        self.cd_direction = ""
        self.cd_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
        self.only_pass = ""
        self.cding = False
    
    def create_vec(self):
        self.vec=[]

    def update_vec(self,data_api,trade_type):
        self.update_data(data_api,trade_type)
        if self.last_close is not None:
            vol = abs(self.price - self.last_close)
            self.vec.append(vol)
            if len(self.vec)>self.config['cd_vol_ma_length']:
                del self.vec[0]
            vol_ma=sum(self.vec)/len(self.vec)

            self.only_pass = ""
            if self.cding:
                if self.timestamp- self.cd_time >= timedelta(minutes=self.config['cd_length']):
                    self.cding = False
                    self.cd_direction=""
                elif (
                        vol > vol_ma * self.config['cd_vol_multi']
                        and vol / self.price > self.config['cd_vol_floor']
                    ):
                    self.cd_time = self.timestamp
                    self.cd_direction = "rise" if self.price > self.last_close else "fall"
                    if self.cd_direction == "rise":
                        self.only_pass = "sell"
                    elif self.cd_direction == "fall":
                        self.only_pass = "buy"
            elif (
                vol > vol_ma * self.config['cd_vol_multi']
                and vol / self.price > self.config['cd_vol_floor']
            ):
                self.cding = True
                self.cd_time = self.timestamp
                self.cd_direction = "rise" if self.price > self.last_close else "fall"
                if self.cd_direction == "rise":
                    self.only_pass = "sell"
                elif self.cd_direction == "fall":
                    self.only_pass = "buy"

class OrderChain:
    def __init__(self, account, logic_state: State):
        try:
            self.orders = self.create_order_chain(account,logic_state)
            self.order_constraint(account, logic_state.symbol,logic_state)
        except Exception as e:
            print('錯誤OrderChain')

    def update_order_chain(
        self, account, logic_state: State
    ):
        self.orders = self.create_order_chain(account, logic_state)
        self.order_constraint(account, logic_state.symbol,logic_state)

    def create_unwind_all_orders(self, symbol: str, price: float, inventory: float):
        orders = []
        if inventory > 0:
            order = {
                "symbol": symbol,
                "price": price,
                "size": inventory,
                "side": "sell",
                "type": "unwind_all",
            }
        elif inventory < 0:
            order = {
                "symbol": symbol,
                "price": price,
                "size": -inventory,
                "side": "buy",
                "type": "unwind_all",
            }
        orders.append(order)
        return orders
    #YU: 若logicstate有買賣訊號，按照自定義參數決定買賣多少用多少錢買
    
    def create_order_chain(
        self, account:MyAccount, logic_state: State
    ):
        orders = []
        price = logic_state.price
        last_close = logic_state.last_close
        inventory = account.get_inventory(logic_state.symbol,'SWAP')
        # inventory = account.get_inventory(logic_state.symbol,logic_state.config['type'])
        balance = (
            account.get_balance('USDT') * float(logic_state.config['weight']) * int(logic_state.config["leverage"])
        )
        strategy_config = logic_state.config

        if (
            logic_state.cd_direction == "rise"
            and inventory * price / balance < 0
        ) or (logic_state.cd_direction == "fall" and inventory > 0):
            orders = self.create_unwind_all_orders(
                logic_state.symbol, price, inventory
            )
            return orders

        buys = [
            price * (1 - (s + strategy_config["spread_diff"]))
            for s in strategy_config["spread"]
        ]
        sells = [
            price * (1 + (s + strategy_config["spread_diff"]))
            for s in strategy_config["spread"]
        ]
        #改成有加上最小單位邏輯
        # size = [
        #     balance * p * strategy_config["sizing_factor"] / price
        #     for p in strategy_config["position_size"]
        # ]

        size = [
            # float(int((balance * p * strategy_config["sizing_factor"] / price)/(strategy_config['min_order']))*strategy_config['min_order'])/strategy_config['one_sz']
            float(strategy_config['one_sz'])
            for p in strategy_config["position_size"]
        ]
        volatility = abs(last_close - price)

        bias_factor = strategy_config["bias"] * -1
            #breakpoint()
        if inventory > 0:
            long_bias = [1 + ((inventory / s) * bias_factor * 2) if s!=0 else 0 for s in size]
            sell_bias = [1 + ((inventory / s) * bias_factor) if s!=0 else 0 for s in size]
        elif inventory < 0:
            long_bias = [1 + ((inventory / s) * bias_factor) if s!=0 else 0 for s in size]
            sell_bias = [1 + ((inventory / s) * bias_factor * 2) if s!=0 else 0 for s in size]
        else:
            long_bias = [1 + ((inventory / s) * bias_factor) if s!=0 else 0 for s in size]
            sell_bias = [1 + ((inventory / s) * bias_factor) if s!=0 else 0 for s in size]

        buys = [
            {
                "symbol": logic_state.symbol,
                "price": min(a * b - volatility, price * 0.9995),
                "size": sz,
                "side": "buy",
                "type": "normal",
            }
            for a, b, sz in zip(buys, long_bias, size)
        ]
        sells = [
            {
                "symbol": logic_state.symbol,
                "price": max(a * b + volatility, price * 1.0005),
                "size": sz,
                "side": "sell",
                "type": "normal",
            }
            for a, b, sz in zip(sells, sell_bias, size)
        ]

        #YU: 開始買賣
        if logic_state.only_pass == "buy":
            cumu_order_size = 0
            for buy in buys:
                if inventory == 0:#YU: 庫存為0不買賣有點奇怪
                    continue
                if cumu_order_size + buy["size"] < abs(inventory):
                    buy["type"] = "only_pass"
                    orders.append(buy)
                    cumu_order_size += buy["size"]
                else:
                    buy["size"] = abs(inventory) - cumu_order_size
                    buy["type"] = "only_pass"
                    orders.append(buy)
                    break
        elif logic_state.only_pass == "sell":
            cumu_order_size = 0
            for sell in sells:
                if inventory == 0:
                    continue
                if cumu_order_size + sell["size"] < abs(inventory):
                    sell["type"] = "only_pass"
                    orders.append(sell)
                    cumu_order_size += sell["size"]
                else:
                    sell["size"] = abs(inventory) - cumu_order_size
                    sell["type"] = "only_pass"
                    orders.append(sell)
                    break
        else:
            orders += buys
            orders += sells

        # for i in orders:
        #     if i["price"] < 0:
        #         print(long_bias)
            # import sys
            # sys.exit()
        return orders
    
    def order_constraint(self, account, symbol,logic_state:State):
        max_nav = account.get_balance('USDT') * logic_state.config['leverage'] * logic_state.config['weight']

        remove_orders = []
        # inventory = account.get_inventory(logic_state.symbol,logic_state.config['type'])
        inventory = account.get_inventory(logic_state.symbol,'SWAP')
        for order in self.orders:
            if order["side"] == "buy" and inventory > 0:
                if (order["size"] + inventory) * order[
                    "price"
                ] > max_nav:
                    remove_orders.append(order)
            elif order["side"] == "sell" and inventory < 0:
                if (order["size"] + abs(inventory)) * order[
                    "price"
                ] > max_nav:
                    remove_orders.append(order)
        if len(remove_orders) > 0:
            for order in remove_orders:
                # print("Remove order:", order)
                self.orders.remove(order)

if __name__=='__main__':
    pass
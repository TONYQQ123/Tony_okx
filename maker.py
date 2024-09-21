import okx.Trade as Trade
import okx.Account as Account
import json
from Account import Blance,MyAccount
import okx.MarketData as MarketData
from collections import defaultdict
import threading
from state import State,OrderChain
from trade import place_limit,cancel_allOrders,cancel_and_unwind_all
import os
import signal
import sys
import schedule
import time
from openpyxl import Workbook,load_workbook
from datetime import datetime
import pandas as pd
class ModelState:
    def __init__(self, config,account:MyAccount,data_api):
        self.count=0
        self.config = config
        self.maker_config = {
            market_config["market"]: market_config
            for market_config in config["maker_config"]
        }
        self.markets = list(self.maker_config.keys())

        self.bar_config = defaultdict(lambda: defaultdict(dict))
        for m in self.markets:
            self.bar_config[m] = {"look_back_period": 360}
            self.bar_config[m] = {"look_back_period": 360}

        self.account = account
        self.data_thread = threading.Thread(
            target=self.account.update_inventory,
            args=(self.markets,),
        )
        self.data_thread.start()
        self.logic_state = {
            market: State(market,self.maker_config[market]['strategy_config'])
            for market in self.markets
        }

        for logic_state in self.logic_state.values():
            logic_state.update_vec(data_api,config['INSTRUMENY'])
        
    
    def update_state(self, markets: list,data_api,trade_type):
        for market in markets:
            self.logic_state[market].update_vec(data_api,trade_type)

def run_threads(threads: list, timeout: int):
    for th in threads:
        th.start()

    for th in threads:
        th.join(timeout=timeout)
    
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

import csv

def write_to_csv(data):
    file_name = "assets.csv"
    fieldnames = ['num', 'assets', 'time']

    with open(file_name, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0:
            writer.writeheader()

        for row in data:
            writer.writerow({'num': row[0], 'assets': row[1], 'time': row[2]})


def calculate_and_send_orders(account: MyAccount, logic_state: State,trade_api):
    order_chain = OrderChain(account,logic_state)
        # print(order_chain.orders)
        # send orders
            # try:
            #     exchange_api.cancel_all_orders(account.okx, logic_state.market)
            # except:
            #     pass
    try:
            cancel_allOrders(trade_api)
    except:
        pass
    print('開始下單')
    place_limit(trade_api, order_chain.orders)
    model_state.count+=1
    current_time=datetime.now()
    assets=[model_state.count,account.balance.total,current_time]
    write_to_csv([assets])
    print(account.balance.total)
    print('order sent')
        # else:
        #     res = exchange_api.create_basket_limit_orders2(account.okx,order_chain.orders)
            
        #     logging.info(res)

def main(model_state: ModelState, markets: list,data_api,trade_api):
        # cancel all orders (multi-threads)
    if model_state.config["time_offset"] > 0:
        time.sleep(model_state.config["time_offset"])
    try:
        cancel_allOrders(trade_api)
    except:
        pass
            # threads = []
            # for market in markets:
            #     if model_state.account.resend_type[market] == "resend_every_time":
            #         threads.append(
            #             threading.Thread(
            #                 target=exchange_api.cancel_all_orders,
            #                 args=(
            #                     model_state.account.okx,
            #                     market,
            #                 ),
            #             )
            #         )
            #     elif model_state.account.resend_type[market] == "resend_when_any_filled":
            #         threads.append(threading.Thread(target=model_state.account.check_resend_flag))

            # run_threads(threads, timeout=10)
        

        # update quote and account data (single thread)
    model_state.update_state(markets,data_api,model_state.config['INSTRUMENY'])
        # print(f"[{datetime.now()}] model state updated.")

        # calculate new orders (multi-threads)
    threads = []
    for market in markets:
        #calculate_and_send_orders(model_state.account,model_state.logic_state,trade_api)
        threads.append(
            threading.Thread(
                target=calculate_and_send_orders,
                args=(
                    model_state.account,model_state.logic_state[market],trade_api
                ),
            )
        )
    run_threads(threads, timeout=10)

def riskmanagement(account: MyAccount,symbol,trade_api):
    current_balance = account.get_balance(symbol)
    risk_ratio = account.risk_alert
    if current_balance < account.inital_capital *(1-risk_ratio):
        cancel_and_unwind_all(trade_api)
        print(f"{round(risk_ratio * 100,2)}% RISK ALERT !")
        current_pid = os.getpid()
        try:
            os.kill(current_pid,signal.SIGKILL)
            sys.exit()
        
        except:
            print("SHUTDOWN FAILED, TRY AGAIN")
            os._exit(0)


def routine_schedule(model_state: ModelState,data_api,trade_api):
    try:
        schedule_second = {}
        for market, maker_config in model_state.maker_config.items():
            if maker_config["time_offset"] in list(schedule_second.keys()):
                schedule_second[maker_config["time_offset"]].append(market)
            else:
                schedule_second[maker_config["time_offset"]] = [market]

        for second, markets in schedule_second.items():
            schedule.every().minute.at(":%02d" % second).do(main, model_state, markets,data_api,trade_api)

        schedule.every().minute.at(":00").do(riskmanagement, model_state.account,'USDT',trade_api)
        # schedule.every(15).minutes.at(":00").do(log_trades, my_client, model_state)
    except Exception as e:
        print(e)


if __name__=='__main__':
    with open('settings.json','r') as file:
        setting=json.load(file)
    tradeAPI=Trade.TradeAPI(setting['api_key'], setting['api_secret'],setting["password"], False,setting['FLAG'])
    marketDataAPI = MarketData.MarketAPI(setting['FLAG'])

    account=MyAccount(setting)
    model_state=ModelState(setting,account,marketDataAPI)
    main(model_state,model_state.markets,marketDataAPI,tradeAPI)
    routine_schedule(model_state,marketDataAPI,tradeAPI)

    stop_requested = False
    stop_lock = threading.Lock()
    def key(trade_api):
        while True:
            stop=str(input('輸入end停止: '))
            if stop=='end':
                with stop_lock:
                    global stop_requested
                    stop_requested=True
                cancel_and_unwind_all(trade_api)
                break

    key_input=threading.Thread(target=key,args=(tradeAPI,))
    key_input.start()
    while not stop_requested:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            stop_requested = True
        except Exception as exception:
            print(f"Continuing after problem running market-making iteration: {exception}")
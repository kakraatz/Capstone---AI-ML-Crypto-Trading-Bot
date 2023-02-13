# -*- coding: utf-8 -*-
"""
Created on Sun Feb 12 09:16:50 2023

@author: JohnMurphy
"""
from krm_lib.services.machinelearning.rl.enviornments.trading import TradingEnv
from krm_lib.services.machinelearning.rl.agents.ppo_agent import Agent
from krm_lib.services.machinelearning.rl.agents.ppo_agent import ActorNetwork
from krm_lib.services.machinelearning.rl.agents.ppo_agent import CriticNetwork
from krm_lib.services.data.stock.stocks import StockHistory
from krm_lib.services.data.crypto.crypto import CryptoHistory
from krm_lib.utilities.helpers import Plotters
import matplotlib.pyplot as plt
import numpy as np
# PyTorch
import os
import pandas as pd
import torch as T
from krm_lib.services.apis.binance import BinanceAPI



# STOCK CONSTANTS
STOCK_START_DATE = "2017-01-1"
STOCK_END_DATE = "2022-06-01"
STOCK_SYMBOL = "AAPL"

# CRYPTO CONSTANTS
CRYPTO_SYMBOL = "BTCUSD"
# Time Range for Training Dataset
CRYPTO_START = "2020-06-01"
CRYPTO_END = "2023-02-10"

alpha = 0.0004
def run_test():
    # Get Test Data
    crypto_test = CryptoHistory(symbol=CRYPTO_SYMBOL, start_date=CRYPTO_START, end_date=CRYPTO_END)
    df = crypto_test.get_scaled_price_df()  

    # Min Max Scaled
    df_mod = df.copy()
    
    # Split Training and Testing
    df_train = df_mod.copy()
    df_train = df_train.iloc[:500]
    df_test = df_mod.copy()
    df_test = df_test.iloc[500:]   
    
    
    env = TradingEnv(df_test, initial_account_balance=1000000)
    # LOAD
    n_actions = env.action_space.n
    input_dims = env.observation_space.shape
    #alpha = 0.0003
    model = ActorNetwork(n_actions, input_dims, alpha)
    model.load_state_dict(T.load("tmp/actor_torch_ppo"))
    model.eval()
    
    # RUN
    reporting_df = df_test.copy()
    long_probs = []
    short_probs = []
    is_long = 1
    is_short = 1
    long_ratio = 0.5
    for step in range(5, len(reporting_df)): # changed from reporting_df

        item_0_T0 = df_mod.loc[step - 0, "Open"].item()
        item_1_T0 = df_mod.loc[step - 0, "High"].item()
        item_2_T0 = df_mod.loc[step - 0, "Low"].item()
        item_3_T0 = df_mod.loc[step - 0, "Close"].item()
        item_4_T0 = df_mod.loc[step - 0, "Volume"].item()
        item_5_T0 = df_mod.loc[step - 0, "VWAP"].item()
        
        obs = np.array([item_0_T0, item_1_T0, item_2_T0, item_3_T0, item_4_T0, item_5_T0, long_ratio])
        
        state = T.tensor(obs).float().to(model.device)
        dist = model(state)
        probs = dist.probs.cpu().detach().numpy()
        
        print(np.argmax(probs), probs)
        action = np.argmax(probs)
        
        if action == 0:
            is_long += 1
        if action == 0: # Edited from 0? not sure why that would be incorrect
            is_short += 1
        long_ratio = is_long / (is_long + is_short)

        long_probs.append(probs[0])
        short_probs.append(probs[1])


    # Equity Capital Benchmark
    capital = 1
    perc_invest = 1
    df_res = reporting_df.copy()
    df_res = df_res[["Open", "Close_Price"]]
    df_res["Returns"] = df_res["Close_Price"] / df_res["Close_Price"].shift(1) - 1
    df_res = df_res.iloc[5:, :]
    df_res["Longs"] = long_probs
    df_res["Shorts"] = short_probs
    df_res.loc[df_res["Longs"] >= 0.5, "DIR"] = df_res["Longs"]
    df_res.loc[df_res["Longs"] < 0.5, "DIR"] = -df_res["Shorts"]
    df_res = df_res.reset_index(drop=True)

    equity = capital
    equities = [capital]
    for index, row in df_res.iterrows():
        if index > 0:
            dir_value = df_res.loc[index - 1, "DIR"].item()
            ret_value = df_res.loc[index, "Returns"].item()
            equity = equities[index - 1] + equities[index - 1] * perc_invest * dir_value * ret_value
            equities.append(equity)
            
    df_res["Equity"] = equities
    df_res["Benchmark"] = df_res["Returns"].cumsum() + 1
    df_res.head()
    df_res

    # Very Interesting Plot of Buy and Sell Calls
    plt.rcParams["figure.figsize"] = (15,3)
    df_res[["Longs"]].plot(color="green")
    df_res[["Shorts"]].plot(color="red")

    # Metrics
    Benchmark_Perc = (df_res["Close_Price"].iloc[-1] / df_res["Close_Price"].iloc[0] - 1) * 100
    ROI_Perc = (df_res["Equity"].iloc[-1] / capital - 1) * 100
    print(f"Benchmark Return {round(Benchmark_Perc, 2)}%")
    print(f"ROI at {round(ROI_Perc, 2)}%")

    plt.rcParams["figure.figsize"] = (15,5)
    df_res[["Benchmark", "Equity"]].plot()
    return df, df_train, df_test

def run_train():
    # Get Training Data
    crypto_train = CryptoHistory(symbol=CRYPTO_SYMBOL, start_date=CRYPTO_START, end_date=CRYPTO_END)
    df = crypto_train.get_scaled_price_df()
    
    # Min Max Scaled
    df_mod = df.copy()
    
    # Split Training and Testing
    df_train = df_mod.copy()
    df_train = df_train.iloc[:500]
    df_test = df_mod.copy()
    df_test = df_test.iloc[500:]   
    
    plt.rcParams["figure.figsize"] = (15,5)
    df_train["Close_Price"].plot()
    df_test["Close_Price"].plot()
    
    env = TradingEnv(df_train, initial_account_balance=1000000)
    N = 20
    batch_size = 5
    n_epochs = 10
    
    agent = Agent(n_actions=env.action_space.n, batch_size=batch_size, 
                    alpha=alpha, n_epochs=n_epochs, 
                    input_dims=env.observation_space.shape)

    n_games = 1000
    figure_file = 'crypto_training.png'

    best_score = env.reward_range[0]
    score_history = []

    learn_iters = 0
    avg_score = 0
    n_steps = 0
    
    print("... starting ...")
    for i in range(n_games):
        observation = env.reset()
        done = False
        score = 0
        while not done:
            action, prob, val = agent.choose_action(observation)
            observation_, reward, done, info = env.step(action)
            n_steps += 1
            score += reward
            agent.remember(observation, action, prob, val, reward, done)
            if n_steps % N == 0:
                agent.learn()
            observation = observation_
            
        # Save history
        score_history.append(score)
        avg_score = np.mean(score_history[-50:])
        
        if avg_score > best_score:
            best_score = avg_score
            agent.save_models()
        
        print(f"episide: {i}, score: {score}, avg score: {avg_score}, best_score: {best_score}")
            
    plotter = Plotters()
    x = [i+1 for i in range(len(score_history))]
    plotter.plot_learning_curve(x, score_history, figure_file)
    return df, df_train, df_test
# Test Main

if __name__ == '__main__':
    #df, df_train, df_test = run_train()
    df, df_train, df_test = run_test()
    #binance = BinanceAPI()
    #df = binance.get_daily_price_history(CRYPTO_SYMBOL, CRYPTO_START, CRYPTO_END, 'dataframe')
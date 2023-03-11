# -*- coding: utf-8 -*-
"""
Created on Sun Feb 12 08:52:28 2023

@author: JohnMurphy
"""
import numpy as np
import matplotlib.pyplot as plt
# MAIN

class Plotters():
    def __init__(self):
        pass
    
    def plot_learning_curve(self, x, scores, figure_file="learning_curve.png"):
        plt_learning_curve_fig = plt.figure(figsize=(15,5))
        running_avg = np.zeros(len(scores))
        for i in range(len(running_avg)):
            running_avg[i] = np.mean(scores[max(0, i-50):(i+1)])
            plt.plot(x, running_avg)
            plt.title('Running average of previous 50 scores')
            plt.savefig(figure_file)

    def plot_market_train_test(self, df_train, df_test, figure_file="train_test_split.png"):
        train_test_fig = plt.figure(figsize=(15,5))
        df_train["Close_Price"].plot()
        df_test["Close_Price"].plot()
        plt.title('Market Price - Train/Test Split')
        plt.savefig(figure_file)
        
    def plot_test_profit(self, df_profit, df_price, figure_file="test_profit.png"):
        test_profit_fig = plt.figure(figsize=(15,5))
        df_profit["Profit"].plot(color='green')
        df_price["Price"].plot(color='black')
        plt.title('Market Price vs. Profit')
        plt.savefig(figure_file)
        
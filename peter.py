# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt


# Create a Stratey
class TestStrategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None

        self.POINT_DISTANCE_TO_CLOSE_TRADE = 0.03
        self.BET_SIZE_MULTIPLIER = 18
        self.bankrupt = False

        self.startingBetSize = 1700
        self.betSize = self.startingBetSize
        self.shouldLong = True
        self.isLong = False

        self.totalTrades = 0
        self.totalWins = 0
        self.totalLosses = 0
        self.biggestLossStreak = 0
        self.currentLossStreak = 0

        self.macdDaily = bt.indicators.MACD(self.data1,
            period_me1=self.p.macd1,
            period_me2=self.p.macd2,
            period_signal=self.p.macdsig)

        self.macdWeekly = bt.indicators.MACD(self.data2,
            period_me1=self.p.macd1,
            period_me2=self.p.macd2,
            period_signal=self.p.macdsig)

        self.macdMonthly = bt.indicators.MACD(self.data3,
            period_me1=self.p.macd1,
            period_me2=self.p.macd2,
            period_signal=self.p.macdsig)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                self.buyprice = order.executed.price

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            self.bankrupt = True

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        if trade.pnl < 0: 
            self.betSize = self.betSize * 2
            self.currentLossStreak += 1
            self.totalLosses += 1
            if self.currentLossStreak > self.biggestLossStreak:
                self.biggestLossStreak = self.currentLossStreak
        else:
            self.betSize = self.startingBetSize
            self.startingBetSize += self.BET_SIZE_MULTIPLIER
            self.currentLossStreak = 0
            self.totalWins += 1

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        # self.log('Close, %.2f' % self.dataclose[0])

        if self.bankrupt is True:
            cerebro.runstop()

        # red line
        print(self.macdDaily.macd[0])
        # blue line
        print(self.macdDaily.signal[0])

        if self.macdMonthly.macd[0] > 0 and self.macdMonthly.macd[0] > self.macdMonthly.macd[-1] and self.macdWeekly.macd[0] > 0 and self.macdWeekly.macd[0] > self.macdWeekly.macd[-1] and self.macdDaily.macd[0] > 0:
            self.shouldLong = True
        elif self.macdMonthly.macd[0] < 0 and self.macdMonthly.macd[0] < self.macdMonthly.macd[-1] and self.macdWeekly.macd[0] < 0 and self.macdWeekly.macd[0] < self.macdWeekly.macd[-1] and self.macdDaily.macd[0] < 0:
            self.shouldLong = False

        if self.order:
            return

        if not self.position:
            if self.shouldLong:
                self.isLong = True
                self.order = self.buy(size=self.betSize)
            else:
                self.isLong = False
                self.order = self.sell(size=self.betSize)
            self.totalTrades += 1
                

        # Sort out how to sell now
        
        # if self.position:
        #     if self.dataclose[0] >= self.buyprice + self.POINT_DISTANCE_TO_CLOSE_TRADE or self.dataclose[0] <= self.buyprice - self.POINT_DISTANCE_TO_CLOSE_TRADE:
        #         self.order = self.close()

    def stop(self):
        print('Total trades: ', self.totalTrades)
        print('Total wins: ', self.totalWins)
        print('Total losses: ', self.totalLosses)
        if self.totalTrades > 0 and self.totalWins > 0:
            print ('Winrate: {0:.0f}%'.format(self.totalWins / self.totalTrades * 100))
        print('Biggest loss streak: ', self.biggestLossStreak)

if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'EURUSD_H1.csv')

    # Create a Data Feed
    data = bt.feeds.GenericCSVData(
        dataname=datapath,
        dtformat=('%Y-%m-%d %H:%M'),
        fromdate=datetime.datetime(2007, 1, 1),
        # todate=datetime.datetime(2007, 10, 20),
        todate=datetime.datetime(2022, 8, 29),
        reverse=False,
        nullvalue=0.0,
        timeframe = bt.TimeFrame.Minutes, 
        compression = 60,
        datetime=0,
        high=2,
        low=3,
        open=1,
        close=4,
        volume=-1,
        openinterest=-1)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    cerebro.resampledata(data, timeframe = bt.TimeFrame.Days, compression = 1)
    cerebro.resampledata(data, timeframe = bt.TimeFrame.Weeks, compression = 1)
    cerebro.resampledata(data, timeframe = bt.TimeFrame.Months, compression = 1)

    # Set our desired cash start
    cerebro.broker.setcash(10000.0)

    # Set the commission
    cerebro.broker.setcommission(commission=0.0, mult=100.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print("Final Portfolio Value: £{:,.2f}".format(cerebro.broker.getvalue()))

    # Plot the result
    cerebro.plot(style='candle')
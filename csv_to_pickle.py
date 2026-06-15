# -*- coding: utf-8 -*-
"""
Created on Tue May 26 04:23:54 2026

@author: 123
"""


import pandas as pd


#df = pd.read_csv("EURUSD60.csv", sep="\t", parse_dates=["time"], index_col="time")

df = pd.read_csv("EURUSD60.csv", sep="\t", header=None,
                 names=["time","open","high","low","close","volume"],
                 parse_dates=["time"], index_col="time",
                 dayfirst=True)
df = df[["open","high","low","close"]]



df.to_pickle("cache/EURUSD_1H_2010_2026.pkl")

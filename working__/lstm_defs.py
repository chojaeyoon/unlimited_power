# -*- coding: utf-8 -*-
"""LSTM_defs.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ziT3-IzwzSAv75zoO8-vRJ9w0kTkKajz
"""

import pandas as pd
from google.colab import drive
from pandas import Series, DataFrame
from matplotlib import pyplot
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import seaborn as sns
from pandas import DataFrame
from pandas import concat
import os
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import torch.optim as optim

def drop_clms(dataset):
  dataset['Time'] = dataset['Hour'] + dataset['Minute']*(0.5/30)
  dataset = dataset[what_to_use]
  return dataset

# 머신러닝에 쓰기 위해서 재정렬 시키는 함수
def series_to_supervised(data, n_in=1, n_out=1, target = 'TARGET', dropnan=True):
    df = DataFrame(data)
    df.drop(target, axis = 1, inplace=True)
    df2 = DataFrame(data[target])
    cols, names = list(), list()
    n_vars = 1 if type(df) is list else df.shape[1]
    n_vars2 = 1 if type(df2) is list else df2.shape[1]
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df2.shift(-i))
        if i == 0:
            names += [('TARGET%d(t)' % (j+1)) for j in range(n_vars2)]
        else:
            names += [('TARGET%d(t+%d)' % (j+1, i)) for j in range(n_vars2)]
    # put it all together
    agg = concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg

def seperator(dataset):
  
  # series_to_supervised 함수를 지나며 전처리를 하면 하나의 row에 이전 7일간의 데이터가 일렬로 들어가고(train), 여기에 target으로 미래 96일 발전량이 따라 붙는다.
  # 이 둘이 한 줄에 있으므로 적절한 지점에서 잘라서 train_X와 train_y로 사용한다.
  X = dataset.iloc[:, :n_obs]
  y = dataset.iloc[:, -future_window:]
  
  # validation을 해야하니까, train으로 준 데이터를 train/test로 자른다.
  # 사용가능한 연도가 3개년이고, 대충 train에 2년치, test에 1년치를 주었다 (7:3)
  # 42 = ultimate answer to life the universe and everything
  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.30, random_state=42)

  # 학습과 검증 데이터를 원하는 모양([1,4,2]) 이런 식으로 바꾸는 함수
  #### 처음 모양 (36490, 2016)
  # 2년치가 데이터(730일 * 하루에 48틱 = 36490개)로 있고, 이전 일주일 데이터 7*48 = 336인데 사용한 변수가 6개라면 336*6이다.
  # 일단 2016개의 데이터를 틱별로(30분 단위로) 잘라준다
  # 한 틱에 6개의 변수가 들어간다면 이를 n_features로 반영
  
  #### 수정할 모양 (36490, 336, 6)
  # 6개 특징이 30분 단위로 336개(일주일) 준비되어 있다.
  # 이런 데이터가 36490개 있어서 학습에 사용할 수 있다.

  # y 데이터는 1개 변수(발전량)만 나오고, 미래 2일 (2*48 = 96틱)이므로
  # 형태 ('총 데이터의 개수', '미래/과거의 길이', '사용한 변수의 개수')
  # == (36490, 96, 1) 으로 reshape 한다.

  train_X = X_train.values
  train_X = train_X.reshape(train_X.shape[0],-1,n_features)
  train_y = y_train.values
  train_y = train_y.reshape(train_y.shape[0],future_window)

  test_X = X_test.values
  test_X = test_X.reshape(test_X.shape[0],-1,n_features)
  test_y = y_test.values
  test_y = test_y.reshape(test_y.shape[0],future_window)

  return train_X, train_y, test_X, test_y

def data_maker(train_X, train_y, test_X, test_y):
  train_X = torch.tensor(np.array(train_X), dtype=torch.float)
  train_X = train_X.transpose(1,0)
  train_y = torch.tensor(np.array(train_y), dtype=torch.float)

  test_X = torch.tensor(np.array(test_X), dtype=torch.float)
  test_X = test_X.transpose(1,0)
  test_y = torch.tensor(np.array(test_y), dtype=torch.float)
  return train_X, train_y, test_X, test_y

############ 파라미터 #####################
# 하루의 틱
ticks = 48
# 예측에 사용할 일수
days = 7
n_days = ticks*days

# 미래 예측할 일수
future_days = 2
future_window = ticks * future_days

### 모든변수
# ['Hour', 'Minute', 'Day', 'WS', 'Time', 'DHI','DNI','RH','T','TARGET']
# 사용할 변수
what_to_use = ['Time', 'DHI','DNI','RH','T','TARGET']

n_features = len(what_to_use) - 1
n_obs = n_days * n_features

# 한 번에 뭉테기로 투입할 자료의 양
batches = 100
# 몇 번이나 반복하여 학습할 것인다.
epoch = 200

def data_loader(dataset):

  ############ 파라미터 #####################
  # 하루의 틱
  ticks = 48
  # 예측에 사용할 일수
  days = 7
  n_days = ticks*days

  # 미래 예측할 일수
  future_days = 2
  future_window = ticks * future_days

  ### 모든변수
  # ['Hour', 'Minute', 'Day', 'WS', 'Time', 'DHI','DNI','RH','T','TARGET']
  # 사용할 변수
  what_to_use = ['Time', 'DHI','DNI','RH','T','TARGET']

  n_features = len(what_to_use) - 1
  n_obs = n_days * n_features


  dataset = drop_clms(dataset)
  dataset = series_to_supervised(dataset, n_days, future_window, target='TARGET')
  train_X, train_y, test_X, test_y = seperator(dataset)
  train_X, train_y, test_X, test_y = data_maker(train_X, train_y, test_X, test_y)
  return train_X, train_y, test_X, test_y
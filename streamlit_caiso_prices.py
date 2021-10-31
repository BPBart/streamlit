# -*- coding: utf-8 -*-
"""
Created on Sat Oct 30 16:38:03 2021

@author: Brian
"""

# %% imports
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import zipfile
import io
import time
import datetime as dt

# %% functions
@st.cache
def get_caiso_csv(url, sleepy=5):
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content),'r')
    z = [pd.read_csv(z.open(f)) for f in z.namelist()][0].rename(columns = {'INTERVALSTARTTIME_GMT':'datetime'})
    z['datetime'] = pd.to_datetime(z['datetime'].str.replace('T',' ')).dt.tz_convert('US/Pacific')
    z = z.sort_values(by = 'datetime')
    time.sleep(sleepy)
    return(z)

def caiso_realtime(date_start = '20211028',date_end = '20211101', node = 'OTMESA_2_PL1X3-APND'):
    url = f'http://oasis.caiso.com/oasisapi/SingleZip?queryname=PRC_INTVL_LMP&startdatetime={date_start}T08:00-0000&enddatetime={date_end}T08:00-0000&version=1&market_run_id=RTM&node={node}&resultformat=6'
    df_rtm = get_caiso_csv(url)
    df_rtm = df_rtm[df_rtm['LMP_TYPE'].isin(['LMP'])]
    df_rtm = df_rtm[['datetime','MW']].rename(columns = {'MW':'Price (RTM)'})
    return df_rtm
def caiso_fmm(date_start = '20211028',date_end = '20211101', node = 'OTMESA_2_PL1X3-APND'):
    url = f'http://oasis.caiso.com/oasisapi/SingleZip?queryname=PRC_RTPD_LMP&startdatetime={date_start}T08:00-0000&enddatetime={date_end}T08:00-0000&version=1&market_run_id=RTPD&node={node}&resultformat=6'
    df_fmm = get_caiso_csv(url)
    df_fmm = df_fmm[df_fmm['LMP_TYPE'].isin(['LMP'])]
    df_fmm = df_fmm[['datetime','PRC']].rename(columns = {'PRC':'Price (FMM)'})
    return df_fmm
def caiso_dam(date_start = '20211028',date_end = '20211101', node = 'OTMESA_2_PL1X3-APND'):
    url = f'http://oasis.caiso.com/oasisapi/SingleZip?queryname=PRC_LMP&startdatetime={date_start}T08:00-0000&enddatetime={date_end}T08:00-0000&version=1&market_run_id=DAM&node={node}&resultformat=6'
    df_dam = get_caiso_csv(url)
    df_dam = df_dam[df_dam['LMP_TYPE'].isin(['LMP'])]
    df_dam = df_dam[['datetime','MW']].rename(columns = {'MW':'Price (DAM)'})
    return df_dam


# %% getting
# generate relevant datetime window
date_start = (dt.date.today()-dt.timedelta(days =2)).strftime("%Y%m%d")
date_end = (dt.date.today()+dt.timedelta(days =2)).strftime("%Y%m%d")

data_load_state = st.text('Loading data...')
st.title('''CAISO Power Prices''')
# dam
df_dam = caiso_dam(date_start,date_end)
df_dam.set_index('datetime',inplace=True)
df_dam = df_dam.resample('5min').pad().reset_index()
# fmm
df_fmm = caiso_fmm(date_start,date_end)
df_fmm.set_index('datetime',inplace=True)
df_fmm = df_fmm.resample('5min').pad().reset_index()
#rtm
df_rtm = caiso_realtime(date_start,date_end)

data_load_state.text('Loading data...done!')
#merge
date_start = (dt.date.today()-dt.timedelta(days =1)).strftime("%Y%m%d")
datebone = pd.DataFrame({'datetime':pd.date_range(date_start,date_end,freq='5min',tz='US/Pacific')})

df_lmps = pd.merge(datebone,df_dam,'left','datetime')
df_lmps = pd.merge(df_lmps,df_fmm,'left','datetime')
df_lmps = pd.merge(df_lmps,df_rtm,'left','datetime')
df_lmps.columns = ['datetime','DAM','FMM','RTM']

df_lmps_1min = df_lmps.copy(deep = True)
df_lmps_1min.set_index('datetime',inplace=True)
df_lmps_1min = df_lmps_1min.resample('1min').pad().reset_index()
df_melt = pd.melt(df_lmps_1min,id_vars='datetime',value_vars=['RTM','FMM','DAM'],value_name = '$/MWh',var_name = 'LMPs')

# %% streamlitting
# chart

st.subheader('Otay Mesa timeseries')
fig = px.line(df_melt,x='datetime',y='$/MWh',color='LMPs')
fig.update_layout(
    font=dict(
        family="Arial",
        size=14,
        color="White"
    )
    )
st.plotly_chart(fig)

mindate = datebone.iloc[0,0].strftime('%Y,%m,%d')
maxdate = datebone.iloc[-1,0].strftime('%Y,%m,%d')
# datetime slider
toggle_datestart = st.sidebar.date_input('start date', datebone.iloc[0,0])
toggle_dateend = st.sidebar.date_input('end date',datebone.iloc[-1,0])

df_melt = df_melt[df_melt['datetime']>=mindate&df_melt['datetime']<=maxdate]
df_lmps = df_lmps[df_lmps['datetime']>=mindate&df_lmps['datetime']<=maxdate]

st.subheader('Raw prices')
st.write(df_lmps)

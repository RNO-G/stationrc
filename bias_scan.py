import numpy as np
import matplotlib.pyplot as plt
import random
import time
import scipy

import stationrc.radiant
import stationrc.remote_control
import pandas as pd

station = stationrc.remote_control.VirtualStation()

def bias_scan(start, end, points): 
    
    channels = range(0, 24)
    ped = [[]]*len(channels)
    tot_ped = [[]]*len(channels)
    scan = []
    interval = np.arange(int(start), int(end), int((end-start)/points))
    
    for v in interval:
        station.radiant_pedestal_set(value = int(v))
        pedestal_at_v = station.radiant_pedestal_get()

        for ch in channels: 
        	# averaged pedestal
            ped[ch] = ped[ch] + [np.mean(pedestal_at_v[ch])]
            #gets the pedestal of all 4096 storage cells
            tot_ped[ch] = tot_ped[ch] + [pedestal_at_v[ch]]

    bias_scan = np.array(interval)
    pedestal = [np.array(j) for j in ped]
    
    return bias_scan, pedestal, tot_ped
    
def line(x, m, b): 
    return m * x + b

def fit(adc, samples):
    opt, _ = scipy.optimize.curve_fit(line, xdata=adc, ydata=samples)
    lin_fit = [opt[0] * x + opt[1] for x in adc]
    return lin_fit, opt[0], opt[1]

def check_coeff(m, b):
    m_min = 1.0
    m_max = 1.3
    b_min = 150.0
    b_max = 250.0
    if ((m_min < m < m_max) & (b_min < b < b_max)):
        print('PASSED')
    else:
        print('FAILED')

#input ADC counts
start = 0 
end = 2000 
points = 10

adc_list, samples, tot_pedestal = bias_scan(start, end, points)

#Change channel here
channel = 0

#prepare the data before the fit
horizontal_arr = [[]]*len(tot_pedestal[channel][0]) #shape 4096*10
for i in range(len(tot_pedestal[channel][0])):
    for i_v in range(len(adc_list)):
        horizontal_arr[i] = horizontal_arr[i] + [tot_pedestal[channel][i_v][i]]
#fit
fit_ped = [[]]*len(horizontal_arr)
channel = 0
for ind in range(len(horizontal_arr)):
    ft = fit(adc_list, horizontal_arr[ind])[0]
    #print(fit(adc_list, horizontal_arr[ind])[1], fit(adc_list, horizontal_arr[ind])[2])
    fit_ped[ind] = fit_ped[ind]+ft

df0 = pd.DataFrame(np.array(fit_ped), columns=adc_list)
#to save and read
#df0.to_csv("tot_pedestal_fit_CH0.csv")
#df0 = pd.read_csv("tot_pedestal_fit_CH0.csv", index_col=0)

plt.rcParams["figure.figsize"] = (7, 5)
for i in range(len(df0)):
    plt.plot(list(df0.columns), horizontal_arr[i], '.', label='data, CH'+str(ch))
    plt.plot(list(df0.columns), df0.iloc[i], '--', label='fit', linewidth=0.5)
plt.xlabel('input ADC')
plt.ylabel('V bias')
plt.grid()
#plt.legend()
plt.show()

#fit averaged pedestals and plot
fit_array = [[]]*24

for ch in range(0,24):
    ft = fit(adc_list, samples[ch])
    fit_array[ch] = fit_array[ch]+ft
    
df_fit = pd.DataFrame(np.array(fit_array), columns=adc_list)

#to save and read
#df_fit.to_csv("bias_scan_fit.csv")
#df_fit = pd.read_csv("bias_scan_fit.csv", index_col=0)

plt.rcParams["figure.figsize"] = (3,0.5)
for ch in range(0, 24):
    plt.plot(list(df_fit.columns), samples[ch], '.', label='data, CH'+str(ch))
    plt.plot(list(df_fit.columns), df.iloc[ch], '--', label='fit', linewidth=0.5)
    plt.xlabel('ADC')
    plt.ylabel('V bias')
    plt.grid()
	plt.legend()
    plt.show()

#plot all pedestal samples with gradient
plt.rcParams["figure.figsize"] = (10,3)
#change channel here
channel = 0

bias = range(adc_list[0], adc_list[-1], int((adc_list[-1]-adc_list[0])/10)) #y
num_samples = range(len(tot_pedestal[channel][0])) #x
# z = relation between x and y: for every value of bias the sample has a corresponding pedestal value
#z dim has to be x * y 
z = tot_pedestal[channel]

c = plt.imshow(z, cmap ='plasma', 
               extent =[min(num_samples), max(num_samples), min(bias), max(bias)],
               interpolation ='nearest', origin ='lower')
plt.colorbar(c)
plt.xlabel('Sample')
plt.ylabel('Bias Input (ADC)')
plt.title('bias scan, CH'+str(channel), fontweight ="ultralight")
plt.show()

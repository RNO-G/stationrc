import numpy as np
import matplotlib.pyplot as plt
from scipy import optimize
import argparse

import stationrc.remote_control
import stationrc.common


parser = argparse.ArgumentParser()

parser.add_argument(
    "-c",
    "--channel",
    type=int,
    default=range(24),
    nargs="*",
    help="Plot certain channel. If None plot all channels. (Default: None)",
)

parser.add_argument("--start", type=int, default=0, nargs="?")
parser.add_argument("--stop", type=int, default=2000, nargs="?")
parser.add_argument("--points", type=int, default=10, nargs="?")

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

station = stationrc.remote_control.VirtualStation()

def bias_scan(start, end, points):

    dac_input = np.arange(int(start), int(end), int((end - start) / points))

    pedestals = np.zeros((len(dac_input), 24, 4096))

    for idx, v in enumerate(dac_input):
        station.radiant_pedestal_set(value = int(v))
        pedestal_at_v = np.array(station.radiant_pedestal_get())

        pedestals[idx] = pedestal_at_v

    return dac_input, pedestals

def line(x, m, b):
    return m * x + b

def fit(adc, samples):
    opt, _ = optimize.curve_fit(line, xdata=adc, ydata=samples)
    lin_fit = opt[0] * adc + opt[1]
    return lin_fit, opt[0], opt[1]


dac_input, pedestals = bias_scan(args.start, args.stop, args.points)
mean_pedestal_per_channel = np.mean(pedestals, axis=-1)

print(mean_pedestal_per_channel.shape)
plt.plot(pedestals[0][0])
plt.xlabel("samples")
plt.ylabel("ADC")
plt.show(block=False)

nrows, ncols = 6, 4
fig, axs = plt.subplots(nrows, ncols, figsize=(10, 10), sharex=True, sharey=True)

for ch, mean_pedestal in enumerate(mean_pedestal_per_channel.T):
    print(dac_input, mean_pedestal)
    lin_fit, a, b = fit(dac_input, mean_pedestal)
    print(lin_fit, a, b)
    axs.flatten()[ch].plot(dac_input, mean_pedestal, '.', label=f'data, CH {ch}')
    axs.flatten()[ch].plot(dac_input, lin_fit, '--')
    axs.flatten()[ch].legend(fontsize=5)


fig.supxlabel('DAC input')
fig.supylabel('ADC output')
fig.tight_layout()
plt.show(block=False)

# for channel in channels:

#     #prepare the data before the fit
#     horizontal_arr = [[]]*len(tot_pedestal[channel][0]) #shape 4096*10
#     for i in range(len(tot_pedestal[channel][0])):
#         for i_v in range(len(adc_list)):
#             horizontal_arr[i] = horizontal_arr[i] + [tot_pedestal[channel][i_v][i]]

#     #fit
#     fit_ped = [[]]*len(horizontal_arr)
#     for ind in range(len(horizontal_arr)):
#         ft = fit(adc_list, horizontal_arr[ind])[0]
#         fit_ped[ind] = fit_ped[ind]+ft

#     df0 = pd.DataFrame(np.array(fit_ped), columns=adc_list)

#     ax = axs[channel // ncols][channel % ncols]
#     for i in range(len(df0)):
#         ax.plot(list(df0.columns), horizontal_arr[i], '.') #data for channel
#         ax.plot(list(df0.columns), df0.iloc[i], '--', linewidth=0.5) #fit
#     ax.set_xlabel('input ADC')
#     ax.set_ylabel('V bias')
# fig.tight_layout()
# #plt.savefig("bias_scan_total_fit.png")
# #plt.close()
# plt.show(block=False)


#plot all pedestal samples with gradient
fig, axs = plt.subplots(4, 6, figsize=(16, 8), sharex=True, sharey=True, layout='constrained')

bias = range(dac_input[0], dac_input[-1], int((dac_input[-1] - dac_input[0]) / len(dac_input))) #y

# v_adc, channel, sample -> channel, v_adc, sample
pedestals = np.swapaxes(pedestals, 0, 1)

for idx, (ax, peds) in enumerate(zip(axs.flatten(), pedestals)):
    c = ax.imshow(peds, cmap ='plasma',
                   extent =[0, 4095, min(bias), max(bias)],
                   interpolation ='nearest', origin ='lower')

cbr = fig.colorbar(c, ax=axs.ravel().tolist(), pad=0.02)
cbr.set_label(r"ADC output")
fig.supxlabel('samples')
fig.supylabel('DAC input')
# fig.subplots_adjust(hspace=0.02)
plt.show()

import sys
import numpy as np

try:
    from matplotlib import pyplot as plt
except ImportError:
    print("matplotlib not available - you can not plot daq data")

try:
    import mattak.Dataset
except ImportError:
    print("mattak not available - you can not rootify daq data")

# From testing in Chicago
# host_aliases = {
#     "st11": "10.42.1.30",
#     "radiant-017": "10.42.1.30",

#     "st12": "10.42.1.94",
#     "radiant-007": "10.42.1.94",
#     "radiant-016": "10.42.1.94",

#     "st13": "10.42.1.188",
#     "radiant-014": "10.42.1.188",

#     "st14": "10.42.1.134",
#     "radiant-012": "10.42.1.134",

#     "st15": "10.42.1.102",
#     "radiant-011": "10.42.1.102",

#     "st16": "10.42.1.254",
#     "radiant-004": "10.42.1.254",

#     "st17": "10.42.1.168",
#     "radiant-003": "10.42.1.168",

#     "127.0.0.1": "127.0.0.1"
# }

# Greenland
host_aliases = {

    "st11": "10.3.0.53",
    "rno-g-011": "10.3.0.53",

    "st12": "10.3.0.42",
    "rno-g-012": "10.3.0.42",

    "st13": "10.3.0.9",
    "rno-g-013": "10.3.0.9",

    "st14": "10.3.0.56",
    "rno-g-014": "10.3.0.56",

    "st21": "10.3.0.6",
    "rno-g-021": "10.3.0.6",

    "st22": "10.3.0.60",
    "rno-g-022": "10.3.0.60",

    "st23": "10.3.0.20",
    "rno-g-023": "10.3.0.20",

    "st24": "10.3.0.10",
    "rno-g-024": "10.3.0.10",

    "127.0.0.1": "127.0.0.1"
}

def convert_alias_to_ip(host):

    if host in host_aliases:
        host = host_aliases[host]
    else:
        if host not in host_aliases.values():
            # raise ValueError(f"Unknown host: {host}")
            print(f"Unknown host: {host}")

    # match = re.match(f"[0-9]{3}\.[0-9]{2}\.[0-9]{1}\.[0-9]{3}", host)
    # assert match is not None, f"{host} is not a valid ip address"


    return host


def get_channels_for_quad(quad):
    if quad == 0:
        return [0, 1, 2, 3, 12, 13, 14, 15]
    if quad == 1:
        return [4, 5, 6, 7, 16, 17, 18, 19]
    if quad == 2:
        return [8, 9, 10, 11, 20, 21, 22, 23]
    return None


def quad_for_channel(channel_id):
    if channel_id in [0, 1, 2, 3, 12, 13, 14, 15]:
        return 0
    elif channel_id in [4, 5, 6, 7, 16, 17, 18, 19]:
        return 1
    elif channel_id in [8, 9, 10, 11, 20, 21, 22, 23]:
        return 2
    else:
        raise ValueError("Invalid channel id!")


def plot_run_waveforms(data_path):

    import os
    
    plot_path = os.path.join(data_path, "plots")
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
    
    from rnog_analysis_tools.glitch_unscrambler import glitch_detection_per_event
    dset = mattak.Dataset.Dataset(station=0, run=0, data_path=data_path)

    dset.setEntries((0, dset.N()))
    
    for idx, (ev, wfs) in enumerate(dset.iterate()):

        fig, axs = plt.subplots(4, 6, sharex=True, sharey=True, gridspec_kw=dict(hspace=0.06, wspace=0.06))
        fig2, axs2 = plt.subplots(4, 6, sharex=True, sharey=True, gridspec_kw=dict(hspace=0.06, wspace=0.06))

        print(ev)
        for ch in range(24):
            ax = axs.flatten()[ch]
            ax2 = axs2.flatten()[ch]
            times = np.arange(len(wfs[ch])) / 2.4
            ax.plot(times, wfs[ch], label=f"Ch {ch}", lw=1)
            ax.legend(fontsize=5)
            ax.grid()
            # ax.set_xticks([500, 1500])

            # print(f"Ch{ch}: {glitch_detection_per_event.is_channel_scrambled(wfs[ch])}")
            # ax2.plot(np.fft.rfftfreq(2048, 1 / 2.4) * 1000, 20 * np.log10(np.abs(np.fft.rfft(wfs[ch]))),
            #          label=f"Ch {ch}", color="C1", lw=1)

            ax2.plot(wfs[ch],
                     label=f"Ch {ch}", color="C1", lw=1)
            
            ax2.legend(fontsize=5)
            ax2.grid()
            # ax2.set_yscale("log")
            # ax2.set_xlim(None, 850)


        fig.supxlabel("time / ns")
        fig.supylabel("ADC")
        # fig.savefig(f"waveforms_{dset.run}_{idx}.png", transparent=False)

        # ax.set_xlim(30, 120)
        # fig.savefig(f"waveforms_{dset.run}_{idx}_zoom.png", transparent=False)

        fig2.supxlabel("Sample")
        fig2.supylabel("ADU")

        # fig2.savefig(f"spectras_{dset.run}_{idx}.png", transparent=False)

        # sys.exit()
        plt.savefig(os.path.join(plot_path, f"evt_{idx}.pdf"))
        plt.close()


if __name__ == "__main__":

    plot_run_waveforms(sys.argv[1])
    # convert_alias_to_ip(sys.argv[1])

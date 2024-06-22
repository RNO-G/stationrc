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

host_aliases = {
    "st11": "10.42.1.30",
    "radiant-017": "10.42.1.30",

    "st12": "10.42.1.94",
    "radiant-007": "10.42.1.94",
    "radiant-016": "10.42.1.94",

    "st13": "10.42.1.188",
    "radiant-014": "10.42.1.188",

    "st14": "10.42.1.134",
    "radiant-012": "10.42.1.134",

    "st15": "10.42.1.102",
    "radiant-011": "10.42.1.102",

    "st16": "10.42.1.254",
    "radiant-004": "10.42.1.254",

    "st17": "10.42.1.168",
    "radiant-003": "10.42.1.168",

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

def plot_run_waveforms(data_path):

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

            ax2.plot(np.fft.rfftfreq(2048, 1 / 2.4) * 1000, np.abs(np.fft.rfft(wfs[ch])),
                     label=f"Ch {ch}", color="C1", lw=1)
            ax2.legend(fontsize=5)
            ax2.grid()
            ax2.set_yscale("log")
            ax2.set_xlim(None, 850)


        fig.supxlabel("time / ns")
        fig.supylabel("ADC")
        # fig.savefig(f"waveforms_{dset.run}_{idx}.png", transparent=False)

        # ax.set_xlim(30, 120)
        # fig.savefig(f"waveforms_{dset.run}_{idx}_zoom.png", transparent=False)

        fig2.supxlabel("frequency / MHz")
        fig2.supylabel("spectrum / a.u.")

        # fig2.savefig(f"spectras_{dset.run}_{idx}.png", transparent=False)

        # sys.exit()
        plt.show()


if __name__ == "__main__":

    plot_run_waveforms(sys.argv[1])
    # convert_alias_to_ip(sys.argv[1])
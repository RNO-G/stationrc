import sys
import numpy as np
import mattak.Dataset
from matplotlib import pyplot as plt

host_aliases = {

}


def plot_run_waveforms(data_path):

    dset = mattak.Dataset.Dataset(station=0, run=0, data_path=data_path)

    dset.setEntries((0, dset.N()))

    for ev, wfs in dset.iterate():

        fig, axs = plt.subplots(4, 6, sharex=True, sharey=True, gridspec_kw=dict(hspace=0.06, wspace=0.06))
        fig2, axs2 = plt.subplots(4, 6, sharex=True, sharey=True, gridspec_kw=dict(hspace=0.06, wspace=0.06))

        for ch in range(24):
            ax = axs.flatten()[ch]
            ax2 = axs2.flatten()[ch]
            ax.plot(wfs[ch], label=f"Ch {ch}", lw=1)
            ax.legend(fontsize=5)
            ax.grid()

            ax2.plot(np.fft.rfftfreq(2048, 1 / 2.4) * 1000, np.abs(np.fft.rfft(wfs[ch])),
                     label=f"Ch {ch}", color="C1", lw=1)
            ax2.legend(fontsize=5)
            ax2.grid()
            ax2.set_yscale("log")
            ax2.set_xlim(None, 850)


        fig.supxlabel("samples")
        fig.supylabel("ADC")

        fig2.supxlabel("frequency / MHz")
        fig2.supylabel("")
        plt.show()

if __name__ == "__main__":

    plot_run_waveforms(sys.argv[1])
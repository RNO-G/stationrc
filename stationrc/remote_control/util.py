import logging
import numpy as np
import random
import time

import stationrc.radiant


def get_time_run(station, frequency, trigs_per_roll=4):
    NUM_CHANNELS = 24

    station.radiant_low_level_interface.lab4d_controller_stop()
    station.radiant_low_level_interface.calram_zero(zerocross_only=True)
    station.radiant_low_level_interface.calram_mode(
        mode=stationrc.radiant.LAB4_Calram.CalMode.NONE
    )
    station.radiant_low_level_interface.lab4d_controller_start()
    # junk the first 4
    station.radiant_low_level_interface.lab4d_controller_force_trigger(
        block=True, num_trig=trigs_per_roll, safe=False
    )
    # swap the CalMode to zerocrossing
    station.radiant_low_level_interface.calram_mode(
        mode=stationrc.radiant.LAB4_Calram.CalMode.ZEROCROSSING
    )
    # Run to 384 samples, I dunno what happens at 512 yet, screw it.
    for i in range(3 * trigs_per_roll):
        station.radiant_low_level_interface.lab4d_controller_force_trigger(
            block=True, num_trig=128, safe=False
        )
    station.radiant_low_level_interface.lab4d_controller_stop()

    # This should check to make sure it's actually 384, which it *should* be.
    # We're doing things in groups of 384 because it can't trip the ZC overflow
    # limit.
    numRolls = station.radiant_low_level_interface.calram_num_rolls()
    station.radiant_low_level_interface.dma_enable(
        mode=stationrc.radiant.RadDMA.calDmaMode
    )
    base = station.radiant_low_level_interface.calram_base()
    for ch in range(NUM_CHANNELS):
        station.radiant_low_level_interface.dma_set_descriptor(
            channel=ch,
            address=base + 4096 * 4 * ch,
            length=4096,
            increment=True,
            final=(ch == (NUM_CHANNELS - 1)),
        )

    station.radiant_low_level_interface.dma_begin()
    # Data comes in as 4096*4*numLabs bytes in little-endian format.
    # Convert it to 4096*numLabs uint32's.
    rawtime = np.frombuffer(
        bytearray(
            station.radiant_low_level_interface.dma_read(length=4096 * 4 * NUM_CHANNELS)
        ),
        dtype=np.uint32,
    )
    # Now view it as an array of [numLabs][4096]
    timeByLab = rawtime.reshape(NUM_CHANNELS, 4096)
    # Building up the times is a little harder than the pedestals.
    # The first thing we do is zero out the invalid seams. That way when we add everything,
    # all we need to do is rescale the seam by 8/3s.
    # The invalid seams are 0 and every (sample % 256) = 128 for *every trigger*.
    # So if we have 4 triggers in a roll of 4096, the invalid seams are 0, 128, 384, 640, 896.
    # and we only have 3/8 valid.

    # NOTE: I could almost certainly do this by reshaping/transposing magic crap. Screw it for now.
    for ch in range(NUM_CHANNELS):
        # What we do depends on the record length. If we have 4 trigs per roll, it's
        # 8 windows per record. If it's 2 trigs per roll, we have 16 windows per record.
        samplesPerRecord = 4096 // trigs_per_roll
        for i in range(trigs_per_roll):
            # The first one is always invalid because we don't have the last when it arrives.
            timeByLab[ch][samplesPerRecord * i] = 0
            windowsPerRecord = samplesPerRecord / 128
            # Now every (sample % 256) == 128 is invalid because we buffer them in case the
            # next seam is invalid due to being the end of the record.
            for j in range(int(windowsPerRecord / 2)):
                timeByLab[ch][samplesPerRecord * i + 256 * j + 128] = 0

    # We now reshape our times by window. 128 samples per window, 32 windows per roll.
    # So we're now an array of [numLabs][32][128].
    timeByWindow = timeByLab.reshape(NUM_CHANNELS, 32, 128)

    # Sum along the window axis, because the samples within a window have the same time.
    # We're now shape (24, 128)
    timeByWindow = timeByWindow.sum(axis=1)

    # convert to time. The denominator is number of windows in a roll, numerator is number of picoseconds/cycle.
    convFactor = (1e12 / frequency) / (numRolls * 32)
    # This has to be A = A*B because we're actually creating a new array
    # since we're moving to floats.
    timeByWindow = timeByWindow * convFactor

    # Now rescale the seams, because the seams have lower statistics.
    # This is the number of windows in a record (eg if 4 trigs = 8)
    windowsPerRecord = 4096 / (trigs_per_roll * 128)
    # This is the number of *valid* windows per record (e.g. if 4 trigs = 3)
    validWindowsPerRecord = windowsPerRecord / 2 - 1
    rescale = validWindowsPerRecord * trigs_per_roll / 32
    # Transposing gets us shape (128, 24), and we can
    # rescale all of the LABs automatically. This is just a loop over all LABs
    # rescaling time 0. So if we had 4 trigs per roll, that means only 12/32 of
    # the zerocrossings were nonzero, so we divide by 12/32 (or multiply by 32/12).
    timeByWindow.transpose()[0] /= rescale
    # and we're done
    return timeByWindow


def adjust_seam(seamSample, station, channel, nom_sample, seamTuneNum, mode="seam"):
    # Build the delta. This is totally hacked together.
    # Decrease if too fast, increase if too slow.
    # Change by 3 if it's within 50, change by 7 if it's between 50-100,
    # change by 15 otherwise. Convergence here is slow, but we're trying to
    # avoid bouncing, and we're also trying to avoid the negative case.
    diff = np.abs(seamSample - nom_sample)
    s_diff = seamSample - nom_sample
    if seamTuneNum == 3:
        delta = 1
    else:
        delta = 1  # was 3, takes longer but oh well. better granularity when we're close
        # seam tuning
        if mode == "seam" and diff > 50:
            delta += random.randint(1, 3)  # randomness back in
        if mode == "seam" and diff > 100:
            delta += random.randint(
                2, 6
            )  # max step size of 10. don't want to jump past optimal point too much

        # mean tuning. diff is sizably different from the seam diff
        if mode == "mean" and diff > 0.3:
            delta += 3
        if mode == "mean" and diff > 0.6:
            delta += 6

        # switch signs of delta if using VadjN or if we need to change directions
        if seamTuneNum == 3:
            delta = -1 * delta
        if mode == "seam" and s_diff < 0:
            delta = -1 * delta
        if mode == "mean" and s_diff > 0:
            delta = -1 * delta

    cur = station.radiant_low_level_interface.calibration_specifics_get(channel)[
        seamTuneNum
    ]
    newVal = cur + delta
    # if newVal < (self.nomSample*1.28):
    #    print("hmm feedback got to small. let's try something random!")
    #    newVal = random.randrange(800,1200)
    #    time.sleep(2);
    logging.info(
        f"LAB{channel}: Seam {seamSample:.2f}, register {seamTuneNum} ({cur} -> {newVal})"
    )
    station.radiant_low_level_interface.calibration_specifics_set(
        channel, seamTuneNum, newVal
    )


def adjust_slow(slowSample, slow_step, station, channel, nom_sample, slow_slow_factor, slow_fast_factor):
    if slowSample > (nom_sample * slow_slow_factor):
        slow_step = np.abs(slow_step)
        logging.info(f"Need to speed up slow sample ({slow_step})")
    elif slowSample < (nom_sample * slow_fast_factor):
        slow_step *= -1
        logging.info(f"Need to slow down slow sample ({slow_step})")

    current_state = station.radiant_low_level_interface.calibration_specifics_get(
        channel
    )

    oldavg = 0
    for i in range(257, 383):
        old = current_state[i]
        oldavg += old
        station.radiant_low_level_interface.calibration_specifics_set(
            channel,
            i,
            int(
                old + slow_step
            ),  # Need to convert to int since might default to np.int64
        )

    oldavg = oldavg / 126
    logging.info(
        f"LAB{channel}: Slow {slowSample:.2f}, ({oldavg} -> {oldavg + slow_step})"
    )
    return oldavg + slow_step


def update_seam_and_slow(station, channel, frequency, tune_mode, nom_sample):

    t = get_time_run(station, frequency * 1e6)

    seamSample = t[channel][0]
    slowSample = t[channel][127]

    if tune_mode == "mean":
        seamSample = np.mean(t[channel][1:127])  # trick it again :)

    logging.info(
        f"Seam/slow sample timing now (tune mode = \"{tune_mode}\"): {seamSample:.2f} / {slowSample:.2f} ps, "
        f"total diff: {nom_sample * 127 - np.sum(t[channel][1:128]):.2f} ps.\n"
        f"Mean of middle sample timings now: {np.mean(t[channel][1:127]):.2f}"
    )

    if np.sum(t[channel][1:128]) > nom_sample * 127.68:
        logging.warning(
            f"Feedback LAB{channel} way off ({nom_sample * 127 - np.sum(t[channel][1:128]):.2f}): "
            f"{t[channel][0]} -> {-1 * t[channel][0]:.2f}"
        )
        t[channel][0] *= -1

    return t, seamSample, slowSample


def initial_tune(station, channel, frequency=510, max_tries=50, bad_lab=False, external_signal=False):
    TRY_REG_3_FOR_FAILED_DLL = True

    sample_rate = station.radiant_sample_rate()
    nom_sample = 1 / sample_rate * 1e6
    logging.info(
        f"Tuning channel {channel}. Sample rate is {sample_rate} MHz (nominal sample length: {nom_sample:.2f} ps)"
    )

    initial_state = station.radiant_low_level_interface.calibration_specifics_get(
        channel
    )
    if initial_state[2] == 1024:
        logging.info("Defaults say to NOT use the DLL")
        seamTuneNum = 3
    else:
        logging.info("Defaults say to use the DLL")
        seamTuneNum = 11

    station.radiant_low_level_interface.lab4d_controller_update(channel)
    station.radiant_low_level_interface.calibration_specifics_set(
        channel,
        8,
        station.radiant_low_level_interface.lab4d_controller_autotune_vadjp(
            channel,
            station.radiant_low_level_interface.calibration_specifics_get(channel)[8],
        ),
    )
    station.radiant_low_level_interface.lab4d_controller_update(channel)
    station.radiant_low_level_interface.monselect(channel)
    station.radiant_low_level_interface.lab4d_controller_tmon_set(
        channel, stationrc.radiant.LAB4_Controller.tmon["SSPin"]
    )

    scan = 1 if channel > 11 else 0
    width = station.radiant_low_level_interface.lab4d_controller_scan_width(scan)
    logging.info(f"Initial SSPin width: {width}")

    if width > 1800:
        logging.warning("DLL seems broken, disabling")
        # try hack
        station.radiant_low_level_interface.lab4d_controller_write_register(
            channel, address=2, value=1024
        )
        time.sleep(0.5)
        width = station.radiant_low_level_interface.lab4d_controller_scan_width(scan)
        station.radiant_low_level_interface.calibration_specifics_set(channel, 2, 1024)
        station.radiant_low_level_interface.lab4d_controller_update(channel)
        logging.info(f"SSPin width after disabling DLL: {width}")
        if TRY_REG_3_FOR_FAILED_DLL:
            seamTuneNum = 3
            max_tries *= 3
            logging.info("Switching to VadjN")
    else:
        logging.info("DLL is okay")

    curTry = 0
    if sample_rate == 3200:
        target_width = 1000
    elif sample_rate == 2400:  # below 1000 for 3.2GHz, maybe 1000*1.33=1300 for 2.4GHz
        target_width = 1300
    else:
        raise RuntimeError(f"Sample rate of {sample_rate} MHz is not supported")

    while width > target_width and curTry < max_tries:
        newAvg = 0
        current_state = station.radiant_low_level_interface.calibration_specifics_get(
            channel
        )

        # register range to address the samples, only changes the middle samples... hence not 128
        for i in range(257, 383):
            newval = current_state[i] + 25
            station.radiant_low_level_interface.calibration_specifics_set(
                channel, i, newval
            )
            newAvg += newval

        station.radiant_low_level_interface.lab4d_controller_update(channel)
        time.sleep(0.1)
        width = station.radiant_low_level_interface.lab4d_controller_scan_width(scan)
        logging.debug(f"New SSPin width (avg {newAvg / 126}): {width}")
        curTry += 1

    if curTry == max_tries:
        for key in initial_state.keys():
            station.radiant_low_level_interface.calibration_specifics_set(
                channel, key, initial_state[key]
            )
        station.radiant_low_level_interface.lab4d_controller_update(channel)
        logging.error("Initial tune failed! Restored initial state.")
        return False

    if not external_signal:
        station.radiant_calselect(
            quad=channel // 4
        )  # This works because within calSelect quad is normalized with: quad = quad % 3
        station.radiant_sig_gen_off()
        station.radiant_pedestal_update()
        station.radiant_sig_gen_on()
        station.radiant_sig_gen_select_band(frequency=frequency)
        station.radiant_sig_gen_set_frequency(frequency)
    else:
        station.radiant_calselect(quad=None)

    current_state = station.radiant_low_level_interface.calibration_specifics_get(
        channel
    )

    oldavg = 0
    for i in range(257, 383):  # only changes the middle samples... hence not 128
        oldavg += current_state[i]
    oldavg /= 126
    logging.info(f"Starting average trim: {oldavg}")

    do_quit = False
    if sample_rate == 2400:
        seam_slow_factor = 1.03
        seam_fast_factor = 0.97

        slow_slow_factor = 1.01
        slow_fast_factor = (
            0.95  # confusing IK but it's slow sample. make is slightly fast
        )

        mean_slow_factor = 1.001  # 0.1% of 416.66 means this ends when the mean is ~0.4ps off of ideal. seam sample should close enough then.
        mean_fast_factor = 0.999

    elif sample_rate == 3200:  # help tuning a bit
        seam_slow_factor = 1.12
        seam_fast_factor = 0.92

        slow_slow_factor = 1.02
        slow_fast_factor = (
            0.8  # confusing IK but it's slow sample. make is slightly fast
        )

        mean_slow_factor = 1.003  # 0.1% of 416.66 means this ends when the mean is ~0.4ps off of ideal. seam sample should close enough then.
        mean_fast_factor = 0.997

    else:
        raise RuntimeError(f"Sample rate of {sample_rate} MHz is not supported")

    t, meanSample, _ = update_seam_and_slow(station, channel, frequency, "mean", nom_sample)

    slow_step = 10  # was 25
    curTry = 0  # reset

    logging.info(f"Start optimizing seam sample using \"mean\" mode. "
                 f"Target range: ({nom_sample * mean_fast_factor:.3f}, {nom_sample * mean_slow_factor:.3f})")

    while (meanSample > nom_sample * mean_slow_factor
           or meanSample < nom_sample * mean_fast_factor):

        adjust_seam(meanSample, station, channel, nom_sample, seamTuneNum, mode="mean")
        station.radiant_low_level_interface.lab4d_controller_update(channel)

        t, meanSample, _ = update_seam_and_slow(station, channel, frequency, "mean", nom_sample)

        if curTry == max_tries:
            for key in initial_state.keys():
                station.radiant_low_level_interface.calibration_specifics_set(
                    channel, key, initial_state[key]
                )
            station.radiant_low_level_interface.lab4d_controller_update(channel)
            logging.error("Initial tune failed! Restored initial state.")
            return False

        curTry += 1

    t = get_time_run(station, frequency * 1e6)
    seamSample = t[channel][0]
    slowSample = t[channel][127]

    # dumb way to check if we're boucing around the nominal range set by slow and fast factors.
    # If it bounces then adjust slow, which is likely off, then continue with seam (mean)
    bouncing = 0
    tune_mode = "seam"  # default

    if bad_lab == True:
        tune_mode = "mean"
        seam_slow_factor = mean_slow_factor
        seam_fast_factor = mean_fast_factor
        seamSample = np.mean(
            t[channel][1:127]
        )  # trick it to be the right thing. I should probably just pass both to adjust seam
        logging.warning("Using the mean sample instead")

    last_seam = seamSample

    logging.info(f"Start optimizing seam and slow sample using \"{tune_mode}\" mode: "
                f"\nTarget range for seam: ({nom_sample * seam_fast_factor:.3f}, {nom_sample * seam_slow_factor:.3f})"
                f"\nTarget range for slow: ({nom_sample * slow_fast_factor:.3f}, {nom_sample * slow_slow_factor:.3f})")

    while (
        slowSample < nom_sample * slow_fast_factor
        or slowSample > nom_sample * slow_slow_factor
        or seamSample > nom_sample * seam_slow_factor
        or seamSample < nom_sample * seam_fast_factor
    ):
        if curTry >= max_tries:
            for key in initial_state.keys():
                station.radiant_low_level_interface.calibration_specifics_set(
                    channel, key, initial_state[key]
                )
            station.radiant_low_level_interface.lab4d_controller_update(channel)
            logging.error("Initial tune failed! Restored initial state.")
            return False

        # Fix the seam if it's gone off too much.
        if ((seamSample < nom_sample * seam_fast_factor
             or seamSample > nom_sample * seam_slow_factor)
             and bouncing < 3):

            logging.info("----------- SEAM off ----------")
            adjust_seam(seamSample, station, channel, nom_sample, seamTuneNum, mode=tune_mode)
            if (last_seam > nom_sample * seam_slow_factor
                    and seamSample < nom_sample * seam_fast_factor):
                bouncing += 1

            elif (last_seam < nom_sample * seam_fast_factor
                    and seamSample > nom_sample * seam_slow_factor):
                bouncing += 1

            last_seam = seamSample
            if bouncing > 3:
                logging.warning("Bouncing")

        elif (slowSample > nom_sample * slow_slow_factor
                or slowSample < nom_sample * slow_fast_factor):

            logging.info("----------- SLOW off ----------")

            # We ONLY DO THIS if the seam sample's close.
            # This is because the slow sample changes with the seam timing like
            # everything else (actually a little more)
            #
            # So now, we're trying to find a *global* starting point where
            # the slow sample is *too fast*. Because slowing it down is easy!
            # So to do that, we slow everyone else down. Doing that means the
            # the DLL portion speeds up, so the slow sample speeds up as well.
            # This slows down trims 1->126 by adding 25 to them.
            # Remember trim 127 is the slow sample, and trim 0 is the multichannel clock alignment trim.

            # Trim updating is a pain, sigh.
            oldavg = adjust_slow(slowSample, slow_step, station, channel, nom_sample, slow_slow_factor, slow_fast_factor)
            bouncing = 0

        station.radiant_low_level_interface.lab4d_controller_update(channel)

        t, seamSample, slowSample = update_seam_and_slow(station, channel, frequency, tune_mode, nom_sample)

        curTry += 1

        if do_quit:
            logging.warning("Quitting")
            break

    logging.info(
        f"Ending seam sample: {t[channel][0]:.2f}, using register {seamTuneNum} with value "
        f"{station.radiant_low_level_interface.calibration_specifics_get(channel)[seamTuneNum]}."
    )
    logging.info(
        f"Ending slow sample: {t[channel][127]:.2f}, average earlier trims {oldavg}"
    )

    station.radiant_calselect(quad=None)
    station.radiant_sig_gen_off()
    return True

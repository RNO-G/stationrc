import logging
import numpy as np
import random
import time
import copy
import stationrc.radiant

logger = logging.getLogger("LAB4DTuning")


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

    cur = station.radiant_low_level_interface.calibration_specifics_get(channel)[seamTuneNum]
    newVal = cur + delta
    # if newVal < (self.nomSample*1.28):
    #    print("hmm feedback got to small. let's try something random!")
    #    newVal = random.randrange(800,1200)
    #    time.sleep(2);
    if mode == "seam":
        logger.info(
            f"LAB{channel:<2}: Current seam is {seamSample:.2f} ps (register {seamTuneNum}: {cur} -> {newVal})")
    if mode == "mean":
        logger.info(
            f"LAB{channel:<2}: Current mean is {seamSample:.2f} ps (register {seamTuneNum}: {cur} -> {newVal})")

    station.radiant_low_level_interface.calibration_specifics_set(
        channel, seamTuneNum, newVal)


def adjust_slow(slowSample, slow_step, station, channel, nom_sample, slow_slow_factor, slow_fast_factor):
    if slowSample > (nom_sample * slow_slow_factor):
        slow_step = np.abs(slow_step)
        logger.debug(f"Need to speed up slow sample for channel {channel}")
    elif slowSample < (nom_sample * slow_fast_factor):
        slow_step *= -1
        logger.debug(f"Need to slow down slow sample for channel {channel}")

    current_state = station.radiant_low_level_interface.calibration_specifics_get(channel)

    oldavg = 0
    for i in range(257, 383):
        old = current_state[i]
        oldavg += old
        station.radiant_low_level_interface.calibration_specifics_set(
            channel, i, int(old + slow_step))  # Need to convert to int since might default to np.int64

    oldavg = oldavg / 126
    logger.info(f"LAB{channel:<2}: Current slow is {slowSample:.2f} ps ({oldavg} -> {oldavg + slow_step})")

    return oldavg + slow_step


def restore_inital_state(station, channel, state):
    for key in state:
        station.radiant_low_level_interface.calibration_specifics_set(
                    channel, key, state[key])

    station.radiant_low_level_interface.lab4d_controller_update(channel)
    logger.error(f"Initial tune failed for channel {channel}! Restored initial state.")


def update_seam_and_slow(station, channel, frequency, tune_mode, nom_sample):

    t = get_time_run(station, frequency * 1e6)

    seamSample = t[channel, 0]
    slowSample = t[channel, 127]

    if tune_mode == "mean":
        seamSample = np.mean(t[channel, 1:127], axis=-1)  # trick it again :)

    if isinstance(channel, int):
        logger.info(
            f"Seam (mean) / slow sample timing now: {seamSample:.2f} / {slowSample:.2f} ps, "
            f"total diff: {nom_sample * 127 - np.sum(t[channel][1:128]):.2f} ps. ")

        logger.info(f"Mean of middle sample timings now: {np.mean(t[channel][1:127]):.2f}")

        if np.sum(t[channel][1:128]) > nom_sample * 127.68 and tune_mode != "mean":
            logger.warning(
                f"Feedback LAB{channel} way off ({nom_sample * 127 - np.sum(t[channel][1:128]):.2f})")
            # FS: After talking to Ryan which could not make sense of this flip neither and suggested to remove
            # it I am commenting it but keeping the warning.
            seamSample *= -1

    return t, seamSample, slowSample


def get_station_information(station):
    sample_rate = station.radiant_sample_rate()
    nom_sample = 1 / sample_rate * 1e6

    if sample_rate == 3200:
        target_width = 1000
    elif sample_rate == 2400:  # below 1000 for 3.2GHz, maybe 1000*1.33=1300 for 2.4GHz
        target_width = 1300
    else:
        raise RuntimeError(f"Sample rate of {sample_rate} MHz is not supported")

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


    return sample_rate, nom_sample, target_width, seam_slow_factor, seam_fast_factor, \
        slow_slow_factor, slow_fast_factor, mean_slow_factor, mean_fast_factor


def setup_channel(station, channel):
    initial_state = station.radiant_low_level_interface.calibration_specifics_get(channel)
    if initial_state[2] == 1024:
        logger.info(f"LAB{channel:<2}: Defaults say to NOT use the DLL")
        seamTuneNum = 3
    else:
        logger.info(f"LAB{channel:<2}: Defaults say to use the DLL")
        seamTuneNum = 11

    station.radiant_low_level_interface.lab4d_controller_update(channel)

    val = station.radiant_low_level_interface.lab4d_controller_autotune_vadjp(channel,
            station.radiant_low_level_interface.calibration_specifics_get(channel)[8])

    if val is None:
        logger.error(f"LAB{channel}: The result of lab4d_controller_autotune_vadjp is None. Something is wrong.")
        return initial_state, None

    station.radiant_low_level_interface.calibration_specifics_set(
        channel, 8, val)

    station.radiant_low_level_interface.lab4d_controller_update(channel)

    station.radiant_low_level_interface.monselect(channel)
    station.radiant_low_level_interface.lab4d_controller_tmon_set(
        channel, stationrc.radiant.LAB4_Controller.tmon["SSPin"]
    )

    return initial_state, seamTuneNum


def tuned_width(station, channel, target_width, max_tries, seamTuneNum, TRY_REG_3_FOR_FAILED_DLL):
    scan = 1 if channel > 11 else 0
    width = station.radiant_low_level_interface.lab4d_controller_scan_width(scan)
    logger.info(f"LAB{channel:<2}: Initial SSPin width is {width}, target is below {target_width}")

    if width > 1800:
        logger.warning(f"LAB{channel} DLL seems broken, disabling (width = {width})")
        # try hack
        station.radiant_low_level_interface.lab4d_controller_write_register(
            channel, address=2, value=1024
        )
        time.sleep(0.5)
        width = station.radiant_low_level_interface.lab4d_controller_scan_width(scan)
        station.radiant_low_level_interface.calibration_specifics_set(channel, 2, 1024)
        station.radiant_low_level_interface.lab4d_controller_update(channel)
        logger.info(f"SSPin width after disabling DLL: {width}")
        if TRY_REG_3_FOR_FAILED_DLL:
            seamTuneNum = 3
            max_tries *= 3
            logger.info("Switching to VadjN")
    else:
        logger.debug("DLL is okay")

    curTry = 0

    while width > target_width and curTry < max_tries:
        newAvg = 0
        current_state = station.radiant_low_level_interface.calibration_specifics_get(channel)

        # register range to address the samples, only changes the middle samples... hence not 128
        for i in range(257, 383):
            newval = current_state[i] + 25
            station.radiant_low_level_interface.calibration_specifics_set(
                channel, i, newval)
            newAvg += newval

        station.radiant_low_level_interface.lab4d_controller_update(channel)
        time.sleep(0.1)
        width = station.radiant_low_level_interface.lab4d_controller_scan_width(scan)
        logger.info(f"New SSPin width (avg {newAvg / 126}): {width}")
        curTry += 1

    return curTry, seamTuneNum

def initial_tune(station, channel, frequency=510, max_tries=50, bad_lab=False, external_signal=False):
    TRY_REG_3_FOR_FAILED_DLL = True

    sample_rate, nom_sample, target_width, seam_slow_factor, seam_fast_factor, \
        slow_slow_factor, slow_fast_factor, mean_slow_factor, mean_fast_factor = \
        get_station_information(station)

    def seam_in_range(sample):
        return seam_fast_factor * nom_sample < sample < seam_slow_factor * nom_sample

    def mean_in_range(sample):
        return mean_fast_factor * nom_sample < sample < mean_slow_factor * nom_sample

    def slow_in_range(sample):
        return slow_fast_factor * nom_sample < sample < slow_slow_factor * nom_sample


    logger.info(
        f"Tuning channel {channel}. Sample rate is {sample_rate} MHz "
        f"(nominal sample length: {nom_sample:.2f} ps)"
    )

    initial_state, seamTuneNum = setup_channel(station, channel)
    if seamTuneNum is None:
        restore_inital_state(station, channel, initial_state)
        return False

    curTry, seamTuneNum = tuned_width(
        station, channel, target_width, max_tries, seamTuneNum, TRY_REG_3_FOR_FAILED_DLL)

    if curTry == max_tries:
        restore_inital_state(station, channel, initial_state)
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

    # only changes the middle samples... hence not 128
    current_state = station.radiant_low_level_interface.calibration_specifics_get(channel)
    oldavg = np.sum([current_state[i] for i in range(257, 383)]) / 126  # current_state is a dict
    logger.info(f"Starting average trim: {oldavg}")

    slow_step = 25  # was 25
    curTry = 0  # reset

    t, meanSample, _ = update_seam_and_slow(station, channel, frequency, "mean", nom_sample)

    logger.info(f"Use mean as proxy for seam. Start value is {meanSample:.2f} ps. "
                 f"Target range is [{nom_sample * mean_fast_factor:.2f}, "
                 f"{nom_sample * mean_slow_factor:.2f}] ps")

    while not mean_in_range(meanSample):
        logger.info(f"Iteration {curTry} / {max_tries}")

        if curTry == max_tries:
            restore_inital_state(station, channel, initial_state)
            return False

        adjust_seam(meanSample, station, channel, nom_sample, seamTuneNum, mode="mean")
        station.radiant_low_level_interface.lab4d_controller_update(channel)

        t, meanSample, _ = update_seam_and_slow(station, channel, frequency, "mean", nom_sample)

        curTry += 1

    t, seamSample, slowSample = update_seam_and_slow(station, channel, frequency, "seam", nom_sample)
    last_seam = seamSample

    # dumb way to check if we're boucing around the nominal range set by slow and fast factors.
    # If it bounces then adjust slow, which is likely off, then continue with seam (mean)
    bouncing = 0
    tune_mode = "seam"  # default
    curTry = 0  # reset

    if bad_lab:
        tune_mode = "mean"
        seam_slow_factor = mean_slow_factor
        seam_fast_factor = mean_fast_factor

        # trick it to be the right thing. I should probably just pass both to adjust seam
        seamSample = np.mean(t[channel][1:127])
        logger.warning("Using the mean of the middle samples as seam proxy")

    logger.info(f"Optimizing seam / slow. Target range is [{nom_sample * seam_fast_factor:.2f}, {nom_sample * seam_slow_factor:.2f}] ps / "
                 f"[{nom_sample * slow_fast_factor:.2f}, {nom_sample * slow_slow_factor:.2f}] ps")

    while not seam_in_range(seamSample) or not slow_in_range(slowSample):
        logger.info(f"Iteration {curTry} / {max_tries}")

        if curTry >= max_tries:
            restore_inital_state(station, channel, initial_state)
            return False

        # Fix the seam if it's gone off too much.
        if not seam_in_range(seamSample) and bouncing < 3:

            logger.debug("----------- SEAM off ----------")
            adjust_seam(seamSample, station, channel, nom_sample, seamTuneNum, mode=tune_mode)

            if (last_seam > nom_sample * seam_slow_factor
                    and seamSample < nom_sample * seam_fast_factor):
                bouncing += 1

            elif (last_seam < nom_sample * seam_fast_factor
                    and seamSample > nom_sample * seam_slow_factor):
                bouncing += 1

            last_seam = seamSample
            if bouncing > 3:
                logger.warning("Bouncing")

        elif not slow_in_range(slowSample):

            logger.debug("----------- SLOW off ----------")

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
            oldavg = adjust_slow(slowSample, slow_step, station, channel, nom_sample,
                                 slow_slow_factor, slow_fast_factor)
            bouncing = 0

        station.radiant_low_level_interface.lab4d_controller_update(channel)

        t, seamSample, slowSample = update_seam_and_slow(station, channel, frequency, tune_mode, nom_sample)

        curTry += 1

    logger.info(
        f"Ending seam sample: {t[channel][0]:.2f}, using register {seamTuneNum} with value "
        f"{station.radiant_low_level_interface.calibration_specifics_get(channel)[seamTuneNum]}."
    )
    logger.info(
        f"Ending slow sample: {t[channel][127]:.2f}, average earlier trims {oldavg}"
    )

    station.radiant_calselect(quad=None)
    station.radiant_sig_gen_off()
    return True


def get_channels_for_quad(quad):
    if quad == 0:
        return [0, 1, 2, 3, 12, 13, 14, 15]
    if quad == 1:
        return [4, 5, 6, 7, 16, 17, 18, 19]
    if quad == 2:
        return [8, 9, 10, 11, 20, 21, 22, 23]
    return None

def initial_tune_quad(station, quad, frequency=510, max_tries=50, bad_lab=False, external_signal=False,
                      tune_with_rolling_mean=False):
    """
    Time tuning algorithm

    Parameters
    ----------

    station : `radiant.radiant.RADIANT`
        The radiant object.

    quad : int
        Select which quad to tune (the channels of this quad).

    frequency : float
        The tuning frequency in MHz. (Default: 510)

    max_tries : int
        The maximum number of iteration in each of the 2 tuning loops. (Default: 50)

    bad_lab : bool
        ...

    external_signal : bool
        If True, use an external signal for tuning: Do not turn on signal generator and
        do not select the quad. The configured frequency has to match that of the external
        signal. (Default: False)

    tune_with_rolling_mean : bool
        If true, also require the mean over the last 3 measurements of the seam sample to be
        within the tolerance. (Default: False)

    Returns
    -------

    channels : list of ints
        List of all channel which were tuned.

    passed : list of bools
        List of whether a channel was tuned successful.
    """
    TRY_REG_3_FOR_FAILED_DLL = True

    sample_rate, nom_sample, target_width, seam_slow_factor, seam_fast_factor, \
        slow_slow_factor, slow_fast_factor, mean_slow_factor, mean_fast_factor = \
        get_station_information(station)

    def seam_mean_in_range(samples):
        # if tune_with_rolling_mean == False, last_sample == samples_mean
        if len(samples) == 1:  # i.e. == [[...]]
            last_sample = samples[0][-1]
            samples_mean = np.mean(samples)
        else:
            last_sample = samples[:, -1]
            samples_mean = np.mean(samples, axis=-1)

        return np.all([seam_fast_factor * nom_sample < samples_mean, samples_mean < seam_slow_factor * nom_sample,
                        seam_fast_factor * nom_sample < last_sample, last_sample < seam_slow_factor * nom_sample])

    def seam_in_range(samples):
        return np.all([seam_fast_factor * nom_sample < samples, samples < seam_slow_factor * nom_sample])


    def mean_in_range(samples):
        return np.all([mean_fast_factor * nom_sample < samples, samples < mean_slow_factor * nom_sample])

    def slow_in_range(samples):
        return np.all([slow_fast_factor * nom_sample < samples, samples < slow_slow_factor * nom_sample])

    channels = get_channels_for_quad(quad)

    logger.info(
        f"Tuning channels {channels}. Sample rate is {sample_rate} MHz "
        f"(nominal sample length: {nom_sample:.2f} ps)"
    )

    initial_states = []
    seamTuneNums = []
    for channel in channels:
        istate, snum = setup_channel(station, channel)
        initial_states.append(istate)
        seamTuneNums.append(snum)

    failed = np.array([n is None for n in seamTuneNums])

    for ch_idx, channel in enumerate(channels):
        if not failed[ch_idx]:
            curTry, seamTuneNums[ch_idx] = tuned_width(
                station, channel, target_width, max_tries, seamTuneNums[ch_idx], TRY_REG_3_FOR_FAILED_DLL)
        else:
            restore_inital_state(station, channel, initial_states[ch_idx])

        if curTry == max_tries:
            restore_inital_state(station, channel, initial_states[ch_idx])
            failed[ch_idx] = True

    if np.all(failed):
        return channels, [False] * len(channels)

    if not external_signal:
        station.radiant_calselect(
            quad=quad
        )  # This works because within calSelect quad is normalized with: quad = quad % 3
        station.radiant_sig_gen_off()
        station.radiant_pedestal_update()
        station.radiant_sig_gen_on()
        station.radiant_sig_gen_select_band(frequency=frequency)
        station.radiant_sig_gen_set_frequency(frequency)
    else:
        station.radiant_calselect(quad=None)

    oldavgs = []
    for ch_idx, channel in enumerate(channels):
        current_state = station.radiant_low_level_interface.calibration_specifics_get(channel)
        # only changes the middle samples... hence not 128
        oldavg = np.sum([current_state[i] for i in range(257, 383)]) / 126  # current_state is a dict
        oldavgs.append(oldavg)
        if not failed[ch_idx]:
            logger.info(f"LAB{channel:<2}: starting average trim: {oldavg}")

    slow_step = 25  # was 25
    curTry = 0  # reset

    t, meanSample, _ = update_seam_and_slow(station, channels, frequency, "mean", nom_sample)

    # Sanity check - no need to tune dead channels!
    if np.any(meanSample == 0):
        for ch_idx, channel in enumerate(channels):
            if meanSample[ch_idx] == 0:
                logger.info(f"LAB{channel:<2}: Mean is 0, do not tune this channel!")
                restore_inital_state(station, channel, initial_states[ch_idx])
                failed[ch_idx] = True

    logger.info(f"Use mean as proxy for seam. "
                 f"Target range is [{nom_sample * mean_fast_factor:.2f}, "
                 f"{nom_sample * mean_slow_factor:.2f}] ps")

    needs_tuning = ~failed  # channels which already failed do not need to be tuned further
    while not mean_in_range(meanSample[needs_tuning]):
        logger.info(f"Iteration {curTry} / {max_tries}")
        for ch_idx, channel in enumerate(channels):

            if curTry == max_tries and needs_tuning[ch_idx]:
                restore_inital_state(station, channel, initial_states[ch_idx])
                failed[ch_idx] = True
                needs_tuning[ch_idx] = False  # stop here!

            if mean_in_range(meanSample[ch_idx]) or not needs_tuning[ch_idx]:
                if needs_tuning[ch_idx]:
                    # print that only once
                    logger.info(f"-----> LAB{channel} tuned mean: {meanSample[ch_idx]:.2f} ps")

                needs_tuning[ch_idx] = False  # this means: Once it was in range it will not be updated anymore
                continue  # this channel is already in range, skip it

            adjust_seam(meanSample[ch_idx], station, channel, nom_sample, seamTuneNums[ch_idx], mode="mean")
            station.radiant_low_level_interface.lab4d_controller_update(channel)

        if not np.any(needs_tuning):
            break

        # only use data from channels which still need tuning. Otherwise they could fall out of range again
        t, meanSample, _ = update_seam_and_slow(station, channels, frequency, "mean", nom_sample)

        curTry += 1

    # Log last channel(s)
    if np.any(needs_tuning):
        for channel, ms in zip(np.array(channels)[needs_tuning], meanSample[needs_tuning]):
            logger.info(f"-----> LAB{channel:<2} tuned mean: {ms:.2f} ps")

    if np.all(failed):
        return channels, [False] * len(channels)

    t, seamSample, slowSample = update_seam_and_slow(station, channels, frequency, "seam", nom_sample)
    last_seam = copy.deepcopy(seamSample)

    # dumb way to check if we're boucing around the nominal range set by slow and fast factors.
    # If it bounces then adjust slow, which is likely off, then continue with seam (mean)
    bouncing = [0] * len(channels)
    tune_mode = "seam"  # default
    curTry = 0  # reset

    logger.info(f"Optimizing seam / slow. Target range is "
                 f"[{nom_sample * seam_fast_factor:.2f}, {nom_sample * seam_slow_factor:.2f}] ps / "
                 f"[{nom_sample * slow_fast_factor:.2f}, {nom_sample * slow_slow_factor:.2f}] ps")

    # keeping the seam samples like this allows to keep the seam from a prev. interation
    # to calculate a rolling average
    seamSamples = np.array([[ele] for ele in seamSample])

    needs_tuning = ~failed # channels which already failed do not need to be tuned further
    # we always calculate the mean from seamSamples. However, if tune_with_rolling_mean == False we calculate the mean over one number ...
    while not seam_mean_in_range(seamSamples[needs_tuning]) or not slow_in_range(slowSample[needs_tuning]):
        logger.info(f"Iteration {curTry} / {max_tries}")

        for channel, seam in zip(np.array(channels)[needs_tuning], seamSamples[needs_tuning]):
            logger.debug(f"LAB{channel:<2}: current seam samples: {seam}")

        for ch_idx, channel in enumerate(channels):

            if curTry >= max_tries and needs_tuning[ch_idx]:
                restore_inital_state(station, channel, initial_states[ch_idx])
                failed[ch_idx] = True
                needs_tuning[ch_idx] = False  # stop here!

            if seam_in_range(seamSamples[ch_idx]) and slow_in_range(slowSample[ch_idx]):
                if needs_tuning[ch_idx]:
                    # print that only once
                    logger.info(f"-----> LAB{channel} tuned: {np.mean(seamSamples, axis=-1)[ch_idx]:.2f} / {slowSample[ch_idx]:.2f} ps")
                    if tune_with_rolling_mean:
                        logger.info(f"-----> The last three seam samples were: {seamSamples[ch_idx]} ps")
                else:
                    logger.debug(f"-----> LAB{channel} still in range: {np.mean(seamSamples, axis=-1)[ch_idx]:.2f} / {slowSample[ch_idx]:.2f} ps")
                needs_tuning[ch_idx] = False  # this means: Once it was in range it will not be updated anymore
            elif not needs_tuning[ch_idx]:
                # Unless this channel faild in before this while loop it dropped out of range after
                # is was in range
                logger.debug(f"-----> LAB{channel} (probably) out of range again: "
                             f"{np.mean(seamSamples, axis=-1)[ch_idx]:.2f} / {slowSample[ch_idx]:.2f} ps")

            if not needs_tuning[ch_idx]:
                continue

            # Fix the seam if it's gone off too much. Here use seamSample (i.e. the last one only!)
            if not seam_in_range(seamSample[ch_idx]) and bouncing[ch_idx] < 3:

                logger.debug(f"LAB{channel} SEAM off")
                adjust_seam(seamSample[ch_idx], station, channel, nom_sample,
                            seamTuneNums[ch_idx], mode=tune_mode)

                if (last_seam[ch_idx] > nom_sample * seam_slow_factor
                        and seamSample[ch_idx] < nom_sample * seam_fast_factor):
                    bouncing[ch_idx] += 1

                elif (last_seam[ch_idx] < nom_sample * seam_fast_factor
                        and seamSample[ch_idx] > nom_sample * seam_slow_factor):
                    bouncing[ch_idx] += 1

                last_seam = copy.deepcopy(seamSample)
                if bouncing[ch_idx] > 3:
                    logger.warning("Bouncing")

            elif not slow_in_range(slowSample[ch_idx]):

                logger.debug(f"LAB{channel} SLOW off")

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
                oldavgs[ch_idx] = adjust_slow(slowSample[ch_idx], slow_step, station, channel, nom_sample,
                                    slow_slow_factor, slow_fast_factor)
                bouncing[ch_idx] = 0

            station.radiant_low_level_interface.lab4d_controller_update(channel)

        if not np.any(needs_tuning):
            break

        # only use data from channels which still need tuning. Otherwise they could fall out of range again
        t, seamSample, slowSample = update_seam_and_slow(station, channels, frequency, tune_mode, nom_sample)

        if tune_with_rolling_mean:
            # Add new seam to the list to calculate average.
            tmp = []
            for seam_list, new_seam in zip(seamSamples, seamSample):
                if len(seam_list) >= 5:
                    seam_list = np.delete(seam_list, 0)  # remove oldest element

                seam_list = np.append(seam_list, new_seam)
                tmp.append(seam_list)

            seamSamples = np.array(tmp)
        else:
            seamSamples = np.array([[ele] for ele in seamSample])  # just replace all entries

        curTry += 1

    # Log last channel(s)
    if np.any(needs_tuning):
        for channel, seam, slow in zip(np.array(channels)[needs_tuning],
                                       np.mean(seamSamples, axis=-1)[needs_tuning],
                                       slowSample[needs_tuning]):
            logger.info(f"-----> LAB{channel:<2} tuned: {seam:.2f} / {slow:.2f} ps")
            if tune_with_rolling_mean:
                logger.info(f"-----> The last three seam samples were: {seamSamples[ch_idx]} ps")

    for ch_idx, channel in enumerate(channels):
        result = "failed" if failed[ch_idx] else "passed"
        if seamTuneNums[ch_idx] is not None:
            logger.info(
                f"LAB{channel} {result} with seam sample: {np.mean(seamSamples, axis=-1)[ch_idx]:.2f}, using register {seamTuneNums[ch_idx]} with value "
                f"{station.radiant_low_level_interface.calibration_specifics_get(channel)[seamTuneNums[ch_idx]]}.")
        else:
            logger.info(
                f"LAB{channel} {result} with seam sample: {np.mean(seamSamples, axis=-1)[ch_idx]:.2f}.")

        logger.info(
            f"LAB{channel} {result} with slow sample: {slowSample[ch_idx]:.2f}, average earlier trims {oldavgs[ch_idx]}")

    station.radiant_calselect(quad=None)
    station.radiant_sig_gen_off()
    return channels, ~failed

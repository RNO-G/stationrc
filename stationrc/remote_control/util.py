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


def initial_tune(station, channel, frequency=510, max_tries=50):
    TRY_REG_3_FOR_FAILED_DLL = True

    logging.info(f"Tuning channel {channel}")
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
    station.radiant_low_level_interface.monselect(channel)
    station.radiant_low_level_interface.lab4d_controller_tmon_set(
        channel, stationrc.radiant.LAB4_Controller.tmon["SSPin"]
    )

    scan = 0
    if channel > 11:
        scan = 1
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
    while width > 1000 and curTry < max_tries:
        newAvg = 0
        for i in range(257, 383):
            current_state = (
                station.radiant_low_level_interface.calibration_specifics_get(channel)
            )
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

    station.radiant_calselect(channel // 4)
    station.radiant_sig_gen_off()
    station.radiant_sig_gen_configure(pulse=False, band=(2 if frequency > 100 else 0))
    station.radiant_pedestal_update()
    station.radiant_sig_gen_on()
    station.radiant_sig_gen_set_frequency(frequency)

    t = get_time_run(station, frequency * 1e6)
    logging.info(f"Initial seam/slow sample timing: {t[channel][0]} {t[channel][127]}")
    if np.sum(t[channel][1:128]) > 39900:
        logging.warning(
            f"Feedback LAB{channel} way off ({40000 - np.sum(t[channel][1:128])}): {t[channel][0]} -> {-1 * t[channel][0]}"
        )
        t[channel][0] *= -1
    seamSample = t[channel][0]
    slowSample = t[channel][127]

    current_state = station.radiant_low_level_interface.calibration_specifics_get(
        channel
    )
    oldavg = 0
    for i in range(257, 383):
        oldavg += current_state[i]
    oldavg /= 126
    logging.info(f"Starting average trim: {oldavg}")

    curTry = 0
    while slowSample > 290 or seamSample > 350 or (seamSample < 290 and oldavg < 2400):
        if curTry >= max_tries:
            for key in initial_state.keys():
                station.radiant_low_level_interface.calibration_specifics_set(
                    channel, key, initial_state[key]
                )
            station.radiant_low_level_interface.lab4d_controller_update(channel)
            logging.error("Initial tune failed! Restored initial state.")
            return False
        # Fix the seam if it's gone off too much.
        if seamSample < 290 or seamSample > 350:
            # Build the delta. This is totally hacked together.
            # Decrease if too fast, increase if too slow.
            # Change by 3 if it's within 50, change by 7 if it's between 50-100,
            # change by 15 otherwise. Convergence here is slow, but we're trying to
            # avoid bouncing, and we're also trying to avoid the negative case.
            diff = np.abs(seamSample - 312.5)
            if seamTuneNum == 3:
                delta = 1
            else:
                delta = 3
                if diff > 50:
                    delta += random.randint(2, 6)
                if diff > 100:
                    delta += random.randint(4, 12)
                if seamSample < 290:
                    delta *= -1
                if seamTuneNum == 3:
                    delta *= -1
            cur = station.radiant_low_level_interface.calibration_specifics_get(
                channel
            )[seamTuneNum]
            newVal = cur + delta
            if newVal < 400:
                logging.warning(
                    "hmm feedback got to small. let's try something random!"
                )
                newVal = random.randrange(800, 1200)
                time.sleep(2)
            logging.debug(
                f"Feedback LAB{channel} ({seamSample}): {cur} -> {newVal} (register {seamTuneNum})"
            )
            station.radiant_low_level_interface.calibration_specifics_set(
                channel, seamTuneNum, newVal
            )
        elif slowSample > 290 and oldavg < 2400:
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
            oldavg = 0
            current_state = (
                station.radiant_low_level_interface.calibration_specifics_get(channel)
            )
            for i in range(257, 383):
                old = current_state[i]
                oldavg += old
                station.radiant_low_level_interface.calibration_specifics_set(
                    channel, i, old + 25
                )
            oldavg /= 126
            logging.debug(
                f"Slowing early samples: LAB{channel} ({slowSample}): {oldavg} -> {oldavg + 25}"
            )
            oldavg += 25
        elif slowSample < 250 and oldavg > 1800:
            # Trim updating is a pain, sigh.
            oldavg = 0
            current_state = (
                station.radiant_low_level_interface.calibration_specifics_get(channel)
            )
            for i in range(257, 383):
                old = current_state[i]
                oldavg += old
                station.radiant_low_level_interface.calibration_specifics_set(
                    channel, i, old - 25
                )
            oldavg /= 126
            logging.debug(
                f"Speeding early samples: LAB{channel} ({slowSample}): {oldavg} -> {oldavg - 25}"
            )
            oldavg -= 25

        # now update
        station.radiant_low_level_interface.lab4d_controller_update(channel)
        # fetch times again
        t = get_time_run(station, frequency * 1e6)
        logging.debug(f"Seam/slow sample timing now: {t[channel][0]} {t[channel][127]}")
        if np.sum(t[channel][1:128]) > 39900:
            print(
                f"Feedback LAB{channel} way off ({40000 - np.sum(t[channel][1:128])}): {t[channel][0]} -> {-1 * t[channel][0]}"
            )
            t[channel][0] *= -1
        seamSample = t[channel][0]
        slowSample = t[channel][127]
        curTry += 1
    logging.info(
        f"Ending seam sample : {t[channel][0]} feedback {station.radiant_low_level_interface.calibration_specifics_get(channel)[seamTuneNum]} using register {seamTuneNum}"
    )
    logging.info(
        f"Ending slow sample : {t[channel][127]} average earlier trims {oldavg}"
    )
    return True

#!/usr/bin/env python
#
# MCC 118 example program
# Read and display analog input values
#
import sys
from daqhats import hat_list, HatIDs, mcc128, AnalogInputMode, AnalogInputRange, OptionFlags
import numpy as np

# get hat list of MCC daqhat boards
board_list = hat_list(filter_by_id = HatIDs.ANY)
if not board_list:
    print("No boards found")
    sys.exit()

chan_mask = 0
#chan_list=[0,1,2,3]
chan_list=[0]
for chan in chan_list:
    chan_mask |= 0x01 << chan
print(f"chan_mask = {chan_mask}")

# Read and display every channel
for entry in board_list:
    if entry.id == HatIDs.MCC_128:
        print("Board {}: MCC 128".format(entry.address))
        board = mcc128(entry.address)
        print(board.info())
        print(board.a_in_mode_read())
        print(board.a_in_range_read())
        print(board.a_in_mode_write(AnalogInputMode.DIFF))
        print(board.a_in_range_write(AnalogInputRange.BIP_1V))
        print(board.a_in_mode_read())
        print(board.a_in_range_read())
        
        board.a_in_scan_start(chan_mask, 50, 200, OptionFlags.DEFAULT)
        total_samples_read = 0
        timeout = 0.5 
#       while total_samples_read < 50:
        read_result = board.a_in_scan_read_numpy(50, timeout)
        total_samples_read += len(read_result.data)

        print(f"read_results: {read_result}")
        print(f"mean: {np.mean(read_result.data, axis=0)}")
        print(f"std: {np.std(read_result.data, axis=0)}")
        #print(f"std: {np.std(read_result)}")

#        for channel in range(board.info().NUM_AI_CHANNELS):
#            value = board.a_in_read(channel)
#            print("Ch {0}: {1:.3f}".format(channel, value))

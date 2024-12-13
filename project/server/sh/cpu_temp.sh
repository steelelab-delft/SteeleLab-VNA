#!/usr/bin/env bash

# Zynq cpu temperature readout script
# Adapted from: https://www.scivision.dev/measure-red-pitaya-cpu-temperature-terminal/
# Based on: www.kkn.net/~n6tv/xadc.sh

XADC_PATH=/sys/bus/iio/devices/iio:device0

# Print only float value if program argument -F included.
# Repeat if program argument -C (continuous) included.
if ! [[ "$#" = "0" || "$#" = "1" || "$#" = "2" ]]; then
    echo "Must give either 0, 1 or 2 program args."
    echo "-F   float output only"
    echo "-C   continuous: repeat every 180 seconds"
    exit 1
fi

# Check if `bc` is available.
if [ ! -f /usr/bin/bc ]; then
    if [[ "$1" = "-F" || "$2" == "-F" ]]; then
        echo "-1.0"
    else
        echo "temperature = -1.0 degC"
    fi
    exit 2
fi

while [ 1 ]; do
    # Measure and compute temperature.
    OFF=$(cat $XADC_PATH/in_temp0_offset)
    RAW=$(cat $XADC_PATH/in_temp0_raw)
    SCL=$(cat $XADC_PATH/in_temp0_scale)
    FORMULA="(($OFF+$RAW)*$SCL)/1000.0"
    VAL=$(echo "scale=2;${FORMULA}" | bc)

    # Echo result.
    if [[ "$1" = "-F" || "$2" = "-F" ]]; then
        echo "${VAL}"
    else
        printf "%(%Y-%m-%d %H:%M:%S)T "
        echo "temperature = ${VAL} degC"
    fi

    # Repeat or exit.
    if [[ "$1" = "-C" || "$2" = "-C" ]]; then
        sleep 180
    else
        exit 0
    fi
done

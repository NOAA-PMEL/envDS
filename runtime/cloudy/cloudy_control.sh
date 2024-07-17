#!/bin/bash

run_command=$1
target=$2
power_bus=$3
power_state="on"

if [ $run_command = "shutdown" ]; then
    power_state="off"
fi

if [ $target = "services" ] || [ $target = "interfaces" ]; then
    echo python bin/envds.py "$run_command" "$target" -id cloudy -f $(pwd)/runtime/cloudy/"$target".txt
    python bin/envds.py $run_command $target -id cloudy -f $(pwd)/runtime/cloudy/$target.txt
fi

if [ $target = "sensors" ]; then
    if [ $power_bus != "init" ]; then
        echo python bin/envds.py power "$power_bus" -s "$power_state"
        python bin/envds.py power $power_bus -s $power_state
    fi
    echo python bin/envds.py "$run_command" "$target" -id cloudy -f $(pwd)/runtime/cloudy/"$target"_"$power_bus".txt
    python bin/envds.py $run_command $target -id cloudy -f $(pwd)/runtime/cloudy/"$target"_"$power_bus".txt
fi
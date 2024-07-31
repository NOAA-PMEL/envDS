#!/bin/bash

run_command=$1
target=$2
power_bus=$3
power_state="on"

if [ $run_command = "shutdown" ]; then
    power_state="off"
fi

if [ $target = "services" ] || [ $target = "interfaces" ]; then
    echo python bin/envds.py "$run_command" "$target" -id clear -f $(pwd)/runtime/clear/"$target".txt
    python bin/envds.py $run_command $target -id clear -f $(pwd)/runtime/clear/$target.txt
fi

if [ $target = "sensors" ]; then
    if [ $power_bus != "init" ]; then
        echo python bin/envds.py power "$power_bus" -s "$power_state"
        python bin/envds.py power $power_bus -s $power_state
        sleep 5s
    fi
    echo python bin/envds.py "$run_command" "$target" -id clear -f $(pwd)/runtime/clear/"$target"_"$power_bus".txt
    python bin/envds.py $run_command $target -id clear -f $(pwd)/runtime/clear/"$target"_"$power_bus".txt
fi

if [ $target = "all" ]; then
    echo python bin/envds.py power 12v-2 -s "$power_state"
    python bin/envds.py power 12v-2 -s "$power_state"

    echo python bin/envds.py power 12v-1 -s "$power_state"
    python bin/envds.py power 12v-1 -s "$power_state"
    # sleep 5s

    # services
    echo "$run_command" services...
    python bin/envds.py $run_command services -id clear -f $(pwd)/runtime/clear/services.txt

    echo "$run_command" interfaces...
    python bin/envds.py $run_command interfaces -id clear -f $(pwd)/runtime/clear/interfaces.txt

    if [ $run_command = "startup" ]; then
        echo waiting for interfaces to start...
        sleep 10
    fi

    echo "$run_command" sensors...
    python bin/envds.py $run_command sensors -id clear -f $(pwd)/runtime/clear/sensors.txt

    # do mSEMS specific restart?

    echo done.
fi
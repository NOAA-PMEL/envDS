#!/bin/bash
trap 'killall' INT

killall() {
    trap '' INT TERM     # ignore INT and TERM while shutting down
    echo "**** Shutting down... ****"     # added double quotes
    kill -TERM 0         # fixed order, send TERM not INT
    wait
    echo "DONE, your ports are now free!"
}

kubectl port-forward service/minio 9000:api &
kubectl port-forward service/minio 9001:console &

kubectl port-forward service/erddap 8081:http &

kubectl port-forward service/mosquitto 1883:http &
kubectl port-forward service/mosquitto 8883:https &

kubectl port-forward -n kafka service/iot-cluster-kafka-bootstrap 9092 &

out="
Minio API:          http://localhost:9000
Minio Console:      http://localhost:9001
ERDDAP:             http://localhost:8081
Mosquitto (HTTP):   http://localhost:1883
Mosquitto (HTTPS):  http://localhost:8883

Kafka broker:       localhost:9092

"
printf "$out"
cat

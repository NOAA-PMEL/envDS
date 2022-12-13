# Install k3d

https://k3d.io/


# Create cluster

This cluster uses a persistent volume at `./dev/pvc/data` and forwards local ports `8080` and `8443` to the cluster's Traefik load balancer. The load balancer isn't currently used, but may be in the future.

```bash
$ k3d cluster create iot-data-landing \
    --volume $(pwd)/dev/pvc/data:/data \
    --port 8080:80@loadbalancer \
    --port 8443:443@loadbalancer \
    --servers 1 \
    --agents 1

$ export KUBECONFIG=$(k3d kubeconfig write iot-data-landing)
$ kubectl get node

NAME                            STATUS   ROLES                  AGE   VERSION
k3d-iot-data-landing-agent-0    Ready    <none>                 3h10m   v1.22.7+k3s1
k3d-iot-data-landing-server-0   Ready    control-plane,master   3h10m   v1.22.7+k3s1
```

# Setup PersistentStorage

The local folder `./dev/pvc/data` is the persistent volume location on the local host. This just tests the ability for the cluster to use the persistent volumes.

```bash
$ kubectl apply -f dev/pvc/storage.yaml

$ kubectl get pv
NAME             CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                   STORAGECLASS   REASON   AGE
data-pv-volume   200Gi      RWO            Retain           Bound    default/data-pv-claim   local-path              7m12s

$ kubectl get pvc
NAME            STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-pv-claim   Bound    pvc-dac0d354-9903-435e-aaa9-0ca6f9a30209   1Gi        RWO            local-path     9s
```

Now test that you can write a file

```bash
$ kubectl exec pv-claim-test -- sh -c "echo i-wrote-something > /data/testing.txt"
$ cat ./dev/pvc/data/testing.txt
i-wrote-something
```

If that works you can remove the temporary storage resources and continue on

```
$ kubectl delete pod pv-claim-test
$ kubectl delete pvc data-pv-claim
$ kubectl delete pv data-pv-volume
```

# Install Strimizi

https://strimzi.io/quickstarts/

```bash
$ kubectl create namespace kafka
$ kubectl create -n kafka -f 'https://strimzi.io/install/latest?namespace=kafka'
$ kubectl apply -n kafka -f dev/kafka/strimzi.yaml
$ kubectl wait kafka/iot-cluster --for=condition=Ready --timeout=300s -n kafka
kafka.kafka.strimzi.io/iot-cluster condition met
```

Test the Kafka broker

```bash
# Run in a separate terminal
$ kubectl port-forward -n kafka service/iot-cluster-kafka-bootstrap 9092
# Now test the connection
$ kafkacat -L -b localhost:9092
```

# Install Knative Operator

```bash
$ kubectl apply -f https://github.com/knative/operator/releases/download/knative-v1.4.1/operator.yaml
$ kubectl get deployment knative-operator

NAME               READY   UP-TO-DATE   AVAILABLE   AGE
knative-operator   1/1     1            1           22s
```

# Configure Knative (Serving/Eventing)

```bash
$ kubectl apply -f dev/knative/operator.yaml
```

Verify Knative Serving is running:

```bash
$ kubectl get deployment -n knative-serving
NAME                     READY   UP-TO-DATE   AVAILABLE   AGE
activator                1/1     1            1           32s
autoscaler               1/1     1            1           32s
controller               1/1     1            1           31s
domain-mapping           1/1     1            1           31s
domainmapping-webhook    1/1     1            1           31s
webhook                  1/1     1            1           30s
autoscaler-hpa           1/1     1            1           29s
net-kourier-controller   1/1     1            1           28s
3scale-kourier-gateway   1/1     1            1           27s

$ kubectl get KnativeServing knative-serving -n knative-serving
NAME              VERSION   READY   REASON
knative-serving   1.4.0     True
```

Verify Knative Eventing is running:

```bash
$ kubectl get deployment -n knative-eventing
NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
eventing-controller        1/1     1            1           2m54s
pingsource-mt-adapter      0/0     0            0           2m54s
eventing-webhook           1/1     1            1           2m54s
imc-controller             1/1     1            1           2m50s
imc-dispatcher             1/1     1            1           2m49s
mt-broker-filter           1/1     1            1           2m48s
mt-broker-ingress          1/1     1            1           2m48s
mt-broker-controller       1/1     1            1           2m47s
kafka-controller-manager   1/1     1            1           2m45s

$ kubectl get KnativeEventing knative-eventing -n knative-eventing
NAME               VERSION   READY   REASON
knative-eventing   1.4.0     True
```

TODO: Install Kafka as the default Knative Broker

# Install MQTT Broker (Mosquitto)

```bash
$ kubectl apply -f dev/mqtt/
$ kubectl get pods --selector "app=mosquitto"

NAME                        READY   STATUS    RESTARTS   AGE
mosquitto-b5b74bc6d-lxmdk   1/1     Running   0          53m
```

Now forward the MQTT port to your host and test

```bash
# In another terminal, forward port 1883 to mosquitto
$ kubectl port-forward service/mosquitto 1883:http
# Now test the broker
$ mosquitto_pub -h "localhost" -p 1883 -q 1 -t foo/bar -i iot-mqtt-testing -m "Hello" -d

Client device-pmel-test-003 sending CONNECT
Client device-pmel-test-003 received CONNACK (0)
Client device-pmel-test-003 sending PUBLISH (d0, q1, r0, m1, 'foo/bar', ... (5 bytes))
Client device-pmel-test-003 received PUBACK (Mid: 1, RC:0)
Client device-pmel-test-003 sending DISCONNECT
```

# Install ERDDAP

```bash
$ kubectl apply -f dev/erddap
# Run in a new terminal
$ kubectl port-forward service/erddap 8081:http
# Testing ERDDAP by visiting http://localhost:8081
```

ERDDAP is available at [http://localhost:8081/erddap/](http://localhost:8081/erddap/)


# Install Minio

```bash
$ kubectl apply -f dev/minio
# Run in 2 new terminals
$ kubectl port-forward service/minio 9000:api
$ kubectl port-forward service/minio 9001:console
```

The Minio console is available at [http://localhost:9001](http://localhost:9001/) and the Minio API endpoint is available at http://localhost:9000.


# Forward all ports

Once you have completed the above steps you can forward all ports at once using a helper script. Make sure you exit all existing `kubectl port-forward ...` commands in all terminals.

```bash
$ bash dev/ports.sh

Minio API:          http://localhost:9000
Minio Console:      http://localhost:9001
ERDDAP:             http://localhost:8081
Mosquitto (HTTP):   http://localhost:1883
Mosquitto (HTTPS):  https://localhost:8883

Kafka broker:       localhost:9092
```

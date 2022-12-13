# Install Knative Kafka Broker

Broker: https://knative.dev/docs/eventing/broker/kafka-broker/

```bash
$ kubectl apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.4.0/eventing-kafka-controller.yaml
$ kubectl apply -f https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-v1.4.0/eventing-kafka-broker.yaml

$ kubectl get deployments.apps -n knative-eventing

NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
eventing-controller        1/1     1            1           30m
pingsource-mt-adapter      0/0     0            0           30m
eventing-webhook           1/1     1            1           30m
imc-controller             1/1     1            1           30m
imc-dispatcher             1/1     1            1           30m
mt-broker-filter           1/1     1            1           30m
mt-broker-ingress          1/1     1            1           30m
mt-broker-controller       1/1     1            1           30m
kafka-controller-manager   1/1     1            1           8m30s
kafka-controller           1/1     1            1           5m32s
kafka-webhook-eventing     1/1     1            1           5m32s
kafka-source-dispatcher    1/1     1            1           5m24s
kafka-broker-dispatcher    1/1     1            1           62s
kafka-broker-receiver      1/1     1            1           62s
```

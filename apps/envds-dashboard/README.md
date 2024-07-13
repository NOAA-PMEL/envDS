# MQTT Bridge

This app is the glue between any MQTT broker and Knative. The app subscribes to an MQTT Broker/Port/Topic for JSON messages, converts them to CloudEvents, and publishes them to a Knative service URL.

## Configuration

The application is configurable using environmental variables prefiex with `MQTT_BRIDGE_`.

* `MQTT_BROKER` - MQTT broker host
* `MQTT_PORT` - MQTT broker port
* `MQTT_TOPIC_FILTER` - An MQTT filter to use to filter messages, defaults to `'instrument/data/+'` to process one level of serial numbers.
* `MQTT_TOPIC_SUBSCRIPTION` - An MQTT subscription string, defaults to `instrument/#` to capture all instrument data.
* `DRY_RUN` - Setting to `true` will only listen on the MQTT broker and will not publish messages to the Knative service URL. This is useful when running locally and not in a K3D cluster as the Knative service URL isn't available outside of the cluster.

## Deployment

### Local

```shell
$ MQTT_BRIDGE_DRY_RUN=yes python apps/mqtt-bridge/mqtt_bridge.py

at=INFO msg=Starting mqtt_broker=localhost mqtt_port=1883 mqtt_topic_filter=aws-id/acg-daq/+ mqtt_topic_subscription=aws-id/# mqtt_client_id=3916e83c72794d2980524074342836c8 knative_broker=http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default dry_run=true
at=INFO msg=Subscribed mqtt_broker=localhost mqtt_port=1883 mqtt_topic_filter=aws-id/acg-daq/+ mqtt_topic_subscription=aws-id/# mqtt_client_id=3916e83c72794d2980524074342836c8
at=INFO msg="{'attributes': {'specversion': '1.0', 'id': 'c84d8276-128f-4d12-bc82-8f1b6659fab8', 'source': '/sensor/MockCo/Sensor-2/6789', 'type': 'gov.noaa.pmel.acg.data.insert.envds.v2', 'datacontenttype': 'application/json; charset=utf-8', 'time': '2022-06-28T20:01:25.003373+00:00'}, 'data': {'data': {'time': '2022-06-28T20:01:25Z', 'diameter': [0.1, 0.2, 0.35, 0.5, 0.75, 1.0], 'temperature': 23.736, 'rh': 55.149, 'bin_counts': [11, 14, 24, 19, 11, 4]}}}" topic_filter=aws-id/acg-daq/+ subscription=aws-id/#
at=INFO msg="{'attributes': {'specversion': '1.0', 'id': '284dc876-8f79-4d9b-af25-9e5981b831cd', 'source': '/sensor/MockCo/Sensor-1/3456', 'type': 'gov.noaa.pmel.acg.data.insert.envds.v2', 'datacontenttype': 'application/json; charset=utf-8', 'time': '2022-06-28T20:01:25.104533+00:00'}, 'data': {'data': {'time': '2022-06-28T20:01:25Z', 'latitude': 9.959, 'longitude': -149.92, 'altitude': 105.964, 'temperature': 27.221, 'rh': 58.278, 'wind_speed': 11.7, 'wind_direction': 74.397}}}" topic_filter=aws-id/acg-daq/+ subscription=aws-id/#
...
```

### Local K3D cluster

```shell
# From project root
$ make deploy-mqtt-bridge
$ kubectl logs -f mqtt-bridge

at=INFO msg=Starting mqtt_broker=localhost mqtt_port=1883 mqtt_topic_filter=aws-id/acg-daq/+ mqtt_topic_subscription=aws-id/# mqtt_client_id=3916e83c72794d2980524074342836c8 knative_broker=http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default dry_run=true
at=INFO msg=Subscribed mqtt_broker=localhost mqtt_port=1883 mqtt_topic_filter=aws-id/acg-daq/+ mqtt_topic_subscription=aws-id/# mqtt_client_id=3916e83c72794d2980524074342836c8
at=INFO msg="{'attributes': {'specversion': '1.0', 'id': 'c84d8276-128f-4d12-bc82-8f1b6659fab8', 'source': '/sensor/MockCo/Sensor-2/6789', 'type': 'gov.noaa.pmel.acg.data.insert.envds.v2', 'datacontenttype': 'application/json; charset=utf-8', 'time': '2022-06-28T20:01:25.003373+00:00'}, 'data': {'data': {'time': '2022-06-28T20:01:25Z', 'diameter': [0.1, 0.2, 0.35, 0.5, 0.75, 1.0], 'temperature': 23.736, 'rh': 55.149, 'bin_counts': [11, 14, 24, 19, 11, 4]}}}" topic_filter=aws-id/acg-daq/+ subscription=aws-id/#
at=INFO msg="{'attributes': {'specversion': '1.0', 'id': '284dc876-8f79-4d9b-af25-9e5981b831cd', 'source': '/sensor/MockCo/Sensor-1/3456', 'type': 'gov.noaa.pmel.acg.data.insert.envds.v2', 'datacontenttype': 'application/json; charset=utf-8', 'time': '2022-06-28T20:01:25.104533+00:00'}, 'data': {'data': {'time': '2022-06-28T20:01:25Z', 'latitude': 9.959, 'longitude': -149.92, 'altitude': 105.964, 'temperature': 27.221, 'rh': 58.278, 'wind_speed': 11.7, 'wind_direction': 74.397}}}" topic_filter=aws-id/acg-daq/+ subscription=aws-id/#
...
```

import os
import sys
import shutil
import logging
import argparse
import asyncio
import signal
import subprocess
from time import sleep
from kubernetes import config, client
from kubernetes.utils import create_from_yaml, FailToCreateError
from pathlib import Path
import json
import yaml
import platform

import docker
from cloudevents.http import CloudEvent
from cloudevents.conversion import to_structured
from cloudevents.exceptions import InvalidStructuredJSON

from typing import Union, Optional
from pydantic import BaseModel

global cluster_id


class MessageBusConfig(BaseModel):
    # type: str | None = "mqtt"
    # config: dict | None = {"mqtt_port": 1883, "mqtts_port": 8883}
    type: Union[str,None] = "mqtt"
    config: Union[dict,None] = {"mqtt_port": 1883, "mqtts_port": 8883}


# class ClusterConfig(BaseModel):
#     host: str = "localhost"
#     config_dir: str | None = os.path.join(os.getcwd(), "data", "config")
#     certs_dir: str | None = os.path.join(os.getcwd(), "data", "certs")
#     envds_data_dir: str | None = os.path.join(os.getcwd(), "data", "envds")
#     http_port: int | None = 8080
#     https_port: int | None = 8443
#     message_bus: MessageBusConfig | None = MessageBusConfig(
#         type="mqtt", config={"mqtt_port": 1883, "mqtts_port": 8883}
#     )
#     db: str | None = "redis"
#     log_level: str = "info"
#     envds_id: str = "default"

class ClusterConfig(BaseModel):
    host: str = "localhost"
    config_dir: Optional[str] = os.path.join(os.getcwd(), "data", "config")
    certs_dir: Optional[str] = os.path.join(os.getcwd(), "data", "certs")
    envds_data_dir: Optional[str] = os.path.join(os.getcwd(), "data", "envds")
    http_port: Optional[int] = 8080
    https_port: Optional[int] = 8443
    message_bus: Optional[MessageBusConfig] = MessageBusConfig(
        type="mqtt", config={"mqtt_port": 1883, "mqtts_port": 8883}
    )
    db: Optional[str] = "redis"
    log_level: str = "info"
    envds_id: str = "default"

class ApplyConfig(BaseModel):
    file: str
    # namespace: str | None = "default"
    namespace: Optional[str] = "default"


class envdsConfig(BaseModel):
    port: int = 9080


# class SystemConfig(BaseModel):
#     core_packages: list | None = ["envds"]
#     core_services: list | None = ["envds-manage"] #, "envds-registrar", "envds-files"]
#     message_bus: str | None = "mqtt"
#     db: str | None = "redis"
#     added_services: list | None = []
#     user_services: list | None = []
#     namespace: str | None = "envds"

class SystemConfig(BaseModel):
    core_packages: Optional[list] = ["envds"]
    core_services: Optional[list] = ["envds-manage"] #, "envds-registrar", "envds-files"]
    message_bus: Optional[str] = "mqtt"
    db: Optional[str] = "redis"
    added_services: Optional[list] = []
    user_services: Optional[list] = []
    namespace: Optional[str] = "envds"

# utils
def get_kubeconfig():
    # set kubeconfig
    # k3d_args = ["k3d", "kubeconfig", "write", "envds"]
    k3d_args = ["k3d", "kubeconfig", "write", get_cluster_name()]
    print(f"get_kubeconfig: k3d_args: {k3d_args}")
    res = subprocess.run(k3d_args, capture_output=True, text=True)
    # print(f"config: {res.stdout}")
    # print(f"config: {res.stdout}")
    return res.stdout.strip()


def set_kubeconfig():
    # # set kubeconfig
    # k3d_args = [
    #     "k3d",
    #     "kubeconfig",
    #     "write",
    #     "envds"
    # ]
    # res = subprocess.run(k3d_args, capture_output=True, text=True)
    os.environ["KUBECONFIG"] = get_kubeconfig()


def get_registry_port() -> int:
    args = [
        "docker",
        "ps",
        "--format",
        "'{{.Ports}}:'",
        "-f",
        f"name=envds-registry-{get_cluster_id()}",
    ]
    # args = ["docker", "ps", "--format", "'{{.Ports}}:'", "-f", f"name={get_cluster_name()}-registry"]
    print(f"get_registry_port: args: {args}")
    res = subprocess.run(args, capture_output=True, text=True)
    port = res.stdout.strip().split("->")[0].split(":")[1]
    return int(port)


def register_image(image: str):

    print(f"register_image: {image}")
    client = docker.from_env()

    repo = image.split(":")[0]
    tag = image.split(":")[1]
    if tag == "":
        tag = "latest"

    print(f"Get {image}")
    img = client.images.get(image)

    registry = f"localhost:{get_registry_port()}"
    print(f"Tag image as: {registry}/{repo}:{tag}")
    img.tag(f"{registry}/{repo}", tag=tag)

    print(f"Push image: {registry}/{repo}:{tag}")
    client.images.push(f"{registry}/{repo}", tag=tag)

    # registry = f"localhost:{get_registry_port()}"
    # print(f"registry: {registry}")
    # args = ["docker", "pull", image]
    # res = subprocess.run(args, capture_output=True, text=True)
    # print(f"pull: {res.stdout}, {res.stderr}")

    # args = ["docker", "image", "tag", image, f"{registry}/core/{image}"]
    # res = subprocess.run(args, capture_output=True, text=True)
    # print(f"tag: {res.stdout}, {res.stderr}")

    # args = ["docker", "push", f"{registry}/core/{image}"]
    # res = subprocess.run(args, capture_output=True, text=True)
    # print(f"push: {res.stdout}, {res.stderr}")

    # removed here.
    # k3d_args = ["k3d", "image", "import", image, "-c", "envds"]
    # print(f"registering: {image}")
    # print(f"args: {' '.join(k3d_args)}")
    # res = subprocess.run(k3d_args, capture_output=True, text=True)
    # print(f"ouput(error): {res.stderr}")
    # print(f"ouput(out): {res.stdout}")


def get_cluster_name(envds_id: str = None) -> str:
    cfg = get_config("cluster")
    return "-".join(["envds", cfg["envds_id"]])


def get_cluster_id() -> str:
    cfg = get_config("cluster")
    return cfg["envds_id"]


def create_cluster(args) -> bool:
    # print("init")

    cluster_config = ClusterConfig()
    # print(args.envds_data_volume)
    if args.envds_data_volume:
        cluster_config.envds_data_dir = args.envds_data_volume
    if args.envds_cfg_volume:
        cluster_config.config_dir = args.envds_cfg_volume
    if args.envds_certs_volume:
        cluster_config.certs_dir = args.envds_certs_volume
    if args.host:
        cluster_config.host = args.host
    if args.http_port:
        cluster_config.http_port = args.http_port
    if args.https_port:
        cluster_config.https_port = args.https_port
    if args.envds_id:
        cluster_config.envds_id = args.envds_id

    mbconfig = MessageBusConfig()
    if args.mqtt_port:
        mbconfig.config["mqtt_port"] = args.mqtt_port
    if args.https_port:
        mbconfig.config["mqtts_port"] = args.mqtts_port
    cluster_config.message_bus = mbconfig

    Path(cluster_config.envds_data_dir).mkdir(parents=True, exist_ok=True)
    Path(cluster_config.config_dir).mkdir(parents=True, exist_ok=True)
    Path(cluster_config.certs_dir).mkdir(parents=True, exist_ok=True)

    host = ""
    # print(config.host)
    if cluster_config.host != "localhost":
        host = f"{cluster_config.host}:"

    # save cluster config
    # print(f"pre-save: {config}")
    save_config(cluster_config.dict(), cfg_type="cluster")

    cluster_name = get_cluster_name()
    print(f"create_cluster: {cluster_name}")
    try:
        mb_config = cluster_config.message_bus

        # check for running docker/k3d and envds cluster
        res = subprocess.run(
            ["k3d", "cluster", "ls"], check=True, capture_output=True, text=True
        )
        # print(res.stdout)
        for line in res.stdout.split("\n"):
            parts = line.split()
            # print(parts)
            # if parts and parts[0] == "envds":
            if parts and parts[0] == cluster_name:
                print("envds already initialized -- try 'envds start'")
                return True

        # if envds cluster does not exit, create
        k3d_args = [
            "k3d",
            "cluster",
            "create",
            # "envds",
            cluster_name,
            # "--k3s-arg",
            # "--disable=traefik@server:0",
            "--volume",
            f"{cluster_config.envds_data_dir}:/data/envds",
            "--volume",
            f"{cluster_config.config_dir}:/data/config",
            "--volume",
            f"{cluster_config.certs_dir}:/data/certs",
            "--port",
            f"{host}{cluster_config.http_port}:80@loadbalancer",
            "--port",
            f"{host}{cluster_config.https_port}:443@loadbalancer",
            "--port",
            f"{host}{mb_config.config['mqtt_port']}:{1883}@loadbalancer",
            "--port",
            f"{host}{mb_config.config['mqtts_port']}:{8883}@loadbalancer",
            "--port",
            f"{host}{10080}:{10080}/udp@loadbalancer",
            "--registry-create",
            f"envds-registry-{get_cluster_id()}",
            # f"{cluster_name}-registry",
            "--servers",
            "1",
            "--agents",
            "1",
        ]

        print("*** Creating k3d cluster:")
        print(" ".join(k3d_args))
        # print(k3d_args)

        res = subprocess.run(k3d_args, capture_output=True, text=True, encoding="latin-1")
        print(f"stderr: {res.stderr}")
        print(f"stdout: {res.stdout}")

        print("done.")

        # # set kubeconfig
        # kubeconfig_args = [
        #     "k3d",
        #     "kubeconfig",
        #     "write",
        #     cluster_name
        # ]
        # res = subprocess.run(k3d_args, capture_output=True, text=True)
        # print(f"res: {res}")

        # set kubeconfig
        set_kubeconfig()

        # # save cluster config
        # # print(f"pre-save: {config}")
        # save_config(cluster_config.dict(), cfg_type="cluster")

        # # add required CRDs
        # k8s_args = [
        #     "kubectl",
        #     "apply",
        #     "-f",
        #     "./config/cluster/crd"
        # ]
        # res = subprocess.run(k8s_args, capture_output=True, text=True)
        # print(f"stderr: {res.stderr}")
        # print(f"stdout: {res.stdout}")

        return True

    except subprocess.CalledProcessError as e:
        print(
            f"init error: {e}. Check to make sure docker is running and k3d installed"
        )
        return False


# res = subprocess.run(
#     ["k3d", "cluster", "create", "test-subprocess"], capture_output=True, text=True
# )
# print(res.stdout)

# TODO: add init/start erddap


def create_message_bus():

    cluster_config = ClusterConfig()
    if (cluster_config_dict := get_config(cfg_type="cluster")) is not None:
        print(cluster_config_dict)
        cluster_config = ClusterConfig.parse_obj(cluster_config_dict)

    system_config = SystemConfig()
    if (sys_config_dict := get_config(cfg_type="system")) is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # register the image with k3d
    with open(f"./apps/message_bus/{system_config.message_bus}/VERSION", "r") as f:
        tag = f.readline().strip()

    mb_config = cluster_config.message_bus
    if mb_config.type == "mqtt":

        client = docker.from_env()

        mqtt_image = "eclipse-mosquitto"
        try:
            # img = client.images.get(f"core/{mqtt_image}:{tag}")
            img = client.images.get(f"envds/{mqtt_image}:{tag}")
        except docker.errors.ImageNotFound:
            # pull
            # print(f"Pull {img}")
            img = client.images.pull(mqtt_image, tag=tag)

        print(f"Tag image as: envds/eclipse-mosquitto:{tag}")
        # repo = f"core/{mqtt_image}"
        repo = f"envds/{mqtt_image}"
        img.tag(repo, tag=tag)
        register_image(f"{repo}:{tag}")

        # img = f"core/eclipse-mosquitto:{tag}"
        # register_image(img)

        # # start mosquitto
        # filename = f"./apps/core/{system_config.message_bus}/config/{get_cluster_id()}/"
        # cfg = ApplyConfig(file=filename)
        # # cfg.file = os.path.join(os.getcwd(),"mqtt", "config", "mosquitto.yaml")
        # cfg.namespace = "default"
        # print(cfg)
        # apply(cfg)
        start_message_bus()
    else:
        print(f"unkown message bus type: {mb_config.type}")
        exit(1)


def start_message_bus():
    cluster_config = ClusterConfig()
    if (cluster_config_dict := get_config(cfg_type="cluster")) is not None:
        print(cluster_config_dict)
        cluster_config = ClusterConfig.parse_obj(cluster_config_dict)

    system_config = SystemConfig()
    if (sys_config_dict := get_config(cfg_type="system")) is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    mb_config = cluster_config.message_bus
    if mb_config.type == "mqtt":

        filename = f"./apps/message_bus/{system_config.message_bus}/config/{get_cluster_id()}/"
        cfg = ApplyConfig(file=filename)
        # cfg.file = os.path.join(os.getcwd(),"mqtt", "config", "mosquitto.yaml")
        cfg.namespace = "default"
        print(cfg)
        apply(cfg)
    else:
        print(f"unkown message bus type: {mb_config.type}")
        exit(1)


def create_db():

    cluster_config = ClusterConfig()
    if (cluster_config_dict := get_config(cfg_type="cluster")) is not None:
        print(cluster_config_dict)
        cluster_config = ClusterConfig.parse_obj(cluster_config_dict)

    system_config = SystemConfig()
    if (sys_config_dict := get_config(cfg_type="system")) is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # register the image with k3d
    with open(f"./apps/db/{system_config.db}/VERSION", "r") as f:
        tag = f.readline().strip()

    db_config = cluster_config.db
    if db_config == "redis":

        client = docker.from_env()

        db_image = "redis-stack-server"
        try:
            # img = client.images.get(f"core/{db_image}:{tag}")
            img = client.images.get(f"envds/{db_image}:{tag}")
        except docker.errors.ImageNotFound:
            # pull
            # print(f"Pull {img}")
            img = client.images.pull(f"redis/{db_image}", tag=tag)

        # print(f"Tag image as: core/redis-stack-server:{tag}")
        print(f"Tag image as: envds/redis-stack-server:{tag}")
        # repo = f"core/{db_image}"
        repo = f"envds/{db_image}"
        img.tag(repo, tag=tag)
        register_image(f"{repo}:{tag}")

        # img = f"core/eclipse-mosquitto:{tag}"
        # register_image(img)

        # # start mosquitto
        # filename = f"./apps/core/{system_config.db}/config/{get_cluster_id()}/"
        # cfg = ApplyConfig(file=filename)
        # # cfg.file = os.path.join(os.getcwd(),"mqtt", "config", "mosquitto.yaml")
        # cfg.namespace = "default"
        # print(cfg)
        # apply(cfg)
        start_db()
    else:
        print(f"unkown db type: {db_config.type}")
        exit(1)


def start_db():
    cluster_config = ClusterConfig()
    if (cluster_config_dict := get_config(cfg_type="cluster")) is not None:
        print(cluster_config_dict)
        cluster_config = ClusterConfig.parse_obj(cluster_config_dict)

    system_config = SystemConfig()
    if (sys_config_dict := get_config(cfg_type="system")) is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # # register the image with k3d
    # with open(f"./apps/db/{system_config.db}/VERSION", "r") as f:
    #     tag = f.readline().strip()

    db_config = cluster_config.db
    if db_config == "redis":
        # start mosquitto
        filename = f"./apps/db/{system_config.db}/config/{get_cluster_id()}/"
        cfg = ApplyConfig(file=filename)
        # cfg.file = os.path.join(os.getcwd(),"mqtt", "config", "mosquitto.yaml")
        cfg.namespace = "default"
        print(cfg)
        apply(cfg)
    else:
        print(f"unkown db type: {db_config.type}")
        exit(1)


# def save_cluster_config(config: ClusterConfig):
def save_config(config: dict, cfg_type: str = None):
    # print(config)
    global cluster_id
    envds_id = cluster_id

    if cfg_type is None or cfg_type not in ["cluster", "system"]:
        print(f"can't save config of type {cfg_type}")
        return

    try:
        # p = Path(os.path.join(os.getcwd(), "config", "cluster"))
        p = Path(os.path.join(os.getcwd(), "config", cfg_type))
        p.mkdir(parents=True, exist_ok=True)

        # # save as current config
        # # name = f"envds_{cfg_type}.json"
        # name = f"envds-{envds_id}_{cfg_type}.json"
        # # print(p)
        # with open(os.path.join(p, name), "w") as f:
        #     # print(config.dict())
        #     # json.dump(config.dict(), f)
        #     json.dump(config, f)

        if cfg_type == "cluster":
            cluster_name = f"envds-{config['envds_id']}"
        elif cfg_type == "system":
            cluster_name = get_cluster_name()
        print(f"{cfg_type}: {cluster_name}")
        # save additional copy using envds_id for later use
        name = f"{cluster_name}_{cfg_type}.json"
        # print(p)
        with open(os.path.join(p, name), "w") as f:
            # print(config.dict())
            # json.dump(config.dict(), f)
            json.dump(config, f)

    except Exception as e:
        print(e)


# def get_cluster_config() -> ClusterConfig:
def get_config(cfg_type: str = None, envds_id: str = None) -> dict:
    global cluster_id

    if cfg_type is None or cfg_type not in ["cluster", "system"]:
        print(f"can't get config of type {cfg_type}")
        return None

    if envds_id is None:
        envds_id = cluster_id

    name = f"envds_{cfg_type}.json"
    if envds_id:
        name = f"envds-{envds_id}_{cfg_type}.json"

    print(f"get_config: {cfg_type}, {name}")
    try:
        with open(os.path.join(os.getcwd(), "config", cfg_type, name), "r") as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        print(f"config file {name} not found!")
        return None


def get_cluster_status() -> bool:

    # config.load_kube_config(config_file=get_kubeconfig())
    # v1 = client.CoreV1Api(config)
    # api_instance = client.AppsV1Api(v1)
    # name = "traefik"
    # ns = "kube-system"
    # # api_instance.read_namespaced_pod_status(name=name, namespace=ns)
    # status = api_instance.read_namespaced_deployment_status(name, ns, pretty=True)
    # print(status)

    args = ["kubectl", "get", "deployment", "traefik", "-ojson", "-n", "kube-system"]
    res = subprocess.run(args, capture_output=True, text=True)
    # print(f"get_cluster_status: {res}")
    try:
        status = json.loads(res.stdout)
        replicas = status["status"]["availableReplicas"]
        if replicas and replicas >= 1:
            return True
        else:
            return False
    except (json.JSONDecodeError, KeyError):
        return False
    # print(type(replicas))
    # print(f"stderr: {res.stderr}")
    # print(f"stdout: {res.stdout}")


def create_envds(update: bool = True):
    system_config = SystemConfig()
    save_config(system_config.dict(), cfg_type="system")

    build_core_packages(update=update)

    create_core_services(update=update)

    # for x in range(1,10):
    while not get_cluster_status():
        print("waiting for cluster to become ready")
        sleep(10)

    create_message_bus()
    create_db()
    start_core_services(update=update)

    # # create ingress
    # folder = "./config/cluster/ingress"
    # config = ApplyConfig(file=folder)
    # apply(config)

    pass


def build_core_packages(update: bool = True):

    system_config = SystemConfig()
    sys_config_dict = get_config(cfg_type="system")
    if sys_config_dict is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # system_config = SystemConfig(get_config(cfg_type="system"))
    print("*** Build and install core package(s)")
    # core_pkgs = ["envds"]
    for pkg in system_config.core_packages:
        print(f"    working on {pkg}")

        # remove old wheels
        print("\tremoving old build")
        build_path = os.path.join(pkg, "build")
        shutil.rmtree(build_path, ignore_errors=True)
        # try:
        #     os.rmdir(build_path)
        # except (OSError, FileNotFoundError) as e:
        #     print(f"could not remove directory: {build_path}. Error: {e}")
        # res = subprocess.run(
        #     # ["pip", "install", "-e", f"./{pkg}"],
        #     [
        #         "rm",
        #         "-rf",
        #         f"{pkg}/build",
        #     ],
        #     check=True,
        #     capture_output=True,
        #     text=True,
        # )
        # results = res.stdout.split("\n")
        # for r in results:
        #     print(f"\t{r}")

        print("\tremoving old wheel file(s)")
        wheel_path = os.path.join(pkg, "lib")
        try:
            for f in os.listdir(wheel_path):
                if f.endswith(".whl"):
                    os.remove(os.path.join(wheel_path, f))
            # os.remove(wheel_path)
        except (OSError, FileNotFoundError) as e:
            print(f"could not remove directory: {build_path}. Error: {e}")
        # res = subprocess.run(
        #     # ["pip", "install", "-e", f"./{pkg}"],
        #     [
        #         "rm",
        #         "-f",
        #         f"{pkg}/lib/*.whl",
        #     ],
        #     check=True,
        #     capture_output=True,
        #     text=True,
        # )
        # results = res.stdout.split("\n")
        # for r in results:
        #     print(f"\t{r}")
        print("\tbuilding new wheel(s)")
        res = subprocess.run(
            # ["pip", "install", "-e", f"./{pkg}"],
            [
                "pip",
                "wheel",
                f"{pkg}/.",
                # "--use-feature=in-tree-build",
                "--wheel-dir",
                f"{pkg}/lib",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        results = res.stdout.split("\n")
        for r in results:
            print(f"\t{r}")


def create_core_services(update: bool = True):

    system_config = SystemConfig()
    sys_config_dict = get_config(cfg_type="system")
    if sys_config_dict is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # create envds namespace
    config.load_kube_config(config_file=get_kubeconfig())
    v1 = client.CoreV1Api()
    ns_list = v1.list_namespace()
    namespaces = [item.metadata.name for item in ns_list.items]
    if system_config.namespace not in namespaces:
        v1.create_namespace(
            client.V1Namespace(
                metadata=client.V1ObjectMeta(name=system_config.namespace)
            )
        )

    # services = ["envds"]  # ,
    print("*** Installing core services")
    for service in system_config.core_services:
        # build_core_package(pkg=service)
        print(f"\tworking on {service}")
        add_service_image(app=service)
    # register_image
    # build_envds_package()
    # build_core_image(pkg="envds")


# def build_core_package(pkg="envds"):
#     # pkg = "envds"
#     print(f"Build and install {pkg} core package")
#     res = subprocess.run(["pip", "install", "-e", f"./{pkg}"], check=True, capture_output=True, text=True)
#     results = res.stdout.split("\n")
#     for r in results:
#         print(r)

# def add_service(service: str = None, type: str = "core"):
def create_service(service: str = None, app_group: str = None):

    if service is None:
        return
    print(f"service: {service}")
    # add_service_image(app=service, type=type)
    add_service_image(app=service, app_group=app_group)
    start_service(service, app_group=app_group)


def start_service(service: str = None, app_group: str = None, update: bool = True):

    if service is None:
        return

    filename = f"./apps/{service}/config/{get_cluster_id()}/"
    if app_group:
        filename = f"./apps/{app_group}/{service}/config/{get_cluster_id()}/"
    print(f"filename: {filename}")
    cfg = ApplyConfig(file=filename)
    cfg.namespace = "default"
    apply(cfg)

def stop_service(service: str = None, app_group: str = None):

    if service is None:
        return

    filename = f"./apps/{service}/config/{get_cluster_id()}/"
    if app_group:
        filename = f"./apps/{app_group}/{service}/config/{get_cluster_id()}/"
    print(f"filename: {filename}")
    cfg = ApplyConfig(file=filename)
    cfg.namespace = "default"
    delete(cfg)

def startup_services(services_file: str):
    if services_file is None:
        return
    print(f"services_file: {services_file}")
    with open(services_file, "r") as f:
        for service in f:
            print(f"service: {service}")
            start_service(service=service.strip())
            sleep(1)

def startup_interfaces(interfaces_file: str):
    if interfaces_file is None:
        return
    with open(interfaces_file, "r") as f:
        for interface in f:
            # parts = interface.strip().split("/")
            # start_interface(type=parts[0], name=parts[1])
            # sleep(1)

            filename = os.path.join(
                ".",
                "apps",
                "daq",
                "interfaces",
                interface.strip(),
                "config",
                get_cluster_id()
            )

            cfg = ApplyConfig(file=filename)
            cfg.namespace = "default"
            apply(cfg)
            sleep(2)

def startup_sensors(sensors_file: str):
    if sensors_file is None:
        return
    with open(sensors_file, "r") as f:
        for sensor in f:
            # parts = interface.strip().split("/")
            # start_interface(type=parts[0], name=parts[1])
            # sleep(1)

            filename = os.path.join(
                ".",
                "apps",
                "daq",
                "sensors",
                sensor.strip(),
                "config",
                get_cluster_id()
            )

            cfg = ApplyConfig(file=filename)
            cfg.namespace = "default"
            apply(cfg)
            sleep(2)

def shutdown_services(services_file: str):
    if services_file is None:
        return
    print(f"services_file: {services_file}")
    with open(services_file, "r") as f:
        for service in f:
            print(f"service: {service}")
            stop_service(service=service.strip())
            sleep(.5)

def shutdown_interfaces(interfaces_file: str):
    if interfaces_file is None:
        return
    with open(interfaces_file, "r") as f:
        for interface in f:
            # parts = interface.strip().split("/")
            # start_interface(type=parts[0], name=parts[1])
            # sleep(1)

            filename = os.path.join(
                ".",
                "apps",
                "daq",
                "interfaces",
                interface.strip(),
                "config",
                get_cluster_id()
            )

            cfg = ApplyConfig(file=filename)
            cfg.namespace = "default"
            delete(cfg)
            sleep(.5)

def shutdown_sensors(sensors_file: str):
    if sensors_file is None:
        return
    with open(sensors_file, "r") as f:
        for sensor in f:
            # parts = interface.strip().split("/")
            # start_interface(type=parts[0], name=parts[1])
            # sleep(1)

            filename = os.path.join(
                ".",
                "apps",
                "daq",
                "sensors",
                sensor.strip(),
                "config",
                get_cluster_id()
            )

            cfg = ApplyConfig(file=filename)
            cfg.namespace = "default"
            delete(cfg)
            sleep(.5)

# add_instrument(make=cl_args.make, model=cl_args.model, serial_number=cl_args.serial_number)
def create_sensor(make: str, model: str, serial_number: str):

    # if service is None:
    #     return
    print(f"make: {make}, model: {model}, s/n: {serial_number}")
    # add_service_image(app=service, type=type)
    add_sensor_image(make=make, model=model)
    start_sensor(make=make, model=model, serial_number=serial_number)


def start_sensor(make: str, model: str, serial_number: str):

    # if service is None:
    #     return

    # filename = f"./apps/{service}/config/"
    filename = os.path.join(
        ".",
        "apps",
        "daq",
        "sensors",
        make,
        model,
        "config",
        get_cluster_id(),
        f"{model.lower()}-{serial_number}.yaml",
    )

    cfg = ApplyConfig(file=filename)
    cfg.namespace = "default"
    apply(cfg)


def create_interface(type: str, name: str, uid: str):

    # if service is None:
    #     return
    print(f"type: {type}, name: {name}, uid: {uid}")
    # add_service_image(app=service, type=type)
    add_interface_image(type=type, name=name)
    start_interface(type=type, name=name, uid=uid)


def start_interface(type: str, name: str, uid: str):

    # if service is None:
    #     return

    # filename = f"./apps/{service}/config/"
    filename = os.path.join(
        ".",
        "apps",
        "daq",
        "interfaces",
        type,
        name,
        "config",
        get_cluster_id(),
        f"{name.lower()}-{uid}.yaml",
    )

    cfg = ApplyConfig(file=filename)
    cfg.namespace = "default"
    apply(cfg)


def create_dataserver():

    # if service is None:
    #     return
    # print(f"type: {type}, name: {name}, uid: {uid}")
    # add_service_image(app=service, type=type)
    # add_interface_image(type=type, name=name)
    # start_interface(type=type, name=name, uid=uid)

    # create secrets for erddap
    # add erddap image
    # start erddap
    # add dataserver image
    # start dataserver
    pass

    create_erddap()

    add_service_image(app="envds-dataserver", app_group="dataserver")
    start_dataserver()




def create_erddap():

    # TODO: finish building dataserver

    print("here:1")
    cluster_config = ClusterConfig()
    if (cluster_config_dict := get_config(cfg_type="cluster")) is not None:
        print(cluster_config_dict)
        cluster_config = ClusterConfig.parse_obj(cluster_config_dict)
    print("here:2")

    system_config = SystemConfig()
    print("here:3")
    if (sys_config_dict := get_config(cfg_type="system")) is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # register the image with k3d
    print("here:4")
    with open(f"./apps/dataserver/erddap/VERSION", "r") as f:
        tag = f.readline().strip()

    # db_config = cluster_config.db
    # if db_config == "redis":
    print("here:5")

    client = docker.from_env()
    print("here:6")

    erddap_image = "docker-erddap"
    # if platform.machine() == "aarch64":
    #     erddap_image = "docker-erddap-arm64"

    try:        
        # client.images.remove(f"envds/{erddap_image}:{tag}")
        print("trying to pull erddap image from local registry")
        # img = client.images.get(f"core/{db_image}:{tag}")
        img = client.images.get(f"envds/{erddap_image}:{tag}")
        print(f"img: {img}")
    except docker.errors.ImageNotFound:
        if platform.machine() == "aarch64":
            # import from local file
            with open(f"./apps/dataserver/erddap/images/aarch64/axiom_docker-erddap-arm64_latest-jdk11-openjdk.tar", 'rb') as f: 
                img_list = client.images.load(f)
                for im in img_list:
                    print(f"image_list[i]: {im.id}")
                img = img_list[0]
                # print(f"image: {img.id}")
        else:
            # pull
            print(f"Pull axiom/{erddap_image}:{tag}")
            img = client.images.pull(f"axiom/{erddap_image}", tag=tag)

    # print(f"Tag image as: core/redis-stack-server:{tag}")
    print(f"Tag image as: envds/{erddap_image}:{tag}")
    # repo = f"core/{db_image}"
    repo = f"envds/{erddap_image}"
    img.tag(repo, tag=tag)
    register_image(f"{repo}:{tag}")

        # img = f"core/eclipse-mosquitto:{tag}"
        # register_image(img)

    # # start erddap
    # filename = f"./apps/dataserver/erddap/config/{get_cluster_id()}/"
    # cfg = ApplyConfig(file=filename)
    # # cfg.file = os.path.join(os.getcwd(),"mqtt", "config", "mosquitto.yaml")
    # cfg.namespace = "default"
    # print(cfg)
    # apply(cfg)

def start_erddap():
    cluster_config = ClusterConfig()
    if (cluster_config_dict := get_config(cfg_type="cluster")) is not None:
        print(cluster_config_dict)
        cluster_config = ClusterConfig.parse_obj(cluster_config_dict)

    system_config = SystemConfig()
    if (sys_config_dict := get_config(cfg_type="system")) is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # create erddap secret
    key_file = os.path.join("apps", "dataserver", "erddap", "certs", "ssl.key")
    cert_file = os.path.join("apps", "dataserver", "erddap", "certs", "ssl.crt")
    create_tls_secret(name="erddap-tls-secret", key=key_file, cert=cert_file, ns="envds")

    filename = f"./apps/dataserver/erddap/config/{get_cluster_id()}/"
    cfg = ApplyConfig(file=filename)
    # cfg.file = os.path.join(os.getcwd(),"mqtt", "config", "mosquitto.yaml")
    cfg.namespace = "default"
    print(cfg)
    apply(cfg)

def start_dataserver():

    cluster_config = ClusterConfig()
    if (cluster_config_dict := get_config(cfg_type="cluster")) is not None:
        print(cluster_config_dict)
        cluster_config = ClusterConfig.parse_obj(cluster_config_dict)

    system_config = SystemConfig()
    if (sys_config_dict := get_config(cfg_type="system")) is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    # if service is None:
    #     return

    start_erddap()

    # filename = f"./apps/{service}/config/"
    filename = os.path.join(
        ".", "apps", "dataserver", "envds-dataserver", "config", get_cluster_id()
    )

    cfg = ApplyConfig(file=filename)
    cfg.namespace = "default"
    apply(cfg)


def start_core_services(update: bool = True):

    system_config = SystemConfig()
    sys_config_dict = get_config(cfg_type="system")
    if sys_config_dict is not None:
        system_config = SystemConfig.parse_obj(sys_config_dict)

    print("*** Starting core services")
    for service in system_config.core_services:
        # build_core_package(pkg=service)
        print(f"\tworking on {service}")
        filename = f"./apps/{service}/config/{get_cluster_id()}"
        cfg = ApplyConfig(file=filename)
        # cfg.file = os.path.join(os.getcwd(),"mqtt", "config", "mosquitto.yaml")
        cfg.namespace = "default"
        if update:
            delete(cfg)
        apply(cfg)


# def add_service_image(app: str = "envds-manage", type: str = "core") -> str:
def add_service_image(app: str = "envds-manage", app_group: str = "") -> str:

    # registry = f"envds-registry:{get_registry_port()}"
    # registry = f"localhost:{get_registry_port()}"
    # repo = f"{type}/{app}"
    repo = f"envds/{app}"

    print(f"repo: {repo}, app: {app}")
    app_path = f"./apps/{app}"
    if app_group:
        app_path = f"./apps/{app_group}/{app}"

    # with open(f"./apps/{app}/VERSION", "r") as f:
    with open(f"{app_path}/VERSION", "r") as f:
        tag = f.readline()
    # img = f"{registry}/{repo}:{tag}"
    img = f"{repo}:{tag}"

    # with open(f"./apps/{app}/requirements_local.txt", "r") as req_file:
    try:
        with open(f"{app_path}/requirements_local.txt", "r") as req_file:
            while req := req_file.readline():
                print("\tcopying wheel(s) to app library")
                src_path = os.path.join(req, "lib")
                # dest_path = os.path.join("apps", app, "lib", req)
                dest_path = os.path.join(app_path, "lib", req)
                print(f"{src_path}, {dest_path}")
                os.makedirs(dest_path, exist_ok=True)
                for f in os.listdir(src_path):
                    if f.endswith(".whl"):
                        shutil.copyfile(
                            os.path.join(src_path, f), os.path.join(dest_path, f)
                        )
                        # os.remove(os.path.join(wheel_path, f))
    except FileNotFoundError:
        pass

    client = docker.from_env()
    # print(f"client: {client}, {client.info()}")

    print(f"Build {img}")
    # res = client.images.build(path=f"./apps/{app}", tag=img)
    res = client.images.build(path=f"{app_path}", tag=img)
    print(f"Build image result: {res}")

    register_image(img)

    # print(f"Push {img}")
    # res = client.images.push(img)
    # print(f"push image result: {res}")

    # print(client.images.list(registry))


def add_sensor_image(make: str = "MockCo", model: str = "Mock1") -> str:

    # registry = f"envds-registry:{get_registry_port()}"
    # registry = f"localhost:{get_registry_port()}"
    # repo = f"{type}/{app}"
    repo = f"envds/sensor/{make.lower()}-{model.lower()}"

    inst_path = os.path.join("apps", "daq", "sensors", make, model)

    print(f"repo: {repo}, inst_path: {inst_path}")
    # with open(f"./{inst_path}/VERSION", "r") as f:
    with open(os.path.join(".", inst_path, "VERSION"), "r") as f:
        tag = f.readline()
    # img = f"{registry}/{repo}:{tag}"
    img = f"{repo}:{tag}"

    # with open(f"./apps/daq/instruments/{make}/{model}/requirements_local.txt", "r") as req_file:
    with open(os.path.join(".", inst_path, "requirements_local.txt"), "r") as req_file:
        while req := req_file.readline():
            print("\tcopying wheel(s) to app library")
            src_path = os.path.join(req, "lib")
            dest_path = os.path.join(inst_path, "lib", req)
            print(f"{src_path}, {dest_path}")
            os.makedirs(dest_path, exist_ok=True)
            for f in os.listdir(src_path):
                if f.endswith(".whl"):
                    shutil.copyfile(
                        os.path.join(src_path, f), os.path.join(dest_path, f)
                    )
                    # os.remove(os.path.join(wheel_path, f))
    client = docker.from_env()

    print(f"Build {img}")
    # res = client.images.build(path=f"./apps/{inst}", tag=img)
    res = client.images.build(path=os.path.join(".", inst_path), tag=img)
    print(f"Build image result: {res}")

    register_image(img)

    # print(f"Push {img}")
    # res = client.images.push(img)
    # print(f"push image result: {res}")

    # print(client.images.list(registry))


def add_interface_image(type: str = "system", name: str = "default") -> str:

    # registry = f"envds-registry:{get_registry_port()}"
    # registry = f"localhost:{get_registry_port()}"
    # repo = f"{type}/{app}"
    repo = f"envds/interface/{type.lower()}-{name.lower()}"

    iface_path = os.path.join("apps", "daq", "interfaces", type, name)

    print(f"repo: {repo}, iface_path: {iface_path}")
    # with open(f"./{inst_path}/VERSION", "r") as f:
    with open(os.path.join(".", iface_path, "VERSION"), "r") as f:
        tag = f.readline()
    # img = f"{registry}/{repo}:{tag}"
    img = f"{repo}:{tag}"

    # with open(f"./apps/daq/instruments/{make}/{model}/requirements_local.txt", "r") as req_file:
    with open(os.path.join(".", iface_path, "requirements_local.txt"), "r") as req_file:
        while req := req_file.readline():
            print("\tcopying wheel(s) to app library")
            src_path = os.path.join(req, "lib")
            dest_path = os.path.join(iface_path, "lib", req)
            print(f"{src_path}, {dest_path}")
            os.makedirs(dest_path, exist_ok=True)
            for f in os.listdir(src_path):
                if f.endswith(".whl"):
                    shutil.copyfile(
                        os.path.join(src_path, f), os.path.join(dest_path, f)
                    )
                    # os.remove(os.path.join(wheel_path, f))
    client = docker.from_env()

    print(f"Build {img}")
    # res = client.images.build(path=f"./apps/{inst}", tag=img)
    res = client.images.build(path=os.path.join(".", iface_path), tag=img)
    print(f"Build image result: {res}")

    register_image(img)

    # print(f"Push {img}")
    # res = client.images.push(img)
    # print(f"push image result: {res}")

    # print(client.images.list(registry))

def start(args):

    if args.envds_id:
        # switch context
        cluster_config = get_config("cluster", envds_id=args.envds_id)
        system_config = get_config("system", envds_id=args.envds_id)
        if cluster_config is None or system_config is None:
            print(f"No cluster with envds_id = {args.envds_id} found")
            return
        save_config(cluster_config, cfg_type="cluster")
        save_config(system_config, cfg_type="system")

    # k3d_args = ["k3d", "cluster", "start", "envds"]
    k3d_args = ["k3d", "cluster", "start", get_cluster_name()]

    res = subprocess.run(k3d_args, capture_output=True, text=True)
    print(f"result: {res.stdout}")
    print(f"errors: {res.stderr}")

    set_kubeconfig()


def stop():

    # k3d_args = ["k3d", "cluster", "stop", "envds"]
    k3d_args = ["k3d", "cluster", "stop", get_cluster_name()]

    res = subprocess.run(k3d_args, capture_output=True, text=True)
    print(f"result: {res.stdout}")
    print(f"errors: {res.stderr}")


def bootstrap_envds():

    try:
        res = subprocess.run(
            ["k3d", "cluster", "ls"], capture_output=True, check=True, text=True
        )
        print(res)
    except subprocess.CalledProcessError as e:
        print(f"error: {e}")

    # attributes = {
    #     "type": "com.example.sampletype1",
    #     "source": "https://example.com/event-producer",
    # }
    # data = {"message": "Hello World!"}
    # event = CloudEvent(attributes, data)
    # print(event)
    # headers, body = to_structured(event)
    # r = httpx.post("http://localhost:8000/api/v1/ce/apply", headers=headers, data=body)
    # exit()

    ns = "envds-system"
    print(get_kubeconfig())
    config.load_kube_config(config_file=get_kubeconfig())
    k8s_client = client.ApiClient()
    v1 = client.CoreV1Api()
    ns_list = v1.list_namespace()
    namespaces = [item.metadata.name for item in ns_list.items]
    # ns_list = k8s_client.list_namespace()
    print(namespaces)


def create_tls_secret(
    name: str, key: str = "ssl.key", cert: str = "ssl.crt", ns: str = "default"
):

    # use kubectl...easier for now

    config.load_kube_config(config_file=get_kubeconfig())
    k8s_client = client.ApiClient()

    # print(f"file: {args.file}, namespace: {args.namespace}")
    # print(k8s_client, apply_config)
    args = [
        "kubectl",
        "create",
        "secret",
        "tls",
        name,
        "--key",
        key,
        "--cert",
        cert,
        "-n",
        ns,
    ]
    try:
        # create_from_yaml(k8s_client,yaml_file=apply_config.file,namespace=apply_config.namespace,)
        print(f"***envds.create_tls_secret: {' '.join(args)}")
        res = subprocess.run(args, capture_output=True, text=True)
        print(f"result: {res.stdout}")
        print(f"errors: {res.stderr}")

    except Exception as e:
        print(e)


def apply(apply_config: ApplyConfig):

    # use kubectl...easier for now

    config.load_kube_config(config_file=get_kubeconfig())
    k8s_client = client.ApiClient()

    # print(f"file: {args.file}, namespace: {args.namespace}")
    # print(k8s_client, apply_config)
    args = [
        "kubectl",
        "apply",
        "-f",
        f"{apply_config.file}",
        # "-n",
        # f"{apply_config.namespace}",
    ]
    try:
        # create_from_yaml(k8s_client,yaml_file=apply_config.file,namespace=apply_config.namespace,)
        print(f"***envds.apply: {' '.join(args)}")
        res = subprocess.run(args, capture_output=True, text=True)
        print(f"result: {res.stdout}")
        print(f"errors: {res.stderr}")

    except Exception as e:
        print(e)

def delete(apply_config: ApplyConfig):

    # use kubectl...easier for now

    config.load_kube_config(config_file=get_kubeconfig())
    k8s_client = client.ApiClient()

    # print(f"file: {args.file}, namespace: {args.namespace}")
    # print(k8s_client, apply_config)
    args = [
        "kubectl",
        "delete",
        "-f",
        f"{apply_config.file}",
        # "-n",
        # f"{apply_config.namespace}",
    ]
    try:
        # create_from_yaml(k8s_client,yaml_file=apply_config.file,namespace=apply_config.namespace,)
        print(f"***envds.delete: {' '.join(args)}")
        res = subprocess.run(args, capture_output=True, text=True)
        print(f"result: {res.stdout}")
        print(f"errors: {res.stderr}")

    except Exception as e:
        print(e)


# def start_mqtt():
#     # args = [
#     #     "-f",
#     #     "dev/mqtt/mosquitto.yaml"
#     # ]

#     register_image("eclipse-mosquitto:2.0.14")

#     cwd = os.getcwd()
#     args = argparse.Namespace(file=f"{cwd}/k3d/dev/mqtt/mosquitto.yaml", namespace="default")
#     # print(args)
#     apply(args)


# def run(*args):
def run(args):

    global cluster_id
    cluster_id = "default"

    # parent parsers
    id_parent = argparse.ArgumentParser(add_help=False)
    id_parent.add_argument("-id", "--envds-id", type=str, help="envds-id")

    file_parent = argparse.ArgumentParser(add_help=False)
    file_parent.add_argument("-f", "--file", type=str, help="file")

    system_parent = argparse.ArgumentParser(add_help=False)
    system_parent.add_argument(
        "-dv",
        "--envds_data_volume",
        type=str,
        help="data volume",
        # default=(os.path.join(os.getcwd(), "data")),
    )
    system_parent.add_argument(
        "-crtdv",
        "--envds_certs_volume",
        type=str,
        help="certs volume",
        # default=(os.path.join(os.getcwd(), "data")),
    )
    system_parent.add_argument(
        "-cfgdv",
        "--envds_cfg_volume",
        type=str,
        help="config volume",
        # default=(os.path.join(os.getcwd(), "data")),
    )
    system_parent.add_argument(
        "-ho",
        "--host",
        type=str,
        help="host",
        # default=(os.path.join(os.getcwd(), "data")),
    )
    system_parent.add_argument(
        "-http",
        "--http_port",
        type=str,
        help="http port",
        # default=(os.path.join(os.getcwd(), "data")),
    )
    system_parent.add_argument(
        "-https",
        "--https_port",
        type=str,
        help="https port",
        # default=(os.path.join(os.getcwd(), "data")),
    )
    system_parent.add_argument(
        "-mqtt",
        "--mqtt_port",
        type=str,
        help="mqtt port",
        # default=(os.path.join(os.getcwd(), "data")),
    )
    system_parent.add_argument(
        "-mqtts",
        "--mqtts_port",
        type=str,
        help="mqtts port",
        # default=(os.path.join(os.getcwd(), "data")),
    )

    service_parent = argparse.ArgumentParser(add_help=False)
    service_parent.add_argument(
        "-s",
        "--service",
        type=str,
        help="service name",
    )
    # add_service_parser.add_argument("-s", "--service", type=str, help="service name")
    # # add_service_parser.add_argument("-t", "--type", type=str, help="service type")
    # add_service_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")

    sensor_parent = argparse.ArgumentParser(add_help=False)
    sensor_parent.add_argument(
        "-mk",
        "--make",
        type=str,
        help="sensor make",
    )
    sensor_parent.add_argument(
        "-md",
        "--model",
        type=str,
        help="sensor model",
    )
    sensor_parent.add_argument(
        "-sn",
        "--serial-number",
        type=str,
        help="sensor serial number",
    )
    sensor_parent.add_argument(
        "-t",
        "--type",
        type=str,
        help="sensor type",
    )
    sensor_parent.add_argument(
        "-daq",
        "--daq-id",
        type=str,
        help="daq-id",
    )
    # add_sensor_parser.add_argument("-mk", "--make", type=str, help="instrument make")
    # add_sensor_parser.add_argument("-md", "--model", type=str, help="instrument model")
    # add_sensor_parser.add_argument("-sn", "--serial_number", type=str, help="instrument serial number")
    # # add_instrument_parser.add_argument("-t", "--type", type=str, help="service type")
    # add_sensor_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")
    # add_sensor_parser.add_argument(
    #     "-daq",
    #     "--daq-id",
    #     type=str,
    #     help="daq id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    interface_parent = argparse.ArgumentParser(add_help=False)
    interface_parent.add_argument(
        "-t",
        "--type",
        type=str,
        help="interface type",
    )
    interface_parent.add_argument(
        "-n",
        "--name",
        type=str,
        help="interface name",
    )
    interface_parent.add_argument(
        "-u",
        "--uid",
        type=str,
        help="interface uid",
    )
    interface_parent.add_argument(
        "-daq",
        "--daq-id",
        type=str,
        help="interface daq-id",
    )
    # add_interface_parser.add_argument("-t", "--type", type=str, help="interface type")
    # add_interface_parser.add_argument("-n", "--name", type=str, help="interface name")
    # add_interface_parser.add_argument("-u", "--uid", type=str, help="instrument uid")
    # add_interface_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")
    # add_interface_parser.add_argument(
    #     "-daq",
    #     "--daq-id",
    #     type=str,
    #     help="daq id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    dataserver_parent = argparse.ArgumentParser(add_help=False)

    parser = argparse.ArgumentParser()

    command_sp = parser.add_subparsers(dest="command", help="sub-command help")

    create_parser = command_sp.add_parser("create", help="create command")
    create_target_sp = create_parser.add_subparsers(
        dest="target", help="create <target>"
    )
    create_system_parser = create_target_sp.add_parser(
        "system", parents=[id_parent, file_parent, system_parent]
    )
    create_service_parser = create_target_sp.add_parser(
        "service", parents=[id_parent, file_parent, service_parent]
    )
    create_sensor_parser = create_target_sp.add_parser(
        "sensor", parents=[id_parent, file_parent, sensor_parent]
    )
    create_interface_parser = create_target_sp.add_parser(
        "interface", parents=[id_parent, file_parent, interface_parent]
    )
    create_dataserver_parser = create_target_sp.add_parser(
        "dataserver", parents=[id_parent, file_parent, dataserver_parent]
    )

    update_parser = command_sp.add_parser("update", help="update command")
    update_target_sp = update_parser.add_subparsers(
        dest="target", help="update <target>"
    )
    update_system_parser = update_target_sp.add_parser(
        "system", parents=[id_parent, file_parent]
    )
    update_service_parser = update_target_sp.add_parser(
        "service", parents=[id_parent, file_parent, service_parent]
    )
    update_sensor_parser = update_target_sp.add_parser(
        "sensor", parents=[id_parent, file_parent, sensor_parent]
    )
    update_interface_parser = update_target_sp.add_parser(
        "interface", parents=[id_parent, file_parent, interface_parent]
    )
    update_dataserver_parser = update_target_sp.add_parser(
        "dataserver", parents=[id_parent, file_parent, dataserver_parent]
    )


    delete_parser = command_sp.add_parser("delete", help="delete command")
    delete_target_sp = delete_parser.add_subparsers(
        dest="target", help="delete <target>"
    )
    delete_system_parser = delete_target_sp.add_parser("system", parents=[id_parent])

    # run options
    startup_parser = command_sp.add_parser("startup", help="operations: startup command")
    startup_target_sp = startup_parser.add_subparsers(
        dest="target", help="startup <target>"
    )
    # startup_system_parser = startup_target_sp.add_parser(
    #     "system", parents=[id_parent, file_parent, system_parent]
    # )
    startup_services_parser = startup_target_sp.add_parser(
        "services", parents=[id_parent, file_parent] #, service_parent]
    )
    startup_dataserver_parser = startup_target_sp.add_parser(
        "dataserver", parents=[id_parent, file_parent] #, dataserver_parent]
    )
    startup_interfaces_parser = startup_target_sp.add_parser(
        "interfaces", parents=[id_parent, file_parent] #, interface_parent]
    )
    startup_sensors_parser = startup_target_sp.add_parser(
        "sensors", parents=[id_parent, file_parent] #, sensor_parent]
    )

    shutdown_parser = command_sp.add_parser("shutdown", help="operations: shutdown command")
    shutdown_target_sp = shutdown_parser.add_subparsers(
        dest="target", help="shutdown <target>"
    )
    # shutdown_system_parser = shutdown_target_sp.add_parser(
    #     "system", parents=[id_parent, file_parent, system_parent]
    # )
    shutdown_services_parser = shutdown_target_sp.add_parser(
        "services", parents=[id_parent, file_parent] #, service_parent]
    )
    shutdown_dataserver_parser = shutdown_target_sp.add_parser(
        "dataserver", parents=[id_parent, file_parent] #, dataserver_parent]
    )
    shutdown_interfaces_parser = shutdown_target_sp.add_parser(
        "interfaces", parents=[id_parent, file_parent] #, interface_parent]
    )
    shutdown_sensors_parser = shutdown_target_sp.add_parser(
        "sensors", parents=[id_parent, file_parent] #, sensor_parent]
    )



    # subparsers = parser.add_subparsers(dest="command", help="sub-command help")
    # init_parser = subparsers.add_parser("init", help="init envds instance")
    # init_parser.add_argument(
    #     "-dv",
    #     "--envds_data_volume",
    #     type=str,
    #     help="data volume",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # init_parser.add_argument(
    #     "-crtdv",
    #     "--envds_certs_volume",
    #     type=str,
    #     help="certs volume",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # init_parser.add_argument(
    #     "-cfgdv",
    #     "--envds_cfg_volume",
    #     type=str,
    #     help="config volume",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # init_parser.add_argument(
    #     "-ho",
    #     "--host",
    #     type=str,
    #     help="host",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # init_parser.add_argument(
    #     "-http",
    #     "--http_port",
    #     type=str,
    #     help="http port",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # init_parser.add_argument(
    #     "-https",
    #     "--https_port",
    #     type=str,
    #     help="https port",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # init_parser.add_argument(
    #     "-mqtt",
    #     "--mqtt_port",
    #     type=str,
    #     help="mqtt port",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # init_parser.add_argument(
    #     "-mqtts",
    #     "--mqtts_port",
    #     type=str,
    #     help="mqtts port",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    # init_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    # # init_parser.set_defaults(command="init")
    # start_parser = subparsers.add_parser(
    #     "start", help="start initialized envds instance"
    # )
    # start_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # stop_parser = subparsers.add_parser("stop", help="stop envds instance")
    # reg_parser = subparsers.add_parser(
    #     "register-image", help="register image with local registry"
    # )
    # reg_parser.add_argument(
    #     "-i", "--image", type=str, help="name of image to register", required=True
    # )

    # reg_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    # apply_parser = subparsers.add_parser("apply", help="apply yaml configuration file")
    # apply_parser.add_argument("-f", "--file", type=str, help="yaml config file")
    # apply_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")
    # # apply_parser.set_defaults(command="apply")
    # apply_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    # add_service_parser = subparsers.add_parser("add-service", help="add service")
    # add_service_parser.add_argument("-s", "--service", type=str, help="service name")
    # # add_service_parser.add_argument("-t", "--type", type=str, help="service type")
    # add_service_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")
    # add_service_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    # add_sensor_parser = subparsers.add_parser("add-sensor", help="add sensor")
    # add_sensor_parser.add_argument("-mk", "--make", type=str, help="instrument make")
    # add_sensor_parser.add_argument("-md", "--model", type=str, help="instrument model")
    # add_sensor_parser.add_argument("-sn", "--serial_number", type=str, help="instrument serial number")
    # # add_instrument_parser.add_argument("-t", "--type", type=str, help="service type")
    # add_sensor_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")
    # add_sensor_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # add_sensor_parser.add_argument(
    #     "-daq",
    #     "--daq-id",
    #     type=str,
    #     help="daq id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    # add_interface_parser = subparsers.add_parser("add-interface", help="add interface")
    # add_interface_parser.add_argument("-t", "--type", type=str, help="interface type")
    # add_interface_parser.add_argument("-n", "--name", type=str, help="interface name")
    # add_interface_parser.add_argument("-u", "--uid", type=str, help="instrument uid")
    # # add_instrument_parser.add_argument("-t", "--type", type=str, help="service type")
    # add_interface_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")
    # add_interface_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # add_interface_parser.add_argument(
    #     "-daq",
    #     "--daq-id",
    #     type=str,
    #     help="daq id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )

    # add_dataserver_parser = subparsers.add_parser("add-dataserver", help="add dataserver")
    # # add_interface_parser.add_argument("-t", "--type", type=str, help="interface type")
    # # add_interface_parser.add_argument("-n", "--name", type=str, help="interface name")
    # # add_interface_parser.add_argument("-u", "--uid", type=str, help="instrument uid")
    # # add_instrument_parser.add_argument("-t", "--type", type=str, help="service type")
    # add_dataserver_parser.add_argument("-ns", "--namespace", type=str, help="apply to namespace")
    # add_dataserver_parser.add_argument(
    #     "-id",
    #     "--envds-id",
    #     type=str,
    #     help="envds id",
    #     # default=(os.path.join(os.getcwd(), "data")),
    # )
    # # add_interface_parser.add_argument(
    # #     "-daq",
    # #     "--daq-id",
    # #     type=str,
    # #     help="daq id",
    # #     # default=(os.path.join(os.getcwd(), "data")),
    # # )

    # cl_args = parser.parse_args()
    cl_args = parser.parse_args()
    print(cl_args)
    print(cl_args.command)

    # wd = os.getcwd()
    # os.chdir("..")
    # print(wd, os.getcwd())

    if cl_args.envds_id:
        cluster_id = cl_args.envds_id

    if cl_args.command == "create":

        if cl_args.target == "system":
            if create_cluster(cl_args):
                print("cluster created")
                create_envds()
                
        elif cl_args.target == "service":
            create_service(service=cl_args.service)

        elif cl_args.target == "sensor":
            create_sensor(make=cl_args.make, model=cl_args.model, serial_number=cl_args.serial_number)

        elif cl_args.target == "interface":
            create_interface(type=cl_args.type, name=cl_args.name, uid=cl_args.uid)

        elif cl_args.target == "dataserver":
            create_dataserver()
            # pass

    elif cl_args.command == "update":

        if cl_args.target == "system":
            create_envds(update=True)
                
        elif cl_args.target == "service":
            create_service(service=cl_args.service)

        elif cl_args.target == "sensor":
            create_sensor(make=cl_args.make, model=cl_args.model, serial_number=cl_args.serial_number)

        elif cl_args.target == "interface":
            create_interface(type=cl_args.type, name=cl_args.name, uid=cl_args.uid)

        elif cl_args.target == "dataserver":
            create_dataserver()
            # pass
    elif cl_args.command == "startup":

        # if cl_args.target == "system":
        #     if create_cluster(cl_args):
        #         print("cluster created")
        #         create_envds()
                
        if cl_args.target == "services":
            print(cl_args.file)
            startup_services(services_file=cl_args.file)

        elif cl_args.target == "interfaces":
            startup_interfaces(interfaces_file=cl_args.file)

        elif cl_args.target == "sensors":
            startup_sensors(sensors_file=cl_args.file)

        # elif cl_args.target == "sensor":
        #     create_sensor(make=cl_args.make, model=cl_args.model, serial_number=cl_args.serial_number)

    elif cl_args.command == "shutdown":

        # if cl_args.target == "system":
        #     if create_cluster(cl_args):
        #         print("cluster created")
        #         create_envds()
                
        if cl_args.target == "services":
            print(cl_args.file)
            shutdown_services(services_file=cl_args.file)

        elif cl_args.target == "interfaces":
            shutdown_interfaces(interfaces_file=cl_args.file)

        elif cl_args.target == "sensors":
            shutdown_sensors(sensors_file=cl_args.file)

        # elif cl_args.target == "dataserver":
        #     create_dataserver()
            # pass

    # elif cl_args.command == "init":
    #     if create_cluster(cl_args):
    #         init_envds()
    #         # build_core_packages()
    #         # init_message_bus()
    #         # build_core_services()
    #         # build_envds_package()
    #         # build_core_image(pkg="envds")
    #         pass
    #     # start_mqtt()
    # # elif cl_args.command == "start":
    # #     init(cl_args)

    # elif cl_args.command == "start":
    #     start(cl_args)

    # elif cl_args.command == "stop":
    #     stop()

    # elif cl_args.command == "register-image":
    #     register_image(cl_args.image)

    # elif cl_args.command == "add-service":
    #     # add_service(service=cl_args.service, type=cl_args.type)
    #     add_service(service=cl_args.service)

    # elif cl_args.command == "add-sensor":
    #     # add_service(service=cl_args.service, type=cl_args.type)
    #     add_sensor(make=cl_args.make, model=cl_args.model, serial_number=cl_args.serial_number)

    # elif cl_args.command == "add-interface":
    #     # add_service(service=cl_args.service, type=cl_args.type)
    #     add_interface(type=cl_args.type, name=cl_args.name, uid=cl_args.uid)

    # elif cl_args.command == "add-dataserver":
    #     # add_service(service=cl_args.service, type=cl_args.type)
    #     add_dataserver(cl_args)

    # elif cl_args.command == "apply":
    #     if cl_args.file is None:
    #         return

    #     cfg = ApplyConfig(file=cl_args.file)
    #     cfg.file = cl_args.file

    #     if args.namespace:
    #         cfg.namespace = cl_args.namespace

    #     apply(cfg)

    # os.chdir(wd)

    # client = docker.from_env()

    # # client.networks.create("cloudysky")
    # # client.swarm.leave(force=True)
    # # client.swarm.init()
    # # client.swarm.leave(force=True)
    # # clist = client.containers.list()
    # # for c in clist:
    # #     print(c.attrs)
    # config_vol = "/home/derek/Software/python/envDS/tmp_docker/mosquitto_tmp.conf:/mosquitto/config/mosquitto.conf"

    # config = client.configs.get("mosquitto-conf")
    # print(config.attrs)
    # # container_spec = docker.

    # # )

    # mqtt_conf = docker.types.ConfigReference(config_id=config.attrs["ID"],
    #     config_name="mosquitto-conf",
    #     filename="/mosquitto/config/mosquitto.conf"
    # )

    # endpoint_spec = docker.types.EndpointSpec(
    #     ports={1885: (1883, "TCP", "host")}
    # )

    # container_spec = docker.types.ContainerSpec(
    #     image = "eclipse-mosquitto:2.0.14",
    #     configs=[mqtt_conf],
    #     labels={"envds.namespace": "envds-system"}

    # )

    # task_tmpl = docker.types.TaskTemplate(
    #     container_spec=container_spec,
    #     restart_policy=docker.types.RestartPolicy(condition="on-failure")
    # )
    # client.services.create(
    #     # task_template=task_tmpl,
    #     image="eclipse-mosquitto:2.0.14",
    #     # task_template=task_tmpl,
    #     name="mosquitto3",
    #     configs=[mqtt_conf],
    #     endpoint_spec=endpoint_spec,
    #     restart_policy=docker.types.RestartPolicy(condition="on-failure"),
    #     # labels={"envds.namespace": "envds-system"}
    #     labels={"envds.namespace": "envds-system"}
    # )

    # services = client.services.list()
    # for service in services:
    #     print(service.attrs)
    # mqtt_config = client.configs.create(name="mosquitto-config", )
    # client.containers.run(
    #     "eclipse-mosquitto:2.0.14",
    #     name="envds-test1",
    #     network="cloudysky",
    #     ports={"1883/tcp": 1883},
    #     volumes=[config_vol],
    #     restart_policy={"Name": "on-failure"},
    #     detach=True
    # )

    # client.containers.run(
    #     "eclipse-mosquitto:2.0.14",
    #     name="envds-test2",
    #     # network="envds_cloudysky",
    #     ports={"1883/tcp": 1884},
    #     volumes=[config_vol],
    #     restart_policy={"Name": "on-failure"},
    #     labels={"com.docker.compose.project": "test-project"},
    #     detach=True
    # )

    # client.containers.run(
    #     "eclipse-mosquitto:2.0.14",
    #     name="envds-test3",
    #     network="cloudysky",
    #     ports={"1883/tcp": 1885},
    #     volumes=[config_vol],
    #     restart_policy={"Name": "on-failure"},
    #     detach=True
    # )


if __name__ == "__main__":

    print(f"args: {sys.argv[1:]}")

    # print(sys.argv[2])
    # cfg_file = os.path.join(os.getcwd(),sys.argv[2])
    # print(cfg_file)
    # stream = open(cfg_file, 'r')
    # dictionary = yaml.safe_load(stream)
    # print(dictionary)
    # exit(1)

    # change working directory to base of distribution
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # print(BASE_DIR)
    os.chdir(BASE_DIR)

    run(sys.argv)
    # parser = argparse.ArgumentParser()
    # # parser.add_argument("init", help="init envds instance")
    # # parser.add_argument('-f', '--file', help="")
    # subparsers = parser.add_subparsers(help="sub-command help")
    # init_parser = subparsers.add_parser("init", help="init envds instance")
    # apply_parser = subparsers.add_parser('apply', help='apply yaml configuration file')
    # apply_parser.add_argument("-f", "--file", type=str, help="yaml config file")

    # cl_args = parser.parse_args()
    # print(cl_args)
    # if cl_args.init:
    #     print(cl_args.file)

    sys.exit()
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", help="set logging level")
    parser.add_argument(
        "-d", "--debug", help="show debugging output", action="store_true"
    )
    # parser.add_argument("-h", "--host", help="set api host address")
    # parser.add_argument("-p", "--port", help="set api port number")
    # parser.add_argument("-n", "--name", help="set DataSystem name")

    cl_args = parser.parse_args()
    # if cl_args.help:
    #     # print(args.help)
    #     exit()

    log_level = logging.DEBUG
    if cl_args.log_level:
        level = cl_args.log_level
        if level == "WARN":
            log_level = logging.WARN
        elif level == "ERROR":
            log_level = logging.ERROR
        elif log_level == "DEBUG":
            log_level = logging.DEBUG
        elif log_level == "CRITICAL":
            log_level = logging.CRITICAL

    if cl_args.debug:
        log_level = logging.DEBUG

    # set path
    # BASE_DIR = os.path.dirname(
    #     os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # )
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    from envds.util.util import get_datetime, get_datetime_string, get_datetime_format

    asyncio.run(run())
    sys.exit()
    # from envds.envds.envds import DataSystemManager
    from envds.system.envds import DataSystem

    # from envds.message.message import Message
    from envds.util.util import get_datetime, get_datetime_string, get_datetime_format

    # from managers.hardware_manager import HardwareManager
    # from envds.eventdata.eventdata import EventData
    # from envds.eventdata.broker.broker import MQTTBroker

    # configure logging to stdout
    isofmt = "%Y-%m-%dT%H:%M:%SZ"
    # isofmt = get_datetime_format(fraction=True)
    root_logger = logging.getLogger()
    # root_logger.setLevel(logging.DEBUG)
    root_logger.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=isofmt
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    event_loop = asyncio.get_event_loop()

    envds_config = {
        "apiVersion": "envds/v1",
        "kind": "DataSystem",
        "metadata": {
            "name": "who-daq",  # <- this has to be unique name in namespace
            "namespace": "envds",
        },
        "spec": {
            # "class": {
            #     "module": "envds.daq.daq",
            #     "class":  "DAQSystem"
            # },
            "broker": {  # <- insert full broker spec here. will be done if omitted
                "apiVersion": "envds/v1",
                "kind": "envdsBroker",
                "metadata": {
                    "name": "default",
                    # "namespace": "envds" # will pick up default
                },
                "spec": {
                    "type": "MQTT",
                    "host": "localhost",
                    "port": 1883,
                    "protocol": "TCP",
                },
            }
        },
    }

    broker_config = {
        "apiVersion": "envds/v1",
        "kind": "envdsBroker",
        "metadata": {
            "name": "default",
            # "namespace": "envds" # will pick up default
        },
        "spec": {"type": "MQTT", "host": "localhost", "port": 1883, "protocol": "TCP"},
    }

    reg_config = {
        "apiVersion": "envds/v1",
        "kind": "Registry",
        "metadata": {
            "name": "who-daq",  # <- this has to be unique name in namespace
            # "namespace": "acg-test",
            # "part-of": {"kind": "DataSystem", "name": "who-daq"},
        },
        "spec": {
            "class": {"module": "envds.registry.registry", "class": "envdsRegistry"},
        },
    }

    datamanager_config = {
        "apiVersion": "envds/v1",
        "kind": "DataManager",
        "metadata": {
            "name": "who-daq",  # <- this has to be unique name in namespace
            # "namespace": "acg-test",
            # "part-of": {"kind": "DataSystem", "name": "who-daq"},
        },
        "spec": {
            "class": {"module": "envds.data.data", "class": "envdsDataManager"},
            "basePath": "/home/Data/envDS/",
            "save-to-file": True,
            # "meta-data": ??,
            # "data-server": ??,
        },
    }

    daq_config = {
        "apiVersion": "envds/v1",
        "kind": "DAQSystem",
        "metadata": {
            "name": "daq-test",  # <- this has to be unique name in namespace
            "namespace": "acg-test",
            # "part-of": {"kind": "DataSystem", "name": "who-daq"},
        },
        "spec": {
            "class": {"module": "envds.daq.daq", "class": "DAQSystem"},
            # "broker": { # <- insert full broker spec here. will be done if omitted
            #     "apiVersion": "envds/v1",
            #     "kind": "envdsBroker",
            #     "metadata": {
            #         "name": "default",
            #         # "namespace": "envds" # will pick up default
            #     },
            #     "spec": {
            #         "type": "MQTT",
            #         "host": "localhost",
            #         "port": 1883,
            #         "protocol": "TCP"
            #     }
            # }
        },
    }

    controller_config = {
        "apiVersion": "envds/v1",
        "kind": "DAQController",
        "metadata": {
            "name": "controller-test",  # <- this has to be unique name in namespace
            "namespace": "acg-test",
            "labels": {
                "part-of": {
                    "kind": "DAQSystem",
                    "name": "daq-test",  # does this need to ref type (e.g., DAQSystem)?
                }
            },
        },
        "spec": {"class": {"module": "envds.daq.daq", "class": "DAQController"}},
    }

    dummy_instrument_config = {
        "apiVersion": "envds/v1",
        "kind": "DAQInstrument",
        "metadata": {
            "name": "dummy1",  # <- this will be changed in instrument class
            "serial-number": "1234",
            "namespace": "acg-test",
            "labels": {
                "part-of": {
                    "kind": "DAQController",
                    "name": "controller-test",  # does this need to ref type (e.g., DAQSystem)?
                }
            },
        },
        "spec": {
            "class": {"module": "envds.daq.instrument", "class": "DummyInstrument"},
            "controls": None,  # override control start up defaults
            "connections": None,  # map of interface connections
        },
    }

    envds_config_other = [
        # { # envds namespace
        #     "apiVersion": "envds/v1",
        #     "kind": "Namespace",
        #     "metadata": {
        #         "name": "envds"
        #     }
        # },
        {  # message broker
            "apiVersion": "envds/v1",
            "kind": "envdsBroker",
            "metadata": {
                "name": "default",
                # "namespace": "envds" # will pick up default
            },
            "spec": {
                "type": "MQTT",
                "host": "localhost",
                "ports": [{"name": "mqtt", "port": 1883, "protocol": "TCP"}],
            },
        },
        {
            "apiVersion": "envds/v1",
            "kind": "envdsBrokerClient",
            "metadata": {
                "name": "mqtt-client",
                "instance": "mqtt-client-system",
                "namespace": "envds",
                "labels": {"part-of": "envds.sys"},
            },
            "spec": {
                "class": {
                    "module": "envds.message.message",
                    "class": "MQTTBrokerClient",
                }
            },
        },
    ]

    config = {
        # "namespace": "gov.noaa.pmel.acg",
        "message_broker": {
            "name": "mqtt-broker",
            "client": {
                "instance": {
                    "module": "envds.message.message",
                    "class": "MQTTBrokerClient",
                }
            },
            "config": {
                "host": "localhost",
                "port": 1883,
                # "keepalive": 60,
                "ssl_context": None,
                # "ssl_client_cert": None,
                # ne
            },
        },
        "services": {
            "daq_test": {
                "type": "service",
                "name": "daq-test",
                "namespace": "acg",
                "instance": {
                    "module": "envds.daq.daq",
                    "class": "DAQSystem",
                },
                "part-of": "envds.system",
            }
        },
    }

    # config = {
    #     # "namespace": "gov.noaa.pmel.acg",
    #     "message_broker": {
    #         "name": "mqtt-broker"
    #         "client": {
    #             "instance": {
    #                 "module": "envds.message.message",
    #                 "class": "MQTTBrokerClient",
    #             }
    #         },
    #         "config": {
    #             "host": "localhost",
    #             "port": 1883,
    #             # "keepalive": 60,
    #             "ssl_context": None,
    #             # "ssl_client_cert": None,
    #             # ne
    #         },
    #     },
    #     "required-services": {
    #         "registry": {
    #             "apiVersion": "evnds/v1",
    #             "kind": "service",
    #             "metadata": {
    #                 "name": "registry"
    #             }
    #             "spec": {
    #                 "template": {
    #                     "spec": {
    #                         "instance": {
    #                             "module": "envds.registry.registry",
    #                             "class": "envdsRegistry",
    #                         }
    #                     }
    #                 }
    #             }
    #         }
    #     }

    #     "services": {
    #         "daq-test": {
    #             "apiVersion": "evnds/v1",
    #             "kind": "service",
    #             "metadata": {
    #                 "name": "daq-test"
    #             }
    #             "spec": {
    #                 "template": {
    #                     "spec": {
    #                         "instance": {
    #                             "module": "envds.daq.daq",
    #                             "class": "DAQSystem",
    #                         }
    #                     }
    #                 }
    #             }
    #             "type": "service",
    #             "name": "daq-test",
    #             "namespace": "acg",
    #             "instance": {
    #                 "module": "envds.daq.daq",
    #                 "class": "DAQSystem",
    #             },
    #             "part-of": "envds.system",
    #         }
    #     }
    # }

    # add services

    # daq_config = {
    #     "type": "service",
    #     "name": "daq-test",
    #     "namespace": "acg",
    #     "instance": {"module": "envds.daq", "class": "DAQSystem",},
    #     "part-of": "envds.system",
    # }

    # add services

    # daq_config = {
    #     "type": "service",
    #     "name": "daq-test",
    #     "namespace": "acg",
    #     "instance": {"module": "envds.daq", "class": "DAQSystem",},
    #     "part-of": "envds.system",
    # }

    # services =
    #     [
    #         {
    #             "type": "service",
    #             "name": "datamanager",
    #             "namespace": "acg",
    #             "instance": {
    #                 "module": "envds.datamanager.datamanager",
    #                 "class": "envdsDataManager",
    #             },
    #         },
    #         {
    #             "type": "service",
    #             "name": "testdaq",
    #             "namespace": "acg",
    #             "instance": {"module": "envds.daq", "class": "envdsDAQ"},
    #         },
    #     ]

    example = {
        "apiVersion": "envds/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "daq-main",
            "namespace": "acg",
            "labels": {
                "app": "daqmanager",
                # "role": "type of role", # used if replicas>1?
                # "tier": "backend"
            },
        },
        "spec": {  # specification or desired state of object
            # "replicas": 1 # unneeded for our app
            # "selector": { # used if replicas>1?
            #     "matchLabels": {
            #         "app": "daq-manager"
            #     }
            # }
            "template": {  # how to create the object
                "metadata": {"labels": {"app": "daqmanager"}},
                "spec": {
                    # if using containers, this would be "container"
                    # "containers": [
                    #     {
                    #         "name": "container name"
                    #     }
                    # ]
                    # for envds - no sidecars
                    "envdsApp": {
                        "module": "envds.daq",
                        "class": "DAQSystem",
                        "resources": {},
                        "ports": [],
                    }
                },
            }
        },
    }

    # from https://kubernetes.io/docs/tutorials/stateless-application/guestbook/
    kub_deployment_example = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "redis-leader",
            "labels": {"app": "redis", "role": "leader", "tier": "backend"},
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "redis"}},
            "template": {
                "metadata": {
                    "labels": {"app": "redis", "role": "leader", "tier": "backend"}
                },
                "spec": {
                    "containers": [  # allows for sidecar containers
                        {
                            "name": "leader",
                            "image": "docker.io/redis:6.0.5",
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "100Mi"}
                            },
                            "ports": [{"containerPort": 6379}],
                        }
                    ]
                },
            },
        },
    }

    kub_service_example = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "redis-leader",
            "labels": {"app": "redis", "role": "leader", "tier": "backend"},
        },
        "spec": {
            "ports": [{"port": 6379, "targetPort": 6379}],
            "selector": {"app": "redis", "role": "leader", "tier": "backend"},
        },
    }

    kub_fe_deployment_example = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "frontend"},
        "spec": {
            "replicas": 3,
            "selector": {"matchLabels": {"app": "guestbook", "tier": "frontend"}},
            "template": {
                "metadata": {"labels": {"app": "guestbook", "tier": "frontend"}},
                "spec": {
                    "containers": [
                        {
                            "name": "php-redis",
                            "image": "gcr.io/google_samples/gb-frontend:v5",
                            "env": [{"name": "GET_HOSTS_FROM", "value": "dns"}],
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "100Mi"}
                            },
                            "ports": [{"containerPort": 80}],
                        }
                    ]
                },
            },
        },
    }

    # envds = DataSystemManager(config=config)
    # envds = DataSystem(config=broker_config)
    envds = DataSystem(config=envds_config)
    envds.apply_nowait(config=daq_config)
    envds.apply_nowait(config=datamanager_config)
    envds.apply_nowait(config=controller_config)
    # envds.apply_nowait(config=controller_config)
    # create the DAQManager
    # daq_manager = DAQManager().configure(config=config)
    # if namespace is specified
    # daq_manager.set_namespace("junge")
    # daq_manager.set_msg_broker()
    # daq_manager.start()

    # task = event_loop.create_task(daq_manager.run())
    # task_list = asyncio.all_tasks(loop=event_loop)

    event_loop.add_signal_handler(signal.SIGINT, envds.request_shutdown)
    event_loop.add_signal_handler(signal.SIGTERM, envds.request_shutdown)

    event_loop.run_until_complete(envds.run())

    # try:
    #     event_loop.run_until_complete(daq_manager.run())
    # except KeyboardInterrupt:
    #     root_logger.info("Shutdown requested")
    #     event_loop.run_until_complete(daq_manager.shutdown())
    #     event_loop.run_forever()

    # finally:
    #     root_logger.info("Closing event loop")
    #     event_loop.close()

    # # from daq.manager.sys_manager import SysManager
    # # from daq.controller.controller import ControllerFactory  # , Controller
    # # from client.wsclient import WSClient
    # # import shared.utilities.util as util
    # # from shared.data.message import Message
    # # from shared.data.status import Status
    # # from shared.data.namespace import Namespace

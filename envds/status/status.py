import asyncio
import json
import logging
from envds.util.util import (
    get_datetime,
    get_datetime_string,
    datetime_mod_sec,
    time_to_next,
)


class StatusEvent:
    # def __init__(self) -> None:
    #     pass

    def create(
        type: str,
        state: str,
        status: str = None,
        # wait_for: bool = False,
        ready_status: str = None,
    ):
        if type is None or state is None:
            return None
        if status is None:
            status = Status.UNKNOWN
        # if wait_for:
        #     if not success_status:
        #         success_status = Status.OK

        event = {
            "time": get_datetime_string(),
            "type": type,
            "state": state,
            "status": status,
            "ready-status": ready_status,
        }
        # if "wait_for":
        #     event["success-status"] = success_status

        return event


class StatusMonitor:
    def __init__(self, status=None) -> None:

        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.health_requirements = [Status.TYPE_CREATE, Status.TYPE_RUN]

        if status is None:
            self.status = Status()

        self.loop.create_task(self.monitor_health())

    def get_status(self):
        return self.status

    def add_health_requirement(self, type: str):
        if type not in self.health_requirements:
            self.health_requirements.append(type)

    def remove_health_requirement(self, type: str):
        if type in self.health_requirements:
            self.health_requirements.remove(type)

    async def monitor_health(self):
        """
        Loop to monitor health of status/object
        """

        while True:

            status_map = self.status.status_map
            for type_name, type in status_map.items():
                if type_name in ["health", "last-update-time", "current-time"]:
                    continue

                for state_name, state in type.items():
                    if state_name == "ready":
                        continue

                    if (
                        "ready-status" in state
                        and state["status"] == state["ready-status"]
                    ):
                        type["ready"]["status"] = True
                    else:
                        type["ready"]["status"] = False
                        self.logger.debug(
                            "%s[%s][%s] not ready.", type_name, state_name, state
                        )
                        break

            ready_res = []
            for type in self.health_requirements:
                ready_res.append(self.status.ready(type=type))
            status_map["health"]["ready"]["status"] = all(ready_res)
            # print(all(ready_res))

            await asyncio.sleep(1)


class Status:
    """
    Class to hold status/state of objects. Contains functions to monitor and
    update status based on conditions.
    Status:
        type: type of status (e.g., run, health, sampling)
        state: entry label for a give state of a type (e.g., ready, )
        value: value of state
    """

    # types
    TYPE_CREATE = "create"
    TYPE_RUN = "run"
    TYPE_HEALTH = "health"
    TYPE_REGISTRATION = "registration"
    TYPE_SHUTDOWN = "shutdown"

    # states (default)
    STATE_READY = "ready"
    STATE_RUNSTATE = "run-state"
    STATE_REGISTERED = "registered"
    STATE_SHUTDOWN = "shutdown-state"

    # status
    UNKNOWN = "unknown"
    OK = "ok"
    NOTOK = "notok"
    REGISTERING = "registering"
    REGISTERED = "registered"
    DEREGISTERING = "deregistering"
    NOTREGISTERED = "notregistered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    SHUTTINGDOWN = "shuttingdown"
    SHUTDOWN = "shutdown"
    CREATING = "creating"
    CREATED = "created"
    ENABLING = "enabling"
    ENABLED = "enabled"
    DISABLING = "disabling"
    DISABLED = "disabled"

    def __init__(self) -> None:

        # self.status_map = {
        #     # required groups
        #     "create": {"ready": {"status": False}},
        #     "run": {"ready": {"status": False}},  # , "state": Status.UNKNOWN},
        #     "health": {"ready": {"status": False}},
        #     "shutdown": {"ready": {"status": False}},
        # }
        self.status_map = dict()
        self.add_type_state(Status.TYPE_CREATE, Status.STATE_READY)
        self.add_type_state(Status.TYPE_RUN, Status.STATE_READY)
        self.add_type_state(Status.TYPE_HEALTH, Status.STATE_READY)
        self.add_type_state(Status.TYPE_SHUTDOWN, Status.STATE_READY)

        # # add registration status entry
        # self.update_status(
        #     Status.TYPE_REGISTRATION,
        #     Status.STATE_REGISTERED,
        #     status=Status.UNKNOWN,
        # )

    def event(self, event, **kwargs):
        self.handle_event(event, **kwargs)

    def handle_event(self, event, **kwargs):
        # status event can create a condition to monitor for interim steps
        if not event:
            return

        ready_status = None
        # if event["wait-for"]:
        #     ready_status = event["success-status"]
        self.update_status(
            event["type"],
            event["state"],
            status=event["status"],
            ready_status=event["ready-status"]
            # ready_status = event["ready_status"],
        )

        # self.add_type(event["type"])
        # self.add_type_state(type=event["type"], state=event["state"])

        # ready_status = None
        # if event["wait-for"]:
        #     ready_status = event["success-status"]

        # self.update_status(
        #     event["type"],
        #     event["state"],
        #     status=event["status"],
        #     ready_state=ready_status,
        # )

    def add_type(self, type: str, include_ready=True, update=False) -> None:
        if type:
            if type not in self.status_map or update:
                self.status_map[type] = dict()
                if include_ready:
                    self.status_map[type]["ready"] = {
                        "status": False,
                        "ready-status": None,
                    }

    def add_type_state(
        self,
        type: str,
        state: str,
        status=UNKNOWN,
        ready_status: str = None,
        update=False,
    ) -> None:
        if type is not None and state is not None:
            self.add_type(type)
            if state not in self.status_map[type]:
                self.status_map[type][state] = {"status": status}
            if ready_status is not None:
                self.status_map[type][state]["ready-status"] = ready_status

    def update_status(
        self, type: str, state: str, status=None, ready_status=None
    ) -> None:
        self.add_type(type)
        self.add_type_state(type, state, status=status, ready_status=ready_status)
        if status is not None:
            self.status_map[type][state]["status"] = status
        if ready_status is not None:
            self.status_map[type][state]["ready-status"] = ready_status
        self.status_map["last-update-time"] = get_datetime_string()
        self.status_map["current-time"] = get_datetime_string()

    def ready(self, type: str = "health") -> bool:
        if "ready" in self.status_map[type]:
            return self.status_map[type]["ready"]["status"]
        return False

    def get_current_status(self, type: str = "health", state: str = "ready") -> str:
        try:
            current = self.status_map[type][state]["status"]
            return current
        except KeyError:
            return Status.UNKNOWN

    def to_dict(self) -> dict:
        self.status_map["current-time"] = get_datetime_string()
        return self.status_map

    def to_json(self):
        try:
            return json.dumps(self.to_dict())
        except TypeError:
            return None


async def run(status):

    status = status

    do_run = True
    cnt = 0
    while do_run:
        if cnt == 1:
            event = StatusEvent.create(
                type=Status.TYPE_CREATE,
                state="message_client_created",
                status=False,
                ready_status=True
                # type=Status.TYPE_CREATE, state="test_state", status=True
            )
            status.event(event)

        if cnt == 3:
            event = StatusEvent.create(
                type=Status.TYPE_RUN, state=Status.STATE_READY, status=True
            )
            status.event(event)
        if cnt == 5:
            event = StatusEvent.create(
                type=Status.TYPE_CREATE,
                state="message_client_created",
                status=True
                # type=Status.TYPE_CREATE, state="test_state", status=True
            )
            status.event(event)
        if cnt > 10:
            do_run = False

        print(f"{cnt}-health: {status.ready()}")
        await asyncio.sleep(1)
        cnt += 1

    # for task in asyncio.gather():
    #     task.cancel()
    # return


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    monitor = StatusMonitor()
    status = monitor.get_status()
    loop.run_until_complete(run(status))


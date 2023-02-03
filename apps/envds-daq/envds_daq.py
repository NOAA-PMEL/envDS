import asyncio
import uvicorn
from uvicorn.config import LOGGING_CONFIG
import sys
import os
import logging
from logfmter import Logfmter
import logging.config
from pydantic import BaseSettings, Field
from envds.core import envdsBase, envdsLogger
from envds.util.util import get_datetime_format

# from typing import Union

from pydantic import BaseModel

task_list = []


class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


async def test_task():
    while True:
        await asyncio.sleep(1)
        print("daq test_task...")
        logger = logging.getLogger("envds.info")
        logger.info("test_task", extra={"test": "daq task"})


async def shutdown():
    print("shutting down")
    for task in task_list:
        print(f"cancel: {task}")
        task.cancel()


async def main(server_config: ServerConfig = None):
    # uiconfig = UIConfig(**config)
    if server_config is None:
        server_config = ServerConfig()
    print(server_config)

    print("starting daq test task")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    # # print(LOGGING_CONFIG)
    # dict_config = {
    #     "version": 1,
    #     "disable_existing_loggers": False,
    #     "formatters": {
    #         "logfmt": {
    #             "()": "logfmter.Logfmter",
    #             "keys": ["at", "when", "name"],
    #             "mapping": {"at": "levelname", "when": "asctime"},
    #             "datefmt": get_datetime_format(),
    #         },
    #         "access": {
    #             "()": "uvicorn.logging.AccessFormatter",
    #             "fmt": '%(levelprefix)s %(asctime)s :: %(client_addr)s - "%(request_line)s" %(status_code)s',
    #             "use_colors": True,
    #         },
    #     },
    #     "handlers": {
    #         "console": {"class": "logging.StreamHandler", "formatter": "logfmt"},
    #         "access": {
    #             "formatter": "access",
    #             "class": "logging.StreamHandler",
    #             "stream": "ext://sys.stdout",
    #         },
    #     },
    #     "loggers": {
    #         "": {"handlers": ["console"], "level": "INFO"},
    #         "uvicorn.access": {
    #             "handlers": ["access"],
    #             "level": "INFO",
    #             "propagate": False,
    #         },
    #     },
    # }
    # logging.config.dictConfig(dict_config)

    envdsLogger().init_logger()
    logger = logging.getLogger("envds-daq")

    test = envdsBase()
    task_list.append(asyncio.create_task(test_task()))


    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path="/envds/daq",
        # log_config=dict_config,
    )

    server = uvicorn.Server(config)
    # test = logging.getLogger()
    # test.info("test")
    await server.serve()

    print("starting shutdown...")
    await shutdown()
    print("done.")


if __name__ == "__main__":

    BASE_DIR = os.path.dirname(
        # os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.path.dirname(os.path.abspath(__file__))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    print(sys.argv)
    config = ServerConfig()
    try:
        index = sys.argv.index("--host")
        host = sys.argv[index + 1]
        config.host = host
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--port")
        port = sys.argv[index + 1]
        config.port = int(port)
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--log_level")
        ll = sys.argv[index + 1]
        config.log_level = ll
    except (ValueError, IndexError):
        pass

    # print(LOGGING_CONFIG)

    # handler = logging.StreamHandler(sys.stdout)
    # formatter = Logfmter(
    #     keys=["at", "when", "name"],
    #     mapping={"at": "levelname", "when": "asctime"},
    #     datefmt=get_datetime_format()
    # )

    # # # self.logger = envdsLogger().get_logger(self.__class__.__name__)
    # # handler.setFormatter(formatter)
    # # # logging.basicConfig(handlers=[handler])
    # root_logger = logging.getLogger(__name__)
    # # # root_logger = logging.getLogger(self.__class__.__name__)
    # # # root_logger.addHandler(handler)
    # root_logger.addHandler(handler)
    # root_logger.setLevel(logging.INFO) # this should be settable
    # root_logger.info("in run", extra={"test": "value"})
    # print(root_logger.__dict__)

    # if "--host" in sys.argv:
    #     print(sys.argv.index("--host"))
    #     print(sys)
    asyncio.run(main(config))

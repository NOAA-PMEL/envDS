#import asyncio
import logging

#from typing import Union
#from pydantic import BaseSettings, Field

# from asyncio_mqtt import Client, MqttError

from cloudevents.http import CloudEvent#, event, from_json, to_structured
#from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields


# class EncryptedMessageConfig(BaseSettings):
#     encrypted: Union[bool, None] = False


class Message(object):
    """docstring for Message."""

    def __init__(
        self,
        data: CloudEvent,
        dest_path: str = None,
        source_path: str = None
        # data_type: str = "cloudevent",
        # encryption: EncryptedMessageConfig = None,
    ):
        super(Message, self).__init__()
        
        self.logger = logging.getLogger(__name__)

        self.data = data
        self.dest_path = dest_path
        self.source_path = source_path
        # self.data_type = data_type
        # self.encryption = encryption

    # def test(self):
    #     # print(self.logger)
    #     self.logger.info("Test Message", extra={"key1": "value1"})

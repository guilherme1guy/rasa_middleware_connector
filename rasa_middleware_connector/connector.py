import logging
import asyncio
import uuid
import time
import re

from rasa.core.channels.channel import UserMessage

logger = logging.getLogger(__name__)


class MiddlewareConnector:

    on_new_message = None
    used_middlewares = []

    __ready = False

    def __get_middlewares(self):
        raise NotImplementedError

    def __get_on_new_message(self):
        raise NotImplementedError

    def create_user_message(self, *args, **kwargs) -> UserMessage:
        raise NotImplementedError

    def setup_middlewares(self):
        
        last = None
        for middleware in self.__get_middlewares():
            
            if last is not None:
                middleware.set_next(last)

            last = middleware
            self.used_middlewares.append(middleware)


        if len(self.used_middlewares) > 0:
            last.set_next(self.__get_on_new_message())
        else:
            self.used_middlewares = [self.__get_on_new_message(), ]
    
        self.__ready = True

    async def proccess_message(self, message):

       await self.used_middlewares[0].compute(message)

    async def handle_message(self, *args, **kwargs):

        if not self.__ready:
            self.setup_middlewares()

        message = self.create_user_message(*args, **kwargs)
        await self.proccess_message(message)

    




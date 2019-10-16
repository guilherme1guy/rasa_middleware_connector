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

    middleware_is_ready = False

    def get_middlewares(self):
        raise NotImplementedError

    def get_on_new_message(self):
        raise NotImplementedError

    def create_user_message(self, *args, **kwargs) -> UserMessage:
        raise NotImplementedError

    def setup_middlewares(self):
        
        last = None
        for middleware in self.get_middlewares():
            
            if last is not None:
                last.set_next(middleware.compute)

            last = middleware
            self.used_middlewares.append(middleware)


        if len(self.used_middlewares) > 0:
            last.set_next(self.get_on_new_message())
        else:
            self.used_middlewares = [self.get_on_new_message(), ]
    
        self.middleware_is_ready = True

    async def proccess_message(self, message):

       await self.used_middlewares[0].compute(message)

    async def handle_message(self, *args, **kwargs):

        if not self.middleware_is_ready:
            self.setup_middlewares()

        message = self.create_user_message(*args, **kwargs)
        await self.proccess_message(message)

    




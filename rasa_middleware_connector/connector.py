import logging
import asyncio
import uuid
import time
import re

from rasa.core.channels.channel import UserMessage
from typing import List, Callable

logger = logging.getLogger(__name__)


class MiddlewareConnector:

    """
    Abstract class that adds middleware capacity to the connector.

    To instantiate this class you should implement 'get_middlewares', 
    'get_on_new_message' and 'create_user_message'.
    """

    used_middlewares = []
    middleware_is_ready = False

    def get_middlewares(self) -> List:
        """
        This method should return a list with your middleware objects 
        (created inheriting from `BaseMiddleware` class or that are compatible 
        with the same interface) in order of execution. 

        The Rasa Agent handler will be added after the middlewares.
        
        If no middleware is provided (returnin a empty list), the message will 
        be send directly to Rasa.
        """

        raise NotImplementedError

    def get_on_new_message(self) -> Callable:
        """
        This method returns the Rasa Agent `handle_message` endpoint, 
        usually it is received as the parameter `on_new_message` on the `blueprint` 
        function of a handler.

        It will be used to send the message to Rasa after all middlewares finish.
        """

        raise NotImplementedError

    def create_user_message(self, *args, **kwargs) -> UserMessage:
        """
        Returns a UserMessage object containing the text to be processed.
        """
        
        raise NotImplementedError

    def setup_middlewares(self):
        """
        This method goes trough the middlewares supplied on the 
        get_middlewares function and sets the 'next' attribute following 
        the order of the list. Appens the on_new_message (Rasa Agent Handler) 
        to the end of the middleware list. 
        """
        
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

    async def proccess_message(self, message: UserMessage):
        """
        Send the message object to the first middleware, starting the 
        processment stage.
        """

        await self.used_middlewares[0].compute(message)

    async def handle_message(self, *args, **kwargs):
        """
        Method that handles a new message beeing sent to the connector.
        """

        # setup middlewares it not ready
        if not self.middleware_is_ready:
            self.setup_middlewares()

        # get a UserMessage object from args passed
        message = self.create_user_message(*args, **kwargs)
        
        # sends UserMessage to middlewares
        await self.proccess_message(message)

    




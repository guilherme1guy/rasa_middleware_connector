import logging
import asyncio
import uuid
import time
import re

from rasa.core.channels.channel import UserMessage
from typing import List, Callable

logger = logging.getLogger(__name__)


class MiddleWareConnector:

    """
    Base class for the Input and Output middleware connectors
    """
    
    used_middlewares = []
    middleware_is_ready = False

    def _get_connector_type(self):
        """
        Returns if this connector is a input or a output middleware
        """

        raise NotImplementedError()

    def _get_default_path(self):

        """
        Returns the the callable wich is responsible to return control of the 
        message to Rasa
        """

        raise NotImplementedError()

    def get_middlewares(self) -> List:
        """
        This method should return a list with your middleware objects 
        (created inheriting from `BaseMiddleware` class or that are compatible 
        with the same interface) in order of execution. 

        The Rasa default path will be added after the middlewares.
        
        If no middleware is provided (returnin a empty list), the message will 
        be send directly to Rasa.
        """

        raise NotImplementedError

    def setup_middlewares(self):
        """
        This method goes trough the middlewares supplied on the 
        get_middlewares function and sets the 'next' attribute following 
        the order of the list. Appens the default Rasa path to the end 
        of the middleware list. 
        """

        is_output = True if self._get_connector_type() == 'OUTPUT' else False
        
        last = None
        for middleware in self.get_middlewares():
            
            if last is not None:
                last.set_next(middleware.compute, is_output)

            last = middleware
            self.used_middlewares.append(middleware)


        if len(self.used_middlewares) > 0:
            last.set_next(self._get_default_path(), is_output)
        else:
            self.used_middlewares = [self._get_default_path(), ]
    
        self.middleware_is_ready = True

    async def proccess_message(self, *args):
        """
        Starts the processment stage.
        """

        await self.used_middlewares[0].compute(*args)

   
class InputMiddlewareConnector(MiddleWareConnector):

    """
    Abstract class that adds middleware capacity to input connectors.

    To instantiate this class you should implement 'get_middlewares', 
    'get_on_new_message' and 'create_user_message'.
    """

    def _get_connector_type(self):
        return 'INPUT'

    def _get_default_path(self):
        return self.get_on_new_message()

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


class OutputMiddlewareConnector(MiddleWareConnector):

    def _get_connector_type(self):
        return 'OUTPUT'

    def _get_default_path(self):
        return self.get_connector_class().send_response

    def get_connector_class(self):

        """
        This method should return the class from where 'send_response' should
        be called after middleware processing.
        """

        raise NotImplementedError()

    async def send_response(self, recipient_id: Text, message: Dict[Text, Any]) -> None:
        
        await self.proccess_message(recipient_id, message)


from rasa.core.channels.channel import UserMessage
from typing import Callable, Text, Any, Dict

class BaseMiddleware:

    """
    Interface for Middlewares
    """

    def __init__(self, *args, **kwargs):
        self.next = None
        self.is_output = False

    def set_next(self, next: Callable[[UserMessage], None], is_output):

        """
        Sets the next middleware to call.
        """

        self.next = next
        self.is_output = is_output

    async def compute(self, *args):
        
        """
        This method sends the message to the correct function.
        """

        if self.is_output:
            await self.output_compute(*args)
        else:
            await self.input_compute(*args)

    async def input_compute(self, message: UserMessage):

        """
        This method process a input message, encapsulated in a UserMessage object 

        When done, 'await self.next(message)' should be called.
        """

        raise NotImplementedError()

    
    async def output_compute(self, recipient_id: Text, message: Dict[Text, Any]):
        
        """
        This method process a output message. 

        When done, 'await self.next(recipient_id, message)' should be called.
        """

        raise NotImplementedError()


class RasaDefaultPathMiddleware(BaseMiddleware):

    def __init__(self, endpoint):

        self.endpoint = endpoint

    async def input_compute(self, message):

        await self.endpoint(message)

    async def output_compute(self, recipient_id, message):

        await self.endpoint(message)
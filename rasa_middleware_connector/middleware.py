from rasa.core.channels.channel import UserMessage
from typing import Callable

class BaseMiddleware:

    """
    Interface for Middlewares
    """

    next = None

    def set_next(self, next: Callable[[UserMessage], None]):

        """
        Sets the next middleware to call.
        """

        self.next = next

    async def compute(self, message: UserMessage):

        """
        This method is where the UserMessage will be processed.

        When done, 'await self.next(message)' should be called.
        """

        # await self.next(message)
        raise NotImplementedError()

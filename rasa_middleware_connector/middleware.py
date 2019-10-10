from rasa.core.channels.channel import UserMessage

class BaseMiddleware:

    next = None

    def set_next(self, next):

        self.next = next

    async def compute(self, message: UserMessage):

        raise NotImplementedError()

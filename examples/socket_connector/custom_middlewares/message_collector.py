import logging
import asyncio

from asyncio import Lock
from rasa.core.channels.channel import UserMessage

from rasa_middleware_connector import BaseMiddleware

logger = logging.getLogger(__name__)

class MessageCollector(BaseMiddleware):

    """
    Collects messages sent during a time periodo and combine them 
    into a single message.
    """
    
    mutex = Lock()
    __on_new_message = None

    def __init__(self, connector):
        self.handlers = {}
        self.connector = connector
        
    async def input_compute(self, message: UserMessage):

        logger.info("Middleware MessageCollector received message from {}".format(message.sender_id))
                
        await self.register_message(message, self.next)   

    async def register_message(self, user_message: UserMessage, on_new_message):
        
        sid = user_message.sender_id
        
        if sid in self.handlers:

            try:
                await self.handlers[sid].append_message(user_message)
                logger.info("Added menssage to handler:" + sid)
            except HandlerClosedException:
                await self.create_handler(user_message, on_new_message)

        else:
            # skips delay on first message
            await self.create_handler(user_message, on_new_message, 0)

    async def create_handler(self, user_message, on_new_message, delay=None):
        async with self.mutex:

            sid = user_message.sender_id

            logger.info("Creating handler for: " + sid)

            new_handler = MessageHandler(user_message, on_new_message, delay=delay)
            self.handlers[sid] = new_handler
            

class MessageHandler:
    
    def __init__(self, user_message: UserMessage, on_new_message, delay=None):
        from os import getenv

        if delay is None:
            self.DELAY = float(getenv('DELAY_TIME', 3))
        else:
            self.DELAY = float(delay)

        self.messages = [user_message, ]
        self.sid = user_message.sender_id
        self.on_new_message = on_new_message

        self.mutex = Lock()
        self.reached_commit = False
        self.accepting = True
        

        logger.info(
            "Initializing handler for {} with delay of {}s and message {}".format(
                self.sid, 
                self.DELAY,
                user_message.text
            )
        )
        
        self.timer = AsyncTimer(self.DELAY, self.commit)

    async def append_message(self, user_message: UserMessage):
        
        async with self.mutex:
            if self.accepting is False:
                raise HandlerClosedException()

            full_text = user_message.text
            text_parts = await self.preprocess_text(full_text)
            
            self.messages.append(user_message)
            self.__reset_timer()
            
    def __reset_timer(self):

        self.timer.cancel()
        
        # if the commit has been reached, we shoud not reset the
        # timer, or it will process the message twice
        # there is no problem in not reseting the timer, since the message
        # added in this append operation will still be included
        # thats because the commit function awaits the lock that the funcion 
        # append (caller of this function) has on the message list
        # when the appen function releases the lock, all messages that need
        # to be processed will be alreadly included in the list
        if self.reached_commit is False:
            
            self.timer = AsyncTimer(self.DELAY, self.commit)
  
    async def commit(self):

        # signals that the timer has called this function
        self.reached_commit = True
        logger.info("Handler {} reached commit".format(self.sid))

        async with self.mutex:

            logger.info("Handler {} acquired lock for commit".format(self.sid))

            # close this Handler
            self.accepting = False
            
            # append all messages with a space in between
            complete_text = self.messages[0].text
            for msg in self.messages[1:]:
                complete_text += ' ' + msg.text

            final_message = self.messages[0]
            final_message.text = complete_text

            logger.info("Handler {} finished, sending final message '{}'".format(self.sid, complete_text))

            await self.on_new_message(final_message)
            logger.info("Handler {} closed with messages: {}".format(self.sid, self.messages))
                       
            
class AsyncTimer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()

class HandlerClosedException(Exception):
    pass
import logging
import asyncio

from rasa.core.channels.channel import UserMessage
from rasa.core.channels.socketio import SocketIOInput, SocketIOOutput

from rasa_middleware_connector import InputMiddlewareConnector, OutputMiddlewareConnector
from .custom_middlewares.message_collector import MessageCollector
from .custom_middlewares.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)

class SocketInput(SocketIOInput, InputMiddlewareConnector):

    """A socket.io input channel with middleware support."""

    on_new_message = None
    sio = None

    def get_middlewares(self):

        # returns the middleware list that this connector will use
        # they will be executed respecting the list order and the
        # rasa 'on_new_message' will be added as the last element

        # if this list is empty, only 'on_new_message' will be called
        
        return [
            TextCleaner(),
            MessageCollector(self)        
        ]

    def get_on_new_message(self):

        # returns the default rasa handler for messages
        # this function sends the message objecto to the
        # rasa agent that will handle it

        return self.on_new_message

    def create_user_message(self, sid, data) -> UserMessage:

        # this function receives required data to create a new
        # user message and returns it (based on the official rasa
        # implementation of the socket connector) 
      
        if self.session_persistence:
            if not data.get("session_id"):
                logger.warning(
                    "A message without a valid sender_id "
                    "was received. This message will be "
                    "ignored. Make sure to set a proper "
                    "session id using the "
                    "`session_request` socketIO event."
                )
                return
            sender_id = data["session_id"]
        else:
            sender_id = sid

        text = data["message"]

        output_channel = SocketIOOutput(self.sio, sender_id, self.bot_message_evt)
        message = UserMessage(
            text, output_channel, sid, input_channel=self.name()
        )
        
        return message

    def blueprint(self, on_new_message):

        self.on_new_message = on_new_message

        socketio_webhook = super().blueprint(on_new_message)
        self.sio = socketio_webhook.sio

        # swaps default event handler with the desired handler
        self.sio.handlers = socketio_webhook.sio.handlers
        self.sio.handlers['/'][self.user_message_evt] = self.handle_message

        return socketio_webhook


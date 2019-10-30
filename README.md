# Rasa Middleware Connector

Adds support for middlewares to Rasa connectors. The middlewares run before the message is sent to the Rasa agent allowing text/UserMessage preprocessing.

## Why not add a message_preprocessor when sending the message to the Rasa Agent?

You can do it, and you can also add middleware support to the preprocessor.

This module tries to bring more functionality to pre-processing, allowing access to all fields in a `UserMessage` object and the possibility to cancel a message execution when preprocessing it. 

When you set up a default message preprocessor by passing it as a callable argument on the function `handle_message` (usually called `on_new_message` on the channels), and it can even call a sequence of middlewares, but it only allows access to the text field on a `UserMessage`.

## Usage

### Input Connector
The class `InputMiddlewareConnector` is an abstract class that you should inherit from, together with the desired connector. It should be the first class.
```
class SocketInput(InputMiddlewareConnector, SocketIOInput):
```

You need to implement the methods: `get_middlewares`, `get_on_new_message` and `create_user_message`. And change the connector `handle_message` route to point to the `self.handle_message`. All the following examples are extracts from a custom connector based on the `SocketIOInput`:

```
def blueprint(self, on_new_message):

    # save Agent handler on object for later reference
    self.on_new_message = on_new_message

    # get the webhook from the super blueprint
    socketio_webhook = super().blueprint(on_new_message)
    self.sio = socketio_webhook.sio

    # swaps default event handler with the desired handler
    self.sio.handlers = socketio_webhook.sio.handlers
    self.sio.handlers['/'][self.user_message_evt] = self.handle_message

    return socketio_webhook
```

`get_on_new_message`: this method returns the Rasa Agent `handle_message` endpoint, usually it is received as the parameter `on_new_message` on the `blueprint` function of a handler. (On the example above we save this on `self.on_new_message`)



`get_middlewares`: this method should return a list with your middleware objects (created inheriting from `BaseMiddleware` class) in order of execution. The Rasa Agent handler will be added after the middlewares.
```
def get_middlewares(self):
    
    return [
        TextCleaner(),
        MessageCollector(self)        
    ]
```

`create_user_message(self, *args, **kwargs)`: this method returns a UserMessage object containing your message.
```
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
```

### Output Connector

An output middleware connector is very similar to the input one. You should override `get_middlewares` just like on the input. 

One caveat is that OutputMiddlewareConnector should be the first on the inheritance order. Also, there is the need to provide the connector class on `get_connector_class`:

```
class SocketOutput(OutputMiddlewareConnector, SocketIOOutput):
...
    def get_connector_class(self):
        return SocketIOOutput
```

### Middlewares

Your middlewares should respect the interface defined in the class `BaseMiddleware`: 
* `set_next(self, next, is_output)`
* `compute(self, message: UserMessage)`
* *`input_compute(self, message: UserMessage)`*
* *`output_compute(self, recipient_id: Text, message: Dict[Text, Any])`*
* Attributes: `next`, `is_output`

Note the at least `input_compute` or `output_compute` should be implemented. If you will only use the middleware as an input middleware you can only implement `input_compute`, and if its an only output middleware only `output_compute` needs to be implemented.

`set_next`: sets where your middleware should send the message after you are done processing it.

`compute(self, message: UserMessage)`: starts the processing of your message. Sends it to the appropriate function (`input_compute` or `output_compute`).

`input_compute` or `output_compute`: message processing. After processing the message you should call:
* `await self.next(message)` if input
* `await self.next(recipient_id, message)` if output

Example:
```
async def input_compute(self, message: UserMessage):

    logger.info("Middleware TextCleaner received message from {}".format(message.sender_id))
    
    message.text = self.clean_message(message.text)
    await self.next(message)

# output_compute not implemented since this is an input only middleware
```

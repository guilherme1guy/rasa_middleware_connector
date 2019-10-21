import asyncio
import logging

from rasa.core.channels.channel import UserMessage

from rasa_middleware_connector import BaseMiddleware

logger = logging.getLogger(__name__)

class TextCleaner(BaseMiddleware):

    """
    Cleans message from selected expressions.
    """

    async def input_compute(self, message: UserMessage):

        logger.info("Middleware TextCleaner received message from {}".format(message.sender_id))
        
        message.text = self.clean_message(message.text)
        await self.next(message)

    def clean_message(self, text: str):

        text = text.strip()
        text = text.lower()

        replacements = {
            'a': ['à', 'á', 'ã', 'ä'],
            'e': ['ê', 'ẽ', 'è', 'ë', 'eh', 'é'],
            'i' : ['í', 'ì', 'î', 'ĩ'],
            'o': ['ó', 'ò', 'õ', 'ö'],
            'u': ['ú', 'ù', 'ũ', 'ü'],
            'c': ['ç'],
            'voce': ['vc'],
            '': [','],
            'tambem': ['tbm'],
            'hoje': ['hj'],
            'tudo': ['td'],
            ' esta ': [' ta '],
            ' para ': [' pra ']
        }

        for key, lst in replacements.items():
            for c in lst:
                text = text.replace(c, key)

        return text
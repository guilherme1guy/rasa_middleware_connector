import asyncio
import logging
import requests
import json
import os

from typing import Text, Dict, Any
from rasa.core.channels.channel import UserMessage

from rasa_middleware_connector import BaseMiddleware

logger = logging.getLogger(__name__)

class Translator(BaseMiddleware):

    language_map = None
    translation_engines = None

    language_change_messages = {
        'en': 'Automatic translation provided by Google Translate.',
        'es': 'Traducciones automáticas proporcionadas por [Apertium](http://wiki.apertium.org/wiki/Apertium-apy).',
        'pt': 'Agora estamos falando em português.',
    }


    def __init__(self, bot_language, *args, **kwargs):
        self.bot_language = bot_language

        if not Translator.language_map:
            Translator.language_map = LanguageMap(bot_language)

        if not Translator.translation_engines:
            Translator.translation_engines = {
                'en': GoogleTranslator,
                'es': GoogleTranslator,
            }

        self.avaliable_commands = {
            '/set_lang': self.command_set_lang
        }

        super().__init__(*args, **kwargs)

    async def input_compute(self, message: UserMessage):

        logger.info("Middleware Translator (Input) received message from {}".format(message.sender_id))

        # only send to next middleware when its not a command
        is_command = message.text.startswith('/')
        
        if not is_command:
            message.metadata, message.text = await self.translate(message.sender_id, message.text)
            await self.next(message)
        else:
            await self.commands(message)

    async def output_compute(self, recipient_id: Text, message: Dict[Text, Any]):

        logger.info("Middleware Translator (Output) received message from {}".format(recipient_id))

        _, message['text'] = await self.translate(recipient_id, message['text'])

        if message.get('buttons'):
            buttons = []
            for button in message['buttons']:
                _, button['title'] = await  self.translate(recipient_id, button['title'])
                buttons.append(button)
                
            message['buttons'] = buttons

        await self.next(recipient_id, message)

    async def commands(self, message: UserMessage):

        args = message.text.split(' ')

        if args[0] in self.avaliable_commands:
            await self.avaliable_commands[args[0]](message) 
        else:
            # if we cannot handle the command, send it foward
            await self.next(message)       
        
       
    async def command_set_lang(self, message: UserMessage):
        text = message.text
        args = text.split(' ')

        if len(args) < 2:
            logger.error("Error: no language passed. Doing nothing")
        else:
            self.set_language(message.sender_id, args[1])
            if args[1] in self.language_change_messages:
                await message.output_channel.send_text_message(
                    message.sender_id,
                    self.language_change_messages[args[1]]
                )

    def set_language(self, id, user_language):

        if len(user_language) > 6:
            logger.error('Language name is too big')
        else:
            self.language_map.set_lang(id, user_language)


    async def translate(self, id, text: str):

        user_language = self.language_map.get_lang(id)

        if user_language != self.bot_language:

            text = text.strip()
          
            engine = self.translation_engines[user_language](
                text,
                (self.bot_language if self.is_output else user_language),
                (user_language if self.is_output else self.bot_language),
            )

            text = await engine.translate()

        return {'lang': user_language}, text


class LanguageMap:

    def __init__(self, default_language):

        self.__conversations = {}
        self.default_language = default_language

    def set_lang(self, id, language):

        self.__conversations[id] = language

    def get_lang(self, id):

        if id not in self.__conversations:
            self.__conversations[id] = self.default_language

        return self.__conversations[id]


class TranslationEngine:

    def __init__(self, text, input_language, output_language):

        self.text = text
        self.input_language = input_language
        self.output_language = output_language

    async def translate(self) -> str:
    
        raise NotImplementedError()

    def parse_response(self, response):
        raise NotImplementedError()


class ApertiumTranslator(TranslationEngine):

    def __init__(self, text, input_language, output_language):

        language_codes = self.get_language_codes()

        super().__init__(
            text,
            language_codes[input_language],
            language_codes[output_language]
        )

    def get_language_codes(self):
        return {
            'es': 'spa',
            'en': 'en',
            'pt': 'por'
        }

    async def translate(self):

        url = os.getenv('APERTIUM_URL', '')
        parameters = self.get_post_parameters()

        response = requests.post(url, data = parameters)
        text  = self.parse_response(response)

        return text


    def get_post_parameters(self):

        lang_string = self.input_language + '|' + self.output_language
        parameters = {
            'langpair': lang_string,
            'q': self.text
        }

        return parameters

    def parse_response(self, response):
        
        response_content = None

        if response.status_code == 200:
            response_content = json.loads(response.text)

        elif response_content['responseStatus'] != 200:
            logger.error("Apertium API error")
      
        data = response_content['responseData']
        return data['translatedText'].replace('*', '')
        

class EN_PT_ApertiumYandexTranslator(ApertiumTranslator):

    
    def get_language_codes(self):
        return {
            'es': 'spa',
            'en': 'en',
            'pt': 'pt'
        }
    
    async def translate(self):

        if self.input_language == 'en':
            
            translator = YandexTranslator(self.text, self.input_language, self.output_language)
            return await translator.translate()

        else:                    
            in_es = ApertiumTranslator(self.text, self.input_language, 'es')
            spanish_text = await in_es.translate()
            out_pt = ApertiumTranslator(spanish_text, 'es', self.output_language)            
            return await out_pt.translate()
   
class YandexTranslator(TranslationEngine):

    async def translate(self):

        url = os.getenv('YANDEX_URL', '')
        parameters = self.get_post_parameters()

        response = requests.post(url, data = parameters)
        text  = self.parse_response(response)

        return text

    def get_post_parameters(self):

        lang_string = self.input_language + '-' + self.output_language 

        parameters = {
            'key': os.getenv('YANDEX_API_KEY', ''),
            'text': self.text,
            'lang': lang_string
        }

        return parameters

    def parse_response(self, response):

        response_content = None
        if response.status_code == 200:
            response_content = json.loads(response.text)


        if response_content is not None and response_content['code'] != 200:
            logger.error("Yandex API error")
            return ''
        
        
        return response_content['text'][0]

class GoogleTranslator(TranslationEngine):

    def __init__(self, *args, **kwargs):

        from google.cloud import translate_v3beta1 as google_translator

        # don't forget to set $GOOGLE_APPLICATION_CREDENTIALS to the json 
        # with the authentication data 
        self.client = google_translator.TranslationServiceClient()
        self.project_id = os.getenv('GOOGLE_PROJECT_ID', '')
        self.location = 'global'
        self.parent = self.client.location_path(self.project_id, self.location)

        super().__init__(*args, **kwargs)

    async def translate(self):
        response = self.client.translate_text(
            parent=self.parent,
            contents=[self.text, ],
            mime_type='text/html',
            source_language_code=self.input_language,
            target_language_code=self.output_language
        )

        return self.parse_response(response)


    def parse_response(self, response):
        
        translated_text = response.translations[0].translated_text

        # deals with common formatting errors in translated text,
        # regarding urls in markdown format
        substitutions = {
            '] (': '](',
            '/ ': '/',
            ' /': '/'
        }

        for target, sub in substitutions.items():
            translated_text = translated_text.replace(target, sub)

        return translated_text
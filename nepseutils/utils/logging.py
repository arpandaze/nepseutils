import logging

import threading
import requests


class TelegramLoggingHandler(logging.Handler):
    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def send_telegram_message(self, message: str):
        if self.token and self.chat_id:
            try:
                requests.get(
                    f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={message}",
                )
            except Exception as e:
                print(e)

    def emit(self, record):
        log_entry = self.format(record)
        thread = threading.Thread(target=self.send_telegram_message, args=(log_entry,))
        thread.start()

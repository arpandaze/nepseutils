import logging
import threading
from queue import Queue
from time import sleep

import requests


class TelegramLoggingHandler(logging.Handler):
    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.log_queue = Queue()
        self.flush_interval = 1
        self.flush_thread = threading.Thread(target=self.flush_logs_periodically)
        self.flush_thread.daemon = True
        self.flush_thread.start()

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
        self.log_queue.put(log_entry)

    def flush_logs_periodically(self):
        while True:
            sleep(self.flush_interval)
            self.flush()

    def flush(self):
        if not self.log_queue.empty():
            log_messages = []
            while not self.log_queue.empty():
                log_messages.append(self.log_queue.get())
            batched_log = "\n".join(log_messages)
            self.send_telegram_message(batched_log)

    def shutdown(self):
        self.flush()
        super().close()

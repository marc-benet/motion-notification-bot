import logging
import subprocess
import threading
import time

import telegram
from environs import Env
from moviepy.editor import VideoFileClip

from utils import cleanup_file, get_file_from_log_line, get_local_ip

env = Env()
env.read_env()

filename = env("MOTION_LOG_PATH")
bot_token = env("TELEGRAM_BOT_TOKEN")
chat_id = env("TELEGRAM_CHAT_ID")
report_interval = env.int("REPORT_INTERVAL")  #  in seconds
notify_log_path = env("NOTIFIER_LOG_PATH")
feed_port = env("FEED_PORT", default="8081")
logging.basicConfig(
    filename=env("NOTIFIER_LOG_PATH"),
    filemode="w",
    format="[%(asctime)s]::%(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S %p",
    level=env.int("LOG_LEVEL", logging.INFO),
)

last_relevant = False
event_counter = 0
last_video_path = ""
last_pic_path = ""
time_interval = int(time.time())
initial_time = int(time.time())
feed_ip = get_local_ip()


def telegram_msg(text):
    logging.info(f"TELEGRAM MSG - {text}")
    bot = telegram.Bot(token=bot_token)
    bot.send_message(chat_id=chat_id, text=f"http://{feed_ip}:{feed_port} - {text}")


def telegram_photo(path):
    if "jpg" in path:
        bot = telegram.Bot(token=bot_token)
        try:
            bot.send_photo(chat_id, photo=open(path, "rb"))
            log_level, msg = cleanup_file(path)
            getattr(logging, log_level)(msg)
        except FileNotFoundError:
            logging.error(f"NOT FOUND FILE {path}")
            bot.send_message(
                chat_id=chat_id,
                text="Wanted to send an image which doesn't exist any more :(",
            )


def telegram_video(path, rm_file=False):
    if "mp4" in path:
        bot = telegram.Bot(token=bot_token)
        telegram_msg("Sending recording...")
        try:
            bot.send_video(chat_id, video=open(path, "rb"))
            if rm_file:
                log_level, msg = cleanup_file(path)
                getattr(logging, log_level)(msg)
        except FileNotFoundError:
            logging.error(f"NOT FOUND FILE {path}")
            bot.send_message(
                chat_id=chat_id,
                text="Wanted to send a movie which doesn't exist any more",
            )


def event_end(last_video_path, last_pic_path):
    logging.info(f"VIDEO PATH - {last_video_path}")

    try:
        clip = VideoFileClip(last_video_path)
        clip_duration = clip.duration
    except OSError:
        logging.info("COULDN'T FIND THE RELEVANT MOVIE ANY MORE!")
        clip_duration = 0

    logging.info(f"CLIP DURATION - {clip_duration}")

    if clip_duration > 12:
        logging.info("RELEVANT MOVIE FINISHED!")
        telegram_video(last_video_path)
    else:
        log_level, msg = cleanup_file(last_pic_path)
        getattr(logging, log_level)(msg)
        log_level, msg = cleanup_file(last_video_path)
        getattr(logging, log_level)(msg)
        logging.info("IRRELEVANT MOVIE")


if __name__ == "__main__":
    # telegram_msg("SURVEILANCE STARTED")
    telegram_thread = threading.Thread(
        target=telegram_msg, kwargs={"text": "-- SURVEILANCE STARTED --"}, daemon=True
    )
    telegram_thread.start()
    f = subprocess.Popen(
        ["tail", "-F", filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    while True:
        try:
            line = f.stdout.readline().decode()
            if "File of type 8 saved to:" in line:
                last_video_path = get_file_from_log_line(line)
                logging.info(f"NEW VIDEO EVENT LOG - {line}")
                logging.info(f"FILE PATH - {last_pic_path}")

            if "motion_detected:" in line:
                initial_time = int(time.time())
                logging.info("MOTION DETECTED!")

            if "Thread exiting" in line:
                logging.info("MOTION PROCESS SHUTDOWN")
                telegram_thread = threading.Thread(
                    target=telegram_msg,
                    kwargs={"text": "Camera shutting down..."},
                    daemon=True,
                )
                telegram_thread.start()
                # telegram_msg("Camera shutting down...")

            if "motion_init: Camera 0 started" in line:
                logging.info("MOTION PROCESS STARTUP")
                # telegram_msg("Camera started")
                telegram_thread = threading.Thread(
                    target=telegram_msg, kwargs={"text": "Camera sarted"}, daemon=True
                )
                telegram_thread.start()

            if "End of event" in line:
                event_thread = threading.Thread(
                    target=event_end,
                    kwargs={
                        "last_video_path": last_video_path,
                        "last_pic_path": last_pic_path,
                    },
                    daemon=True,
                )
                event_thread.start()
                event_counter += 1

            if "File of type 1 saved to:" in line:
                last_pic_path = get_file_from_log_line(line)
                logging.info(f"NEW IMAGE EVENT LOG - {line}")
                logging.info(f"FILE PATH - {last_pic_path}")

            if (int(time.time()) - time_interval) > report_interval:
                msg = "---- REPORT ---- \n"
                msg += f"-> counted {event_counter} events \n"
                # msg += f"-> {relevant_counter} videos recorded"
                telegram_thread = threading.Thread(
                    target=telegram_msg, kwargs={"text": msg}, daemon=True
                )
                telegram_thread.start()
                # telegram_msg(msg)
                time_interval = int(time.time())
                event_counter = 0
                # relevant_counter = 0

        except telegram.error.TimedOut:
            logging.critical("Telegram TimeOut Error :(")

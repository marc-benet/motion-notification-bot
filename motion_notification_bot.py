import os
import subprocess
import time
import logging

import telegram

from environs import Env


env = Env()
env.read_env()

filename = env("MOTION_LOG_PATH")
bot_token = env("TELEGRAM_BOT_TOKEN")
chat_id = env("TELEGRAM_CHAT_ID")
report_interval = env.int("REPORT_INTERVAL")  #  in seconds
notify_log_path = env("NOTIFIER_LOG_PATH")
logging.basicConfig(
    filename=env("NOTIFIER_LOG_PATH"),
    filemode="w",
    format="[%(asctime)s]::%(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S %p",
    level=env.int("LOG_LEVEL", logging.INFO),
)

last_relevant = False
irrelevant_counter = 0
relevant_counter = 0
last_video_path = ""
last_pic_path = ""
time_interval = int(time.time())
initial_time = int(time.time())
final_time = int(time.time())


def cleanup_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        logging.error(f"NOT FOUND FILE {path}")
    except PermissionError:
        logging.error(f"NO PERMISSION TO REMOVE {path}")

    logging.info(f"REMOVED - {path}")


def get_file_from_log_line(log_line):
    return log_line.strip("\n").split(" ")[-1]


def telegram_msg(text):
    bot = telegram.Bot(token=bot_token)
    bot.send_message(chat_id=chat_id, text=text)


def telegram_photo(path):
    if "jpg" in path:
        bot = telegram.Bot(token=bot_token)
        try:
            bot.send_photo(chat_id, photo=open(path, "rb"))
            cleanup_file(path)
        except FileNotFoundError:
            logging.error(f"NOT FOUND FILE {path}")
            bot.send_message(
                chat_id=chat_id,
                text="Wanted to send an image which doesn't exist any more :(",
            )


def telegram_video(path, rm_file=True):
    if "mp4" in path:
        bot = telegram.Bot(token=bot_token)
        bot.send_message(chat_id=chat_id, text="Sending recording...")
        try:
            bot.send_video(chat_id, video=open(path, "rb"))
            if rm_file:
                cleanup_file(path)
        except FileNotFoundError:
            logging.error(f"NOT FOUND FILE {path}")
            bot.send_message(
                chat_id=chat_id,
                text="Wanted to send a movie which doesn't exist any more",
            )


telegram_msg("SURVEILANCE STARTED")
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
            telegram_msg("Camera shutting down...")

        if "motion_init: Camera 0 started" in line:
            logging.info("MOTION PROCESS STARTUP")
            telegram_msg("Camera started")

        if "End of event" in line:
            final_time = int(time.time())
            logging.info(f"VIDEO PATH - {last_video_path}")
            if (final_time - initial_time) > 20:
                logging.info("RELEVANT MOVIE FINISHED!")
                telegram_photo(last_pic_path)
                telegram_video(last_video_path)
                relevant_counter += 1
                last_relevant = True
            elif last_relevant:
                # if it started relevant we want the final of the video even
                # if it was not going to be considered relevant
                logging.info("RELEVANT BECAUSE LAST RELEVANT FINISHED!")
                telegram_photo(last_pic_path)
                telegram_video(last_video_path)
                relevant_counter += 1
                last_relevant = False
            else:
                irrelevant_counter += 1
                cleanup_file(last_pic_path)
                cleanup_file(last_video_path)
                logging.info("IRRELEVANT MOVIE")
                last_relevant = False

        if "File of type 1 saved to:" in line:
            last_pic_path = get_file_from_log_line(line)
            logging.info(f"NEW IMAGE EVENT LOG - {line}")
            logging.info(f"FILE PATH - {last_pic_path}")

        if (int(time.time()) - time_interval) > report_interval:
            msg = "---- REPORT ---- \n"
            msg += f"-> {irrelevant_counter} irrelevant events \n"
            msg += f"-> {relevant_counter} videos recorded"
            telegram_msg(msg)
            time_interval = int(time.time())
            irrelevant_counter = 0
            relevant_counter = 0

    except telegram.error.TimedOut:
        logging.critical("Telegram TimeOut Error :(")

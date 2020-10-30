# MOTION NOTIFICATION BOT

**MOTION NOTIFICATION BOT** provides a telegram notificator bot to run in parallel with [Motion](https://motion-project.github.io/). The notification bot is checking constantly for updates on Motion's log file and reacts on different events while having consistency over the whole motion recording session.

Is also able to decide if the motion capture recording is relevant or not by a configurable time-lapse between the event initiation event and the finalisation one.

## Dependencies
- [Motion](https://motion-project.github.io/) (running at the same moment)
- python3.8
- [Poetry](https://python-poetry.org/) (python packages version control)

## Usage examples
### Define your environment variables following the environment example file together with virtualenv & poetry
```sh
cp .env.example .env
vim .env
python3 -m venv venv
source venv/bin/activate
pip install poetry
poetry install
python3 motion_notification_bot.py
```
### Use [Supervisord](http://supervisord.org/) to make the python script to run always since startup
This is how the software is regularly tested together with the motion service since startup. All in a raspberry-pi4.

So instead of doing `python3 motion_notification_bot.py` you can follow this to make it run in backround as mentioned before.
```sh
sudo apt-get install supervisord
cp etc/motion_notify_example.conf /etc/supervisor/conf.d/motion_notify.conf
vim /etc/supervisor/conf.d/motion_notify.conf  # edit it with your routes & user
sudo supervisorctl reread
sudo supervisorctl reload
```
From now on the python service is ready

## Configuring your telegram credentials
In the .env.example file you will find two config params to set up with your own telegram bot token your telegram chat ID.
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Once they're filled in with your bot & chat identifiers the software is ready to go.

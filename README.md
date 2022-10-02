# Telegram Mirror Bot
This bot mirrors the media uploaded in r/soccer to a telegram channel.

Telegram offers unlimted storage to its users and recently, it let anyone on the internet preview content on a public channel without requiring a telegram account. The aim of this bot is to 'exploit' this and serve telegram as a mirror.

## Working
This bot crawls through the reddit api for new soccer posts every minute.
Once a post with media flare is found, it:

1. Tries to process the link in the post and sends the video.
2. If it can't process the link in the post, it crawls the mirror links under the automoderator comment and tries to process all links again.
3. It tries this process 5 times in 5 minutes in total, if none of the links work.

Processing the video link:
1. Uses youtube-dl to get the direct link.
2. Checks if the link is greater than 14mb, compresses the video if it is.
3. Sends the video to the telegram channel
4. Posts a reddit comment under the automoderator with the link to the video


## Setup
1. Clone the repo
  ```bash
  git clone https://github.com/RtiM0/telegram-mirror-bot.git
  cd telegram-mirror-bot
  ```
2. Create virtualenv
  ```bash
  python3 -m venv env
  source env/bin/activate
  ```
3. [Install ffmpeg](https://ffmpeg.org/download.html)
4. Install requirements
  ```bash
  pip install -r requirements.txt
  ```
5. make `.env` file
  ```ini
  TOKEN = "<Telegram Bot Token>"
  ```
6. make `praw.ini` file
  ```ini
  [telegram mirror bot]
  client_id=<Reddit Client ID>
  client_secret=<Reddit Client Secret>
  username=<Reddit Account Username>
  password=<Reddit Account Password>
  user_agent=tg mirror bot 0.1
  ```
## Contributing
The bot can be optimized further, especially with the video compression. If you have ways to improve upon the current algorithm, Pull requests are welcomed.

## License
[GPL](https://choosealicense.com/licenses/gpl-3.0/)

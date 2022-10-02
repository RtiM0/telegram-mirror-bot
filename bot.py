import math
import os
import traceback
from datetime import datetime, timedelta
from re import findall
from string import Template

import asyncpraw
from dotenv import load_dotenv
from fake_headers import Headers
from requests import get, head
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, Defaults, PicklePersistence
from yt_dlp import YoutubeDL

from logger import logger
from video import Video

reddit = asyncpraw.Reddit('telegram mirror bot') 

REDDIT_COMMENT = Template('''
[Mirror](https://tttttt.me/s/soccer_mirror/$message_id/)

^(You DON'T need telegram to view these links, if you can't see a video in this link then replace tttttt[dot]me with t[dot]me in the link.)

^(Help Improve this bot! - [Source Code](https://github.com/RtiM0/telegram-mirror-bot))
''')

def get_reddit(permalink="/r/soccer/new?limit=20") -> dict:
        feed = get(
            f"https://api.reddit.com{permalink}",
            headers=Headers(headers=True).generate(),
        ).json()
        if type(feed) == list:
            return feed[1]["data"]["children"]
        else:
            return feed["data"]["children"]

def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])

async def send_video(context, video, title, reddit_post, automod_id):
    msg = await context.bot.send_video(
        chat_id="@soccer_mirror",
        video=video,
        caption=f"{title}\n\n<a href=\"{reddit_post}\"><b>Reddit Link</b></a>",
        supports_streaming=True,
    )
    try:
        automod_comment = await reddit.comment(id=automod_id)
        await automod_comment.reply(body=REDDIT_COMMENT.substitute(message_id=msg.message_id))
    except Exception:
        logger.error(traceback.format_exc())
        pass

async def look_for_goals(context):
    context.bot_data["goalsdone"] = context.bot_data.get("goalsdone", [])
    feed = get_reddit()
    for post in feed:
        post = post["data"]
        title = post["title"]
        if (
            title not in context.bot_data["goalsdone"]
            and post["url"] is not None
            and post["link_flair_text"] is not None
            and (
                post["link_flair_text"].lower() == "media"
                or post["link_flair_text"].lower() == "mirror"
            )
        ):
            logger.info(f"FOUND GOAL: {title}")
            ref = await get_stream([post["url"]], title, f"https://reddit.com{post['permalink']}", get_reddit(post["permalink"])[0]["data"]["id"], context)
            if not ref:
                context.job_queue.run_repeating(
                    monitor_thread,
                    60,
                    data=[
                        get_reddit(post["permalink"])[0]["data"][
                            "permalink"
                        ],
                        [post["url"]],
                        title,
                        f"https://reddit.com{post['permalink']}",
                        datetime.now() + timedelta(minutes=5),
                    ],
                    name=f"Monitor for {title}",
                )
            context.bot_data["goalsdone"].append(title)
    

async def get_stream(links: list, title: str, reddit_post: str, automod_id, context):
    for link in links:
        try:
            with YoutubeDL({"logger": logger}) as ydl:
                result = ydl.extract_info(link, download=False)
                if "entries" in result:
                    video = result["entries"][0]
                else:
                    video = result
                try:
                    if not video.get("url",None):
                        continue
                    vid_head = head(video["url"], allow_redirects=True)
                    if (
                        "youtube" not in video["url"]
                        and vid_head.status_code == 200
                    ):
                        vid_size = int(vid_head.headers.get('content-length', 0))
                        if vid_size > 10000:
                            logger.info(f"Found direct for {link} [size - {convert_size(vid_size)}]")
                            if (vid_size >= 14000000):
                                logger.info(f"Compressing Video of size - {convert_size(vid_size)}")
                                try:
                                    input_video = Video(vid_head.url)
                                    output_path = input_video.compress_video(12*1000)
                                    if output_path:
                                        logger.info(f"Video compressed to size - {convert_size(output_path.stat().st_size)}")
                                        await send_video(context, output_path.open("rb"), title, reddit_post, automod_id)
                                        os.remove(output_path.resolve())
                                        return True
                                except Exception:
                                    pass
                            else:
                                try:
                                    await send_video(context, vid_head.url,title, reddit_post, automod_id)
                                    return True
                                except BadRequest:
                                    try:
                                        await send_video(context, get(vid_head.url).content,title, reddit_post, automod_id)
                                        return True
                                    except Exception:
                                        pass
                except Exception:
                    pass
        except Exception:
            pass
    return False

async def monitor_thread(context):
    job = context.job
    automoderator_permalink, links, title, reddit_post, end_time = job.data
    automod = get_reddit(automoderator_permalink)[0]["data"]
    mirrors_comments = automod["replies"]
    if type(mirrors_comments) == dict:
        for mirror in mirrors_comments["data"]["children"]:
            urls = findall(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+",
                mirror["data"]["body"],
            )
            for url in urls:
                links.append(url.strip("()"))
    logger.info(f"Found {len(links)} mirrors for {title}")
    ref = await get_stream(links, title, reddit_post, automod["id"], context)
    if ref or (end_time < datetime.now()):
        context.job.schedule_removal()

def main():
    load_dotenv()
    application = Application.builder().token(os.environ.get("TOKEN")).defaults(defaults=Defaults(parse_mode=ParseMode.HTML)).read_timeout(300).persistence(persistence=PicklePersistence(filepath="tgmirrorbot")).build()
    application.job_queue.run_repeating(
        look_for_goals,
        60,
    )
    application.run_polling()


if __name__ == "__main__":
    main()

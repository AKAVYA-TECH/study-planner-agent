import re
from datetime import datetime
from uuid import uuid4
from urllib.parse import quote

import requests
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

YOUTUBE_API_KEY = "Enter your api key"

agent = Agent()
chat_proto = Protocol(spec=chat_protocol_spec)


def get_youtube_videos(subject: str) -> str:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": f"{subject} crash course tutorial",
        "type": "video",
        "maxResults": 3,
        "key": YOUTUBE_API_KEY,
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        videos = []
        for item in res.get("items", []):
            title = item["snippet"]["title"]
            link = f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            videos.append(f"- {title}: {link}")
        return "\n".join(videos) or "Koi video nahi mila."
    except Exception:
        return "YouTube videos fetch karne me error aayi."


def get_wiki_summary(subject: str) -> str:
    headers = {"User-Agent": "StudyAgent/1.0"}
    try:
        # Step 1: search se sahi page title dhundo
        search = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": subject,
                "srlimit": 1,
                "format": "json",
            },
            headers=headers,
            timeout=10,
        ).json()
        results = search.get("query", {}).get("search", [])
        if not results:
            return "Sorry, is topic ka Wikipedia summary nahi mila."

        title = quote(results[0]["title"].replace(" ", "_"))

        # Step 2: us page ka summary lo
        res = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=headers,
            timeout=10,
        ).json()
        return res.get("extract", "Sorry, is topic ka Wikipedia summary nahi mila.")
    except Exception:
        return "Wikipedia fetch karne me error aayi."


def make_reply(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=text),
            EndSessionContent(type="end-session"),
        ],
    )


@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.utcnow(), acknowledged_msg_id=msg.msg_id
        ),
    )

    for item in msg.content:
        if isinstance(item, StartSessionContent):
            continue
        if isinstance(item, TextContent):
            # @handle hata do, sirf subject bacha rahe
            subject = re.sub(r"@\S+", "", item.text).strip()
            if not subject:
                await ctx.send(
                    sender,
                    make_reply("Kripya koi subject ya topic likho, jaise: Data Structures"),
                )
                continue

            ctx.logger.info(f"Subject: {subject}")

            summary = get_wiki_summary(subject)
            videos = get_youtube_videos(subject)

            plan = (
                f"📚 **Study Plan for {subject}** 📚\n\n"
                f"**📖 Quick Summary:**\n{summary}\n\n"
                f"**📺 Top 3 Crash Courses:**\n{videos}\n\n"
                f"Best of luck for your exams! 🚀"
            )
            await ctx.send(sender, make_reply(plan))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Ack from {sender}")


agent.include(chat_proto, publish_manifest=True)

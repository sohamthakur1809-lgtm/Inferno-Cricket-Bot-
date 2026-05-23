import asyncio
import random

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message

from config import BOT_TOKEN, OWNER_ID

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# =========================
# DATABASES
# =========================

teams = {}
team_invites = {}
active_matches = {}
user_stats = {}
shot_media = {}

# =========================
# HELPERS
# =========================

def init_user(user_id):
    if user_id not in user_stats:
        user_stats[user_id] = {
            "runs": 0,
            "matches": 0,
            "wickets": 0,
            "wins": 0,
            "highest": 0
        }


def scoreboard(match):
    return (
        f"🏏 <b>{match['team1']} vs {match['team2']}</b>\n\n"
        f"Score: {match['runs']}/{match['wickets']}\n"
        f"Overs: {match['balls']//6}.{match['balls']%6}\n\n"
        f"👤 Batter: {match['batter_name']}\n"
        f"🎯 Bowler: {match['bowler_name']}"
    )

# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: Message):
    await message.reply(
        "🏏 <b>LEGENDARY HAND CRICKET BOT</b>\n\n"
        "/createteam TeamName\n"
        "/jointeam TeamName\n"
        "/startmatch Team1 Team2"
    )

# =========================
# CREATE TEAM
# =========================

@dp.message(Command("createteam"))
async def create_team(message: Message):

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return await message.reply("Usage: /createteam TeamName")

    team_name = args[1]

    if team_name in teams:
        return await message.reply("❌ Team already exists")

    teams[team_name] = {
        "captain": message.from_user.id,
        "captain_name": message.from_user.full_name,
        "players": [message.from_user.id],
        "player_names": [message.from_user.full_name]
    }

    await message.reply(
        f"🏏 Team Created Successfully\n\n"
        f"Team: <b>{team_name}</b>\n"
        f"Captain: {message.from_user.full_name}"
    )

# =========================
# JOIN TEAM
# =========================

@dp.message(Command("jointeam"))
async def join_team(message: Message):

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return await message.reply("Usage: /jointeam TeamName")

    team_name = args[1]

    if team_name not in teams:
        return await message.reply("❌ Team not found")

    if message.from_user.id in teams[team_name]["players"]:
        return await message.reply("Already joined")

    teams[team_name]["players"].append(message.from_user.id)
    teams[team_name]["player_names"].append(message.from_user.full_name)

    await message.reply(
        f"✅ Joined Team <b>{team_name}</b>"
    )

# =========================
# START MATCH
# =========================

@dp.message(Command("startmatch"))
async def start_match(message: Message):

    args = message.text.split()

    if len(args) < 3:
        return await message.reply(
            "Usage:\n/startmatch Team1 Team2"
        )

    team1 = args[1]
    team2 = args[2]

    if team1 not in teams or team2 not in teams:
        return await message.reply("❌ Team not found")

    active_matches[message.chat.id] = {
        "team1": team1,
        "team2": team2,
        "team1_captain": teams[team1]["captain"],
        "team2_captain": teams[team2]["captain"],
        "runs": 0,
        "wickets": 0,
        "balls": 0,
        "bowler_pick": None,
        "batting_team": None,
        "bowling_team": None,
        "batter": None,
        "bowler": None,
        "batter_name": None,
        "bowler_name": None,
        "toss_phase": True,
        "waiting": "headtail"
    }

    toss_captain = random.choice([
        teams[team1]["captain"],
        teams[team2]["captain"]
    ])

    active_matches[message.chat.id]["toss_caller"] = toss_captain

    await message.reply(
        f"🏏 <b>{team1}</b> vs <b>{team2}</b>\n\n"
        f"🪙 Toss Time!\n\n"
        f"Captain send:\n"
        f"head OR tail"
    )

# =========================
# TOSS SYSTEM
# =========================

@dp.message(F.text.lower().in_(["head", "tail"]))
async def toss_call(message: Message):

    if message.chat.id not in active_matches:
        return

    match = active_matches[message.chat.id]

    if not match["toss_phase"]:
        return

    if match["waiting"] != "headtail":
        return

    if message.from_user.id != match["toss_caller"]:
        return

    result = random.choice(["head", "tail"])

    if result == message.text.lower():
        winner = message.from_user.id
    else:
        if winner := match["team1_captain"] == message.from_user.id:
            winner = match["team2_captain"]
        else:
            winner = match["team1_captain"]

    match["toss_winner"] = winner
    match["waiting"] = "batbowl"

    await message.reply(
        f"🪙 Toss Result: <b>{result.upper()}</b>\n\n"
        f"Toss Winner choose:\n"
        f"bat OR bowl"
    )

# =========================
# BAT BOWL DECISION
# =========================

@dp.message(F.text.lower().in_(["bat", "bowl"]))
async def bat_bowl(message: Message):

    if message.chat.id not in active_matches:
        return

    match = active_matches[message.chat.id]

    if match["waiting"] != "batbowl":
        return

    if message.from_user.id != match["toss_winner"]:
        return

    choice = message.text.lower()

    if message.from_user.id == match["team1_captain"]:
        winner_team = match["team1"]
        loser_team = match["team2"]
    else:
        winner_team = match["team2"]
        loser_team = match["team1"]

    if choice == "bat":
        match["batting_team"] = winner_team
        match["bowling_team"] = loser_team
    else:
        match["batting_team"] = loser_team
        match["bowling_team"] = winner_team

    batting_team_data = teams[match["batting_team"]]
    bowling_team_data = teams[match["bowling_team"]]

    batter_id = batting_team_data["players"][0]
    bowler_id = bowling_team_data["players"][0]

    match["batter"] = batter_id
    match["bowler"] = bowler_id

    match["batter_name"] = bot_data_name(batter_id)
    match["bowler_name"] = bot_data_name(bowler_id)

    match["toss_phase"] = False

    await message.reply(
        f"🏏 Match Started\n\n"
        f"{match['batting_team']} elected to BAT first\n\n"
        f"{scoreboard(match)}"
    )

    await bot.send_message(
        bowler_id,
        "🎯 Your turn to bowl\n\nSend number (1-6)"
    )

# =========================
# GET USER NAME
# =========================

def bot_data_name(user_id):
    for team in teams.values():
        for index, player in enumerate(team["players"]):
            if player == user_id:
                return team["player_names"][index]

    return "Player"

# =========================
# BOWLER DM INPUT
# =========================

@dp.message(F.chat.type == "private")
async def bowler_dm(message: Message):

    if message.text not in ["1", "2", "3", "4", "5", "6"]:
        return

    for chat_id, match in active_matches.items():

        if match["bowler"] == message.from_user.id:

            match["bowler_pick"] = int(message.text)

            await message.reply("✅ Bowl locked")

            await bot.send_message(
                OWNER_ID,
                f"🎯 LIVE BOWLER MOVE\n\n"
                f"Bowler: {message.from_user.full_name}\n"
                f"Selected: {message.text}"
            )

# =========================
# GAMEPLAY
# =========================

@dp.message(F.chat.type.in_(["group", "supergroup"]))
async def gameplay(message: Message):

    if message.chat.id not in active_matches:
        return

    match = active_matches[message.chat.id]

    if message.from_user.id != match["batter"]:
        return

    if message.text not in ["0", "1", "2", "3", "4", "5", "6"]:
        return

    if match["bowler_pick"] is None:
        return await message.reply("⏳ Waiting for bowler")

    batter_pick = int(message.text)
    bowler_pick = match["bowler_pick"]

    result_text = ""

    if batter_pick == 0:

        result_text = "🛡 DOT BALL"

    elif batter_pick == bowler_pick:

        result_text = "💀 OUT"

        match["wickets"] += 1

        init_user(match["bowler"])
        user_stats[match["bowler"]]["wickets"] += 1

    else:

        result_text = f"💥 {batter_pick} RUNS"

        match["runs"] += batter_pick

        init_user(match["batter"])

        user_stats[match["batter"]]["runs"] += batter_pick

    match["balls"] += 1

    # MEDIA SYSTEM
    if str(batter_pick) in shot_media:

        file_id = shot_media[str(batter_pick)]

        await bot.send_animation(
            message.chat.id,
            file_id,
            caption=(
                f"{result_text}\n\n"
                f"👤 {match['batter_name']} → {batter_pick}\n"
                f"🎯 {match['bowler_name']} → {bowler_pick}\n\n"
                f"{scoreboard(match)}"
            )
        )

    else:

        await message.reply(
            f"{result_text}\n\n"
            f"👤 {match['batter_name']} → {batter_pick}\n"
            f"🎯 {match['bowler_name']} → {bowler_pick}\n\n"
            f"{scoreboard(match)}"
        )

    match["bowler_pick"] = None

    await bot.send_message(
        match["bowler"],
        "🎯 Bowl Again\n\nSend number (1-6)"
    )

# =========================
# USER STATS
# =========================

@dp.message(Command("userstats"))
async def userstats_cmd(message: Message):

    user_id = message.from_user.id

    init_user(user_id)

    stats = user_stats[user_id]

    await message.reply(
        f"🏏 PLAYER STATS\n\n"
        f"👤 {message.from_user.full_name}\n\n"
        f"Matches: {stats['matches']}\n"
        f"Runs: {stats['runs']}\n"
        f"Highest: {stats['highest']}\n"
        f"Wickets: {stats['wickets']}\n"
        f"Wins: {stats['wins']}"
    )

# =========================
# LEADERBOARD
# =========================

@dp.message(Command("leaderboard"))
async def leaderboard(message: Message):

    if not user_stats:
        return await message.reply("No stats yet")

    sorted_players = sorted(
        user_stats.items(),
        key=lambda x: x[1]["runs"],
        reverse=True
    )

    text = "🏆 GLOBAL LEADERBOARD\n\n"

    rank = 1

    for user_id, stats in sorted_players[:10]:

        text += (
            f"{rank}. {stats['runs']} Runs\n"
        )

        rank += 1

    await message.reply(text)

# =========================
# SECRET OWNER PANEL
# =========================

@dp.message(Command("wowadminwow"))
async def owner_panel(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    await message.reply(
        "👑 OWNER PANEL\n\n"
        "/watchmatch\n"
        "/set0\n"
        "/set1\n"
        "/set2\n"
        "/set3\n"
        "/set4\n"
        "/set5\n"
        "/set6\n"
        "/setout"
    )

# =========================
# WATCH MATCH
# =========================

@dp.message(Command("watchmatch"))
async def watch_match(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    text = "📡 ACTIVE MATCHES\n\n"

    if not active_matches:
        text += "No active matches"

    for chat_id, match in active_matches.items():

        text += (
            f"🏏 {match['team1']} vs {match['team2']}\n"
        )

    await message.reply(text)

# =========================
# MEDIA SETUP
# =========================

async def save_media(message, key):

    if message.from_user.id != OWNER_ID:
        return

    if not message.reply_to_message:
        return await message.reply("Reply to gif/video/sticker")

    media_msg = message.reply_to_message

    file_id = None

    if media_msg.animation:
        file_id = media_msg.animation.file_id

    elif media_msg.video:
        file_id = media_msg.video.file_id

    elif media_msg.sticker:
        file_id = media_msg.sticker.file_id

    if not file_id:
        return await message.reply("Invalid media")

    shot_media[key] = file_id

    await message.reply(f"✅ Media saved for {key}")

@dp.message(Command("set0"))
async def set0(message: Message):
    await save_media(message, "0")

@dp.message(Command("set1"))
async def set1(message: Message):
    await save_media(message, "1")

@dp.message(Command("set2"))
async def set2(message: Message):
    await save_media(message, "2")

@dp.message(Command("set3"))
async def set3(message: Message):
    await save_media(message, "3")

@dp.message(Command("set4"))
async def set4(message: Message):
    await save_media(message, "4")

@dp.message(Command("set5"))
async def set5(message: Message):
    await save_media(message, "5")

@dp.message(Command("set6"))
async def set6(message: Message):
    await save_media(message, "6")

@dp.message(Command("setout"))
async def setout(message: Message):
    await save_media(message, "out")

# =========================
# MAIN
# =========================

async def main():
    print("Bot Started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import threading
import json
import os
import sys
import tkinter as tk
import customtkinter as ctk
import discord
from discord import app_commands
from discord.ext import commands, tasks
import yt_dlp
import webbrowser
# --- Configuration & Storage ---
CONFIG_FILE = "bot_config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"token": "MTE5NDEwMzgyMTcxOTMxNDU0Mg.G4Id_A.2oEV1OUdDv59YB4WN5hmrYUpIaKJu0vQRSXVuA", "activity_type": "Listening", "activity_text": "/play | /stop"}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# --- نظام حفظ اللوحات التلقائي ---
DASHBOARDS_FILE = "dashboards.json"


def load_dashboards():
    if os.path.exists(DASHBOARDS_FILE):
        try:
            with open(DASHBOARDS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}


def save_dashboards(data):
    with open(DASHBOARDS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# --- مسار FFmpeg الديناميكي (لحل مشكلة الـ exe) ---
# --- مسار FFmpeg الديناميكي (لحل مشكلة الـ exe) ---

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

FFMPEG_PATH = os.path.join(application_path, "ffmpeg.exe")

# --- Discord Bot Setup & Audio Engine ---
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot_thread = None
bot_loop = None
is_running = False

# إعدادات يوتيوب الأساسية والمستقرة (مقطع واحد فقط)
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'restrictfilenames': False,
    'noplaylist': True,  # 🚀 منع البلاي ليست
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',  # 🚀 يرجع نتيجة واحدة فقط
    'source_address': '0.0.0.0',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# إعدادات البث الصوتي بدون انقطاع
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M',
    'options': '-vn -b:a 192k'
}
# نظام تخزين المقاطع لكل سيرفر
music_queues = {}


def check_queue(guild, vc, bot_loop=None):
    if not bot_loop:
        bot_loop = asyncio.get_event_loop()

    if guild.id in music_queues and len(music_queues[guild.id]) > 0:
        next_song = music_queues[guild.id].pop(0)
        try:
            player = YTDLSource(discord.FFmpegPCMAudio(
                next_song['url'], executable=FFMPEG_PATH, **FFMPEG_OPTIONS), data=next_song)
            vc.play(player, after=lambda e: bot_loop.create_task(
                after_play(guild, vc)))
            log_to_gui(f"[AUDIO] Playing: {player.title}")
            asyncio.run_coroutine_threadsafe(
                update_dashboard(guild, vc, next_song), bot_loop)
        except Exception as e:
            log_to_gui(f"[ERROR] Queue error: {e}")
            check_queue(guild, vc, bot_loop)
    else:
        asyncio.run_coroutine_threadsafe(
            update_dashboard(guild, vc, None), bot_loop)


async def after_play(guild, vc):
    check_queue(guild, vc, bot.loop)


async def after_play(guild, vc):
    check_queue(guild, vc, bot.loop)


async def after_play(guild, vc):
    check_queue(guild, vc, bot.loop)
# إعدادات البث الصوتي بدون انقطاع
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M',
    'options': '-vn -b:a 192k'
}

# --- محرك مخصص لسحب الرابط الصوتي المباشر (لحل مشكلة البلاي ليست) ---
YTDL_OPTIONS_SINGLE = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
}
ytdl_single = yt_dlp.YoutubeDL(YTDL_OPTIONS_SINGLE)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.8):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.webpage_url = data.get('webpage_url', 'https://youtube.com')

    @classmethod
    async def from_query(cls, query, *, loop=None):
        loop = loop or asyncio.get_event_loop()

        # التأكد إذا كان النص يمثل رابطاً أو كلمة بحث
        if not query.startswith(('http://', 'https://')):
            query = f"ytsearch:{query}"

        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH, **FFMPEG_OPTIONS), data=data)


    # --- نظام الطابور واللوحة الثابتة ---
music_queues = {}
dashboards = {}


async def update_dashboard(guild, vc, current_song=None):
    if guild.id not in dashboards:
        return
    msg = dashboards[guild.id]

    # رابط البنر الاحترافي الخاص بك (يظهر وقت الانتظار)
    banner_url = "https://i.imgur.com/zahHM79.jpg?v=1"

    if current_song:
        embed = discord.Embed(
            title="🎵 جارٍ التشغيل الآن",
            description=f"**[{current_song.get('title', 'Unknown')}]({current_song.get('webpage_url', 'https://youtube.com')})**",
            color=0x00E676
        )

        # هنا صورة الفيديو تأخذ مكان البنر (كصورة رئيسية كبيرة)
        if current_song.get('thumbnail'):
            embed.set_image(url=current_song['thumbnail'])

        q_len = len(music_queues.get(guild.id, []))
        if q_len > 0:
            embed.set_footer(text=f"المنتظر في الطابور: {q_len} مقاطع ⏳")
    else:
        embed = discord.Embed(
            title="🎧 المشغل الاحترافي",
            description="في انتظار طلباتكم...\nاضغط على زر 🔍 **بحث / تشغيل** لبدء الاستماع.",
            color=0x2b2d31
        )
        # البنر الاحترافي يظهر فقط عندما لا يكون هناك مقطع يعمل
        embed.set_image(url=banner_url)

    try:
        await msg.edit(embed=embed, view=StaticPlayerView())
    except Exception as e:
        log_to_gui(f"[ERROR] Failed to update dashboard: {e}")


def check_queue(guild, vc, bot_loop=None):
    if not bot_loop:
        bot_loop = asyncio.get_event_loop()

    if guild.id in music_queues and len(music_queues[guild.id]) > 0:
        next_song = music_queues[guild.id].pop(0)
        try:
            player = YTDLSource(discord.FFmpegPCMAudio(
                next_song['url'], executable=FFMPEG_PATH, **FFMPEG_OPTIONS), data=next_song)
            vc.play(player, after=lambda e: bot_loop.create_task(
                after_play(guild, vc)))
            log_to_gui(f"[AUDIO] Playing: {player.title}")
            asyncio.run_coroutine_threadsafe(
                update_dashboard(guild, vc, next_song), bot_loop)
        except Exception as e:
            log_to_gui(f"[ERROR] Queue error: {e}")
            check_queue(guild, vc, bot_loop)
    else:
        asyncio.run_coroutine_threadsafe(
            update_dashboard(guild, vc, None), bot_loop)


async def after_play(guild, vc):
    check_queue(guild, vc, bot.loop)

# --- واجهات المستخدم (القوائم، النوافذ، والأزرار) ---


class SearchDropdown(discord.ui.Select):
    def __init__(self, results, vc, interaction):
        self.results = results
        self.vc = vc

        options = []
        for i, res in enumerate(results):
            title = res.get('title', 'Unknown Title')[:90]
            duration = res.get('duration_string', 'N/A')
            options.append(discord.SelectOption(
                label=title, description=f"المدة: {duration}", value=str(i), emoji="🎵"))

        super().__init__(placeholder="اختر المقطع من القائمة...",
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_song = self.results[int(self.values[0])]

        guild_id = interaction.guild.id
        if guild_id not in music_queues:
            music_queues[guild_id] = []
        music_queues[guild_id].append(selected_song)

        if not self.vc.is_playing() and not self.vc.is_paused():
            check_queue(interaction.guild, self.vc, bot.loop)
            await interaction.followup.send(f"▶️ جاري تشغيل: **{selected_song['title']}**")
        else:
            await interaction.followup.send(f"✅ تم الإضافة للطابور: **{selected_song['title']}**")
            await update_dashboard(interaction.guild, self.vc, self.vc.source.data if self.vc.source else None)


class SearchView(discord.ui.View):
    def __init__(self, results, vc, interaction):
        super().__init__(timeout=60)
        self.add_item(SearchDropdown(results, vc, interaction))


class PlayModal(discord.ui.Modal, title="تشغيل مقطع"):
    query_input = discord.ui.TextInput(
        label="ضع الرابط أو اسم المقطع",
        placeholder="مثال: اكتب اسم أغنية أو ضع رابط يوتيوب مباشر",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ جاري البحث والتشغيل...", ephemeral=True)

        # إذا وضع رابط فيه بلاي ليست، البوت سيتجاهل البلاي ليست ويشغل المقطع الأول فقط
        query = self.query_input.value.split('&list=')[0]

        if not interaction.user.voice:
            await interaction.edit_original_response(content="❌ **يجب أن تكون في روم صوتي أولاً!**")
            return

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        try:
            loop = asyncio.get_event_loop()

            # إذا كان مجرد نص (ليس رابط)، نضيف له أمر البحث
            if not query.startswith(('http://', 'https://')):
                query = f"ytsearch:{query}"

            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))

            if 'entries' in data:
                song_info = data['entries'][0]
            else:
                song_info = data

            guild_id = interaction.guild.id
            if guild_id not in music_queues:
                music_queues[guild_id] = []

            music_queues[guild_id].append(song_info)
            await interaction.edit_original_response(content=f"✅ تم الإضافة للطابور: **{song_info['title']}**")

            if not vc.is_playing() and not vc.is_paused():
                check_queue(interaction.guild, vc, bot.loop)
            else:
                await update_dashboard(interaction.guild, vc, vc.source.data if vc.source else None)

        except Exception as e:
            log_to_gui(f"[ERROR] Playback failed: {e}")
            await interaction.edit_original_response(content="❌ **حدث خطأ، تأكد من الرابط أو حاول مجدداً.**")


class StaticPlayerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="بحث / تشغيل", style=discord.ButtonStyle.success, emoji="🔍", custom_id="btn_play")
    async def play_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PlayModal())

    @discord.ui.button(label="إيقاف / تشغيل", style=discord.ButtonStyle.primary, emoji="⏯️", custom_id="btn_pause")
    async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("تم الإيقاف المؤقت ⏸️", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("تم استئناف التشغيل ▶️", ephemeral=True)
        else:
            await interaction.response.send_message("لا يوجد مقطع يعمل!", ephemeral=True)

    @discord.ui.button(label="تخطي", style=discord.ButtonStyle.secondary, emoji="⏭️", custom_id="btn_skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("تم تخطي المقطع ⏭️", ephemeral=True)
        else:
            await interaction.response.send_message("لا يوجد شيء لتخطيه!", ephemeral=True)

    @discord.ui.button(label="إيقاف البوت", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="btn_stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            music_queues[interaction.guild.id] = []
            await vc.disconnect()
            await update_dashboard(interaction.guild, None, None)
            await interaction.response.send_message("تم إيقاف البوت ومسح الطابور ⏹️", ephemeral=True)
        else:
            await interaction.response.send_message("البوت ليس في روم صوتي!", ephemeral=True)
# --- Bot Events & Commands ---


@bot.event
async def on_ready():
    bot.add_view(StaticPlayerView())  # لتفعيل الأزرار دائماً
    await bot.tree.sync()

    # --- استعادة اللوحات المحفوظة تلقائياً ---
    saved_dashboards = load_dashboards()
    for guild_id_str, data in saved_dashboards.items():
        try:
            guild_id = int(guild_id_str)
            channel_id = data.get("channel_id")
            message_id = data.get("message_id")

            channel = bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="🎧 المشغل الاحترافي",
                    description="في انتظار طلباتكم...\nاضغط على زر 🔍 **بحث / تشغيل** لبدء الاستماع.",
                    color=0x2b2d31
                )
                embed.set_image(url="https://i.imgur.com/zahHM79.jpg?v=1")

                try:
                    # محاولة جلب الرسالة القديمة وتحديثها
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(embed=embed, view=StaticPlayerView())
                    dashboards[guild_id] = msg
                    log_to_gui(
                        f"[SYSTEM] Restored dashboard for guild: {guild_id}")
                except discord.NotFound:
                    # إذا تم حذف الرسالة من الشات، نرسل واحدة جديدة تلقائياً
                    msg = await channel.send(embed=embed, view=StaticPlayerView())
                    dashboards[guild_id] = msg
                    saved_dashboards[guild_id_str]["message_id"] = msg.id
                    save_dashboards(saved_dashboards)
                    log_to_gui(
                        f"[SYSTEM] Recreated dashboard for guild: {guild_id}")
        except Exception as e:
            log_to_gui(f"[ERROR] Failed to restore dashboard: {e}")

    log_to_gui(f"[SYSTEM] Logged in successfully as: {bot.user.name}")
    update_gui_status("ONLINE", "#00E676")
    update_ping_task.start()


@bot.tree.command(name="setup", description="إنشاء لوحة التحكم الثابتة في هذا الشات (للمسؤولين)")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎧 المشغل الاحترافي",
        description="في انتظار طلباتكم...\nاضغط على زر 🔍 **بحث / تشغيل** لبدء الاستماع.",
        color=0x2b2d31
    )
    embed.set_image(url="https://i.imgur.com/XqQM3yV.gif")

    await interaction.response.send_message("تم إنشاء اللوحة بنجاح (هذه الرسالة ستختفي)", ephemeral=True)
    msg = await interaction.channel.send(embed=embed, view=StaticPlayerView())
    dashboards[interaction.guild.id] = msg

    # حفظ الروم والرسالة في الملف ليتم استعادتها تلقائياً عند التشغيل القادم
    saved_dashboards = load_dashboards()
    saved_dashboards[str(interaction.guild.id)] = {
        "channel_id": interaction.channel.id,
        "message_id": msg.id
    }
    save_dashboards(saved_dashboards)
    log_to_gui(
        f"[SYSTEM] Setup completed and saved for guild: {interaction.guild.id}")


@tasks.loop(seconds=5)
async def update_ping_task():
    if bot.is_ready() and gui_instance:
        ping = round(bot.latency * 1000)
        gui_instance.update_ping(f"{ping} ms")

# --- Bridge Functions & CustomTkinter UI ---
gui_instance = None


def log_to_gui(message):
    if gui_instance:
        gui_instance.append_log(message)
    else:
        print(message)


def update_gui_status(status_text, color):
    if gui_instance:
        gui_instance.update_status(status_text, color)


def run_async_bot(token, act_type, act_text):
    global bot_loop, is_running
    is_running = True
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    act = discord.Activity(type=getattr(discord.ActivityType, act_type.lower(
    ), discord.ActivityType.listening), name=act_text)
    try:
        bot_loop.run_until_complete(bot.start(token))
    except Exception as e:
        log_to_gui(f"[CRITICAL ERROR] Bot stopped: {str(e)}")
        update_gui_status("OFFLINE", "#FF5252")
    finally:
        is_running = False
        update_gui_status("OFFLINE", "#FF5252")


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class BotDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        global gui_instance
        gui_instance = self
        self.title("Discord Audio Engine — Professional Dashboard")
        self.geometry("850x600")
        self.minsize(750, 500)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.config_data = load_config()

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        ctk.CTkLabel(self.sidebar_frame, text="⚡ AUDIO BOT PRO", font=ctk.CTkFont(
            size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        ctk.CTkLabel(self.sidebar_frame, text="SYSTEM STATUS:", font=ctk.CTkFont(
            size=12, weight="bold"), text_color="gray").grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.status_badge = ctk.CTkButton(self.sidebar_frame, text="OFFLINE", font=ctk.CTkFont(
            size=12, weight="bold"), fg_color="#FF5252", hover=False, height=28)
        self.status_badge.grid(row=2, column=0, padx=20,
                               pady=(5, 15), sticky="ew")
        ctk.CTkLabel(self.sidebar_frame, text="LATENCY (PING):", font=ctk.CTkFont(
            size=12, weight="bold"), text_color="gray").grid(row=3, column=0, padx=20, pady=(5, 0), sticky="w")
        self.ping_value = ctk.CTkLabel(
            self.sidebar_frame, text="-- ms", font=ctk.CTkFont(size=16, weight="bold"))
        self.ping_value.grid(row=4, column=0, padx=20,
                             pady=(0, 15), sticky="w")
# إضافة زر دعوة البوت
        self.invite_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=" دعوة البوت لسيرفرك",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#5865F2",  # لون ديسكورد الرسمي
            hover_color="#4752C4",
            command=self.open_invite_link
        )
        self.invite_btn.grid(row=5, column=0, padx=20,
                             pady=(15, 10), sticky="ew")
        # Main Area
        self.main_frame = ctk.CTkFrame(
            self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Control Card
        self.control_card = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.control_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.control_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.control_card, text="Bot Token:", font=ctk.CTkFont(
            weight="bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.token_entry = ctk.CTkEntry(
            self.control_card, placeholder_text="Paste your Discord Bot Token here...", show="•")
        self.token_entry.grid(row=0, column=1, padx=(
            0, 10), pady=15, sticky="ew")
        self.token_entry.insert(0, self.config_data.get("token", ""))
        self.show_token_btn = ctk.CTkButton(
            self.control_card, text="👁️", width=40, command=self.toggle_token_visibility)
        self.show_token_btn.grid(row=0, column=2, padx=(0, 15), pady=15)

        self.btn_frame = ctk.CTkFrame(
            self.control_card, fg_color="transparent")
        self.btn_frame.grid(row=1, column=0, columnspan=3,
                            padx=15, pady=(0, 15), sticky="ew")
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)
        self.start_btn = ctk.CTkButton(self.btn_frame, text="▶ START BOT", font=ctk.CTkFont(
            weight="bold"), fg_color="#00E676", hover_color="#00C853", text_color="black", height=40, command=self.start_bot)
        self.start_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.stop_btn = ctk.CTkButton(self.btn_frame, text="■ STOP BOT", font=ctk.CTkFont(
            weight="bold"), fg_color="#FF5252", hover_color="#D50000", height=40, state="disabled", command=self.stop_bot)
        self.stop_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Activity Card
        self.act_card = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.act_card.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.act_card.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(self.act_card, text="Presence:", font=ctk.CTkFont(
            weight="bold")).grid(row=0, column=0, padx=15, pady=12, sticky="w")
        self.act_type_combo = ctk.CTkComboBox(
            self.act_card, values=["Listening", "Playing", "Watching"], width=120)
        self.act_type_combo.grid(row=0, column=1, padx=(0, 10), pady=12)
        self.act_type_combo.set(
            self.config_data.get("activity_type", "Listening"))
        self.act_text_entry = ctk.CTkEntry(
            self.act_card, placeholder_text="Status text (e.g., /play | /stop)")
        self.act_text_entry.grid(
            row=0, column=2, padx=(0, 15), pady=12, sticky="ew")
        self.act_text_entry.insert(0, self.config_data.get(
            "activity_text", "/play | /stop"))

        # Log Card
        self.log_card = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.log_card.grid(row=2, column=0, sticky="nsew")
        self.log_card.grid_columnconfigure(0, weight=1)
        self.log_card.grid_rowconfigure(1, weight=1)
        log_header = ctk.CTkFrame(self.log_card, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        log_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_header, text="💻 LIVE ACTIVITY CONSOLE", font=ctk.CTkFont(
            size=12, weight="bold"), text_color="gray").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_header, text="Clear Logs", width=80, height=24, font=ctk.CTkFont(
            size=11), command=self.clear_logs).grid(row=0, column=1, sticky="e")
        self.log_textbox = ctk.CTkTextbox(self.log_card, font=ctk.CTkFont(
            family="Consolas", size=12), wrap="word")
        self.log_textbox.grid(row=1, column=0, padx=15,
                              pady=(0, 15), sticky="nsew")
        self.log_textbox.insert(
            "end", "[SYSTEM] Dashboard initialized. Ready to start.\n")
        self.log_textbox.configure(state="disabled")
        # أمر لتشغيل البوت تلقائياً بعد نصف ثانية من فتح الواجهة
        self.after(500, self.start_bot)

    def toggle_token_visibility(self):
        current = self.token_entry.cget("show")
        if current == "•":
            self.token_entry.configure(show="")
            self.show_token_btn.configure(text="🔒")
        else:
            self.token_entry.configure(show="•")
            self.show_token_btn.configure(text="👁️")
    def open_invite_link(self):
        # استبدل هذا الرابط برابط دعوة البوت الخاص بك
        invite_url = "https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands"
        
        self.append_log("[SYSTEM] Opening invite link in browser...")
        webbrowser.open(invite_url)
    def append_log(self, text):
        def _update():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", text + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _update)

    def clear_logs(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def update_status(self, text, color):
        def _update():
            self.status_badge.configure(text=text, fg_color=color)
            if text == "ONLINE":
                self.start_btn.configure(state="disabled", fg_color="gray")
                self.stop_btn.configure(state="normal", fg_color="#FF5252")
            else:
                self.start_btn.configure(state="normal", fg_color="#00E676")
                self.stop_btn.configure(state="disabled", fg_color="gray")
                self.update_ping("-- ms")
        self.after(0, _update)

    def update_ping(self, ping_text):
        def _update(): self.ping_value.configure(text=ping_text)
        self.after(0, _update)

    def start_bot(self):
        global bot_thread, is_running
        token = self.token_entry.get().strip()
        if not token:
            self.append_log("[ERROR] Cannot start: Bot Token is empty!")
            return
        act_type = self.act_type_combo.get()
        act_text = self.act_text_entry.get().strip()
        save_config({"token": token, "activity_type": act_type,
                    "activity_text": act_text})
        if not is_running:
            self.append_log("[SYSTEM] Connecting to Discord Gateway...")
            self.update_status("CONNECTING...", "#FFAB00")
            bot_thread = threading.Thread(target=run_async_bot, args=(
                token, act_type, act_text), daemon=True)
            bot_thread.start()

    def stop_bot(self):
        global bot_loop
        if bot_loop and bot.is_ready():
            self.append_log("[SYSTEM] Shutting down bot engine...")
            update_ping_task.stop()
            asyncio.run_coroutine_threadsafe(bot.close(), bot_loop)


if __name__ == "__main__":
    app = BotDashboard()
    app.mainloop()

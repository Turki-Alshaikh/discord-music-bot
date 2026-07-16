import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import imageio_ffmpeg
from keep_alive import keep_alive

# --- إعدادات المحرك الصوتي ---
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# إعدادات yt-dlp للبحث السريع والبث المباشر بأعلى جودة
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',  # يتيح البحث بالاسم إذا لم يكن المدخل رابطاً
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

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
        # جلب البيانات سواء كانت رابط مباشر أو كلمات بحث
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        # إذا كان نتيجة بحث، نأخذ أول فيديو يتطابق مع الاسم
        if 'entries' in data:
            data = data['entries'][0]
            
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH, **FFMPEG_OPTIONS), data=data)

# --- أحداث البوت ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'🟢 تم تشغيل البوت بنجاح باسم: {bot.user.name}')
    print('✅ الأوامر الجاهزة للاستخدام في السيرفر: /play | /stop')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/play | /stop"))

# --- أمر التشغيل (/play) ---
@bot.tree.command(name="play", description="تشغيل مقطع صوتي عن طريق الرابط أو كتابة اسمه مباشرة")
@app_commands.describe(query="ضع رابط اليوتيوب أو اكتب اسم المقطع للبحث عنه")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    # التحرك لتأكد أن المستخدم داخل روم صوتي
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ **يجب أن تدخل روم صوتي أولاً لتشغيل الصوت!**")
        return

    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client

    # الاتصال بالروم الصوتي أو الانتقال لروم المستخدم
    if not vc:
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)

    # إيقاف أي مقطع يعمل حالياً لتشغيل الجديد
    if vc.is_playing():
        vc.stop()

    try:
        player = await YTDLSource.from_query(query, loop=bot.loop)
        vc.play(player, after=lambda e: print(f'خطأ في التشغيل: {e}') if e else None)

        embed = discord.Embed(
            title="▶️ جاري التشغيل الآن",
            description=f"**[{player.title}]({player.webpage_url})**",
            color=0x00E676
        )
        embed.set_footer(text=f"طلب بواسطة: {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Error: {e}")
        await interaction.followup.send("❌ **تعذر العثور على المقطع أو تشغيله، تأكد من الاسم أو الرابط.**")

# --- أمر الإيقاف (/stop) ---
@bot.tree.command(name="stop", description="إيقاف الصوت ومغادرة الروم الصوتي فوراً")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        if vc.is_playing():
            vc.stop()
        await vc.disconnect()
        await interaction.response.send_message("⏹️ **تم إيقاف الصوت ومغادرة الروم.**")
    else:
        await interaction.response.send_message("⚠️ **البوت ليس متصلاً بأي روم صوتي حالياً.**", ephemeral=True)

# ضع توكن البوت الخاص بك هنا بين التنصيص
BOT_TOKEN = "MTE5NDEwMzgyMTcxOTMxNDU0Mg.G4Id_A.2oEV1OUdDv59YB4WN5hmrYUpIaKJu0vQRSXVuA"

if __name__ == "__main__":
    keep_alive()  # <-- هذا السطر اللي يشغل سيرفر الويب بالخلفية
    bot.run(BOT_TOKEN)
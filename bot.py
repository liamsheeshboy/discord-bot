import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import os
import json
from datetime import timedelta

# =========================
# INTENTS + BOT SETUP
# =========================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.invites = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CONFIG - ALL IN ONE PLACE
# =========================
TOKEN = "MTUxNDA2NDExMjE3MzE4NzExNg.GFlBuA.AHvmpi10ZHYSncZ4brEVAV_ynmJNzlyR2Oy8nY"  # ← שנה רק כאן

# CHANNELS
ANNOUNCEMENT_CHANNEL_ID = 1514127301892243496
WELCOME_CHANNEL_ID      = 1514058728981139606
RULES_CHANNEL_ID        = 1514058847793184908
TICKET_CATEGORY_ID      = 1514129029140054056

# ROLES
MEMBER_ROLE_ID = 1514122683451965520
STAFF_ROLE_ID  = 1514129192185364580

BANNER_PATH = "banner.png"
REPUTATION_FILE = "reputation.json"

# =========================
# REPUTATION SYSTEM
# =========================
def load_reputation():
    if os.path.exists(REPUTATION_FILE):
        with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_reputation(data):
    with open(REPUTATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

rep_data = load_reputation()

# =========================
# RULES VIEW
# =========================
class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Accept Rules", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(1514122683451965520)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ You accepted the rules and received the **Member** role!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Member role not found.", ephemeral=True)

# =========================
# TICKET VIEWS
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Open Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message("You already have an open ticket 😛", ephemeral=True)
            return

        category = guild.get_channel(1514129029140054056)
        staff_role = guild.get_role(1514129192185364580)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites
        )

        await channel.send(f"{user.mention} Thank you for opening a ticket! 😛\nStaff will be with you shortly.")
        await channel.send(view=CloseTicketView())
        await interaction.response.send_message(f"✅ Your ticket has been created: {channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await interaction.channel.delete()

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")


@bot.event
async def on_member_join(member):
    guild = member.guild
    member_count = guild.member_count

    try:
        banner = Image.open(BANNER_PATH).convert("RGBA")
        draw = ImageDraw.Draw(banner)

        try:
            font_big = ImageFont.truetype("arial.ttf", 42)
            font_small = ImageFont.truetype("arial.ttf", 30)
        except:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Avatar
        avatar_asset = member.display_avatar.with_size(256)
        avatar_bytes = await avatar_asset.read()
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar = avatar.resize((200, 200))

        mask = Image.new("L", (200, 200), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 200, 200), fill=255)

        avatar_circle = Image.new("RGBA", (200, 200))
        avatar_circle.paste(avatar, (0, 0), mask)

        banner.paste(avatar_circle, (40, 40), avatar_circle)

        # Text
        draw.text((260, 60), f"Welcome {member.display_name}!", fill="white", font=font_big)
        draw.text((260, 130), f"Members: {member_count}", fill="white", font=font_small)

        buffer = io.BytesIO()
        banner.save(buffer, format="PNG")
        buffer.seek(0)

        channel = bot.get_channel(1514058728981139606)
        if channel:
            await channel.send(file=discord.File(fp=buffer, filename="welcome.png"))

    except Exception as e:
        print(f"Welcome image error: {e}")
        channel = bot.get_channel(1514058728981139606)
        if channel:
            await channel.send(f"Welcome {member.mention}! 🎉")


# =========================
# REPUTATION COMMANDS
# =========================
@bot.command()
async def rep(ctx, member: discord.Member = None):
    """Check someone's reputation"""
    if member is None:
        member = ctx.author

    user_id = str(member.id)
    reps = rep_data.get(user_id, 0)

    embed = discord.Embed(
        title="Reputation",
        description=f"**{member.display_name}** has **{reps}** reputation points.",
        color=0x00ff99
    )
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def addrep(ctx, member: discord.Member, amount: int):
    """Add reputation to a member"""
    user_id = str(member.id)
    rep_data[user_id] = rep_data.get(user_id, 0) + amount
    save_reputation(rep_data)
    await ctx.send(f"✅ Added **{amount}** reputation to {member.mention}. Now has **{rep_data[user_id]}**.")


@bot.command()
@commands.has_permissions(administrator=True)
async def removerep(ctx, member: discord.Member, amount: int):
    """Remove reputation from a member"""
    user_id = str(member.id)
    rep_data[user_id] = max(0, rep_data.get(user_id, 0) - amount)
    save_reputation(rep_data)
    await ctx.send(f"✅ Removed **{amount}** reputation from {member.mention}. Now has **{rep_data[user_id]}**.")


# =========================
# ANNOUNCEMENT COMMAND
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, message):
    """Send an announcement"""
    channel = bot.get_channel(1514127301892243496)
    if not channel:
        return await ctx.send("Announcement channel not found.")

    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=0xffcc00
    )
    embed.set_footer(text=f"Announced by {ctx.author}")
    
    await channel.send(embed=embed)
    await ctx.send("✅ Announcement sent!")


# =========================
# RULES COMMAND
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def rules(ctx):
    """Send rules panel"""
    channel = bot.get_channel(RULES_CHANNEL_ID)
    if not channel:
        return await ctx.send("❌ Rules channel not found.")

    # === בדיקת קובץ באנר ===
    if not os.path.exists(BANNER_PATH):
        return await ctx.send(f"❌ **שגיאה:** לא נמצא קובץ banner!\n"
                             f"חיפשתי כאן: `{os.path.abspath(BANNER_PATH)}`")

    try:
        embed = discord.Embed(
            title="📜 Server Rules",
            description="""
**1.** Be respectful to all members. No harassment, hate speech, or discrimination.
**2.** No spamming or flooding.
**3.** No advertising without permission.
**4.** Do not share personal information.
**5.** Keep content appropriate (no NSFW).
**6.** Use channels correctly.
**7.** Do not impersonate others.
**8.** Staff decisions are final.
**9.** Have fun and be positive 😛
            """,
            color=0x2b2d31
        )

        file = discord.File(BANNER_PATH, filename="banner.png")
        embed.set_image(url="attachment://banner.png")

        await channel.send(file=file, embed=embed, view=RulesView())
        await ctx.send("✅ Rules panel sent successfully!")

    except Exception as e:
        await ctx.send(f"❌ Error sending rules: {e}")

# =========================
# TICKETS COMMAND
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def tickets(ctx):
    """Send ticket panel"""
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Click the button below to open a ticket with the staff team.",
        color=0x00ff99
    )
    await ctx.send(embed=embed, view=TicketView())


# =========================
# MODERATION COMMANDS
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member} has been banned.")


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member} has been kicked.")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason=None):
    """Timeout a member for X minutes"""
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"✅ {member} has been timed out for {minutes} minutes.")
    except Exception as e:
        await ctx.send(f"Error: {e}")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    """Remove timeout"""
    try:
        await member.timeout(None)
        await ctx.send(f"✅ Timeout removed from {member}.")
    except Exception as e:
        await ctx.send(f"Error: {e}")


@bot.command()
async def test(ctx):
    await ctx.send("Bot is working 😛")

    # =========================
# REVIEWS / FEEDBACK SYSTEM
# =========================

class ReviewModal(discord.ui.Modal, title="📝 Write a Review"):
    review_title = discord.ui.TextInput(
        label="Title (optional)",
        placeholder="e.g. Great server!",
        required=False,
        max_length=100
    )
    
    review_content = discord.ui.TextInput(
        label="Your Review",
        style=discord.TextStyle.paragraph,
        placeholder="Write your honest feedback here...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⭐ New Review",
            description=self.review_content.value,
            color=0xffd700
        )
        
        if self.review_title.value:
            embed.title = f"⭐ {self.review_title.value}"
        
        embed.set_author(
            name=interaction.user.display_name, 
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_footer(text=f"Reviewed by {interaction.user} • ID: {interaction.user.id}")

        # חיפוש חדר לפי שם
        review_channel = discord.utils.get(interaction.guild.text_channels, name="reputation🟢")
        
        if review_channel:
            await review_channel.send(embed=embed)
            await interaction.response.send_message("✅ Thank you for your review! It has been posted in #REPUTATION.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Could not find the **REPUTATION** channel.", ephemeral=True)


class ReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Write Review", style=discord.ButtonStyle.blurple, emoji="⭐")
    async def write_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReviewModal())


# =========================
# SEND REVIEW PANEL COMMAND
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def reviews(ctx):
    """Send the review panel"""
    embed = discord.Embed(
        title="📊 Server Reviews & Feedback",
        description="Click the button below to share your honest opinion about the server.\nYour feedback is very important to us!",
        color=0xffd700
    )
    embed.set_footer(text="All reviews are public")
    
    await ctx.send(embed=embed, view=ReviewView())
    await ctx.send("✅ Review panel has been sent!")


# =========================
# RUN BOT
# =========================
bot.run("MTUxNDA2NDExMjE3MzE4NzExNg.GFlBuA.AHvmpi10ZHYSncZ4brEVAV_ynmJNzlyR2Oy8nY")
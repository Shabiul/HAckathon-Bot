import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
from scrapers import HackathonScraper
from datetime import datetime
from utils import format_hackathon_message, get_common_timezones, format_date
import pytz
from dateutil import parser
from app import db_session
from models import User, Team, team_members
from badge_utils import initialize_badges, check_and_award_badges, get_user_badges

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot with all required intents
intents = discord.Intents.default()
intents.message_content = True  # For reading message content
intents.members = True  # For member-related features
intents.guilds = True  # For server-related features
intents.voice_states = True  # For voice features
intents.guild_messages = True  # For message-related features
intents.reactions = True  # For reaction features

# Initialize bot and tree for slash commands
class HackathonBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)
        self.scraper = HackathonScraper()
        self.notification_channels = set()
        self.user_timezones = {}

    async def setup_hook(self):
        await self.tree.sync()
        initialize_badges()
        self.check_hackathons.start()

bot = HackathonBot()
tree = bot.tree

@bot.event
async def on_ready():
    """Called when the bot has successfully connected to Discord"""
    logger.info(f'Successfully logged in as {bot.user} (ID: {bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    for guild in bot.guilds:
        logger.info(f'Connected to guild: {guild.name} (ID: {guild.id})')
    logger.info('Started periodic hackathon check task')

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler for bot events"""
    logger.error(f'Error in {event}:', exc_info=True)

@tree.command(name="hackathons", description="Shows current hackathons from various platforms")
async def get_hackathons(interaction: discord.Interaction):
    """Command to fetch current hackathons"""
    try:
        hackathons, _ = await bot.scraper.get_all_hackathons()

        if not hackathons:
            await interaction.response.send_message("No active hackathons found at the moment.")
            return

        # Get user's preferred timezone
        user_tz = bot.user_timezones.get(interaction.user.id)

        # Create an embedded message
        embed = discord.Embed(
            title="Current Hackathons",
            description=f"Here are the active hackathons{f' (Times in {user_tz})' if user_tz else ' (Times in UTC)'}:",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        for hackathon in hackathons:
            embed.add_field(
                name=hackathon['title'],
                value=f"Platform: {hackathon['platform']}\n"
                      f"Date: {format_date(hackathon['date'], user_tz)}\n"
                      f"Link: {hackathon['link']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Error fetching hackathons: {str(e)}")
        await interaction.response.send_message("Sorry, there was an error fetching hackathon information.")

@tree.command(name="set_timezone", description="Set your preferred timezone for hackathon times")
async def set_timezone(interaction: discord.Interaction, timezone: str = None):
    if not timezone:
        common_tzs = get_common_timezones()
        embed = discord.Embed(
            title="Available Timezones",
            description="Use `/set_timezone <timezone>` with one of these timezones:",
            color=discord.Color.blue()
        )
        for tz in common_tzs:
            current_time = datetime.now(pytz.timezone(tz))
            embed.add_field(
                name=tz,
                value=f"Current time: {current_time.strftime('%H:%M %Z')}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)
        return

    try:
        # Validate timezone
        pytz.timezone(timezone)
        bot.user_timezones[interaction.user.id] = timezone
        await interaction.response.send_message(f"✅ Your timezone has been set to {timezone}!")
    except Exception as e:
        logger.error(f"Error setting timezone: {str(e)}")
        await interaction.response.send_message("❌ Invalid timezone! Use `/set_timezone` to see available options.")

@tree.command(name="create_team", description="Create a new team for a hackathon")
async def create_team(
    interaction: discord.Interaction,
    hackathon_id: str,
    team_name: str,
    description: str = None
):
    """Create a new team for a hackathon"""
    try:
        # Get or create user
        user = User.query.filter_by(discord_id=str(interaction.user.id)).first()
        if not user:
            user = User(discord_id=str(interaction.user.id), username=interaction.user.name)
            db_session.add(user)
            db_session.commit()

        # Check if team name already exists for this hackathon
        existing_team = Team.query.filter_by(hackathon_id=hackathon_id, name=team_name).first()
        if existing_team:
            await interaction.response.send_message("❌ A team with this name already exists for this hackathon!")
            return

        # Create new team
        team = Team(
            name=team_name,
            hackathon_id=hackathon_id,
            leader_id=user.id,
            description=description
        )
        db_session.add(team)

        # Add creator as first member
        team.members.append(user)
        db_session.commit()

        # After successful team creation, check for new badges
        new_badges = check_and_award_badges(user.id)
        if new_badges:
            badge_message = "🎉 You've earned new badges!\n"
            for badge in new_badges:
                badge_message += f"{badge['icon']} **{badge['name']}**: {badge['description']}\n"
            await interaction.followup.send(badge_message)

        embed = discord.Embed(
            title="✅ Team Created Successfully!",
            description=f"Team: {team_name}\nLeader: {interaction.user.name}",
            color=discord.Color.green()
        )
        if description:
            embed.add_field(name="Description", value=description, inline=False)

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Error creating team: {str(e)}")
        await interaction.response.send_message("❌ There was an error creating your team. Please try again.")

@tree.command(name="join_team", description="Join an existing team")
async def join_team(interaction: discord.Interaction, team_name: str, hackathon_id: str):
    """Join an existing team"""
    try:
        # Get or create user
        user = User.query.filter_by(discord_id=str(interaction.user.id)).first()
        if not user:
            user = User(discord_id=str(interaction.user.id), username=interaction.user.name)
            db_session.add(user)
            db_session.commit()

        # Find team
        team = Team.query.filter_by(name=team_name, hackathon_id=hackathon_id).first()
        if not team:
            await interaction.response.send_message("❌ Team not found!")
            return

        # Check if user is already in the team
        if user in team.members:
            await interaction.response.send_message("❌ You are already a member of this team!")
            return

        # Add user to team
        team.members.append(user)
        db_session.commit()

        # After successfully joining, check for new badges
        new_badges = check_and_award_badges(user.id)
        if new_badges:
            badge_message = "🎉 You've earned new badges!\n"
            for badge in new_badges:
                badge_message += f"{badge['icon']} **{badge['name']}**: {badge['description']}\n"
            await interaction.followup.send(badge_message)

        await interaction.response.send_message(f"✅ You have successfully joined team {team_name}!")

    except Exception as e:
        logger.error(f"Error joining team: {str(e)}")
        await interaction.response.send_message("❌ There was an error joining the team. Please try again.")

@tree.command(name="badges", description="Display your earned achievement badges")
async def show_badges(interaction: discord.Interaction):
    """Show your earned badges"""
    try:
        user = User.query.filter_by(discord_id=str(interaction.user.id)).first()
        if not user:
            await interaction.response.send_message("❌ You haven't participated in any teams yet!")
            return

        badges = get_user_badges(user.id)

        if not badges:
            await interaction.response.send_message("You haven't earned any badges yet. Keep participating to earn some! 🎯")
            return

        embed = discord.Embed(
            title=f"{interaction.user.name}'s Badges",
            description="Here are your earned achievements:",
            color=discord.Color.gold()
        )

        for badge in badges:
            embed.add_field(
                name=f"{badge.icon} {badge.name}",
                value=f"{badge.description}\n*{badge.criteria}*",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        logger.error(f"Error showing badges: {str(e)}")
        await interaction.response.send_message("❌ There was an error fetching your badges. Please try again.")

@tasks.loop(hours=6)
async def check_hackathons():
    """Periodic task to check for new hackathons and notify channels"""
    logger.info("Checking for new hackathons...")
    try:
        _, new_hackathons = await bot.scraper.get_all_hackathons()

        if new_hackathons and bot.notification_channels:
            embed = discord.Embed(
                title="🆕 New Hackathons Found!",
                description="Here are the newly added hackathons:",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            for hackathon in new_hackathons:
                embed.add_field(
                    name=hackathon['title'],
                    value=f"Platform: {hackathon['platform']}\n"
                          f"Date: {format_date(hackathon['date'])}\n"
                          f"Link: {hackathon['link']}",
                    inline=False
                )

            for channel_id in bot.notification_channels:
                try:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error sending notification to channel {channel_id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in periodic hackathon check: {str(e)}")

def run_bot():
    """Function to run the bot with error handling"""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("No Discord token found! Please ensure DISCORD_TOKEN is set in environment variables.")
        return

    try:
        logger.info("Attempting to connect to Discord...")
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Failed to log in to Discord. Please verify your token is correct.")
    except discord.PrivilegedIntentsRequired:
        logger.error("Bot requires privileged intents that aren't enabled in the Discord Developer Portal. "
                    "Please enable the required intents (Server Members Intent, Message Content Intent) "
                    "in your bot's settings at https://discord.com/developers/applications")
    except Exception as e:
        logger.error(f"Unexpected error while running bot: {str(e)}", exc_info=True)
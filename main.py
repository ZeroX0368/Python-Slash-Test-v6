# python slash v4 đang test 
import discord
from discord.ext import commands
import json
import os
import asyncio
import random
from datetime import datetime, timedelta

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Giveaway Button View
class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label='🎉 Join Giveaway', style=discord.ButtonStyle.primary, custom_id='join_giveaway')
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaways = load_giveaways()
        
        if self.giveaway_id not in giveaways:
            await interaction.response.send_message("This giveaway no longer exists.", ephemeral=True)
            return
            
        giveaway_data = giveaways[self.giveaway_id]
        
        if giveaway_data.get('ended', False):
            await interaction.response.send_message("This giveaway has already ended.", ephemeral=True)
            return
            
        # Check if user already joined
        if 'participants' not in giveaway_data:
            giveaway_data['participants'] = []
            
        if interaction.user.id in giveaway_data['participants']:
            await interaction.response.send_message("You have already joined this giveaway!", ephemeral=True)
            return
            
        # Add user to participants
        giveaway_data['participants'].append(interaction.user.id)
        giveaways[self.giveaway_id] = giveaway_data
        save_giveaways(giveaways)
        
        # Update the embed to show new participant count
        try:
            participants_count = len(giveaway_data['participants'])
            end_time = giveaway_data['end_time']
            
            updated_embed = discord.Embed(
                title="🎉 GIVEAWAY 🎉",
                description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** {giveaway_data['winners']}\n**Ends:** <t:{int(end_time)}:R>\n**Participants:** {participants_count}\n\nClick the button below to join!",
                color=discord.Color.blue()
            )
            
            # Get host user for footer
            try:
                host_user = await interaction.client.fetch_user(giveaway_data['host_id'])
                updated_embed.set_footer(text=f"Hosted by {host_user.display_name}")
            except:
                updated_embed.set_footer(text="Hosted by Unknown User")
            
            await interaction.message.edit(embed=updated_embed, view=self)
        except Exception as e:
            print(f"Error updating giveaway embed: {e}")
        
        await interaction.response.send_message("✅ You have successfully joined the giveaway!", ephemeral=True)

# Data storage files
WHITELIST_FILE = 'whitelist.json'
GIVEAWAYS_FILE = 'giveaways.json'
WELCOME_FILE = 'welcome.json'
STICKIES_FILE = 'stickies.json'
AFK_FILE = 'afk.json'

# Bot start time for uptime tracking
bot_start_time = datetime.utcnow()

def load_whitelist():
    """Load whitelist from JSON file"""
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_whitelist(whitelist):
    """Save whitelist to JSON file"""
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(whitelist, f, indent=2)

def load_giveaways():
    """Load giveaways from JSON file"""
    if os.path.exists(GIVEAWAYS_FILE):
        with open(GIVEAWAYS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_giveaways(giveaways):
    """Save giveaways to JSON file"""
    with open(GIVEAWAYS_FILE, 'w') as f:
        json.dump(giveaways, f, indent=2)

def load_welcome():
    """Load welcome settings from JSON file"""
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_welcome(welcome_data):
    """Save welcome settings to JSON file"""
    with open(WELCOME_FILE, 'w') as f:
        json.dump(welcome_data, f, indent=2)

def load_stickies():
    """Load sticky messages from JSON file"""
    if os.path.exists(STICKIES_FILE):
        with open(STICKIES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_stickies(stickies_data):
    """Save sticky messages to JSON file"""
    with open(STICKIES_FILE, 'w') as f:
        json.dump(stickies_data, f, indent=2)

def load_afk():
    """Load AFK data from JSON file"""
    if os.path.exists(AFK_FILE):
        with open(AFK_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_afk(afk_data):
    """Save AFK data to JSON file"""
    with open(AFK_FILE, 'w') as f:
        json.dump(afk_data, f, indent=2)

def parse_duration(duration_str):
    """Parse duration string like '1h', '30m', '2d' into seconds"""
    duration_str = duration_str.lower()
    multipliers = {
        's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
        'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
        'h': 3600, 'hour': 3600, 'hours': 3600,
        'd': 86400, 'day': 86400, 'days': 86400,
        'w': 604800, 'week': 604800, 'weeks': 604800
    }

    import re
    match = re.match(r'(\d+)([a-z]+)', duration_str)
    if not match:
        return None

    amount, unit = match.groups()
    if unit in multipliers:
        return int(amount) * multipliers[unit]
    return None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

    # Add persistent views for existing giveaways
    giveaways = load_giveaways()
    for message_id, giveaway_data in giveaways.items():
        if not giveaway_data.get('ended', False):
            view = GiveawayView(message_id)
            bot.add_view(view)

    # Start giveaway checker
    bot.loop.create_task(check_giveaways())
    # Start sticky message checker
    bot.loop.create_task(check_stickies())

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a new server"""
    # Find the first text channel the bot can send messages to
    text_channel = None
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            text_channel = channel
            break
    
    if text_channel:
        embed = discord.Embed(
            title="👋 Thanks for adding me!",
            description=f"Hello **{guild.name}**! I'm your new Discord bot assistant.\n\n"
                       f"🎉 **Features:**\n"
                       f"• Giveaway management\n"
                       f"• Welcome system\n"
                       f"• Role management\n"
                       f"• Sticky messages\n"
                       f"• AFK system\n"
                       f"• Moderation tools\n\n"
                       f"📚 Use `/help` to see all available commands!\n"
                       f"🔧 Use `/welcome create` to set up welcome messages\n"
                       f"🎁 Use `/giveaway create` to start giveaways",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Added to {guild.member_count} members • Thanks for choosing our bot!")
        
        try:
            await text_channel.send(embed=embed)
        except Exception as e:
            print(f"Error sending join message to {guild.name}: {e}")
    else:
        print(f"Could not find a text channel to send join message in {guild.name}")

@bot.event
async def on_member_join(member):
    """Handle new member joins for welcome system"""
    welcome_data = load_welcome()
    guild_id = str(member.guild.id)

    if guild_id in welcome_data and welcome_data[guild_id].get('enabled', False):
        welcome_info = welcome_data[guild_id]
        channel = bot.get_channel(welcome_info['channel_id'])

        if channel:
            message = welcome_info['message']
            # Replace placeholders
            message = message.replace('{user}', member.mention)
            message = message.replace('{username}', member.display_name)
            message = message.replace('{server}', member.guild.name)
            message = message.replace('{membercount}', str(member.guild.member_count))

            try:
                await channel.send(message)
            except Exception as e:
                print(f"Error sending welcome message: {e}")

@bot.event
async def on_message(message):
    """Handle AFK system and sticky messages"""
    if message.author.bot:
        return

    # Handle sticky messages immediately
    stickies_data = load_stickies()
    channel_id = str(message.channel.id)

    if channel_id in stickies_data and stickies_data[channel_id].get('active', False):
        sticky_info = stickies_data[channel_id]

        # Check if the message is not the sticky message itself
        if str(message.id) != str(sticky_info.get('message_id')):
            try:
                # Delete old sticky message
                try:
                    old_sticky = await message.channel.fetch_message(sticky_info['message_id'])
                    await old_sticky.delete()
                except:
                    pass

                # Send new sticky message
                new_sticky = await message.channel.send(sticky_info['content'])
                sticky_info['message_id'] = new_sticky.id
                stickies_data[channel_id] = sticky_info
                save_stickies(stickies_data)

            except Exception as e:
                print(f"Error handling sticky message in channel {channel_id}: {e}")

    # AFK system
    afk_data = load_afk()
    user_id = str(message.author.id)

    # Check if user was AFK and remove them
    if user_id in afk_data:
        del afk_data[user_id]
        save_afk(afk_data)
        try:
            await message.channel.send(f"Welcome back {message.author.mention}! I removed your AFK status.")
        except:
            pass

    # Check for AFK mentions
    for mention in message.mentions:
        mention_id = str(mention.id)
        if mention_id in afk_data:
            afk_info = afk_data[mention_id]
            afk_time = datetime.fromtimestamp(afk_info['timestamp'])
            time_ago = datetime.utcnow() - afk_time

            if time_ago.days > 0:
                time_str = f"{time_ago.days} day(s) ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600} hour(s) ago"
            elif time_ago.seconds > 60:
                time_str = f"{time_ago.seconds // 60} minute(s) ago"
            else:
                time_str = "just now"

            reason = afk_info.get('reason', 'No reason provided')
            try:
                await message.channel.send(f"🌙 {mention.display_name} is AFK: {reason} ({time_str})")
            except:
                pass

    await bot.process_commands(message)

async def check_giveaways():
    """Background task to check for ended giveaways"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            giveaways = load_giveaways()
            current_time = datetime.utcnow().timestamp()

            for message_id, giveaway_data in list(giveaways.items()):
                if giveaway_data['end_time'] <= current_time and not giveaway_data.get('ended', False):
                    await end_giveaway_by_id(message_id)

        except Exception as e:
            print(f"Error checking giveaways: {e}")

        await asyncio.sleep(30)  # Check every 30 seconds

async def check_stickies():
    """Background task to maintain sticky messages"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            stickies_data = load_stickies()

            for channel_id, sticky_info in stickies_data.items():
                if not sticky_info.get('active', False):
                    continue

                channel = bot.get_channel(int(channel_id))
                if not channel:
                    continue

                try:
                    # Get recent messages
                    messages = []
                    async for msg in channel.history(limit=10):
                        messages.append(msg)

                    # Check if sticky message is still the last message
                    if messages and str(messages[0].id) != str(sticky_info.get('message_id')):
                        # Delete old sticky and send new one
                        try:
                            old_message = await channel.fetch_message(sticky_info['message_id'])
                            await old_message.delete()
                        except:
                            pass

                        # Send new sticky
                        new_message = await channel.send(sticky_info['content'])
                        sticky_info['message_id'] = new_message.id
                        stickies_data[channel_id] = sticky_info
                        save_stickies(stickies_data)

                except Exception as e:
                    print(f"Error maintaining sticky in channel {channel_id}: {e}")

        except Exception as e:
            print(f"Error in sticky checker: {e}")

        await asyncio.sleep(60)  # Check every minute

async def end_giveaway_by_id(message_id):
    """End a giveaway by message ID"""
    giveaways = load_giveaways()

    if message_id not in giveaways:
        return

    giveaway_data = giveaways[message_id]

    try:
        channel = bot.get_channel(giveaway_data['channel_id'])
        if not channel:
            return

        message = await channel.fetch_message(int(message_id))
        if not message:
            return

        # Get participants from giveaway data
        participants = giveaway_data.get('participants', [])
        
        if not participants:
            embed = discord.Embed(
                title="🎉 Giveaway Ended",
                description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** No one entered!",
                color=discord.Color.red()
            )
            await message.edit(embed=embed, view=None)
            giveaways[message_id]['ended'] = True
            save_giveaways(giveaways)
            return

        # Get user objects from participant IDs
        users = []
        for user_id in participants:
            try:
                user = await bot.fetch_user(user_id)
                users.append(user)
            except:
                continue

        if not users:
            embed = discord.Embed(
                title="🎉 Giveaway Ended",
                description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** No one entered!",
                color=discord.Color.red()
            )
            await message.edit(embed=embed, view=None)
        else:
            winners = random.sample(users, min(giveaway_data['winners'], len(users)))

            winner_mentions = [winner.mention for winner in winners]
            embed = discord.Embed(
                title="🎉 Giveaway Ended",
                description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** {', '.join(winner_mentions)}",
                color=discord.Color.gold()
            )
            await message.edit(embed=embed, view=None)

            # Send congratulations message
            for winner in winners:
                await channel.send(f":tada: Congratulations, {winner.mention}! You won **{giveaway_data['prize']}**!")

        giveaways[message_id]['ended'] = True
        save_giveaways(giveaways)

    except Exception as e:
        print(f"Error ending giveaway {message_id}: {e}")

@bot.tree.command(name="whitelist", description="Manage whitelist users")
@discord.app_commands.describe(
    action="Choose an action",
    user="User to add/remove (optional for view)"
)
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name="view_users", value="view_users"),
    discord.app_commands.Choice(name="add_user", value="add_user"),
    discord.app_commands.Choice(name="remove_user", value="remove_user")
])
async def whitelist(interaction: discord.Interaction, action: discord.app_commands.Choice[str], user: discord.Member = None):
    whitelist_data = load_whitelist()

    if action.value == "view_users":
        if not whitelist_data:
            embed = discord.Embed(
                title="Whitelist Users",
                description="No users in whitelist",
                color=discord.Color.blue()
            )
        else:
            user_list = []
            for user_id in whitelist_data:
                try:
                    discord_user = await bot.fetch_user(user_id)
                    user_list.append(f"• {discord_user.display_name} ({discord_user.id})")
                except:
                    user_list.append(f"• Unknown User ({user_id})")

            embed = discord.Embed(
                title="Whitelist Users",
                description="\n".join(user_list),
                color=discord.Color.blue()
            )

        await interaction.response.send_message(embed=embed)

    elif action.value == "add_user":
        if user is None:
            await interaction.response.send_message("Please specify a user to add to the whitelist.", ephemeral=True)
            return

        if user.id in whitelist_data:
            embed = discord.Embed(
                title="User Already Whitelisted",
                description=f"{user.display_name} is already in the whitelist.",
                color=discord.Color.orange()
            )
        else:
            whitelist_data.append(user.id)
            save_whitelist(whitelist_data)
            embed = discord.Embed(
                title="User Added",
                description=f"{user.display_name} has been added to the whitelist.",
                color=discord.Color.green()
            )

        await interaction.response.send_message(embed=embed)

    elif action.value == "remove_user":
        if user is None:
            await interaction.response.send_message("Please specify a user to remove from the whitelist.", ephemeral=True)
            return

        if user.id not in whitelist_data:
            embed = discord.Embed(
                title="User Not Found",
                description=f"{user.display_name} is not in the whitelist.",
                color=discord.Color.red()
            )
        else:
            whitelist_data.remove(user.id)
            save_whitelist(whitelist_data)
            embed = discord.Embed(
                title="User Removed",
                description=f"{user.display_name} has been removed from the whitelist.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

# Helper function to check if user is whitelisted
def is_whitelisted(user_id):
    """Check if a user is in the whitelist"""
    whitelist_data = load_whitelist()
    return user_id in whitelist_data

# Example command that uses whitelist check
@bot.tree.command(name="protected", description="A command only whitelisted users can use")
async def protected_command(interaction: discord.Interaction):
    if not is_whitelisted(interaction.user.id):
        await interaction.response.send_message("You are not whitelisted to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Welcome! You have access to this protected command.")

@bot.tree.command(name="role", description="Manage roles for members")
@discord.app_commands.describe(
    action="Choose an action",
    role="The role to add/remove"
)
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name="all", value="all"),
    discord.app_commands.Choice(name="human", value="human"),
    discord.app_commands.Choice(name="bots", value="bots"),
    discord.app_commands.Choice(name="removeall", value="removeall"),
    discord.app_commands.Choice(name="removehumans", value="removehumans"),
    discord.app_commands.Choice(name="removebots", value="removebots")
])
async def role_command(interaction: discord.Interaction, action: discord.app_commands.Choice[str], role: discord.Role):
    # Check if user has permission to manage roles
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("You don't have permission to manage roles.", ephemeral=True)
        return

    # Check if bot can manage the specified role
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("I cannot manage this role because it's higher than or equal to my highest role.", ephemeral=True)
        return

    # Defer the response as this might take a while
    await interaction.response.defer()

    guild = interaction.guild
    success_count = 0
    error_count = 0

    try:
        if action.value == "all":
            # Add role to all members
            for member in guild.members:
                try:
                    if role not in member.roles:
                        await member.add_roles(role, reason=f"Role added by {interaction.user}")
                        success_count += 1
                except discord.Forbidden:
                    error_count += 1
                except discord.HTTPException:
                    error_count += 1

            embed = discord.Embed(
                title="Role Added to All Members",
                description=f"Successfully added {role.mention} to {success_count} members.\n{error_count} failed.",
                color=discord.Color.green()
            )

        elif action.value == "human":
            # Add role to all human members (not bots)
            for member in guild.members:
                if not member.bot:
                    try:
                        if role not in member.roles:
                            await member.add_roles(role, reason=f"Role added by {interaction.user}")
                            success_count += 1
                    except discord.Forbidden:
                        error_count += 1
                    except discord.HTTPException:
                        error_count += 1

            embed = discord.Embed(
                title="Role Added to Human Members",
                description=f"Successfully added {role.mention} to {success_count} human members.\n{error_count} failed.",
                color=discord.Color.green()
            )

        elif action.value == "bots":
            # Add role to all bot members
            for member in guild.members:
                if member.bot:
                    try:
                        if role not in member.roles:
                            await member.add_roles(role, reason=f"Role added by {interaction.user}")
                            success_count += 1
                    except discord.Forbidden:
                        error_count += 1
                    except discord.HTTPException:
                        error_count += 1

            embed = discord.Embed(
                title="Role Added to Bot Members",
                description=f"Successfully added {role.mention} to {success_count} bot members.\n{error_count} failed.",
                color=discord.Color.green()
            )

        elif action.value == "removeall":
            # Remove role from all members
            for member in guild.members:
                try:
                    if role in member.roles:
                        await member.remove_roles(role, reason=f"Role removed by {interaction.user}")
                        success_count += 1
                except discord.Forbidden:
                    error_count += 1
                except discord.HTTPException:
                    error_count += 1

            embed = discord.Embed(
                title="Role Removed from All Members",
                description=f"Successfully removed {role.mention} from {success_count} members.\n{error_count} failed.",
                color=discord.Color.red()
            )

        elif action.value == "removehumans":
            # Remove role from all human members
            for member in guild.members:
                if not member.bot:
                    try:
                        if role in member.roles:
                            await member.remove_roles(role, reason=f"Role removed by {interaction.user}")
                            success_count += 1
                    except discord.Forbidden:
                        error_count += 1
                    except discord.HTTPException:
                        error_count += 1

            embed = discord.Embed(
                title="Role Removed from Human Members",
                description=f"Successfully removed {role.mention} from {success_count} human members.\n{error_count} failed.",
                color=discord.Color.red()
            )

        elif action.value == "removebots":
            # Remove role from all bot members
            for member in guild.members:
                if member.bot:
                    try:
                        if role in member.roles:
                            await member.remove_roles(role, reason=f"Role removed by {interaction.user}")
                            success_count += 1
                    except discord.Forbidden:
                        error_count += 1
                    except discord.HTTPException:
                        error_count += 1

            embed = discord.Embed(
                title="Role Removed from Bot Members",
                description=f"Successfully removed {role.mention} from {success_count} bot members.\n{error_count} failed.",
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        error_embed = discord.Embed(
            title="Error",
            description=f"An error occurred while processing the command: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

@bot.tree.command(name="giveaway", description="Manage giveaways")
@discord.app_commands.describe(
    action="Choose an action",
    prize="Prize for the giveaway (create/edit)",
    duration="Duration (e.g., '1h', '30m', '2d') (create/edit)",
    winners="Number of winners (default: 1) (create/edit/reroll)",
    channel="Channel for giveaway (default: current) (create)",
    message_id="Message ID of the giveaway (delete/edit/end/reroll)"
)
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name="create", value="create"),
    discord.app_commands.Choice(name="delete", value="delete"),
    discord.app_commands.Choice(name="edit", value="edit"),
    discord.app_commands.Choice(name="end", value="end"),
    discord.app_commands.Choice(name="reroll", value="reroll")
])
async def giveaway_command(
    interaction: discord.Interaction, 
    action: discord.app_commands.Choice[str],
    prize: str = None,
    duration: str = None,
    winners: int = 1,
    channel: discord.TextChannel = None,
    message_id: str = None
):
    # Check permissions for giveaway management
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to manage giveaways.", ephemeral=True)
        return

    giveaways = load_giveaways()

    if action.value == "create":
        if not prize:
            await interaction.response.send_message("Please specify a prize for the giveaway.", ephemeral=True)
            return

        if not duration:
            await interaction.response.send_message("Please specify a duration for the giveaway (e.g., '1h', '30m', '2d').", ephemeral=True)
            return

        duration_seconds = parse_duration(duration)
        if duration_seconds is None:
            await interaction.response.send_message("Invalid duration format. Use formats like '1h', '30m', '2d'.", ephemeral=True)
            return

        if duration_seconds < 60:
            await interaction.response.send_message("Duration must be at least 1 minute.", ephemeral=True)
            return

        if winners < 1:
            winners = 1

        target_channel = channel or interaction.channel
        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>\n**Participants:** 0\n\nClick the button below to join!",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        await interaction.response.send_message(f"Giveaway created in {target_channel.mention}!", ephemeral=True)

        view = GiveawayView(None)  # Will be updated with message ID
        message = await target_channel.send(embed=embed, view=view)
        
        # Update view with message ID
        view.giveaway_id = str(message.id)
        await message.edit(view=view)

        giveaways[str(message.id)] = {
            'prize': prize,
            'duration': duration_seconds,
            'winners': winners,
            'channel_id': target_channel.id,
            'host_id': interaction.user.id,
            'end_time': end_time.timestamp(),
            'ended': False,
            'participants': []
        }
        save_giveaways(giveaways)

    elif action.value == "delete":
        if not message_id:
            await interaction.response.send_message("Please specify the message ID of the giveaway to delete.", ephemeral=True)
            return

        if message_id not in giveaways:
            await interaction.response.send_message("Giveaway not found.", ephemeral=True)
            return

        giveaway_data = giveaways[message_id]

        try:
            channel_obj = bot.get_channel(giveaway_data['channel_id'])
            if channel_obj:
                message = await channel_obj.fetch_message(int(message_id))
                await message.delete()

            del giveaways[message_id]
            save_giveaways(giveaways)

            await interaction.response.send_message("Giveaway deleted successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error deleting giveaway: {str(e)}", ephemeral=True)

    elif action.value == "edit":
        if not message_id:
            await interaction.response.send_message("Please specify the message ID of the giveaway to edit.", ephemeral=True)
            return

        if message_id not in giveaways:
            await interaction.response.send_message("Giveaway not found.", ephemeral=True)
            return

        giveaway_data = giveaways[message_id]

        if giveaway_data.get('ended', False):
            await interaction.response.send_message("Cannot edit an ended giveaway.", ephemeral=True)
            return

        # Update giveaway data
        if prize:
            giveaway_data['prize'] = prize
        if duration:
            duration_seconds = parse_duration(duration)
            if duration_seconds is None:
                await interaction.response.send_message("Invalid duration format. Use formats like '1h', '30m', '2d'.", ephemeral=True)
                return
            giveaway_data['duration'] = duration_seconds
            giveaway_data['end_time'] = (datetime.utcnow() + timedelta(seconds=duration_seconds)).timestamp()
        if winners >= 1:
            giveaway_data['winners'] = winners

        try:
            channel_obj = bot.get_channel(giveaway_data['channel_id'])
            message = await channel_obj.fetch_message(int(message_id))

            end_time = datetime.fromtimestamp(giveaway_data['end_time'])

            participants_count = len(giveaway_data.get('participants', []))
            embed = discord.Embed(
                title="🎉 GIVEAWAY 🎉",
                description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** {giveaway_data['winners']}\n**Ends:** <t:{int(giveaway_data['end_time'])}:R>\n**Participants:** {participants_count}\n\nClick the button below to join!",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Hosted by {bot.get_user(giveaway_data['host_id']).display_name}")

            view = GiveawayView(message_id)
            await message.edit(embed=embed, view=view)
            save_giveaways(giveaways)

            await interaction.response.send_message("Giveaway updated successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error editing giveaway: {str(e)}", ephemeral=True)

    elif action.value == "end":
        if not message_id:
            await interaction.response.send_message("Please specify the message ID of the giveaway to end.", ephemeral=True)
            return

        if message_id not in giveaways:
            await interaction.response.send_message("Giveaway not found.", ephemeral=True)
            return

        if giveaways[message_id].get('ended', False):
            await interaction.response.send_message("This giveaway has already ended.", ephemeral=True)
            return

        await interaction.response.send_message("Ending giveaway...", ephemeral=True)
        await end_giveaway_by_id(message_id)

    elif action.value == "reroll":
        if not message_id:
            await interaction.response.send_message("Please specify the message ID of the giveaway to reroll.", ephemeral=True)
            return

        if message_id not in giveaways:
            await interaction.response.send_message("Giveaway not found.", ephemeral=True)
            return

        giveaway_data = giveaways[message_id]

        if not giveaway_data.get('ended', False):
            await interaction.response.send_message("Cannot reroll an active giveaway. End it first.", ephemeral=True)
            return

        try:
            channel_obj = bot.get_channel(giveaway_data['channel_id'])
            message = await channel_obj.fetch_message(int(message_id))

            # Get participants from giveaway data
            participants = giveaway_data.get('participants', [])
            
            if not participants:
                await interaction.response.send_message("No participants found for this giveaway.", ephemeral=True)
                return

            # Get user objects from participant IDs
            users = []
            for user_id in participants:
                try:
                    user = await bot.fetch_user(user_id)
                    users.append(user)
                except:
                    continue

            if not users:
                await interaction.response.send_message("No valid entries found for reroll.", ephemeral=True)
                return

            reroll_winners = winners if winners >= 1 else giveaway_data['winners']
            new_winners = random.sample(users, min(reroll_winners, len(users)))

            winner_mentions = [winner.mention for winner in new_winners]

            embed = discord.Embed(
                title="🎉 Giveaway Rerolled",
                description=f"**Prize:** {giveaway_data['prize']}\n**New Winners:** {', '.join(winner_mentions)}",
                color=discord.Color.purple()
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"Error rerolling giveaway: {str(e)}", ephemeral=True)

@bot.tree.command(name="welcome", description="Manage welcome system")
@discord.app_commands.describe(
    action="Choose an action",
    channel="Channel for welcome messages",
    message="Welcome message content"
)
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name="status", value="status"),
    discord.app_commands.Choice(name="create", value="create"),
    discord.app_commands.Choice(name="change", value="change"),
    discord.app_commands.Choice(name="text", value="text"),
    discord.app_commands.Choice(name="toggle", value="toggle"),
    discord.app_commands.Choice(name="delete", value="delete"),
    discord.app_commands.Choice(name="info", value="info")
])
async def welcome_command(interaction: discord.Interaction, action: discord.app_commands.Choice[str], channel: discord.TextChannel = None, message: str = None):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need Manage Server permission to use this command.", ephemeral=True)
        return

    welcome_data = load_welcome()
    guild_id = str(interaction.guild.id)

    if action.value == "status":
        if guild_id in welcome_data:
            welcome_info = welcome_data[guild_id]
            status = "✅ Enabled" if welcome_info.get('enabled', False) else "❌ Disabled"
            channel_mention = f"<#{welcome_info['channel_id']}>" if 'channel_id' in welcome_info else "Not set"

            embed = discord.Embed(
                title="Welcome System Status",
                description=f"**Status:** {status}\n**Channel:** {channel_mention}",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="Welcome System Status",
                description="❌ Welcome system not configured",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    elif action.value == "create":
        if not channel or not message:
            await interaction.response.send_message("Please specify both channel and message for welcome setup.", ephemeral=True)
            return

        welcome_data[guild_id] = {
            'channel_id': channel.id,
            'message': message,
            'enabled': True
        }
        save_welcome(welcome_data)

        embed = discord.Embed(
            title="Welcome System Created",
            description=f"Welcome messages will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    elif action.value == "change":
        if guild_id not in welcome_data:
            await interaction.response.send_message("Welcome system not configured. Use `/welcome create` first.", ephemeral=True)
            return

        if channel:
            welcome_data[guild_id]['channel_id'] = channel.id
        if message:
            welcome_data[guild_id]['message'] = message

        save_welcome(welcome_data)

        embed = discord.Embed(
            title="Welcome System Updated",
            description="Welcome settings have been updated successfully.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    elif action.value == "text":
        if guild_id not in welcome_data:
            await interaction.response.send_message("Welcome system not configured. Use `/welcome create` first.", ephemeral=True)
            return

        if not message:
            await interaction.response.send_message("Please provide a new welcome message.", ephemeral=True)
            return

        welcome_data[guild_id]['message'] = message
        save_welcome(welcome_data)

        embed = discord.Embed(
            title="Welcome Message Updated",
            description="Welcome message has been updated successfully.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    elif action.value == "toggle":
        if guild_id not in welcome_data:
            await interaction.response.send_message("Welcome system not configured. Use `/welcome create` first.", ephemeral=True)
            return

        welcome_data[guild_id]['enabled'] = not welcome_data[guild_id].get('enabled', False)
        save_welcome(welcome_data)

        status = "enabled" if welcome_data[guild_id]['enabled'] else "disabled"
        embed = discord.Embed(
            title="Welcome System Toggled",
            description=f"Welcome system has been {status}.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    elif action.value == "delete":
        if guild_id in welcome_data:
            del welcome_data[guild_id]
            save_welcome(welcome_data)

            embed = discord.Embed(
                title="Welcome System Deleted",
                description="Welcome system has been removed.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="No Welcome System",
                description="No welcome system configured to delete.",
                color=discord.Color.orange()
            )

        await interaction.response.send_message(embed=embed)

    elif action.value == "info":
        if guild_id in welcome_data:
            welcome_info = welcome_data[guild_id]
            status = "✅ Enabled" if welcome_info.get('enabled', False) else "❌ Disabled"
            channel_mention = f"<#{welcome_info['channel_id']}>"

            embed = discord.Embed(
                title="Welcome System Information",
                color=discord.Color.blue()
            )
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Channel", value=channel_mention, inline=True)
            embed.add_field(name="Message", value=welcome_info['message'], inline=False)
        else:
            embed = discord.Embed(
                title="Welcome System Information",
                description="❌ Welcome system not configured",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="welcome-preview", description="Preview welcome message")
async def welcome_preview(interaction: discord.Interaction):
    welcome_data = load_welcome()
    guild_id = str(interaction.guild.id)

    if guild_id not in welcome_data:
        await interaction.response.send_message("Welcome system not configured.", ephemeral=True)
        return

    message = welcome_data[guild_id]['message']
    # Replace placeholders with examples
    preview = message.replace('{user}', interaction.user.mention)
    preview = preview.replace('{username}', interaction.user.display_name)
    preview = preview.replace('{server}', interaction.guild.name)
    preview = preview.replace('{membercount}', str(interaction.guild.member_count))

    embed = discord.Embed(
        title="Welcome Message Preview",
        description=preview,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="welcome-format", description="Show formatting options for welcome messages")
async def welcome_format(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Welcome Message Formatting",
        description="You can use these placeholders in your welcome message:",
        color=discord.Color.blue()
    )
    embed.add_field(name="{user}", value="Mentions the new user", inline=True)
    embed.add_field(name="{username}", value="User's display name", inline=True)
    embed.add_field(name="{server}", value="Server name", inline=True)
    embed.add_field(name="{membercount}", value="Total member count", inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stick", description="Stick a message to the channel")
@discord.app_commands.describe(message="Message to stick")
async def stick(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages permission to use this command.", ephemeral=True)
        return

    stickies_data = load_stickies()
    channel_id = str(interaction.channel.id)

    # Remove existing sticky if any
    if channel_id in stickies_data and stickies_data[channel_id].get('active', False):
        try:
            old_message = await interaction.channel.fetch_message(stickies_data[channel_id]['message_id'])
            await old_message.delete()
        except:
            pass

    # Send new sticky message
    sticky_message = await interaction.channel.send(f"📌 **STICKY:** {message}")

    stickies_data[channel_id] = {
        'content': f"📌 **STICKY:** {message}",
        'message_id': sticky_message.id,
        'active': True,
        'author_id': interaction.user.id
    }
    save_stickies(stickies_data)

    await interaction.response.send_message("✅ Message has been stickied!", ephemeral=True)

@bot.tree.command(name="stickstop", description="Stop the stickied message in the channel")
async def stickstop(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages permission to use this command.", ephemeral=True)
        return

    stickies_data = load_stickies()
    channel_id = str(interaction.channel.id)

    if channel_id not in stickies_data or not stickies_data[channel_id].get('active', False):
        await interaction.response.send_message("No active sticky message in this channel.", ephemeral=True)
        return

    stickies_data[channel_id]['active'] = False
    save_stickies(stickies_data)

    await interaction.response.send_message("✅ Sticky message stopped!", ephemeral=True)

@bot.tree.command(name="stickstart", description="Restart a stopped sticky message")
async def stickstart(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages permission to use this command.", ephemeral=True)
        return

    stickies_data = load_stickies()
    channel_id = str(interaction.channel.id)

    if channel_id not in stickies_data:
        await interaction.response.send_message("No sticky message configured in this channel.", ephemeral=True)
        return

    if stickies_data[channel_id].get('active', False):
        await interaction.response.send_message("Sticky message is already active.", ephemeral=True)
        return

    # Send sticky message again
    sticky_message = await interaction.channel.send(stickies_data[channel_id]['content'])

    stickies_data[channel_id]['message_id'] = sticky_message.id
    stickies_data[channel_id]['active'] = True
    save_stickies(stickies_data)

    await interaction.response.send_message("✅ Sticky message restarted!", ephemeral=True)

@bot.tree.command(name="stickremove", description="Remove the stickied message")
async def stickremove(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages permission to use this command.", ephemeral=True)
        return

    stickies_data = load_stickies()
    channel_id = str(interaction.channel.id)

    if channel_id not in stickies_data:
        await interaction.response.send_message("No sticky message in this channel.", ephemeral=True)
        return

    # Delete the sticky message
    try:
        message = await interaction.channel.fetch_message(stickies_data[channel_id]['message_id'])
        await message.delete()
    except:
        pass

    del stickies_data[channel_id]
    save_stickies(stickies_data)

    await interaction.response.send_message("✅ Sticky message removed!", ephemeral=True)

@bot.tree.command(name="getstickies", description="Show all active and stopped stickies")
async def getstickies(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages permission to use this command.", ephemeral=True)
        return

    stickies_data = load_stickies()

    if not stickies_data:
        await interaction.response.send_message("No sticky messages configured.", ephemeral=True)
        return

    embed = discord.Embed(title="Sticky Messages", color=discord.Color.blue())

    for channel_id, sticky_info in stickies_data.items():
        channel = bot.get_channel(int(channel_id))
        if channel:
            status = "🟢 Active" if sticky_info.get('active', False) else "🔴 Stopped"
            content = sticky_info['content'][:100] + "..." if len(sticky_info['content']) > 100 else sticky_info['content']
            embed.add_field(
                name=f"#{channel.name}",
                value=f"{status}\n{content}",
                inline=False
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="afk", description="Set AFK status")
@discord.app_commands.describe(reason="Reason for being AFK")
async def afk(interaction: discord.Interaction, reason: str = "No reason provided"):
    afk_data = load_afk()
    user_id = str(interaction.user.id)

    afk_data[user_id] = {
        'reason': reason,
        'timestamp': datetime.utcnow().timestamp()
    }
    save_afk(afk_data)

    embed = discord.Embed(
        title="AFK Status Set",
        description=f"You are now AFK: {reason}",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)

class SearchView(discord.ui.View):
    def __init__(self, scripts, query, mode, total_results):
        super().__init__(timeout=300)
        self.scripts = scripts
        self.query = query
        self.mode = mode
        self.total_results = total_results
        self.current_page = 0
        self.scripts_per_page = 5
        self.max_pages = (len(scripts) - 1) // self.scripts_per_page + 1
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.max_pages - 1
        
        # Update button labels with page info
        self.previous_button.label = f"◀ Previous"
        self.next_button.label = f"Next ▶"
    
    def get_embed(self):
        start_idx = self.current_page * self.scripts_per_page
        end_idx = min(start_idx + self.scripts_per_page, len(self.scripts))
        current_scripts = self.scripts[start_idx:end_idx]
        
        filter_text = f" ({self.mode.name})" if self.mode and self.mode.value != "all" else ""
        embed = discord.Embed(
            title=f"🔍 ScriptBlox Search Results{filter_text}",
            description=f"Found **{self.total_results}** scripts for: `{self.query if self.query else 'all scripts'}`",
            color=discord.Color.blue()
        )
        
        for i, script in enumerate(current_scripts, start_idx + 1):
            title = script.get("title", "Unknown Title")
            game = script.get("game", {}).get("name", "Unknown Game")
            is_paid = script.get("isPatched", False)
            verified = script.get("verified", False)
            views = script.get("views", 0)
            slug = script.get("slug", "")
            
            # Create status indicators
            status_icons = []
            if is_paid:
                status_icons.append("💎 Paid")
            else:
                status_icons.append("🆓 Free")
            
            if verified:
                status_icons.append("✅ Verified")
            
            status_text = " • ".join(status_icons)
            
            # Create script URL
            script_url = f"https://scriptblox.com/script/{slug}" if slug else "N/A"
            
            field_value = f"**Game:** {game}\n**Status:** {status_text}\n**Views:** {views:,}\n**Link:** [View Script]({script_url})"
            
            embed.add_field(
                name=f"{i}. {title}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} • {self.total_results} total results • ScriptBlox")
        return embed
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📊 Page Info", style=discord.ButtonStyle.primary)
    async def page_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        info_embed = discord.Embed(
            title="📊 Search Information",
            color=discord.Color.blue()
        )
        info_embed.add_field(name="Query", value=self.query if self.query else "All scripts", inline=True)
        info_embed.add_field(name="Mode", value=self.mode.name if self.mode else "All", inline=True)
        info_embed.add_field(name="Total Results", value=f"{self.total_results:,}", inline=True)
        info_embed.add_field(name="Current Page", value=f"{self.current_page + 1}/{self.max_pages}", inline=True)
        info_embed.add_field(name="Scripts Per Page", value=str(self.scripts_per_page), inline=True)
        info_embed.add_field(name="Results Showing", value=f"{self.current_page * self.scripts_per_page + 1}-{min((self.current_page + 1) * self.scripts_per_page, len(self.scripts))}", inline=True)
        
        await interaction.response.send_message(embed=info_embed, ephemeral=True)

@bot.tree.command(name="search", description="Search ScriptBlox scripts")
@discord.app_commands.describe(
    query="Search query",
    mode="Filter by script type"
)
@discord.app_commands.choices(mode=[
    discord.app_commands.Choice(name="All", value="all"),
    discord.app_commands.Choice(name="Free", value="free"),
    discord.app_commands.Choice(name="Paid", value="paid")
])
async def search_scripts(interaction: discord.Interaction, query: str = "", mode: discord.app_commands.Choice[str] = None):
    import aiohttp
    
    await interaction.response.defer()
    
    try:
        # Build API URL
        api_url = "https://scriptblox.com/api/script/search"
        params = {"q": query}
        
        if mode and mode.value != "all":
            params["mode"] = mode.value
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                if response.status != 200:
                    await interaction.followup.send("❌ Failed to fetch results from ScriptBlox API.", ephemeral=True)
                    return
                
                data = await response.json()
                
                if not data.get("result") or not data["result"].get("scripts"):
                    embed = discord.Embed(
                        title="🔍 ScriptBlox Search Results",
                        description=f"No scripts found for: `{query if query else 'all scripts'}`",
                        color=discord.Color.orange()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                scripts = data["result"]["scripts"]
                total_results = len(scripts)
                
                # Create pagination view
                view = SearchView(scripts, query, mode, total_results)
                embed = view.get_embed()
                
                await interaction.followup.send(embed=embed, view=view)
                
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Search Error",
            description=f"An error occurred while searching: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="invite", description="Get bot invite link")
async def invite(interaction: discord.Interaction):
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
    embed = discord.Embed(
        title="Invite Bot",
        description=f"[Click here to invite me to your server!]({invite_url})",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {latency}ms",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="uptime", description="Check bot uptime")
async def uptime(interaction: discord.Interaction):
    uptime_duration = datetime.utcnow() - bot_start_time
    days = uptime_duration.days
    hours, remainder = divmod(uptime_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

    embed = discord.Embed(
        title="⏰ Bot Uptime",
        description=f"Uptime: {uptime_str}",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show help menu")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Commands Help",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="📋 Whitelist Commands",
        value="`/whitelist view_users` - View whitelisted users\n`/whitelist add_user` - Add user to whitelist\n`/whitelist remove_user` - Remove user from whitelist",
        inline=False
    )

    embed.add_field(
        name="🎭 Role Commands",
        value="`/role all <role>` - Add role to all members\n`/role human <role>` - Add role to humans\n`/role bots <role>` - Add role to bots\n`/role removeall <role>` - Remove role from all",
        inline=False
    )

    embed.add_field(
        name="🎉 Giveaway Commands",
        value="`/giveaway create` - Create giveaway\n`/giveaway delete` - Delete giveaway\n`/giveaway edit` - Edit giveaway\n`/giveaway end` - End giveaway\n`/giveaway reroll` - Reroll winners",
        inline=False
    )

    embed.add_field(
        name="👋 Welcome Commands",
        value="`/welcome` - View status\n`/welcome create` - Set up welcome\n`/welcome toggle` - Enable/disable\n`/welcome-preview` - Preview message",
        inline=False
    )

    embed.add_field(
        name="📌 Sticky Commands",
        value="`/stick` - Stick message\n`/stickstop` - Stop sticky\n`/stickstart` - Restart sticky\n`/stickremove` - Remove sticky\n`/getstickies` - List all stickies",
        inline=False
    )

    embed.add_field(
        name="🔧 Utility Commands",
        value="`/afk` - Set AFK status\n`/search scripts` - Search ScriptBlox\n`/invite` - Get invite link\n`/ping` - Check latency\n`/uptime` - Check uptime",
        inline=False
    )

    embed.add_field(
        name="⚖️ Moderation Commands",
        value="Use moderation commands with appropriate permissions:\n`ban`, `kick`, `unban`, `mute`, `softban`, `lock`, `unlock`, `lockall`, `unlockall`, `unmute`, `clear`, `setmuterole`",
        inline=False
    )

    await interaction.response.send_message(embed=embed)

# Moderation Commands
@bot.tree.command(name="ban", description="Ban a user")
@discord.app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You don't have permission to ban members.", ephemeral=True)
        return

    try:
        await user.ban(reason=reason)
        embed = discord.Embed(
            title="User Banned",
            description=f"{user.mention} has been banned.\nReason: {reason}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Failed to ban user: {str(e)}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a user")
@discord.app_commands.describe(user="User to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("You don't have permission to kick members.", ephemeral=True)
        return

    try:
        await user.kick(reason=reason)
        embed = discord.Embed(
            title="User Kicked",
            description=f"{user.mention} has been kicked.\nReason: {reason}",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Failed to kick user: {str(e)}", ephemeral=True)

@bot.tree.command(name="unban", description="Unban a user")
@discord.app_commands.describe(user_id="User ID to unban")
async def unban(interaction: discord.Interaction, user_id: str):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You don't have permission to unban members.", ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        embed = discord.Embed(
            title="User Unbanned",
            description=f"{user.mention} has been unbanned.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Failed to unban user: {str(e)}", ephemeral=True)

@bot.tree.command(name="clear", description="Clear messages")
@discord.app_commands.describe(amount="Number of messages to clear (1-100)")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to manage messages.", ephemeral=True)
        return

    if amount < 1 or amount > 100:
        await interaction.response.send_message("Amount must be between 1 and 100.", ephemeral=True)
        return

    try:
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(
            title="Messages Cleared",
            description=f"Deleted {len(deleted)} messages.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to clear messages: {str(e)}", ephemeral=True)

bot.run('bot token')

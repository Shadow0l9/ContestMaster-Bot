import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio
import random
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Database setup
def setup_database():
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    # Create contests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        channel_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        status TEXT DEFAULT 'scheduled',
        question_pool TEXT,
        max_participants INTEGER DEFAULT 0
    )
    ''')
    
    # Create participants table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        contest_id INTEGER NOT NULL,
        points INTEGER DEFAULT 0,
        join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contest_id) REFERENCES contests (id),
        UNIQUE(user_id, contest_id)
    )
    ''')
    
    # Create questions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contest_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        points INTEGER DEFAULT 10,
        FOREIGN KEY (contest_id) REFERENCES contests (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Contest management functions
def create_contest(name, description, channel_id, guild_id, creator_id, start_time, end_time=None, question_pool=None, max_participants=0):
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO contests (name, description, channel_id, guild_id, creator_id, start_time, end_time, question_pool, max_participants)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, channel_id, guild_id, creator_id, start_time, end_time, question_pool, max_participants))
    
    contest_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return contest_id

def get_active_contests():
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
    SELECT id, name, channel_id, guild_id, start_time, end_time
    FROM contests
    WHERE status = 'active' OR (status = 'scheduled' AND start_time <= ?)
    ''', (now,))
    
    contests = cursor.fetchall()
    conn.close()
    return contests

def register_participant(user_id, contest_id):
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO participants (user_id, contest_id)
        VALUES (?, ?)
        ''', (user_id, contest_id))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # User already registered
        success = False
    
    conn.close()
    return success

def get_leaderboard(contest_id):
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT user_id, points
    FROM participants
    WHERE contest_id = ?
    ORDER BY points DESC
    LIMIT 10
    ''', (contest_id,))
    
    leaderboard = cursor.fetchall()
    conn.close()
    return leaderboard

def add_question(contest_id, question, answer, points=10):
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO questions (contest_id, question, answer, points)
    VALUES (?, ?, ?, ?)
    ''', (contest_id, question, answer, points))
    
    conn.commit()
    conn.close()

def get_random_question(contest_id):
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, question, answer, points
    FROM questions
    WHERE contest_id = ?
    ORDER BY RANDOM()
    LIMIT 1
    ''', (contest_id,))
    
    question = cursor.fetchone()
    conn.close()
    return question

def update_points(user_id, contest_id, points):
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE participants
    SET points = points + ?
    WHERE user_id = ? AND contest_id = ?
    ''', (points, user_id, contest_id))
    
    conn.commit()
    conn.close()

# Bot events
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    setup_database()
    check_contests.start()

# Task to check and update contest status
@tasks.loop(minutes=1)
async def check_contests():
    contests = get_active_contests()
    now = datetime.datetime.now()
    
    for contest in contests:
        contest_id, name, channel_id, guild_id, start_time, end_time = contest
        
        # Convert string times to datetime objects
        start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        
        if end_time:
            end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        
        # Check if contest should start
        if start_time <= now:
            conn = sqlite3.connect('contests.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT status FROM contests WHERE id = ?', (contest_id,))
            status = cursor.fetchone()[0]
            
            if status == 'scheduled':
                cursor.execute('UPDATE contests SET status = ? WHERE id = ?', ('active', contest_id))
                conn.commit()
                
                await channel.send(f'🎮 **Contest Started!** 🎮\n"{name}" is now active! Use `!join {contest_id}` to participate!')
            
            # Check if contest should end
            if end_time and end_time <= now and status == 'active':
                cursor.execute('UPDATE contests SET status = ? WHERE id = ?', ('completed', contest_id))
                conn.commit()
                
                # Get final leaderboard
                leaderboard = get_leaderboard(contest_id)
                
                # Create leaderboard message
                leaderboard_msg = f'🏆 **Contest Ended!** 🏆\n"{name}" has concluded! Final results:\n\n'
                
                for i, (user_id, points) in enumerate(leaderboard):
                    user = await bot.fetch_user(user_id)
                    leaderboard_msg += f'{i+1}. {user.name}: {points} points\n'
                
                await channel.send(leaderboard_msg)
            
            conn.close()

# Bot commands
@bot.command(name='create')
async def create_contest_command(ctx, name: str, start_time: str, *, description: str = "No description provided"):
    """
    Create a new contest
    Usage: !create "Contest Name" "YYYY-MM-DD HH:MM" "Contest description"
    """
    try:
        # Parse start time
        start_datetime = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        
        # Create contest
        contest_id = create_contest(
            name=name,
            description=description,
            channel_id=ctx.channel.id,
            guild_id=ctx.guild.id,
            creator_id=ctx.author.id,
            start_time=start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        await ctx.send(f'🎉 Contest "{name}" created successfully! ID: {contest_id}\nStarting at: {start_time}\n\nParticipants can join using `!join {contest_id}`')
    
    except ValueError:
        await ctx.send('❌ Invalid date format. Please use YYYY-MM-DD HH:MM')
    except Exception as e:
        await ctx.send(f'❌ Error creating contest: {str(e)}')

@bot.command(name='join')
async def join_contest(ctx, contest_id: int):
    """Join a contest"""
    success = register_participant(ctx.author.id, contest_id)
    
    if success:
        await ctx.send(f'✅ {ctx.author.mention} has joined the contest! Good luck!')
    else:
        await ctx.send(f'❌ {ctx.author.mention}, you are already registered for this contest.')

@bot.command(name='addq')
async def add_question_command(ctx, contest_id: int, points: int, question: str, *, answer: str):
    """
    Add a question to a contest
    Usage: !addq contest_id points "Question text" "Answer text"
    """
    # Check if user is the contest creator
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT creator_id FROM contests WHERE id = ?', (contest_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or result[0] != ctx.author.id:
        await ctx.send('❌ You can only add questions to contests you created.')
        return
    
    add_question(contest_id, question, answer, points)
    await ctx.send(f'✅ Question added to contest {contest_id}!')
    
    # Delete the command message to hide the answer
    await ctx.message.delete()

@bot.command(name='question')
async def ask_question(ctx, contest_id: int):
    """Ask a random question from the contest"""
    # Check if user is registered for the contest
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM participants WHERE user_id = ? AND contest_id = ?', (ctx.author.id, contest_id))
    participant = cursor.fetchone()
    
    cursor.execute('SELECT status FROM contests WHERE id = ?', (contest_id,))
    status = cursor.fetchone()
    
    conn.close()
    
    if not participant:
        await ctx.send(f'❌ You must join the contest first using `!join {contest_id}`')
        return
    
    if not status or status[0] != 'active':
        await ctx.send('❌ This contest is not active.')
        return
    
    question_data = get_random_question(contest_id)
    
    if not question_data:
        await ctx.send('❌ No questions available for this contest.')
        return
    
    q_id, question, answer, points = question_data
    
    await ctx.send(f'**Question ({points} points):** {question}\n\nReply with `!answer {contest_id} {q_id} your_answer`')

@bot.command(name='answer')
async def submit_answer(ctx, contest_id: int, question_id: int, *, user_answer: str):
    """Submit an answer to a question"""
    # Get the correct answer
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT answer, points FROM questions WHERE id = ? AND contest_id = ?', (question_id, contest_id))
    question_data = cursor.fetchone()
    
    conn.close()
    
    if not question_data:
        await ctx.send('❌ Invalid question ID.')
        return
    
    correct_answer, points = question_data
    
    # Check if the answer is correct (case insensitive)
    if user_answer.lower() == correct_answer.lower():
        update_points(ctx.author.id, contest_id, points)
        await ctx.send(f'✅ Correct! You earned {points} points.')
    else:
        await ctx.send('❌ Incorrect answer. Try again!')

@bot.command(name='leaderboard')
async def show_leaderboard(ctx, contest_id: int):
    """Show the contest leaderboard"""
    leaderboard = get_leaderboard(contest_id)
    
    if not leaderboard:
        await ctx.send('❌ No participants in this contest yet.')
        return
    
    # Get contest name
    conn = sqlite3.connect('contests.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name FROM contests WHERE id = ?', (contest_id,))
    contest_name = cursor.fetchone()[0]
    
    conn.close()
    
    # Create leaderboard message
    leaderboard_msg = f'🏆 **Leaderboard for "{contest_name}"** 🏆\n\n'
    
    for i, (user_id, points) in enumerate(leaderboard):
        user = await bot.fetch_user(user_id)
        leaderboard_msg += f'{i+1}. {user.name}: {points} points\n'
    
    await ctx.send(leaderboard_msg)

@bot.command(name='help_contest')
async def help_command(ctx):
    """Show ContestMaster help"""
    help_text = """
**🎮 ContestMaster Bot Commands 🎮**

**Contest Creation & Management:**
`!create "Contest Name" "YYYY-MM-DD HH:MM" "Contest description"` - Create a new contest
`!addq contest_id points "Question text" "Answer text"` - Add a question to your contest

**Participant Commands:**
`!join contest_id` - Join a contest
`!question contest_id` - Get a random question from the contest
`!answer contest_id question_id your_answer` - Submit an answer
`!leaderboard contest_id` - View the contest leaderboard

**Need more help?**
Contact the server admin for assistance.
"""
    await ctx.send(help_text)

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: No token found. Please set the DISCORD_TOKEN environment variable.")
    else:
        bot.run(token)

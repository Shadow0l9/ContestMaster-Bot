# ContestMaster Discord Bot

This repository contains a Discord bot designed to create and manage contests, quizzes, and competitions within your server. Perfect for community engagement and fun events!

## Features

- Create scheduled contests with custom settings
- Participant registration system with point tracking
- Random question generation from a customizable database
- Automated notifications for participants before contests begin
- Interactive leaderboard with real-time updates
- Virtual rewards system (special roles, badges)

## Getting Started

### Prerequisites

- Python 3.8+
- Discord.py library
- SQLite database
- A Discord bot token

### Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/contest-master-bot.git
cd contest-master-bot
```

2. Install required dependencies
```bash
pip install discord.py python-dotenv
```

3. Create a `.env` file with your Discord bot token
```
DISCORD_TOKEN=your_discord_bot_token_here
```

4. Run the bot
```bash
python main.py
```

## Usage

### Contest Creation & Management

- `!create "Contest Name" "YYYY-MM-DD HH:MM" "Contest description"` - Create a new contest
- `!addq contest_id points "Question text" "Answer text"` - Add a question to your contest

### Participant Commands

- `!join contest_id` - Join a contest
- `!question contest_id` - Get a random question from the contest
- `!answer contest_id question_id your_answer` - Submit an answer
- `!leaderboard contest_id` - View the contest leaderboard

### Help Command

- `!help_contest` - Display all available commands

## Example Workflow

1. Create a contest:
```
!create "Trivia Night" "2025-06-01 20:00" "Weekly trivia contest with prizes!"
```

2. Add questions to the contest:
```
!addq 1 10 "What is the capital of France?" "Paris"
!addq 1 20 "Who wrote 'Romeo and Juliet'?" "William Shakespeare"
```

3. Participants join the contest:
```
!join 1
```

4. When the contest starts, participants can request questions:
```
!question 1
```

5. Participants submit answers:
```
!answer 1 1 Paris
```

6. Check the leaderboard:
```
!leaderboard 1
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to the discord.py community for their excellent documentation
- Inspired by various quiz and contest formats from popular Discord communities

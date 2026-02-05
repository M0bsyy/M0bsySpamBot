import asyncio
import logging
import random
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

# 🎨 Terminal colors
COLORS = {
    'red': '\033[1;31m',
    'green': '\033[1;32m',
    'yellow': '\033[1;33m',
    'cyan': '\033[36m',
    'blue': '\033[1;34m',
    'reset': '\033[0m',
    'bold': '\033[1m'
}

# 🔐 ADMIN CONFIGURATION
# यहां अपने admin user IDs add करें (numeric IDs)
ADMIN_USER_IDS = [7585357695]  # अपने admin user IDs से replace करें
BOT_TOKEN = "8346482878:AAHOCAsIqDCr6mvE4Xwb9ZENTo0t1vYrNnY"

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Global variables
active_bots = {}
authorized_users = set()  # Authorized users (admin द्वारा approved)
emoji_suffixes = ["💔", "😖", "🦋", "🤍", "🔥", "⁉️", "😞", "👾", "🤤", "😋", "😛", "👌", "☺️", "😝", "😕", "🙂", "🤛", "🤜", "🤚", "👋", "🫶", "🙌", "👐", "✍️", "🤟", "🤲", "🙏", "💅", "💅", "🩷", "🧡", "💛", "💚", "💔", "❤️", "🔥", "❤️", "🩹", "❣️", "💕", "💞", "💟", "💝", "💘", "💖", "💓", "💗", "💌", "💢", "💥", "💤", "💦", "💨", "❤️", "🧡", "❤️‍🔥", "☮️", "🌑", "🌘", "🌗", "🌖", "🌖", "🌕", "🌔", "🌓", "🌒", "🐯", "🐱", "🦁", "🐻‍❄️", "🐨", "🐼", "🐹", "🦝", "🐭", "🐰", "🐺", "🐻", "🐷", "🐽", "⚕️", "♾️", "🐗", "🦓", "🦓", "🦓", "🦄", "⚛️", "🐉", "🦖", "🦕", "🉑", "💮", "🪷", "🉐", "🐲", "🦎", "🆑", "🙈", "🙉", "🙊", "🚼", "🈲", "🅾️", "⛔", "🐴", "🛑", "📛", "❌", "⭕", "🚫", "🔇", "🔕", "🚭", "🚷", "❗", "📵", "🔞", "🚱", "🚳", "🚯", "❕", "❓", "❔", "‼️", "🫁", "🦁", "☢️", "〽️", "⚜️", "🔱", "🔆", "🔅", "☣️", "☄️", "🚸", "🔰", "♻️", "🈯", "💠", "🌛", "✳️", "🌍", " 🌏", "🌏", "➿", "🌫️", "🛃", "🌚", "🌜", "🌝", "⛰️", "🏔️", "☀️", "🌤️", "🌥️", "🌦️", "⛈️", "🌩️", "🌧️", "🪨", "🌀", "🌨️", "🏞️", "🌈", "🌪️", "☃️", "⚡", "⛄", "🌺", "🍂", "🌻", "🍀", "🪴", "🌴", "🌲", "🪵", "🌱", "💮", "🪷", "🥀", "🌹"]

# 🔐 Authorization decorator
def require_authorization(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Admin users को हमेशा access दें
        if user_id in ADMIN_USER_IDS:
            return await func(update, context, *args, **kwargs)
        
        # Regular users के लिए check authorization
        if user_id in authorized_users:
            return await func(update, context, *args, **kwargs)
        else:
            await update.message.reply_text(
                "❌ Access Denied!\n\n"
                "You are not authorized to use this bot.\n"
                "Please contact admin for access.\n\n"
                "Your User ID: " + str(user_id)
            )
            return
    
    return wrapper

# 🔐 Admin-only decorator
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id in ADMIN_USER_IDS:
            return await func(update, context, *args, **kwargs)
        else:
            await update.message.reply_text("❌ This command is for admins only!")
            return
    
    return wrapper

class InstagramMessenger:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session_id = ""
        self.dm_url = ""
        self.task_count = 10
        self.delay_ms = 100
        self.message_templates = [f"Message {i+1}" for i in range(100)]
        self.custom_messages = []
        self.is_running = False
        self.success_count = 0
        self.fail_count = 0
        self.browser = None
        self.context = None
        self.tasks = []

    def generate_message(self):
        if self.custom_messages:
            return random.choice(self.custom_messages)
        else:
            base = random.choice(self.message_templates)
            emoji = random.choice(emoji_suffixes)
            return f"{base} {emoji}"

    async def message_loop(self):
        page = await self.context.new_page()
        try:
            await page.goto(self.dm_url, wait_until='domcontentloaded', timeout=60000)
            # Wait for message input field
            message_input = page.locator('div[aria-label="Message"][contenteditable="true"]')
            await message_input.wait_for(timeout=20000)
        except Exception as e:
            logging.error(f"Init failed: {e}")
            return

        while self.is_running:
            try:
                message = self.generate_message()
                
                # Type message
                await message_input.fill(message)
                await asyncio.sleep(0.5)
                
                # Press Enter to send
                await message_input.press("Enter")
                
                self.success_count += 1
                logging.info(f"Message sent: {message}")

                await asyncio.sleep(self.delay_ms / 1000)

            except Exception as e:
                self.fail_count += 1
                logging.error(f"Failed to send message: {e}")
                await asyncio.sleep(0.001)

    async def start(self):
        if self.is_running:
            return False

        self.is_running = True
        self.success_count = 0
        self.fail_count = 0

        # Launch browser
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-http-cache'])
        
        self.context = await self.browser.new_context(
            locale="en-US",
            extra_http_headers={"Referer": "https://www.instagram.com/"},
            viewport=None
        )
        
        await self.context.add_cookies([{
            "name": "sessionid",
            "value": self.session_id,
            "domain": ".instagram.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        }])

        # Start tasks
        self.tasks = [asyncio.create_task(self.message_loop()) for _ in range(self.task_count)]
        return True

    async def stop(self):
        self.is_running = False
        if self.tasks:
            for task in self.tasks:
                task.cancel()
            self.tasks = []
        
        if self.browser:
            await self.browser.close()
            self.browser = None

    def get_stats(self):
        total = self.success_count + self.fail_count
        return {
            'success': self.success_count,
            'failed': self.fail_count,
            'total': total,
            'messages': len(self.custom_messages) if self.custom_messages else len(self.message_templates),
            'tasks': self.task_count,
            'delay': self.delay_ms,
            'running': self.is_running
        }

# Telegram Bot Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Admin users के लिए special message
    if user_id in ADMIN_USER_IDS:
        await update.message.reply_text(
            f"👑 Welcome Admin {user_name}!\n\n"
            "🤖 Instagram Group Messenger Bot\n\n"
            "🔐 Admin Commands:\n"
            "/admin_users - List authorized users\n"
            "/add_user <user_id> - Add authorized user\n"
            "/remove_user <user_id> - Remove authorized user\n\n"
            "🤖 Bot Commands:\n"
            "/set_session <session_id> - Set Instagram session ID\n"
            "/set_url <group_url> - Set group URL\n"
            "/set_messages msg1,msg2,msg3 - Set custom messages\n"
            "/set_tasks <number> - Set number of parallel tasks\n"
            "/set_delay <ms> - Set delay in milliseconds\n"
            "/start_bot - Start messaging\n"
            "/stop_bot - Stop messaging\n"
            "/stats - Show current stats\n"
            "/status - Show bot status\n\n"
            f"Your User ID: {user_id}"
        )
    elif user_id in authorized_users:
        if user_id not in active_bots:
            active_bots[user_id] = InstagramMessenger(user_id)
        
        await update.message.reply_text(
            f"👋 Welcome {user_name}!\n\n"
            "🤖 Instagram Group Messenger Bot\n\n"
            "Available Commands:\n"
            "/set_session <session_id> - Set Instagram session ID\n"
            "/set_url <group_url> - Set group URL\n"
            "/set_messages msg1,msg2,msg3 - Set custom messages\n"
            "/set_tasks <number> - Set number of parallel tasks\n"
            "/set_delay <ms> - Set delay in milliseconds\n"
            "/start_bot - Start messaging\n"
            "/stop_bot - Stop messaging\n"
            "/stats - Show current stats\n"
            "/status - Show bot status\n\n"
            f"Your User ID: {user_id}"
        )
    else:
        await update.message.reply_text(
            "🔒 Access Required!\n\n"
            "You are not authorized to use this bot.\n"
            "Please contact admin for access.\n\n"
            f"Your User ID: {user_id}\n"
            "Send this ID to admin to request access."
        )

# 🔐 ADMIN COMMANDS
@admin_only
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized_users:
        await update.message.reply_text("📋 No authorized users yet.")
        return
    
    users_list = "\n".join([f"• {user_id}" for user_id in authorized_users])
    await update.message.reply_text(f"📋 Authorized Users:\n\n{users_list}")

@admin_only
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide user ID\nUsage: /add_user 123456789")
        return
    
    try:
        user_id = int(context.args[0])
        authorized_users.add(user_id)
        await update.message.reply_text(f"✅ User {user_id} added successfully!")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid user ID (numbers only)")

@admin_only
async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide user ID\nUsage: /remove_user 123456789")
        return
    
    try:
        user_id = int(context.args[0])
        if user_id in authorized_users:
            authorized_users.remove(user_id)
            await update.message.reply_text(f"✅ User {user_id} removed successfully!")
            
            # Also remove their bot instance if exists
            if user_id in active_bots:
                bot = active_bots[user_id]
                if bot.is_running:
                    await bot.stop()
                del active_bots[user_id]
        else:
            await update.message.reply_text(f"❌ User {user_id} not found in authorized users")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid user ID")

# 🔐 AUTHORIZED USER COMMANDS
@require_authorization
async def set_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        active_bots[user_id] = InstagramMessenger(user_id)
    
    if not context.args:
        await update.message.reply_text("❌ Please provide session ID\nUsage: /set_session your_session_id_here")
        return
    
    session_id = ' '.join(context.args)
    active_bots[user_id].session_id = session_id
    await update.message.reply_text("✅ Session ID set successfully!")

@require_authorization
async def set_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        active_bots[user_id] = InstagramMessenger(user_id)
    
    if not context.args:
        await update.message.reply_text("❌ Please provide group URL\nUsage: /set_url https://instagram.com/direct/t/...")
        return
    
    dm_url = ' '.join(context.args)
    active_bots[user_id].dm_url = dm_url
    await update.message.reply_text("✅ Group URL set successfully!")

@require_authorization
async def set_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        active_bots[user_id] = InstagramMessenger(user_id)
    
    if not context.args:
        await update.message.reply_text("❌ Please provide messages\nUsage: /set_messages Hello,How are you?,Good morning")
        return
    
    messages_text = ' '.join(context.args)
    messages = [msg.strip() for msg in messages_text.split(',') if msg.strip()]
    active_bots[user_id].custom_messages = messages
    await update.message.reply_text(f"✅ {len(messages)} messages set successfully!")

@require_authorization
async def set_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        active_bots[user_id] = InstagramMessenger(user_id)
    
    if not context.args:
        await update.message.reply_text("❌ Please provide number of tasks\nUsage: /set_tasks 10")
        return
    
    try:
        task_count = int(context.args[0])
        active_bots[user_id].task_count = task_count
        await update.message.reply_text(f"✅ Task count set to {task_count}!")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number")

@require_authorization
async def set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        active_bots[user_id] = InstagramMessenger(user_id)
    
    if not context.args:
        await update.message.reply_text("❌ Please provide delay in ms\nUsage: /set_delay 100")
        return
    
    try:
        delay_ms = int(context.args[0])
        active_bots[user_id].delay_ms = delay_ms
        await update.message.reply_text(f"✅ Delay set to {delay_ms}ms!")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number")

@require_authorization
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        active_bots[user_id] = InstagramMessenger(user_id)
    
    bot = active_bots[user_id]
    
    if not bot.session_id or not bot.dm_url:
        await update.message.reply_text("❌ Please set session ID and group URL first!")
        return
    
    success = await bot.start()
    if success:
        await update.message.reply_text(
            f"🚀 Bot started successfully!\n\n"
            f"📊 Configuration:\n"
            f"• Tasks: {bot.task_count}\n"
            f"• Delay: {bot.delay_ms}ms\n"
            f"• Messages: {len(bot.custom_messages) if bot.custom_messages else 100}\n"
            f"• Group: {bot.dm_url}\n\n"
            f"Use /stats to check progress"
        )
    else:
        await update.message.reply_text("❌ Bot is already running!")

@require_authorization
async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        await update.message.reply_text("❌ No active bot found!")
        return
    
    bot = active_bots[user_id]
    if not bot.is_running:
        await update.message.reply_text("❌ Bot is not running!")
        return
    
    stats = bot.get_stats()
    await bot.stop()
    
    await update.message.reply_text(
        f"🛑 Bot stopped!\n\n"
        f"📊 Final Stats:\n"
        f"✅ Messages Sent: {stats['success']}\n"
        f"❌ Failed: {stats['failed']}\n"
        f"📈 Total Attempts: {stats['total']}"
    )

@require_authorization
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        await update.message.reply_text("❌ No active bot found!")
        return
    
    bot = active_bots[user_id]
    stats = bot.get_stats()
    
    status = "🟢 RUNNING" if stats['running'] else "🔴 STOPPED"
    
    await update.message.reply_text(
        f"📊 Bot Statistics\n\n"
        f"Status: {status}\n"
        f"✅ Messages Sent: {stats['success']}\n"
        f"❌ Failed: {stats['failed']}\n"
        f"📈 Total Attempts: {stats['total']}\n"
        f"🔄 Tasks: {stats['tasks']}\n"
        f"⏱️ Delay: {stats['delay']}ms\n"
        f"📝 Message Templates: {stats['messages']}\n"
        f"🔗 URL: {bot.dm_url[:50]}..." if bot.dm_url else "🔗 URL: Not set"
    )

@require_authorization
async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_bots:
        await update.message.reply_text("❌ No bot configuration found!")
        return
    
    bot = active_bots[user_id]
    status = "🟢 RUNNING" if bot.is_running else "🔴 STOPPED"
    
    await update.message.reply_text(
        f"🤖 Bot Status\n\n"
        f"Status: {status}\n"
        f"Session ID: {'✅ Set' if bot.session_id else '❌ Not set'}\n"
        f"Group URL: {'✅ Set' if bot.dm_url else '❌ Not set'}\n"
        f"Tasks: {bot.task_count}\n"
        f"Delay: {bot.delay_ms}ms\n"
        f"Messages: {len(bot.custom_messages) if bot.custom_messages else 100}\n"
        f"Sample message: {bot.generate_message()}"
    )

def main():
    # Bot token directly set
    BOT_TOKEN = "8346482878:AAHOCAsIqDCr6mvE4Xwb9ZENTo0t1vYrNnY"
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Admin commands
    application.add_handler(CommandHandler("admin_users", admin_users))
    application.add_handler(CommandHandler("add_user", add_user))
    application.add_handler(CommandHandler("remove_user", remove_user))
    
    # User commands (require authorization)
    application.add_handler(CommandHandler("set_session", set_session))
    application.add_handler(CommandHandler("set_url", set_url))
    application.add_handler(CommandHandler("set_messages", set_messages))
    application.add_handler(CommandHandler("set_tasks", set_tasks))
    application.add_handler(CommandHandler("set_delay", set_delay))
    application.add_handler(CommandHandler("start_bot", start_bot))
    application.add_handler(CommandHandler("stop_bot", stop_bot))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("status", show_status))
    
    print(f"🤖 Telegram Bot Started!")
    print(f"🔐 Admin User IDs: {ADMIN_USER_IDS}")
    print(f"👥 Authorized Users: {len(authorized_users)}")
    application.run_polling()

if __name__ == "__main__":
    main()

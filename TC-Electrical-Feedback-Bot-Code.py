import os
import logging
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Directly set the bot token here
TELEGRAM_BOT_TOKEN = '7674973439:AAEEwMmCTCBJxxOJDCa0Nzi9ToRYuclGZPM'

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Google Sheets setup
SERVICE_ACCOUNT_FILE = 'TC-Electrical-Feedback-Bot-Code.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = '1KV2TsvDUEPBdf4DMVCNPz7nH4XEzso0Fxf5-ZwpK1-c'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)

# Function to write feedback to Google Sheets
def write_to_sheet(data):
    try:
        sheet = service.spreadsheets()
        body = {"values": [data]}
        result = sheet.values().append(
            spreadsheetId=SHEET_ID,
            range='A2',
            insertDataOption="INSERT_ROWS",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
    except Exception as e:
        logger.error(f"Failed to write to Google Sheets: {e}")

# Function to create inline buttons
def feedback_buttons():
    keyboard = [
        [InlineKeyboardButton("Send Feedback", callback_data='send')],
        [InlineKeyboardButton("Edit/Add More", callback_data='edit')],
        [InlineKeyboardButton("Discard Feedback", callback_data='discard')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Conversation steps
EVENT_DATE, EVENT_NAME, FEEDBACK, CONFIRM = range(4)

# Telegram bot command: Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Heyyy, thank you for taking the time to share your observations with us!\n\n"
        "Please start by providing the date for the feedback (e.g., 2024-12-28):"
    )
    return EVENT_DATE

# Ask for the Chapel service or event
async def get_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_date = update.message.text.strip()
    context.user_data['event_date'] = event_date
    await update.message.reply_text("Thank you! Now, could you tell me what Chapel service or event you're referring to?")
    return EVENT_NAME

# Ask for feedback
async def get_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_name = update.message.text.strip()
    context.user_data['event_name'] = event_name
    await update.message.reply_text("Great! Please write your feedback on this event or service:")
    return FEEDBACK

# Ask for confirmation before saving
async def confirm_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    feedback = update.message.text.strip()
    context.user_data['feedback'] = feedback

    await update.message.reply_text(
        "Is this feedback correct?\n\n"
        f"**Date:** {context.user_data['event_date']}\n"
        f"**Event:** {context.user_data['event_name']}\n"
        f"**Feedback:** {context.user_data['feedback']}\n\n"
        "Please confirm:",
        reply_markup=feedback_buttons()
    )
    return CONFIRM

# Handle confirmation button presses
async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'send':
        # Store the feedback in Google Sheets
        feedback_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            context.user_data['event_date'],
            context.user_data['event_name'],
            context.user_data['feedback']
        ]
        write_to_sheet(feedback_data)

        await query.edit_message_text(
            "Thank you for your feedback! It will be reviewed. If you want to send another feedback, click /start."
        )
        return ConversationHandler.END

    elif query.data == 'edit':
        await query.edit_message_text("Please enter your updated feedback:")
        return FEEDBACK

    elif query.data == 'discard':
        await query.edit_message_text("Your feedback has been discarded. Thank you for your time! Have a nice day.")
        return ConversationHandler.END

# Main function to run the bot
def main():
    # Use the bot token directly here
    TOKEN = TELEGRAM_BOT_TOKEN

    # Check if the token is loaded correctly
    if not TOKEN:
        logger.error("Telegram bot token is missing. Please check your .env file.")
        return

    # Set up the conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EVENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_name)],
            EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_feedback)],
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_feedback)],
            CONFIRM: [CallbackQueryHandler(handle_confirmation)],
        },
        fallbacks=[],
    )

    application = Application.builder().token(TOKEN).build()

    # Add command and message handlers
    application.add_handler(conversation_handler)

    # Run the bot
    import nest_asyncio
    nest_asyncio.apply()
    application.run_polling()

if __name__ == "__main__":
    main()

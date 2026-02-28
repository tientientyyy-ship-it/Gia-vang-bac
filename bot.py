import os
import requests
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
print("TOKEN OK" if TELEGRAM_TOKEN else "NO TOKEN")

class PriceBot:
    def get_crypto(self, coin_id, name):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd,vnd'}
            data = requests.get(url, params=params).json()
            coin = data[coin_id]
            return f"{name}\nUSD: ${coin['usd']}\nVND: {coin['vnd']:,}đ"
        except:
            return f"{name} error"
    
    def get_gold(self):
        try:
            data = requests.get("https://gjapi.apis.gjlab.vn/gold-price").json()['data']
            return f"Vàng SJC\nMua: {data['sjc_buy']}đ\nBán: {data['sjc_sell']}đ"
        except:
            return "Vàng loading..."
    
    def menu(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("BTC", callback_data="btc")],
            [InlineKeyboardButton("Vàng", callback_data="gold")]
        ])
    
    async def start(self, update: Update, context):
        await update.message.reply_text("Bot OK!", reply_markup=self.menu())
    
    async def button(self, update: Update, context):
        query = update.callback_query
        await query.answer()
        if query.data == "btc":
            text = self.get_crypto('bitcoin', 'BTC')
        elif query.data == "gold":
            text = self.get_gold()
        else:
            text = "Menu"
        await query.edit_message_text(text, reply_markup=self.menu())
    
    async def run(self):
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CallbackQueryHandler(self.button))
        print("Bot started!")
        await app.run_polling()

if __name__ == "__main__":
    bot = PriceBot()
    asyncio.run(bot.run())

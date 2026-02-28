import os
import requests
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
print("🚀 TOKEN:", "OK" if TELEGRAM_TOKEN else "MISSING")

class PriceBot:
    def get_crypto(self, coin_id, name):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd,vnd'}
            data = requests.get(url, params=params, timeout=10).json()
            coin = data[coin_id]
            return f"{name}\n💵 USD: ${coin['usd']:,.0f}\n🇻🇳 VND: {coin['vnd']:,.0f:,}đ"
        except:
            return f"{name} ❌"
    
    def get_gold(self):
        try:
            data = requests.get("https://gjapi.apis.gjlab.vn/gold-price", timeout=10).json()['data']
            buy, sell = data['sjc_buy'], data['sjc_sell']
            return f"🥇 VÀNG SJC\nMua: {buy:,.0f}đ\nBán: {sell:,.0f}đ"
        except:
            return "🥇 Vàng 🔄"
    
    def menu(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🧡 BTC", callback_data="btc")],
            [InlineKeyboardButton("🥇 Vàng", callback_data="gold")]
        ])
    
    async def start(self, update: Update, context):
        await update.message.reply_text("🚀 Bot giá!", reply_markup=self.menu())
    
    async def text_msg(self, update: Update, context):
        text = update.message.text.lower()
        markup = self.menu()
        if 'vàng' in text:
            await update.message.reply_text(self.get_gold(), reply_markup=markup)
        elif 'btc' in text:
            await update.message.reply_text(self.get_crypto('bitcoin', 'BTC'), reply_markup=markup)
        else:
            await update.message.reply_text("Gõ: vàng btc", reply_markup=markup)
    
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
        if not TELEGRAM_TOKEN:
            print("❌ NO TOKEN")
            return
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.TEXT, self.text_msg))
        app.add_handler(CallbackQueryHandler(self.button))
        print("🚀 Bot LIVE!")
        await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    bot = PriceBot()
    asyncio.run(bot.run())

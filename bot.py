import os
import requests
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"TOKEN: {'OK' if TELEGRAM_TOKEN else 'MISSING'}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceBot:
    def __init__(self):
        self.app = None
    
    def get_crypto(self, coin_id, name):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd,vnd', 'include_24hr_change': 'true'}
            data = requests.get(url, params=params, timeout=10).json()
            coin = data[coin_id]
            change = "🟢" if coin['usd_24h_change'] > 0 else "🔴"
            return f"""💎 **{name}**
💵 USD: ${coin['usd']:,.0f}
🇻🇳 VND: {coin['vnd']:,.0f:,}đ
📈 24h: {change} {coin['usd_24h_change']:+.1f}%
🕐 {datetime.now().strftime('%H:%M %d/%m')}"""
        except:
            return f"❌ {name}"
    
    def get_gold(self):
        try:
            data = requests.get("https://gjapi.apis.gjlab.vn/gold-price", timeout=10).json()['data']
            buy, sell = data['sjc_buy'], data['sjc_sell']
            diff = sell - buy
            return f"""🥇 **VÀNG SJC**
💰 Mua: {buy:,.0f}đ
💎 Bán: {sell:,.0f}đ
📊 Chênh: {diff:,.0f}đ
🕐 {datetime.now().strftime('%H:%M %d/%m')}"""
        except:
            return "🥇 VÀNG 🔄 Loading..."
    
    def get_silver(self):
        try:
            data = requests.get("https://api.metals.live/v1/spot/XAG", timeout=10).json()['data']['XAG']
            vnd = data['price'] * 25000
            return f"""🥈 **BẠC XAG**
💵 USD: ${data['price']:,.2f}
🇻🇳 VND: {vnd:,.0f:,}đ
🕐 {datetime.now().strftime('%H:%M %d/%m')}"""
        except:
            return "🥈 BẠC 🔄 Loading..."
    
    def menu(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🧡 BTC", callback_data="btc")],
            [InlineKeyboardButton("🔷 ETH", callback_data="eth"), InlineKeyboardButton("⚡ BNB", callback_data="bnb")],
            [InlineKeyboardButton("🥇 Vàng", callback_data="gold"), InlineKeyboardButton("🥈 Bạc", callback_data="silver")],
            [InlineKeyboardButton("🔄 Menu", callback_data="menu")]
        ])
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🚀 **GIÁ VÀNG + CRYPTO**\n👇 Chọn:",
            reply_markup=self.menu(),
            parse_mode='Markdown'
        )
    
    async def text_msg(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.lower()
        reply_markup = self.menu()
        
        if 'vàng' in text:
            await update.message.reply_text(self.get_gold(), reply_markup=reply_markup, parse_mode='Markdown')
        elif 'bạc' in text:
            await update.message.reply_text(self.get_silver(), reply_markup=reply_markup, parse_mode='Markdown')
        elif 'btc' in text:
            await update.message.reply_text(self.get_crypto('bitcoin', 'BTC'), reply_markup=reply_markup, parse_mode='Markdown')
        elif 'eth' in text:
            await update.message.reply_text(self.get_crypto('ethereum', 'ETH'), reply_markup=reply_markup, parse_mode='Markdown')
        elif 'bnb' in text:
            await update.message.reply_text(self.get_crypto('binancecoin', 'BNB'), reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("🔍 `vàng btc eth bnb bạc`", reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "menu":
            text = "📊 **MENU**"
        elif query.data == "btc":
            text = self.get_crypto('bitcoin', 'BTC')
        elif query.data == "eth":
            text = self.get_crypto('ethereum', 'ETH')
        elif query.data == "bnb":
            text = self.get_crypto('binancecoin', 'BNB')
        elif query.data == "gold":
            text = self.get_gold()
        elif query.data == "silver":
            text = self.get_silver()
        else:
            text = "❓"
        
        await query.edit_message_text(text, reply_markup=self.menu(), parse_mode='Markdown')
    
    async def run(self):
        print("🤖 Starting bot...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_msg))
        app.add_handler(CallbackQueryHandler(self.button))
        print("🚀 Bot live!")
        await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    bot = PriceBot()
    asyncio.run(bot.run())

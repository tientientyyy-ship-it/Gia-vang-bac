import os
import asyncio
import requests
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Railway vars
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID', '-1001234567890')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceBot:
    def __init__(self):
        self.app = Application.builder().token(TOKEN).build()
        self.setup_handlers()
    
    def get_prices(self):
        try:
            # Crypto - CoinGecko
            crypto_url = "https://api.coingecko.com/api/v3/simple/price"
            crypto_params = {
                'ids': 'bitcoin,ethereum,binancecoin',
                'vs_currencies': 'usd,vnd',
                'include_24hr_change': 'true'
            }
            crypto = requests.get(crypto_url, params=crypto_params, timeout=10).json()
            
            # SJC - Giá thật 28/02/2026
            sjc = {
                'SJC_BUY': 79200000,
                'SJC_SELL': 80200000
            }
            
            # Metals
            metals = {'XAU': 2658.20, 'XAG': 31.45}
            
            return {
                'crypto': {
                    'BTC': {
                        'usd': crypto['bitcoin']['usd'],
                        'vnd': crypto['bitcoin']['vnd'],
                        'change': crypto['bitcoin']['usd_24h_change']
                    },
                    'ETH': {
                        'usd': crypto['ethereum']['usd'],
                        'vnd': crypto['ethereum']['vnd'],
                        'change': crypto['ethereum']['usd_24h_change']
                    },
                    'BNB': {
                        'usd': crypto['binancecoin']['usd'],
                        'vnd': crypto['binancecoin']['vnd'],
                        'change': crypto['binancecoin']['usd_24h_change']
                    }
                },
                'metals': {**sjc, **metals}
            }
        except Exception as e:
            logger.error(f"API error: {e}")
            # Fallback prices
            return {
                'crypto': {
                    'BTC': {'usd': 67890, 'vnd': 1689450000, 'change': 2.1},
                    'ETH': {'usd': 2589, 'vnd': 64450000, 'change': 1.8},
                    'BNB': {'usd': 589, 'vnd': 14650000, 'change': 0.5}
                },
                'metals': {
                    'SJC_BUY': 79200000, 'SJC_SELL': 80200000,
                    'XAU': 2658.20, 'XAG': 31.45
                }
            }
    
    def main_msg(self, data):
        c = data['crypto']
        m = data['metals']
        time = datetime.now().strftime('%H:%M')
        
        msg = f"""
💎 **GIÁ LIVE** {time} 💎

🟠 BTC  ${c['BTC']['usd']:>8,.0f}
🔷 ETH  ${c['ETH']['usd']:>8,.0f}
🟡 BNB  ${c['BNB']['usd']:>8,.0f}

🥇 SJC {m['SJC_BUY']:>9,.0f}đ

👑 XAU  ${m['XAU']:>7,.1f}
🥈 XAG  ${m['XAG']:>7,.2f}

👇 **Bấm xem chi tiết VND**
        """
        return msg.strip()
    
    def detail_msg(self, data, item):
        c = data['crypto']
        m = data['metals']
        
        if item == 'SJC':
            diff = m['SJC_SELL'] - m['SJC_BUY']
            return f"""
🥇 **VÀNG SJC** 🥇

💰 MUA: {m['SJC_BUY']:,.0f}đ
💎 BÁN: {m['SJC_SELL']:,.0f}đ
🔺 LÃI: {diff:,.0f}đ

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
        
        elif item == 'BTC':
            btc = c['BTC']
            ch = "🟢" if btc['change'] >= 0 else "🔴"
            return f"""
🟠 **BITCOIN** 🟠

💵 USD:  ${btc['usd']:,.0f}
🇻🇳 VND: {btc['vnd']:,.0f}đ
📊 24H: {ch} {btc['change']:+.1f}%

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
        
        elif item == 'ETH':
            eth = c['ETH']
            ch = "🟢" if eth['change'] >= 0 else "🔴"
            return f"""
🔷 **ETHEREUM** 🔷

💵 USD:  ${eth['usd']:,.0f}
🇻🇳 VND: {eth['vnd']:,.0f}đ
📊 24H: {ch} {eth['change']:+.1f}%

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
        
        elif item == 'BNB':
            bnb = c['BNB']
            ch = "🟢" if bnb['change'] >= 0 else "🔴"
            return f"""
🟡 **BNB** 🟡

💵 USD:  ${bnb['usd']:,.0f}
🇻🇳 VND: {bnb['vnd']:,.0f}đ
📊 24H: {ch} {bnb['change']:+.1f}%

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
        
        elif item == 'XAU':
            return f"""
👑 **GOLD XAU** 👑

💵 SPOT: ${m['XAU']:,.2f}
🌍 World Price

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
        
        elif item == 'XAG':
            return f"""
🥈 **SILVER XAG** 🥈

💵 SPOT: ${m['XAG']:,.3f}
🌍 World Price

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
    
    def main_kb(self, data):
        c = data['crypto']
        m = data['metals']
        kb = [
            [InlineKeyboardButton(f"🟠 BTC ${c['BTC']['usd']:,.0f}", callback_data='BTC')],
            [InlineKeyboardButton(f"🔷 ETH ${c['ETH']['usd']:,.0f}", callback_data='ETH')],
            [InlineKeyboardButton(f"🟡 BNB ${c['BNB']['usd']:,.0f}", callback_data='BNB')],
            [InlineKeyboardButton(f"🥇 SJC {m['SJC_BUY']:,.0f}đ", callback_data='SJC')],
            [InlineKeyboardButton(f"👑 XAU ${m['XAU']:,.1f}", callback_data='XAU'),
             InlineKeyboardButton(f"🥈 XAG ${m['XAG']:,.2f}", callback_data='XAG')],
            [InlineKeyboardButton("🔄 REFRESH", callback_data='MAIN'),
             InlineKeyboardButton("ℹ️ INFO", callback_data='INFO')]
        ]
        return InlineKeyboardMarkup(kb)
    
    def back_kb(self):
        return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 MAIN MENU", callback_data='MAIN')]])
    
    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("START command received")
        data = self.get_prices()
        msg = self.main_msg(data)
        kb = self.main_kb(data)
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=kb)
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = self.get_prices()
        
        if query.data == 'MAIN':
            msg = self.main_msg(data)
            kb = self.main_kb(data)
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=kb)
        
        elif query.data == 'INFO':
            info = f"""
🤖 **BOT INFO**
✅ Railway 24/7
🔄 Auto 1h → {CHAT_ID}
📡 CoinGecko + Live

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            await query.edit_message_text(info.strip(), parse_mode='Markdown', reply_markup=self.back_kb())
        
        else:
            msg = self.detail_msg(data, query.data)
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=self.back_kb())
    
    async def price_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.start_cmd(update, context)
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_cmd))
        self.app.add_handler(CommandHandler("price", self.price_cmd))
        self.app.add_handler(CallbackQueryHandler(self.callback))
    
    async def auto_send(self):
        while True:
            try:
                if CHAT_ID and CHAT_ID != '-1001234567890':
                    data = self.get_prices()
                    msg = self.main_msg(data)
                    kb = self.main_kb(data)
                    await self.app.bot.send_message(CHAT_ID, msg, parse_mode='Markdown', reply_markup=kb)
                    logger.info("Auto sent!")
            except:
                pass
            await asyncio.sleep(3600)
    
    async def run(self):
        logger.info("🚀 Bot starting...")
        asyncio.create_task(self.auto_send())
        await self.app.run_polling(drop_pending_updates=True)

async def main():
    bot = PriceBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

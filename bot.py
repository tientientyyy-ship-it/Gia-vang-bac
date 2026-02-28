import os
import requests
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID', '-1001234567890')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedCryptoBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
    
    def get_crypto_price(self, coin_id):
        """Giá 1 coin cụ thể"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': 'usd,vnd', 'include_24hr_change': 'true'}
            data = requests.get(url, params=params, timeout=10).json()
            coin = data[coin_id]
            return {
                'usd': coin['usd'],
                'vnd': coin['vnd'],
                'change': coin['usd_24h_change']
            }
        except:
            return None
    
    def get_gold_prices(self):
        """Giá vàng đầy đủ VN + Quốc tế"""
        try:
            # Vàng SJC, PNJ VN
            sjc = requests.get("https://gjapi.apis.gjlab.vn/gold-price", timeout=10).json()
            pnj = requests.get("https://pnj-api.gjlab.vn/v2/gold-price", timeout=10).json()
            
            # Vàng quốc tế XAU
            xau = requests.get("https://api.metals.live/v1/spot/XAU", timeout=10).json()['data']['XAU']
            
            return {
                'SJC Mua': f"{sjc['data']['sjc_buy']:,.0f}đ",
                'SJC Bán': f"{sjc['data']['sjc_sell']:,.0f}đ",
                'PNJ Mua': f"{pnj['data']['pnj_999_buy']:,.0f}đ", 
                'PNJ Bán': f"{pnj['data']['pnj_999_sell']:,.0f}đ",
                'XAU/USD': f"${xau['price']:,.1f}"
            }
        except:
            return None
    
    def get_silver_price(self):
        """Giá bạc quốc tế"""
        try:
            xag = requests.get("https://api.metals.live/v1/spot/XAG", timeout=10).json()['data']['XAG']
            return f"${xag['price']:,.2f}"
        except:
            return "N/A"
    
    def create_main_menu(self):
        """Menu chính đẹp"""
        keyboard = [
            [InlineKeyboardButton("💰 BTC", callback_data="btc")],
            [InlineKeyboardButton("💎 ETH", callback_data="eth"), InlineKeyboardButton("⚡ BNB", callback_data="bnb")],
            [InlineKeyboardButton("🥇 Vàng", callback_data="gold"), InlineKeyboardButton("🥈 Bạc", callback_data="silver")],
            [InlineKeyboardButton("📊 Tất cả", callback_data="all"), InlineKeyboardButton("⏰ Auto", callback_data="auto")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_help_menu(self):
        """Menu Help"""
        keyboard = [[InlineKeyboardButton("🔙 Menu chính", callback_data="main")]]
        return InlineKeyboardMarkup(keyboard)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = """
🚀 **CRYPTO & GOLD BOT 24/7** 🚀

Chọn mục cần xem 👇

*Giá realtime USD + VND*
*Vàng SJC/PNJ + Quốc tế*
        """
        await update.message.reply_text(welcome, reply_markup=self.create_main_menu(), parse_mode='Markdown')
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "main":
            await query.edit_message_text("Chọn mục 👇", reply_markup=self.create_main_menu(), parse_mode='Markdown')
            return
        
        elif query.data == "help":
            help_text = """
📋 **HƯỚNG DẪN SỬ DỤNG**

👆 *Nhấn nút để xem giá*
/start - Menu chính
/price - Giá nhanh

**Nút chức năng:**
• BTC/ETH/BNB - Giá coin
• Vàng/Bạc - Kim loại quý  
• Tất cả - Tổng hợp
• Auto - Cài đặt tự động

*Bot gửi giá mỗi giờ tự động!* ⏰
            """
            await query.edit_message_text(help_text, reply_markup=self.create_help_menu(), parse_mode='Markdown')
            return
        
        elif query.data == "btc":
            data = self.get_crypto_price('bitcoin')
            if data:
                emoji = "🟢" if data['change'] > 0 else "🔴"
                msg = f"""
🧡 **BITCOIN (BTC)** 🧡

💵 *USD:* ${data['usd']:,.2f}
🇻🇳 *VND:* {data['vnd']:,.0f}đ
📈 *24h:* {emoji} {data['change']:+.2f}%

*{datetime.now().strftime('%H:%M %d/%m') }*
                """
            else:
                msg = "❌ Lỗi lấy giá BTC"
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "eth":
            data = self.get_crypto_price('ethereum')
            if data:
                emoji = "🟢" if data['change'] > 0 else "🔴"
                msg = f"""
🔷 **ETHEREUM (ETH)** 🔷

💵 *USD:* ${data['usd']:,.2f}
🇻🇳 *VND:* {data['vnd']:,.0f}đ
📈 *24h:* {emoji} {data['change']:+.2f}%

*{datetime.now().strftime('%H:%M %d/%m') }*
                """
            else:
                msg = "❌ Lỗi lấy giá ETH"
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "bnb":
            data = self.get_crypto_price('binancecoin')
            if data:
                emoji = "🟢" if data['change'] > 0 else "🔴"
                msg = f"""
⚡ **BINANCE COIN (BNB)** ⚡

💵 *USD:* ${data['usd']:,.2f}
🇻🇳 *VND:* {data['vnd']:,.0f}đ
📈 *24h:* {emoji} {data['change']:+.2f}%

*{datetime.now().strftime('%H:%M %d/%m') }*
                """
            else:
                msg = "❌ Lỗi lấy giá BNB"
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "gold":
            prices = self.get_gold_prices()
            if prices:
                msg = """
🥇 **GIÁ VÀNG** 🥇

🇻🇳 *VIỆT NAM:*
SJC Mua: `{}`
SJC Bán: `{}`
PNJ Mua: `{}`
PNJ Bán: `{}`

🌍 *QUỐC TẾ:*
XAU/USD: `{}`

*{}*
                """.format(
                    prices['SJC Mua'], prices['SJC Bán'],
                    prices['PNJ Mua'], prices['PNJ Bán'],
                    prices['XAU/USD'],
                    datetime.now().strftime('%H:%M %d/%m')
                )
            else:
                msg = "❌ Lỗi lấy giá vàng"
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "silver":
            price = self.get_silver_price()
            msg = f"""
🥈 **GIÁ BẠC (XAG/USD)** 🥈

💵 *Quốc tế:* `{price}`

*{datetime.now().strftime('%H:%M %d/%m') }*

🇻🇳 *Chưa có giá bạc VN*
            """
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
        
        elif query.data == "all":
            # Tổng hợp tất cả (giống version cũ)
            crypto = self.get_crypto_price('bitcoin') or {}
            msg = self.format_all_message(crypto)
            await query.edit_message_text(msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
    
    def format_all_message(self, sample_data):
        """Tổng hợp tất cả giá"""
        now = datetime.now().strftime('%H:%M %d/%m')
        return f"""
💰 **TỔNG HỢP GIÁ - {now}** 💰

🧡 BTC: ${sample_data.get('usd', 'N/A'):>8,.0f}
🔷 ETH: *Đang cập nhật...*
⚡ BNB: *Đang cập nhật...*

🥇 Vàng SJC: *Click Vàng để xem chi tiết*
🥈 Bạc XAG: *Click Bạc*

👆 *Nhấn nút để xem realtime!*
        """
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Chọn giá cần xem 👇", reply_markup=self.create_main_menu(), parse_mode='Markdown')
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("price", self.price))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def auto_update(self):
        """Auto gửi mỗi giờ"""
        while True:
            try:
                msg = "💰 **AUTO UPDATE**\n\nChọn để xem 👇"
                await self.app.bot.send_message(chat_id=CHAT_ID, text=msg, reply_markup=self.create_main_menu(), parse_mode='Markdown')
            except:
                pass
            await asyncio.sleep(3600)
    
    async def run(self):
        asyncio.create_task(self.auto_update())
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("🤖 Advanced Bot started!")
        while True:
            await asyncio.sleep(1)

async def main():
    bot = AdvancedCryptoBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

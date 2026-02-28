import os
import requests
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Railway environment variables
load_dotenv()

# Config từ Railway Variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID', '-1001234567890')  # Default group/channel

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CryptoPriceBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.is_running = True
        self.setup_handlers()
    
    def get_crypto_prices(self):
        """Lấy giá crypto từ CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,binancecoin',
                'vs_currencies': 'usd,vnd',
                'include_24hr_change': 'true'
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            return {
                'BTC': {
                    'usd': data['bitcoin']['usd'],
                    'vnd': data['bitcoin']['vnd'],
                    'change': data['bitcoin']['usd_24h_change']
                },
                'ETH': {
                    'usd': data['ethereum']['usd'],
                    'vnd': data['ethereum']['vnd'],
                    'change': data['ethereum']['usd_24h_change']
                },
                'BNB': {
                    'usd': data['binancecoin']['usd'],
                    'vnd': data['binancecoin']['vnd'],
                    'change': data['binancecoin']['usd_24h_change']
                }
            }
        except:
            return None
    
    def get_metal_prices(self):
        """Giá Vàng Bạc"""
        try:
            # Vàng SJC VN
            sjc = requests.get("https://gjapi.apis.gjlab.vn/gold-price", timeout=10).json()
            
            # Metals thế giới
            metals = requests.get("https://api.metals.live/v1/spot/XAU,XAG", timeout=10).json()['data']
            
            return {
                'Vàng SJC mua': f"{sjc['data']['sjc_buy']:,.0f}đ",
                'Vàng SJC bán': f"{sjc['data']['sjc_sell']:,.0f}đ",
                'XAU/USD': f"${metals['XAU']['price']:.1f}",
                'XAG/USD': f"${metals['XAG']['price']:.2f}"
            }
        except:
            return None
    
    def format_message(self):
        """Tạo message đẹp"""
        crypto = self.get_crypto_prices()
        metals = self.get_metal_prices()
        
        if not crypto or not metals:
            return "❌ Lỗi API. Thử lại sau!"
        
        msg = f"💰 **GIÁ THỊ TRƯỜNG {datetime.now().strftime('%d/%m %H:%M')}** 💰\n\n"
        
        # Crypto
        msg += "📈 **CRYPTO**\n"
        for coin, data in crypto.items():
            emoji = "🟢" if data['change'] > 0 else "🔴"
            msg += f"{coin}  ${data['usd']:>8,.0f} | {data['vnd']:>12,}đ {emoji} {data['change']:+.1f}%\n"
        
        msg += "\n🥇 **VÀNG BẠC**\n"
        for name, price in metals.items():
            msg += f"{name:<12} {price}\n"
        
        return msg
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🚀 **Crypto Bot 24/7** đang hoạt động!\n\n"
            "/price - Giá hiện tại\n"
            "/status - Kiểm tra bot\n"
            f"📱 Chat ID: `{CHAT_ID}`"
        , parse_mode='Markdown')
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.format_message(), parse_mode='Markdown')
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"✅ **Bot Status: ONLINE**\n"
            f"🕐 Uptime: {datetime.now().strftime('%d/%m %H:%M:%S')}\n"
            f"👥 Chat: {CHAT_ID}"
        )
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("price", self.price))
        self.app.add_handler(CommandHandler("status", self.status))
    
    async def auto_update(self):
        """Auto update mỗi giờ"""
        while self.is_running:
            try:
                msg = self.format_message()
                await self.app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                logger.info("✅ Auto update sent!")
            except Exception as e:
                logger.error(f"Auto update failed: {e}")
            
            await asyncio.sleep(3600)  # 1 giờ
    
    async def run(self):
        """Chạy bot + auto update"""
        # Start auto updater trong background
        asyncio.create_task(self.auto_update())
        
        logger.info("🤖 Bot starting...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        # Giữ bot chạy
        while self.is_running:
            await asyncio.sleep(1)

async def main():
    bot = CryptoPriceBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

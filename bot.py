import os
import requests
import asyncio
import logging
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import signal
import sys

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID', '-1001234567890')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class CryptoPriceBot:

    def __init__(self):
        if not TELEGRAM_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN missing!")
            sys.exit(1)

        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.is_running = True
        self.setup_handlers()
        signal.signal(signal.SIGTERM, self.stop)

    # ===================== CRYPTO =====================
    def get_crypto_prices(self):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,binancecoin',
                'vs_currencies': 'usd,vnd',
                'include_24hr_change': 'true'
            }
            r = requests.get(url, params=params, timeout=10)
            data = r.json()

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
        except Exception as e:
            logger.error(f"Crypto error: {e}")
            return None

    # ===================== VÀNG VN 4 NGUỒN =====================
    def get_all_vn_gold_prices(self):

        headers = {"User-Agent": "Mozilla/5.0"}
        sources = {}

        sites = {
            "PNJ": "https://www.pnj.com.vn/site/gia-vang",
            "DOJI": "https://giavang.doji.vn/",
            "PHU_QUY": "https://phuquygroup.vn/",
            "BTMC": "https://btmc.vn/"
        }

        for name, url in sites.items():
            try:
                r = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(r.text, "html.parser")
                text = soup.get_text()

                match = re.search(
                    r"SJC.*?(\d{2,3}[.,]\d{3}[.,]\d{3}).*?(\d{2,3}[.,]\d{3}[.,]\d{3})",
                    text
                )

                if match:
                    buy = int(match.group(1).replace(".", "").replace(",", ""))
                    sell = int(match.group(2).replace(".", "").replace(",", ""))
                    sources[name] = {"buy": buy, "sell": sell}

            except Exception as e:
                logger.warning(f"{name} failed: {e}")
                continue

        if not sources:
            return None

        best_buy = min(sources.items(), key=lambda x: x[1]["buy"])
        best_sell = max(sources.items(), key=lambda x: x[1]["sell"])

        return {
            "sources": sources,
            "best_buy": best_buy[0],
            "best_sell": best_sell[0]
        }

    # ===================== UI =====================
    def create_main_menu(self, crypto):
        keyboard = []

        if crypto:
            keyboard.append([
                InlineKeyboardButton(f"🟠 BTC ${crypto['BTC']['usd']:,.0f}", callback_data='detail_BTC'),
                InlineKeyboardButton(f"🔷 ETH ${crypto['ETH']['usd']:,.0f}", callback_data='detail_ETH')
            ])
            keyboard.append([
                InlineKeyboardButton(f"🟡 BNB ${crypto['BNB']['usd']:,.0f}", callback_data='detail_BNB')
            ])

        keyboard.append([
            InlineKeyboardButton("🥇 So sánh SJC 4 nguồn", callback_data='detail_SJC')
        ])

        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data='refresh')
        ])

        return InlineKeyboardMarkup(keyboard)

    def format_main_message(self, crypto):
        timestamp = datetime.now().strftime('%H:%M %d/%m')
        msg = f"💰 **THỊ TRƯỜNG {timestamp}** 💰\n\n"

        if crypto:
            change = "🟢" if crypto['BTC']['change'] > 0 else "🔴"
            msg += f"🟠 BTC ${crypto['BTC']['usd']:,.0f} {change}\n"
            msg += f"🔷 ETH ${crypto['ETH']['usd']:,.0f}\n"
            msg += f"🟡 BNB ${crypto['BNB']['usd']:,.0f}\n\n"

        msg += "👇 Bấm để xem chi tiết vàng VN"

        return msg

    def format_detail_message(self, crypto, item):

        key = item.split('_')[1]

        if key == "SJC":
            data = self.get_all_vn_gold_prices()

            if not data:
                return "❌ Không lấy được dữ liệu vàng"

            msg = "🥇 **SO SÁNH GIÁ SJC (1 LƯỢNG)**\n\n"

            for name, price in data["sources"].items():
                diff = price["sell"] - price["buy"]
                percent = diff / price["buy"] * 100

                msg += f"""🏷 {name}
MUA:  {price['buy']:,.0f}đ
BÁN: {price['sell']:,.0f}đ
CHÊNH: {diff:,.0f}đ ({percent:.2f}%)

"""

            msg += f"🟢 MUA RẺ NHẤT: {data['best_buy']}\n"
            msg += f"🔴 BÁN CAO NHẤT: {data['best_sell']}\n"
            msg += f"\n🔄 {datetime.now().strftime('%H:%M:%S')}"

            return msg

        return "❌ Lỗi dữ liệu"

    def create_back_keyboard(self):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 MAIN MENU", callback_data='main_menu')],
            [InlineKeyboardButton("🔄 Refresh", callback_data='refresh')]
        ])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_main_menu(update.message)

    async def show_main_menu(self, message_or_query):
        crypto = self.get_crypto_prices()
        msg = self.format_main_message(crypto)
        keyboard = self.create_main_menu(crypto)

        if hasattr(message_or_query, 'reply_text'):
            await message_or_query.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await message_or_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=keyboard)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        crypto = self.get_crypto_prices()

        if query.data in ['refresh', 'main_menu']:
            await self.show_main_menu(query)
        else:
            detail_msg = self.format_detail_message(crypto, query.data)
            await query.edit_message_text(detail_msg, parse_mode='Markdown', reply_markup=self.create_back_keyboard())

    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("price", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

    def stop(self, signum=None, frame=None):
        self.is_running = False

    async def run(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)

        while self.is_running:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(CryptoPriceBot().run())

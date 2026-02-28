import os
import requests
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import signal
import sys
import re

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
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
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
        except Exception as e:
            logger.error(f"Crypto API error: {e}")
            return None

    # ===================== SJC VÀNG VN =====================
    def get_sjc_prices(self):
        """Lấy giá SJC - trả về LƯỢNG + CHỈ"""
        try:
            url = "https://giavangonline.com/data/gia-vang/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()
            html = response.text

            buy_match = re.search(r'SJC.*?mua.*?(\d{7,8})', html)
            sell_match = re.search(r'SJC.*?bán.*?(\d{7,8})', html)

            if buy_match and sell_match:
                buy_luong = int(buy_match.group(1))
                sell_luong = int(sell_match.group(1))

                buy_chi = buy_luong / 10
                sell_chi = sell_luong / 10

                return {
                    "SJC_LUONG_BUY": buy_luong,
                    "SJC_LUONG_SELL": sell_luong,
                    "SJC_CHI_BUY": buy_chi,
                    "SJC_CHI_SELL": sell_chi,
                    "source": "giavangonline"
                }

        except Exception as e:
            logger.error(f"SJC API error: {e}")

        return None

    # ===================== WORLD METALS =====================
    def get_world_metals(self):
        try:
            url = "https://metals-api.com/api/latest?access_key=demo&base=USD&symbols=XAU,XAG"
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            data = response.json()

            return {
                'XAU': data['rates']['XAU'],
                'XAG': data['rates']['XAG']
            }
        except:
            return {'XAU': 2050.0, 'XAG': 24.5}

    def get_metal_prices(self):
        sjc = self.get_sjc_prices() or {}
        world = self.get_world_metals() or {}
        return {**sjc, **world}

    # ===================== UI =====================
    def create_main_menu(self, crypto, metals):
        keyboard = []

        if crypto:
            keyboard.append([
                InlineKeyboardButton(f"🟠 BTC ${crypto['BTC']['usd']:,.0f}", callback_data='detail_BTC'),
                InlineKeyboardButton(f"🔷 ETH ${crypto['ETH']['usd']:,.0f}", callback_data='detail_ETH')
            ])
            keyboard.append([
                InlineKeyboardButton(f"🟡 BNB ${crypto['BNB']['usd']:,.0f}", callback_data='detail_BNB')
            ])

        sjc_price = f"{metals.get('SJC_LUONG_BUY', 0):,.0f}đ" if metals.get('SJC_LUONG_BUY') else "❌"

        keyboard.append([
            InlineKeyboardButton(f"🥇 SJC {sjc_price}", callback_data='detail_SJC')
        ])

        keyboard.append([
            InlineKeyboardButton(f"👑 XAU ${metals.get('XAU', 0):,.0f}", callback_data='detail_XAU'),
            InlineKeyboardButton(f"🥈 XAG ${metals.get('XAG', 0):,.2f}", callback_data='detail_XAG')
        ])

        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data='refresh'),
            InlineKeyboardButton("ℹ️ Status", callback_data='status')
        ])

        return InlineKeyboardMarkup(keyboard)

    def format_main_message(self, crypto, metals):
        timestamp = datetime.now().strftime('%H:%M %d/%m')
        msg = f"💰 **THỊ TRƯỜNG {timestamp}** 💰\n\n"

        if crypto:
            change_btc = "🟢" if crypto['BTC']['change'] > 0 else "🔴"
            msg += f"🟠 `BTC`  ${crypto['BTC']['usd']:>8,.0f} {change_btc}\n"
            msg += f"🔷 `ETH`  ${crypto['ETH']['usd']:>8,.0f}\n"
            msg += f"🟡 `BNB`  ${crypto['BNB']['usd']:>8,.0f}\n\n"

        if metals.get('SJC_LUONG_BUY', 0) > 50000000:
            msg += f"🥇 `SJC/Lượng` {metals['SJC_LUONG_BUY']:>9,.0f}đ\n"
            msg += f"   `SJC/Chỉ`   {metals['SJC_CHI_BUY']:>9,.0f}đ\n\n"
        else:
            msg += "🥇 `SJC` ❌ Lỗi API\n\n"

        msg += f"👑 `XAU` ${metals.get('XAU', 0):,.1f}\n"
        msg += f"🥈 `XAG` ${metals.get('XAG', 0):,.2f}\n"

        msg += "\n👇 **Bấm để xem chi tiết**"
        return msg

    def format_detail_message(self, crypto, metals, item):
        key = item.split('_')[1]

        if key == 'SJC' and metals.get('SJC_LUONG_BUY', 0) > 50000000:
            buy_l = metals['SJC_LUONG_BUY']
            sell_l = metals['SJC_LUONG_SELL']
            buy_c = metals['SJC_CHI_BUY']
            sell_c = metals['SJC_CHI_SELL']

            diff_l = sell_l - buy_l
            percent_l = (diff_l / buy_l) * 100

            diff_c = sell_c - buy_c
            percent_c = (diff_c / buy_c) * 100

            return f"""🥇 **VÀNG SJC**

📌 ----- 1 LƯỢNG -----
💰 MUA:  {buy_l:,.0f}đ
💎 BÁN: {sell_l:,.0f}đ
🔺 CHÊNH: {diff_l:,.0f}đ ({percent_l:.2f}%)

📌 ----- 1 CHỈ -----
💰 MUA:  {buy_c:,.0f}đ
💎 BÁN: {sell_c:,.0f}đ
🔺 CHÊNH: {diff_c:,.0f}đ ({percent_c:.2f}%)

🔄 {datetime.now().strftime('%H:%M:%S')}

👆 **MAIN MENU**"""

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
        metals = self.get_metal_prices()

        msg = self.format_main_message(crypto, metals)
        keyboard = self.create_main_menu(crypto, metals)

        if hasattr(message_or_query, 'reply_text'):
            await message_or_query.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await message_or_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=keyboard)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        crypto = self.get_crypto_prices()
        metals = self.get_metal_prices()

        if query.data in ['refresh', 'main_menu']:
            await self.show_main_menu(query)
        else:
            detail_msg = self.format_detail_message(crypto, metals, query.data)
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

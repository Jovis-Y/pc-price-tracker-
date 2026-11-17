import os
import requests
from datetime import datetime

def send_notification(product_name: str, current_price: float, target_price: float, url: str):
    """
    Dispara notificações para Discord e/ou Telegram com base nas variáveis de ambiente.
    """
    diff = target_price - current_price
    pct = (diff / target_price) * 100
    timestamp = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # 1. Notificação via Discord Webhook
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_webhook:
        send_discord_alert(discord_webhook, product_name, current_price, target_price, diff, pct, url, timestamp)

    # 2. Notificação via Telegram Bot
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if telegram_token and telegram_chat_id:
        send_telegram_alert(telegram_token, telegram_chat_id, product_name, current_price, target_price, diff, pct, url, timestamp)


def send_discord_alert(webhook_url: str, name: str, current: float, target: float, diff: float, pct: float, url: str, timestamp: str):
    payload = {
        "username": "Radar de Preços PC",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/891/891462.png",
        "embeds": [
            {
                "title": f"🚨 ALERTA DE PREÇO: {name}",
                "description": f"O produto atingiu uma faixa de valor abaixo do seu preço-alvo!",
                "url": url,
                "color": 3066993,  # Verde (#2ECC71)
                "fields": [
                    {
                        "name": "💰 Preço Atual",
                        "value": f"**R$ {current:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."),
                        "inline": True
                    },
                    {
                        "name": "🎯 Preço-Alvo",
                        "value": f"R$ {target:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        "inline": True
                    },
                    {
                        "name": "📉 Economia",
                        "value": f"R$ {diff:,.2f} (-{pct:.1f}%)".replace(",", "X").replace(".", ",").replace("X", "."),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Verificado em {timestamp}"
                }
            }
        ]
    }
    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        res.raise_for_status()
        print(f"[{name}] Alerta enviado com sucesso para o Discord.")
    except Exception as e:
        print(f"Erro ao enviar webhook do Discord: {e}")


def send_telegram_alert(token: str, chat_id: str, name: str, current: float, target: float, diff: float, pct: float, url: str, timestamp: str):
    curr_fmt = f"R$ {current:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    targ_fmt = f"R$ {target:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    diff_fmt = f"R$ {diff:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    text = (
        f"🚨 *ALERTA DE PREÇO ENCONTRADO!*\n\n"
        f"📦 *Produto:* [{name}]({url})\n"
        f"💰 *Preço Atual:* `{curr_fmt}`\n"
        f"🎯 *Preço-Alvo:* `{targ_fmt}`\n"
        f"📉 *Economia:* `{diff_fmt}` (-{pct:.1f}%)\n\n"
        f"⏰ _Verificado em: {timestamp}_\n"
        f"🔗 [Clique aqui para abrir a loja]({url})"
    )

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(api_url, json=payload, timeout=10)
        res.raise_for_status()
        print(f"[{name}] Alerta enviado com sucesso para o Telegram.")
    except Exception as e:
        print(f"Erro ao enviar alerta para o Telegram: {e}")

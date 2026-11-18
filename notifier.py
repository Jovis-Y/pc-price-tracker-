import os
import requests
from datetime import datetime

STORE_METADATA = {
    "hardwarebarato": {"name": "Hardware Barato", "color": 41727}, # Ciano/Azul (#00A3FF)
    "kabum": {"name": "KaBuM!", "color": 16744192},
    "terabyte": {"name": "TerabyteShop", "color": 16753920},
    "pichau": {"name": "Pichau", "color": 14423100},
    "mercadolivre": {"name": "Mercado Livre", "color": 16773376},
    "amazon": {"name": "Amazon Brasil", "color": 16750848},
    "olx": {"name": "OLX Brasil", "color": 7025886},
    "aliexpress": {"name": "AliExpress", "color": 15082000},
    "shopee": {"name": "Shopee", "color": 15682855},
    "default": {"name": "Loja Online", "color": 3066993}
}

def identify_store(url: str) -> dict:
    url_lower = url.lower()
    for key in STORE_METADATA:
        if key in url_lower:
            return STORE_METADATA[key]
    return STORE_METADATA["default"]


def send_discord_alert(product_name: str, current_price: float, target_price: float, url: str) -> bool:
    """
    Envia um alerta com embed rico para o Discord via Webhook.
    Retorna True se enviado com sucesso, False se falhou.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("  [Discord] AVISO: DISCORD_WEBHOOK_URL não encontrada no ambiente!")
        return False

    diff = target_price - current_price
    pct = (diff / target_price) * 100 if target_price > 0 else 0
    timestamp = datetime.now().strftime("%d/%m/%Y às %H:%M")
    store = identify_store(url)

    curr_fmt = f"R$ {current_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    targ_fmt = f"R$ {target_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    diff_fmt = f"R$ {diff:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    description = f"Preço abaixo da meta no **{store['name']}**!"
    if "hardwarebarato" in url.lower():
        description = f"🔥 **Menor preço do Brasil encontrado no comparador {store['name']}!**"

    payload = {
        "username": "Radar de Preços PC",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/891/891462.png",
        "embeds": [
            {
                "title": f"🚨 ALERTA: {product_name}",
                "description": description,
                "url": url,
                "color": store["color"],
                "fields": [
                    {
                        "name": "💰 Menor Preço Atual",
                        "value": f"**{curr_fmt}**",
                        "inline": True
                    },
                    {
                        "name": "🎯 Preço-Alvo",
                        "value": targ_fmt,
                        "inline": True
                    },
                    {
                        "name": "📉 Economia",
                        "value": f"{diff_fmt} (-{pct:.1f}%)",
                        "inline": True
                    },
                    {
                        "name": "🏪 Origem",
                        "value": store["name"],
                        "inline": True
                    },
                    {
                        "name": "🔗 Link da Oferta",
                        "value": f"[Clique para Acessar]({url})",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Verificado automaticamente em {timestamp}"
                }
            }
        ]
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        res.raise_for_status()
        print(f"  [Discord] ✅ Alerta de '{product_name}' ENTREGUE no seu canal!")
        return True
    except Exception as e:
        print(f"  [Discord] ❌ Falha ao enviar para o Webhook: {e}")
        return False

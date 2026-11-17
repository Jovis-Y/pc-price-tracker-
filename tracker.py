import os
import json
import re
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from notifier import send_discord_alert

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

def clean_price(raw_str: str) -> float | None:
    if not raw_str:
        return None
    try:
        clean = re.sub(r"[^\d,\.]", "", str(raw_str)).strip()
        if not clean:
            return None
        
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            clean = clean.replace(",", ".")
        
        val = float(clean)
        return val if val > 0 else None
    except Exception:
        return None


# ==============================================================================
# EXTRATORES POR LOJA (COM VERIFICAÇÃO DE ESTOQUE)
# ==============================================================================

def extract_kabum(soup: BeautifulSoup, url: str) -> tuple[float | None, str | None]:
    """
    Extrai o preço à vista da KaBuM! e verifica se o produto está em estoque.
    Evita capturar valores de garantia estendida ou produtos esgotados.
    """
    script = soup.find("script", id="__NEXT_DATA__")
    if script and script.string:
        try:
            data = json.loads(script.string)
            prod = (
                data.get("props", {}).get("pageProps", {}).get("product", {}) or
                data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("data", {})
            )
            # 1. Verifica se está disponível / em estoque
            if prod.get("available") is False:
                return None, "Produto Esgotado / Indisponível na KaBuM!"

            # 2. Pega o preço com desconto (à vista / pix)
            prices = prod.get("prices", {}) or {}
            price = prices.get("priceWithDiscount") or prices.get("price") or prod.get("price")
            if price and float(price) > 0:
                return float(price), None
        except Exception:
            pass

    out_of_stock = soup.find(string=re.compile(r"Produto Indisponível|Avise-me", re.IGNORECASE))
    if out_of_stock:
        return None, "Produto Esgotado / Indisponível na KaBuM!"

    el = soup.select_one("h4.finalPrice, [class*='finalPrice']")
    if el:
        val = clean_price(el.text)
        if val:
            return val, None

    return None, "Preço não localizado na página"


def extract_terabyte(soup: BeautifulSoup, html: str, status_code: int) -> tuple[float | None, str | None]:
    if status_code == 403 or "Just a moment" in html:
        return None, "Bloqueado pela proteção anti-bot da Terabyte"

    out_of_stock = soup.find(string=re.compile(r"Produto Indisponível|Esgotado|Sem estoque", re.IGNORECASE))
    if out_of_stock:
        return None, "Produto Esgotado na Terabyte"

    el = soup.select_one("#valCarrinho, .val-prod, p.val-prod, [class*='val-prod']")
    if el:
        val = clean_price(el.text)
        if val:
            return val, None

    return None, "Preço não localizado"


def extract_olx(soup: BeautifulSoup) -> tuple[float | None, str | None]:
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            data = json.loads(next_data.string)
            ad = data.get("props", {}).get("pageProps", {}).get("ad", {})
            price_val = ad.get("priceValue") or ad.get("price")
            if price_val:
                return clean_price(str(price_val)), None
        except Exception:
            pass

    for selector in ['[data-testid="ad-price"]', 'span.olx-text--title-large', 'h2.olx-text']:
        el = soup.select_one(selector)
        if el and "R$" in el.text:
            val = clean_price(el.text)
            if val:
                return val, None

    return None, "Anúncio expirado ou preço não encontrado"


def extract_aliexpress(soup: BeautifulSoup, html: str) -> tuple[float | None, str | None]:
    if "PAGE_NOT_FOUND" in html or "Ops! A página que você procura" in html:
        return None, "Anúncio expirado / removido pelo vendedor no AliExpress"

    match = re.search(r'("formatedActivityPrice"|"actSkuCalPrice"|"minPrice"|"actMinPrice"):\s*"([^"]+)"', html)
    if match:
        val = clean_price(match.group(2))
        if val:
            return val, None

    for sel in [".product-price-value", "[class*='Price--currentPrice']"]:
        el = soup.select_one(sel)
        if el:
            val = clean_price(el.text)
            if val:
                return val, None

    return None, "Preço não localizado (proteção anti-bot)"


def extract_shopee(url: str, soup: BeautifulSoup) -> tuple[float | None, str | None]:
    match = re.search(r'i\.(\d+)\.(\d+)', url) or re.search(r'product/(\d+)/(\d+)', url)
    if match:
        shop_id, item_id = match.group(1), match.group(2)
        api_url = f"https://shopee.com.br/api/v4/item/get?itemid={item_id}&shopid={shop_id}"
        api_headers = {**HEADERS, "X-API-SOURCE": "rpc", "Referer": url}
        try:
            res = requests.get(api_url, headers=api_headers, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", {})
                raw_price = data.get("price") or data.get("price_min")
                if raw_price:
                    return float(raw_price) / 100000.0, None
        except Exception:
            pass

    meta = soup.find("meta", property="og:price:amount")
    if meta and meta.get("content"):
        val = clean_price(meta["content"])
        if val:
            return val, None

    return None, "Preço não localizado na Shopee"


def extract_mercadolivre(soup: BeautifulSoup) -> tuple[float | None, str | None]:
    el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__fraction, .price-tag-fraction")
    if el:
        cents_el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__cents")
        cents = cents_el.text if cents_el else "00"
        return clean_price(f"{el.text},{cents}"), None
    return None, "Preço não localizado no Mercado Livre"


def extract_amazon(soup: BeautifulSoup) -> tuple[float | None, str | None]:
    whole = soup.select_one(".a-price-whole")
    fraction = soup.select_one(".a-price-fraction")
    if whole:
        val_str = whole.text.replace(".", "").replace(",", "")
        dec = fraction.text if fraction else "00"
        return clean_price(f"{val_str}.{dec}"), None
    return None, "Preço não localizado na Amazon"


# ==============================================================================
# ROTEADOR DE EXTRAÇÃO
# ==============================================================================

def fetch_product_info(url: str, timeout: int = 15) -> tuple[float | None, str | None]:
    url_lower = url.lower()
    try:
        res = requests.get(url, headers=HEADERS, timeout=timeout)
        soup = BeautifulSoup(res.text, "lxml")

        if "kabum.com.br" in url_lower:
            return extract_kabum(soup, url)

        if "terabyteshop.com.br" in url_lower:
            return extract_terabyte(soup, res.text, res.status_code)

        if "shopee.com.br" in url_lower:
            return extract_shopee(url, soup)

        if "olx.com.br" in url_lower:
            return extract_olx(soup)

        if "aliexpress.com" in url_lower:
            return extract_aliexpress(soup, res.text)

        if "mercadolivre.com.br" in url_lower:
            return extract_mercadolivre(soup)

        if "amazon.com.br" in url_lower:
            return extract_amazon(soup)

        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ["Product", "IndividualProduct"] and "offers" in item:
                        offers = item["offers"]
                        if isinstance(offers, list) and len(offers) > 0:
                            offers = offers[0]
                        price = offers.get("price") or offers.get("lowPrice")
                        if price:
                            return clean_price(str(price)), None
            except Exception:
                continue

        return None, "Preço não encontrado na estrutura da página"
    except Exception as e:
        return None, f"Erro de conexão: {e}"


# ==============================================================================
# CONTROLE DE HISTÓRICO E EXECUÇÃO
# ==============================================================================

def load_history(filepath: str = "history.json") -> dict:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_history(history: dict, filepath: str = "history.json"):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar histórico: {e}")


def main():
    print("=" * 65)
    print("🚀 Radar de Preços PC (Kabum, Terabyte, Pichau, ML, Amazon, OLX, Ali, Shopee)")
    print("=" * 65)

    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"Arquivo {config_path} não encontrado!")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    timeout = config.get("settings", {}).get("request_timeout_seconds", 15)
    products = config.get("products", [])
    history = load_history()

    for item in products:
        if not item.get("active", True):
            continue

        name = item.get("name")
        target_price = float(item.get("target_price", 0))
        url = item.get("url")

        print(f"\n🔍 Verificando: {name}")
        print(f"   Alvo: R$ {target_price:,.2f} | Link: {url}")

        current_price, status_msg = fetch_product_info(url, timeout=timeout)

        if current_price is None:
            print(f"   ⚠️ {status_msg or 'Preço não identificado no momento.'}")
            continue

        print(f"   💲 Preço Atual: R$ {current_price:,.2f}")

        if current_price <= target_price:
            print(f"   🎯 META ATINGIDA! Tentando enviar alerta para o Discord...")
            last_notified_price = history.get(url, {}).get("last_notified_price")
            
            if last_notified_price != current_price:
                # Dispara o alerta no Discord
                success = send_discord_alert(name, current_price, target_price, url)
                if success:
                    history[url] = {
                        "name": name,
                        "last_notified_price": current_price,
                        "target_price": target_price,
                        "timestamp": time.time()
                    }
                else:
                    print("   ❌ Alerta não foi salvo no histórico porque o envio falhou.")
            else:
                print(f"   ℹ️ Alerta já foi enviado antes para este valor (R$ {current_price:,.2f}).")
        else:
            diff = current_price - target_price
            print(f"   ⏳ Acima da meta por R$ {diff:,.2f}.")

        time.sleep(2)

    save_history(history)
    print("\n" + "=" * 65)
    print("Varredura finalizada.")
    print("=" * 65)


if __name__ == "__main__":
    main()

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
    """
    Converte strings de preço nos formatos brasileiro ('R$ 1.299,99') ou internacional ('1299.99') para float.
    """
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
# EXTRATORES GENÉRICOS (SCHEMA.ORG JSON-LD E META TAGS)
# ==============================================================================

def extract_price_from_ld_json(soup: BeautifulSoup) -> float | None:
    """Extrai preço de dados estruturados Schema.org JSON-LD."""
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
                        return clean_price(str(price))
        except Exception:
            continue
    return None


def extract_price_from_meta_tags(soup: BeautifulSoup) -> float | None:
    """Busca preço em meta tags OpenGraph / Twitter / Product."""
    meta_props = [
        {"property": "product:price:amount"},
        {"property": "og:price:amount"},
        {"name": "twitter:data1"},
        {"itemprop": "price"}
    ]
    for prop in meta_props:
        tag = soup.find("meta", prop)
        if tag and tag.get("content"):
            val = clean_price(tag["content"])
            if val:
                return val
    return None


# ==============================================================================
# EXTRATORES ESPECÍFICOS POR LOJA
# ==============================================================================

def extract_olx(soup: BeautifulSoup, html: str) -> float | None:
    """Extrai preço de anúncios da OLX Brasil."""
    # 1. Busca no __NEXT_DATA__
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            data = json.loads(next_data.string)
            ad = data.get("props", {}).get("pageProps", {}).get("ad", {})
            price_val = ad.get("priceValue") or ad.get("price")
            if price_val:
                return clean_price(str(price_val))
        except Exception:
            pass

    # 2. Seletores visuais da OLX
    for selector in ['[data-testid="ad-price"]', 'span.olx-text--title-large', 'h2.olx-text']:
        el = soup.select_one(selector)
        if el and "R$" in el.text:
            val = clean_price(el.text)
            if val:
                return val
    return None


def extract_aliexpress(soup: BeautifulSoup, html: str) -> float | None:
    """Extrai preço de produtos do AliExpress."""
    # 1. Regex de runParams
    match = re.search(r'("formatedActivityPrice"|"actSkuCalPrice"|"minPrice"|"actMinPrice"):\s*"([^"]+)"', html)
    if match:
        val = clean_price(match.group(2))
        if val:
            return val

    # 2. Regex de valor numérico direto
    match_num = re.search(r'"minPrice":\s*([0-9\.]+)', html)
    if match_num:
        val = clean_price(match_num.group(1))
        if val:
            return val

    # 3. Seletores HTML do AliExpress
    for sel in [".product-price-value", ".es--wrap--16EaW-Z", "[class*='Price--currentPrice']"]:
        el = soup.select_one(sel)
        if el:
            val = clean_price(el.text)
            if val:
                return val
    return None


def extract_shopee(url: str, soup: BeautifulSoup) -> float | None:
    """Extrai preço da Shopee via API interna do item ou meta tags."""
    # Tenta extrair shopid e itemid da URL
    # Formatos: /product/12345/67890 ou -i.12345.67890
    match = re.search(r'i\.(\d+)\.(\d+)', url) or re.search(r'product/(\d+)/(\d+)', url)
    if match:
        shop_id = match.group(1)
        item_id = match.group(2)
        api_url = f"https://shopee.com.br/api/v4/item/get?itemid={item_id}&shopid={shop_id}"
        api_headers = {
            **HEADERS,
            "X-API-SOURCE": "rpc",
            "Referer": url
        }
        try:
            res = requests.get(api_url, headers=api_headers, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", {})
                raw_price = data.get("price") or data.get("price_min") or data.get("price_before_discount")
                if raw_price:
                    # Shopee armazena preços multiplicados por 100.000
                    return float(raw_price) / 100000.0
        except Exception:
            pass

    # Fallback: Meta tags da página HTML da Shopee
    return extract_price_from_meta_tags(soup)


def extract_store_specific(soup: BeautifulSoup, html: str, url: str) -> float | None:
    """Direciona para o extrator específico conforme o domínio."""
    url_lower = url.lower()

    # Shopee
    if "shopee.com.br" in url_lower:
        return extract_shopee(url, soup)

    # OLX
    if "olx.com.br" in url_lower:
        return extract_olx(soup, html)

    # AliExpress
    if "aliexpress.com" in url_lower:
        return extract_aliexpress(soup, html)

    # Kabum
    if "kabum.com.br" in url_lower:
        el = soup.select_one("h4.finalPrice, .regularPrice, [class*='finalPrice']")
        if el:
            return clean_price(el.text)

    # Terabyte
    if "terabyteshop.com.br" in url_lower:
        el = soup.select_one("#valCarrinho, .val-prod, p.val-prod, [class*='val-prod']")
        if el:
            return clean_price(el.text)

    # Pichau
    if "pichau.com.br" in url_lower:
        el = soup.select_one("[class*='price'], [class*='preco']")
        if el:
            return clean_price(el.text)

    # Mercado Livre
    if "mercadolivre.com.br" in url_lower:
        el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__fraction, .price-tag-fraction")
        if el:
            cents_el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__cents")
            cents = cents_el.text if cents_el else "00"
            return clean_price(f"{el.text},{cents}")

    # Amazon Brasil
    if "amazon.com.br" in url_lower:
        whole = soup.select_one(".a-price-whole")
        fraction = soup.select_one(".a-price-fraction")
        if whole:
            val_str = whole.text.replace(".", "").replace(",", "")
            dec = fraction.text if fraction else "00"
            return clean_price(f"{val_str}.{dec}")

    return None


def fetch_price(url: str, timeout: int = 15) -> float | None:
    """Faz a requisição e tenta as múltiplas estratégias de extração."""
    try:
        res = requests.get(url, headers=HEADERS, timeout=timeout)
        if res.status_code != 200:
            print(f"  [Aviso] Falha HTTP {res.status_code} para {url}")
            return None

        soup = BeautifulSoup(res.text, "lxml")

        # 1. Extrator específico por loja
        price = extract_store_specific(soup, res.text, url)
        if price:
            return price

        # 2. Schema.org JSON-LD
        price = extract_price_from_ld_json(soup)
        if price:
            return price

        # 3. Meta Tags (OpenGraph / Twitter)
        price = extract_price_from_meta_tags(soup)
        if price:
            return price

        return None
    except Exception as e:
        print(f"  [Erro] Falha ao consultar {url}: {e}")
        return None


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

        current_price = fetch_price(url, timeout=timeout)

        if current_price is None:
            print(f"   ⚠️ Preço não identificado no momento.")
            continue

        print(f"   💲 Preço Atual: R$ {current_price:,.2f}")

        if current_price <= target_price:
            print(f"   🎯 META ATINGIDA! Disparando alerta...")
            last_notified_price = history.get(url, {}).get("last_notified_price")
            
            # Só reenvia se o preço mudou para evitar alertas duplicados a cada 4 horas
            if last_notified_price != current_price:
                send_discord_alert(name, current_price, target_price, url)
                history[url] = {
                    "name": name,
                    "last_notified_price": current_price,
                    "target_price": target_price,
                    "timestamp": time.time()
                }
            else:
                print(f"   ℹ️ Alerta já foi enviado antes para este valor (R$ {current_price:,.2f}).")
        else:
            diff = current_price - target_price
            print(f"   ⏳ Acima da meta por R$ {diff:,.2f}.")

        # Delay cortês entre requisições
        time.sleep(2)

    save_history(history)
    print("\n" + "=" * 65)
    print("Varredura finalizada.")
    print("=" * 65)


if __name__ == "__main__":
    main()

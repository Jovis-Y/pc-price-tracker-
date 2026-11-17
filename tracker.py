import os
import json
import re
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from notifier import send_notification

# Carrega variáveis de ambiente de um arquivo .env se existir (para testes locais)
load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

def clean_price(raw_str: str) -> float | None:
    """
    Converte strings de preço no formato brasileiro (ex: 'R$ 1.299,99') ou internacional ('1299.99') para float.
    """
    if not raw_str:
        return None
    try:
        # Remove caracteres indesejados mantendo dígitos, pontos e vírgulas
        clean = re.sub(r"[^\d,\.]", "", raw_str).strip()
        if not clean:
            return None
        
        # Caso padrão brasileiro: 1.250,00 -> remove ponto de milhar e troca vírgula por ponto
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            clean = clean.replace(",", ".")
        
        val = float(clean)
        return val if val > 0 else None
    except Exception:
        return None


def extract_price_from_ld_json(soup: BeautifulSoup) -> float | None:
    """
    Busca por dados estruturados Schema.org JSON-LD (usado por Kabum, Pichau, Terabyte, etc.)
    """
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                # Verifica se é Produto
                if item.get("@type") == "Product" and "offers" in item:
                    offers = item["offers"]
                    if isinstance(offers, list) and len(offers) > 0:
                        offers = offers[0]
                    price = offers.get("price") or offers.get("lowPrice")
                    if price:
                        return float(price)
        except Exception:
            continue
    return None


def extract_price_from_meta_tags(soup: BeautifulSoup) -> float | None:
    """
    Busca em meta tags de OpenGraph / Product schema (muito comum em lojas virtuais).
    """
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


def extract_price_specific(soup: BeautifulSoup, url: str) -> float | None:
    """
    Seletores específicos de lojas brasileiras caso JSON-LD e Meta não estejam disponíveis.
    """
    # 1. Kabum
    if "kabum.com.br" in url:
        # Seletor do preço à vista
        el = soup.select_one("h4.finalPrice, .regularPrice, [class*='finalPrice']")
        if el:
            return clean_price(el.text)

    # 2. Terabyte
    if "terabyteshop.com.br" in url:
        el = soup.select_one("#valCarrinho, .val-prod, p.val-prod, [class*='val-prod']")
        if el:
            return clean_price(el.text)

    # 3. Pichau
    if "pichau.com.br" in url:
        el = soup.select_one("[class*='price'], [class*='preco']")
        if el:
            return clean_price(el.text)

    # 4. Mercado Livre
    if "mercadolivre.com.br" in url:
        el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__fraction, .price-tag-fraction")
        if el:
            cents_el = soup.select_one(".ui-pdp-price__second-line .andes-money-amount__cents")
            cents = cents_el.text if cents_el else "00"
            return clean_price(f"{el.text},{cents}")

    # 5. Amazon Brasil
    if "amazon.com.br" in url:
        whole = soup.select_one(".a-price-whole")
        fraction = soup.select_one(".a-price-fraction")
        if whole:
            val_str = whole.text.replace(".", "").replace(",", "")
            dec = fraction.text if fraction else "00"
            return clean_price(f"{val_str}.{dec}")

    return None


def fetch_price(url: str, timeout: int = 15) -> float | None:
    """
    Faz a requisição HTTP e extrai o preço atual do produto.
    """
    try:
        res = requests.get(url, headers=HEADERS, timeout=timeout)
        if res.status_code != 200:
            print(f"  [Aviso] Falha HTTP {res.status_code} para {url}")
            return None

        soup = BeautifulSoup(res.text, "lxml")

        # Estratégia 1: JSON-LD (Mais estável e oficial)
        price = extract_price_from_ld_json(soup)
        if price:
            return price

        # Estratégia 2: Meta Tags
        price = extract_price_from_meta_tags(soup)
        if price:
            return price

        # Estratégia 3: Seletores específicos por loja
        price = extract_price_specific(soup, url)
        if price:
            return price

        return None
    except Exception as e:
        print(f"  [Erro] Falha ao consultar {url}: {e}")
        return None


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
    print("=" * 60)
    print("Iniciando Monitor de Preços de Hardware")
    print("=" * 60)

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
        print(f"   Alvo: R$ {target_price:,.2f} | URL: {url}")

        current_price = fetch_price(url, timeout=timeout)

        if current_price is None:
            print(f"   ⚠️ Não foi possível obter o preço no momento.")
            continue

        print(f"   💲 Preço Encontrado: R$ {current_price:,.2f}")

        # Verifica se o preço atingiu a meta
        if current_price <= target_price:
            print(f"   🎯 OPORTUNIDADE! Preço atingiu ou superou o alvo!")
            
            # Verifica se já notificamos esse preço específico para evitar spam
            last_notified_price = history.get(url, {}).get("last_notified_price")
            if last_notified_price != current_price:
                send_notification(name, current_price, target_price, url)
                history[url] = {
                    "name": name,
                    "last_notified_price": current_price,
                    "target_price": target_price,
                    "timestamp": time.time()
                }
            else:
                print(f"   ℹ️ Alerta já disparado anteriormente para este valor (R$ {current_price:,.2f}).")
        else:
            diff = current_price - target_price
            print(f"   ⏳ Acima do alvo por R$ {diff:,.2f}.")

        # Pequeno delay para respeitar os servidores
        time.sleep(2)

    save_history(history)
    print("\n" + "=" * 60)
    print("Varredura finalizada com sucesso.")
    print("=" * 60)


if __name__ == "__main__":
    main()

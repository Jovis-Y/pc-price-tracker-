# 🚀 Radar de Preços de Hardware (Discord Edition)

Monitor automatizado de preços de peças de PC rodando gratuitamente via **GitHub Actions** com alertas ricos direto no **Discord**.

---

### 🏪 Lojas e Comparadores Suportados

1. **Hardware Barato** *(⭐ Comparador que reúne KaBuM, Terabyte, Pichau, Amazon e ML no mesmo link!)*
2. **KaBuM!**
3. **TerabyteShop**
4. **Pichau**
5. **Mercado Livre**
6. **Amazon Brasil**
7. **OLX Brasil** *(Ótimo para oportunidades em monitores e usados)*
8. **AliExpress** *(Excelente para processadores e memórias RAM)*
9. **Shopee Brasil**

---

### 💡 Dica de Ouro: Usar o Hardware Barato
Ao invés de colocar o link de uma loja específica, você pode colocar o link do produto no **Hardware Barato**. Ele monitora **todas as lojas do Brasil ao mesmo tempo** e o robô vai sempre capturar o **menor valor de todas elas** sem risco de bloqueio de Cloudflare!

Exemplo de link no `config.json`:
* `https://www.hardwarebarato.com/produtos/processadores/ryzen-7-5700x3d`
* `https://www.hardwarebarato.com/produtos/fontes/xpg-core-reactor-ii-ve-850w`

---

### ⚙️ Como Configurar o Webhook no GitHub

1. No seu servidor do Discord:
   * **Editar Canal** > **Integrações** > **Webhooks** > **Novo Webhook** > **Copiar URL do Webhook**.
2. No seu repositório no GitHub:
   * Acesse: **Settings** > **Secrets and variables** > **Actions**.
   * Em **Repository secrets**, clique em **New repository secret**.
   * **Name:** `DISCORD_WEBHOOK_URL`
   * **Secret:** Cole a URL do Webhook.
3. Permissão para salvar histórico:
   * Em **Settings** > **Actions** > **General** > **Workflow permissions**, marque **Read and write permissions** e salve.

# 🚀 Radar de Preços de Hardware (PC Price Tracker)

Monitor automatizado de preços de peças de PC rodando gratuitamente via **GitHub Actions** com alertas diretos no **Discord** ou **Telegram**.

---

## 🎯 Produtos Monitorados Atualmente

* **Processador:** AMD Ryzen 7 5700X3D (Meta: ≤ R$ 1.250,00)
* **Placa de Vídeo:** AMD Radeon RX 7900 XT 20GB / RX 9070 XT (Meta: ≤ R$ 4.600,00)
* **Monitor Gamer:** 4K 144Hz IPS (ex: Gigabyte M28U) (Meta: ≤ R$ 2.800,00)
* **Cooler:** Thermalright Peerless Assassin 120 SE (Meta: ≤ R$ 250,00)
* **Memória RAM:** Kingston Fury Beast 8GB 3200MHz DDR4 (Meta: ≤ R$ 135,00)

---

## ⚙️ Como Configurar e Hospedar no seu GitHub

### 1. Criar o Repositório no GitHub
1. Acesse o seu [GitHub](https://github.com/) e crie um novo repositório (pode ser **Público** ou **Privado**).
2. Na pasta do projeto no seu computador, inicialize o Git e envie os arquivos:
   ```bash
   git init
   git add .
   git commit -m "feat: setup inicial do monitor de hardware"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   git push -u origin main
   ```

---

### 2. Configurar os Alertas (GitHub Secrets)

Para que o GitHub Actions envie mensagens para você sem expor suas credenciais publicamente:

1. No seu repositório no GitHub, clique em **Settings** > **Secrets and variables** > **Actions**.
2. Clique no botão **New repository secret** e adicione:

#### Opção A: Alerta no Discord (Mais fácil e rápido)
* **Nome:** `DISCORD_WEBHOOK_URL`
* **Valor:** Cole a URL do Webhook do seu servidor (No Discord: *Configurações do Canal > Integrações > Criar Webhook*).

#### Opção B: Alerta no Telegram
* **Nome:** `TELEGRAM_BOT_TOKEN` (Obtido com o [@BotFather](https://t.me/BotFather))
* **Nome:** `TELEGRAM_CHAT_ID` (Obtido com o [@userinfobot](https://t.me/userinfobot))

*(Você pode usar ambos ou apenas um deles!)*

---

### 3. Habilitar Permissão de Escrita no GitHub Actions
Para que o GitHub possa salvar o histórico de preços e não enviar alertas repetidos:
1. Vá em **Settings** > **Actions** > **General**.
2. Role até **Workflow permissions** e selecione:
   * **Read and write permissions**
3. Clique em **Save**.

---

### 4. Como Adicionar ou Modificar Produtos
Abra o arquivo `config.json` e adicione ou edite os itens:

```json
{
  "name": "Nome do Produto",
  "category": "GPU",
  "target_price": 4500.00,
  "url": "https://link-da-loja.com/produto",
  "active": true
}
```

O script já possui suporte a extração automática de preços via dados estruturados (Schema.org / JSON-LD) e seletores para lojas como **Kabum**, **Terabyte**, **Pichau**, **Mercado Livre** e **Amazon**.

---

### 5. Como Testar Manualmente no GitHub
1. No seu repositório, clique na aba **Actions**.
2. No menu lateral esquerdo, clique em **Monitor de Preços de Hardware**.
3. Clique no botão **Run workflow** à direita.

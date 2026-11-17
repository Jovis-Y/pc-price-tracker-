# 🚀 Radar de Preços de Hardware (Discord Edition)

Monitor automatizado de preços de peças de PC rodando gratuitamente via **GitHub Actions** com alertas ricos direto no **Discord**.

---

### 🏪 Lojas Suportadas

1. **KaBuM!**
2. **TerabyteShop**
3. **Pichau**
4. **Mercado Livre**
5. **Amazon Brasil**
6. **OLX Brasil** *(Ótimo para oportunidades em monitores e usados)*
7. **AliExpress** *(Excelente para processadores Ryzen 5700X3D e memórias RAM)*
8. **Shopee Brasil**

---

### 🔔 Como Funciona o Alerta no Discord

Quando o robô encontra um preço **menor ou igual ao seu preço-alvo**, ele envia uma mensagem personalizada no seu canal do Discord com:
* Nome do produto e Loja de origem
* Preço Atual vs Preço-Alvo
* Economia (R$ e %)
* Link direto para a loja
* Cor temática no Embed de acordo com a loja (ex: Laranja KaBuM, Roxo OLX, Vermelho AliExpress, etc.)

---

### ⚙️ Como Configurar no seu GitHub

#### 1. Criar o Repositório no GitHub
1. Acesse [github.com/new](https://github.com/) e crie um repositório (pode ser **Privado** ou **Público**).
2. Na pasta do projeto, envie os arquivos:
   ```bash
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   git push -u origin main
   ```

#### 2. Configurar o Webhook do Discord (GitHub Secret)
1. No seu servidor do Discord, vá nas configurações do canal que receberá os alertas:
   * **Editar Canal** > **Integrações** > **Webhooks** > **Novo Webhook** > **Copiar URL do Webhook**.
2. No seu repositório no GitHub:
   * Vá em **Settings** > **Secrets and variables** > **Actions**.
   * Clique em **New repository secret**.
   * **Name:** `DISCORD_WEBHOOK_URL`
   * **Secret:** Cole a URL do Webhook do Discord.

#### 3. Dar Permissão para Salvar o Histórico
1. No repositório, vá em **Settings** > **Actions** > **General**.
2. Em **Workflow permissions**, selecione **Read and write permissions**.
3. Clique em **Save**.

---

### 📝 Como Adicionar ou Alterar Produtos

Abra o arquivo `config.json` e edite ou insira novos itens:

```json
{
  "name": "AMD Ryzen 7 5700X3D",
  "category": "CPU",
  "target_price": 1250.00,
  "url": "https://pt.aliexpress.com/item/1005006504285741.html",
  "active": true
}
```

* Defina `"active": false` para pausar o monitoramento de um produto sem precisar apagá-lo.

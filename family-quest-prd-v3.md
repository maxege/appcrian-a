# Family Quest — PRD Consolidado v3.0
> Documentação Técnico-Funcional definitiva. Resolve todas as ambiguidades das versões anteriores.

---

## 1. Escopo e Propósito

Plataforma SaaS mobile-first para gestão de tarefas e educação financeira/comportamental de menores, utilizando mecânicas de RPG (XP e Níveis) e economia interna (Loja de Recompensas).

**Princípios de Design:**
- Segurança by-design: dados de menores protegidos por LGPD
- Auditabilidade total: toda transação financeira e de XP é rastreável
- Mobile-first: UX otimizada para telas pequenas, com suporte a PWA

---

## 2. Arquitetura de Usuários

| Papel | Descrição | Acesso |
|---|---|---|
| **Master Admin** | Operador da plataforma. Gerencia planos, suporte e métricas globais. | Painel administrativo web separado |
| **Responsável** | Admin da família. Cria tarefas, gerencia loja, aprova entregas. | App mobile (e-mail + senha) |
| **Co-Responsável** | Membro adicional (Premium). Permissões configuráveis pelo Responsável principal. | App mobile (e-mail + senha) |
| **Filho** | Usuário final. Visualiza tarefas, envia fotos e resgata prêmios. | App mobile (PIN 4 dígitos ou QR Code) |

---

## 3. Matriz de Segurança e Conformidade (LGPD)

### 3.1 Autenticação por Perfil

| Perfil | Método | Armazenamento | Sessão |
|---|---|---|---|
| Master Admin | E-mail + Senha | BCrypt (custo 12) | JWT — 24h |
| Responsável | E-mail + Senha | BCrypt (custo 12) | JWT — 7 dias (Refresh Token) |
| Co-Responsável | E-mail + Senha | BCrypt (custo 12) | JWT — 7 dias (Refresh Token) |
| Filho | PIN 4 dígitos | BCrypt (custo 10) | Sessão local — 12h |

**Regras adicionais:**
- Bloqueio de conta após 5 tentativas de PIN incorretas (cooldown de 15 minutos)
- Refresh Token armazenado em HttpOnly cookie, nunca em localStorage
- Troca de senha obriga invalidação de todos os tokens ativos do usuário

### 3.2 Fluxo de QR Code (Primeiro Acesso do Filho)

1. Responsável gera o QR Code no painel → sistema cria um `token_qrcode` UUID v4 de **uso único** com validade de **30 minutos**
2. O QR Code codifica uma URL deep link: `familyquest://auth/qr?token={uuid}`
3. Filho lê o QR Code com o celular → app valida o token via API
4. Se válido: app solicita que o filho **cadastre seu próprio PIN de 4 dígitos** (confirmado duas vezes)
5. Token é marcado como `usado=true` e invalidado imediatamente
6. Sessão local do filho é iniciada por 12h

### 3.3 Dados de Menores (LGPD)

- **Consentimento explícito** do Responsável no cadastro, gravado com IP e timestamp na tabela `consentimentos`
- Imagens de comprovação de tarefas armazenadas com nome UUID (não identificável) em bucket privado isolado por família
- **Política de retenção:** imagens excluídas automaticamente 90 dias após a tarefa ser concluída ou cancelada
- Direito ao esquecimento: `DELETE /api/familias/{id}` realiza exclusão em cascata de todos os dados e imagens do bucket
- Nenhum dado de menor é exposto em Analytics externo

---

## 4. Modelo de Dados Final (MySQL 8.0)

### 4.1 Planos e Master Admin

```sql
-- Tabela de planos (fonte de verdade para limites do sistema)
CREATE TABLE planos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(50) NOT NULL,           -- 'Free', 'Premium'
    max_filhos  INT NOT NULL,                   -- 1 (Free) | -1 = ilimitado (Premium)
    max_tarefas_ativas INT NOT NULL,            -- 5 (Free) | -1 = ilimitado (Premium)
    permite_foto        TINYINT(1) DEFAULT 0,
    permite_co_resp     TINYINT(1) DEFAULT 0,
    permite_relatorios  TINYINT(1) DEFAULT 0,
    preco_mensal        DECIMAL(8,2) NOT NULL,
    preco_anual         DECIMAL(8,2) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Master Admin (painel operacional separado)
CREATE TABLE admins (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) UNIQUE NOT NULL,
    senha_hash  VARCHAR(255) NOT NULL,
    ativo       TINYINT(1) DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Núcleo de Usuários

```sql
-- Famílias / Responsáveis principais
CREATE TABLE familias (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    nome_familia            VARCHAR(100) NOT NULL,
    email_responsavel       VARCHAR(150) UNIQUE NOT NULL,
    senha_hash              VARCHAR(255) NOT NULL,
    id_plano                INT NOT NULL,
    modo_progressao         TINYINT(1) DEFAULT 1,  -- 1: Autonomia | 0: Manual
    percentual_multa_padrao DECIMAL(5,2) DEFAULT 20.00, -- % aplicado no atraso
    gateway_customer_id     VARCHAR(100),           -- ID no Mercado Pago / Stripe
    trial_expira_em         DATETIME,               -- NULL = trial não ativo
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_plano) REFERENCES planos(id)
);

-- Membros adicionais da família (Co-Responsáveis) — Premium
CREATE TABLE familia_membros (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    id_familia      INT NOT NULL,
    nome            VARCHAR(100) NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    senha_hash      VARCHAR(255) NOT NULL,
    pode_criar_tarefas  TINYINT(1) DEFAULT 1,
    pode_aprovar        TINYINT(1) DEFAULT 1,
    pode_gerenciar_loja TINYINT(1) DEFAULT 0,
    pode_ver_relatorios TINYINT(1) DEFAULT 1,
    ativo           TINYINT(1) DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_familia) REFERENCES familias(id) ON DELETE CASCADE
);

-- Consentimento LGPD (imutável — nunca atualizar, apenas inserir)
CREATE TABLE consentimentos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_familia  INT NOT NULL,
    versao_termo VARCHAR(20) NOT NULL,           -- ex: '2.0'
    ip_origem   VARCHAR(45) NOT NULL,            -- suporta IPv6
    aceito_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_familia) REFERENCES familias(id)
);

-- Filhos
CREATE TABLE filhos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    id_familia      INT NOT NULL,
    nome            VARCHAR(100) NOT NULL,
    pin_hash        VARCHAR(255) NOT NULL,
    avatar_url      VARCHAR(255),
    data_nascimento DATE,
    pontos_saldo    INT DEFAULT 0,
    xp_total        INT DEFAULT 0,
    nivel_atual     INT DEFAULT 1,
    ativo           TINYINT(1) DEFAULT 1,        -- desativado no downgrade
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_familia) REFERENCES familias(id) ON DELETE CASCADE
);

-- Tokens QR Code para primeiro acesso do filho
CREATE TABLE qrcodes_acesso (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_filho    INT NOT NULL,
    token       CHAR(36) NOT NULL UNIQUE,        -- UUID v4
    expira_em   DATETIME NOT NULL,
    usado       TINYINT(1) DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_filho) REFERENCES filhos(id) ON DELETE CASCADE
);
```

### 4.3 Mecânica de Tarefas

```sql
-- Tarefas (Quests)
CREATE TABLE tarefas (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    id_filho            INT NOT NULL,
    id_criador          INT NOT NULL,            -- ID do Responsável ou Co-Responsável
    tipo_criador        ENUM('Responsavel', 'CoResponsavel') NOT NULL,
    titulo              VARCHAR(150) NOT NULL,
    descricao           TEXT,
    pontos_recompensa   INT NOT NULL,
    xp_recompensa       INT NOT NULL,
    data_limite         DATETIME NOT NULL,
    data_envio_foto     DATETIME,
    data_conclusao      DATETIME,
    foto_obrigatoria    TINYINT(1) DEFAULT 1,    -- 0 no plano Free
    foto_url            VARCHAR(255),
    status              ENUM(
                            'Pendente',
                            'Em_Analise',
                            'Concluida',
                            'Rejeitada',
                            'Expirada',
                            'Cancelada'
                        ) DEFAULT 'Pendente',
    motivo_rejeicao     VARCHAR(500),
    percentual_multa_aplicado DECIMAL(5,2),      -- % usado se for multada
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_filho) REFERENCES filhos(id)
);
```

### 4.4 Economia e Auditoria

```sql
-- Loja de Produtos
CREATE TABLE loja_produtos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    id_familia      INT NOT NULL,
    nome            VARCHAR(100) NOT NULL,
    descricao       TEXT,
    preco_pontos    INT NOT NULL,
    nivel_minimo_xp INT DEFAULT 1,
    tipo            ENUM('Fisico', 'Tempo', 'Experiencia') NOT NULL,
    estoque         INT DEFAULT -1,              -- -1 = ilimitado
    exibir_esgotado TINYINT(1) DEFAULT 1,        -- 1: exibe "Esgotado" | 0: oculta
    ativo           TINYINT(1) DEFAULT 1,
    imagem_url      VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_familia) REFERENCES familias(id) ON DELETE CASCADE
);

-- Resgates (compras na loja)
CREATE TABLE resgates (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    id_filho            INT NOT NULL,
    id_produto          INT NOT NULL,
    preco_pontos_pago   INT NOT NULL,            -- snapshot do preço no momento da compra
    status              ENUM('Pendente', 'Entregue', 'Cancelado') DEFAULT 'Pendente',
    id_confirmador      INT,                     -- Responsável ou Co-Resp que confirmou
    data_resgate        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_entrega        DATETIME,
    FOREIGN KEY (id_filho) REFERENCES filhos(id),
    FOREIGN KEY (id_produto) REFERENCES loja_produtos(id)
);

-- Extrato de Pontos (auditoria imutável — NUNCA atualizar registros)
CREATE TABLE transacoes_pontos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_filho    INT NOT NULL,
    valor       INT NOT NULL,                    -- positivo = crédito | negativo = débito
    tipo        ENUM('Tarefa', 'Compra', 'Multa', 'Ajuste_Manual', 'Estorno') NOT NULL,
    ref_tabela  ENUM('tarefas', 'resgates', 'manual') NOT NULL, -- resolve polimorfismo
    ref_id      INT,                             -- FK para a tabela correspondente
    descricao   VARCHAR(255) NOT NULL,           -- texto legível para exibição no extrato
    criado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_filho) REFERENCES filhos(id)
);

-- Extrato de XP (espelha a lógica de transacoes_pontos para XP)
CREATE TABLE transacoes_xp (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_filho    INT NOT NULL,
    valor       INT NOT NULL,                    -- positivo = ganho | negativo = perda
    tipo        ENUM('Tarefa', 'Multa', 'Ajuste_Manual') NOT NULL,
    ref_tabela  ENUM('tarefas', 'manual') NOT NULL,
    ref_id      INT,
    descricao   VARCHAR(255) NOT NULL,
    nivel_antes INT NOT NULL,
    nivel_depois INT NOT NULL,
    criado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_filho) REFERENCES filhos(id)
);

-- Notificações (persistência de push)
CREATE TABLE notificacoes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_destino  INT NOT NULL,
    tipo_destino ENUM('Responsavel', 'CoResponsavel', 'Filho') NOT NULL,
    titulo      VARCHAR(150) NOT NULL,
    corpo       VARCHAR(500) NOT NULL,
    tipo_evento ENUM(
                    'Tarefa_Enviada',
                    'Tarefa_Aprovada',
                    'Tarefa_Rejeitada',
                    'Tarefa_Expirada',
                    'Resgate_Solicitado',
                    'Resgate_Entregue',
                    'Nivel_Subiu',
                    'Item_Destravado'
                ) NOT NULL,
    ref_id      INT,
    lida        TINYINT(1) DEFAULT 0,
    enviada_push TINYINT(1) DEFAULT 0,
    criada_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lida_em     DATETIME
);
```

---

## 5. Regras de Negócio

### RF01 — Ciclo de Vida de uma Tarefa

```
[Pendente] → filho envia foto → [Em_Analise]
                                       ↓ pai aprova  → [Concluida] → créditos liberados
                                       ↓ pai rejeita → [Rejeitada] → filho pode reenviar foto
                                                                           ↓ → [Em_Analise]
[Pendente ou Rejeitada] → deadline expira → notificação ao pai
    ↓ Prorrogar → data_limite atualizada → [Pendente]
    ↓ Multar    → pontos e XP reduzidos → [Concluida] (com multa gravada)
    ↓ Cancelar  → -20 XP, sem pontos   → [Cancelada]
```

**Regra crítica de prazo:** Se o status for `Em_Analise` no momento em que o deadline vence, a tarefa é **imune à expiração automática**. O responsável pode apenas Aprovar ou Rejeitar.

### RF02 — Fluxo de Aprovação/Rejeição

1. Filho envia foto → `status = Em_Analise`, `data_envio_foto = NOW()`
2. Responsável aprova:
   - `status = Concluida`, `data_conclusao = NOW()`
   - Insere em `transacoes_pontos` (tipo `Tarefa`, valor positivo)
   - Insere em `transacoes_xp` (tipo `Tarefa`, valor positivo)
   - Atualiza `filhos.pontos_saldo` e `filhos.xp_total`
   - Dispara verificação de nível (ver RF05)
3. Responsável rejeita:
   - `status = Rejeitada`, `motivo_rejeicao` gravado
   - Push enviado ao filho: "Tarefa rejeitada. Motivo: [motivo]"
   - Filho pode reenviar (retorna ao passo 1)
   - Nenhum saldo é alterado

### RF03 — Atraso e Multa

- `percentual_multa_aplicado` é herdado de `familias.percentual_multa_padrao` no momento da penalização, mas pode ser sobrescrito por tarefa
- Lógica de **Multar**:
  ```
  pontos_com_desconto = tarefas.pontos_recompensa × (1 - percentual / 100)
  Insere transacoes_pontos: valor = pontos_com_desconto (positivo, tipo 'Tarefa')
  Insere transacoes_xp:     valor = -5 (tipo 'Multa')
  status = Concluida
  ```
- Lógica de **Cancelar**:
  ```
  Insere transacoes_xp: valor = -20 (tipo 'Multa')
  status = Cancelada
  -- Nenhum ponto é creditado
  ```

### RF04 — Loja e Resgates

**Vitrine:**
- Produto aparece se `ativo = 1` E `filho.nivel_atual >= produto.nivel_minimo_xp`
- Se `estoque = 0` E `exibir_esgotado = 1`: produto aparece com tag "Esgotado" e botão desabilitado
- Se `estoque = 0` E `exibir_esgotado = 0`: produto é ocultado da vitrine

**Fluxo de compra:**
1. Validação: `filho.pontos_saldo >= produto.preco_pontos` E `estoque != 0`
2. Criar registro em `resgates` com `preco_pontos_pago = produto.preco_pontos` (snapshot)
3. Decrementar `filhos.pontos_saldo`
4. Se `produto.estoque > 0`: decrementar `loja_produtos.estoque`
5. Inserir em `transacoes_pontos` (tipo `Compra`, valor negativo)
6. Se `produto.tipo = Fisico`: notificar responsável com status `Resgate_Solicitado`
7. Responsável confirma entrega → `resgates.status = Entregue`, `data_entrega = NOW()`

### RF05 — Progressão de Níveis

**Fórmula de XP (cumulativo total para atingir o nível N):**

$$XP_{necessário}(N) = \frac{N \times (N - 1)}{2} \times 200$$

| Nível | XP Total Necessário |
|---|---|
| 1 → 2 | 200 XP |
| 2 → 3 | 600 XP |
| 3 → 4 | 1.200 XP |
| 4 → 5 | 2.000 XP |
| 50 (máx.) | 245.000 XP |

**Verificação de nível** (executada após qualquer crédito de XP):
```python
def verificar_nivel(filho):
    for nivel in range(filho.nivel_atual + 1, 51):
        xp_necessario = nivel * (nivel - 1) / 2 * 200
        if filho.xp_total >= xp_necessario:
            filho.nivel_atual = nivel
            disparar_evento_nivel(filho, nivel)
        else:
            break

def disparar_evento_nivel(filho, novo_nivel):
    if filho.familia.modo_progressao == AUTONOMIA:
        # Habilita itens da loja cujo nivel_minimo_xp == novo_nivel
        # (loja_produtos.ativo já é True; o filtro da vitrine cuida do resto)
        notificar(filho, tipo='Nivel_Subiu')
        notificar(filho, tipo='Item_Destravado')  # se houver itens destravados
    else:  # Modo Manual
        notificar(responsavel, tipo='Nivel_Subiu', dados={'filho': filho, 'nivel': novo_nivel})
        # O responsável decide manualmente quais itens liberar via painel
```

**Modo Manual:** O nível do filho ainda sobe normalmente no banco de dados. A diferença é que itens na vitrine continuam ocultos para o filho até que o responsável habilite explicitamente via painel (`loja_produtos.ativo = 1`).

### RF06 — Controle de Limites do Plano

Verificado na camada de serviço (não via trigger de banco):

| Ação | Plano Free | Plano Premium |
|---|---|---|
| Criar filho | Máx. 1 | Ilimitado |
| Tarefas ativas simultâneas | Máx. 5 | Ilimitado |
| Foto de comprovação | ❌ Bloqueada | ✅ Habilitada |
| Co-Responsável | ❌ Bloqueado | ✅ Habilitado |
| Relatórios | ❌ Bloqueado | ✅ Habilitado |

**Política de downgrade (Premium → Free):**
- Filhos excedentes são marcados como `ativo = 0` (dados preservados por 30 dias)
- Responsável escolhe qual(is) filho(s) manter ativo(s) antes do downgrade finalizar
- Após 30 dias sem reativação: dados excedentes são excluídos permanentemente

---

## 6. Stack Tecnológica

### Backend
- **Runtime:** Python 3.12 + FastAPI (async)
- **ORM:** SQLAlchemy 2.0 com Alembic para migrations
- **Autenticação:** python-jose (JWT) + passlib[bcrypt]
- **Filas/Push:** Celery + Redis → dispara FCM (Firebase Cloud Messaging) para Android/iOS
- **Storage:** Cloudflare R2 (compatível com S3) — bucket privado por família, URLs assinadas com expiração de 15 minutos

### Banco de Dados
- **Principal:** MySQL 8.0
- **Cache:** Redis 7 (sessões, rate-limiting, filas Celery)

### Frontend
- **Framework:** React Native (Expo) — iOS e Android com base de código única
- **Estilização:** NativeWind (Tailwind para React Native)
- **Estado:** Zustand + React Query

### Pagamentos
- **Gateway:** Mercado Pago (Brasil-first) com fallback para Stripe
- **Modelo:** Assinatura recorrente mensal/anual
- **Webhook:** endpoint `/api/webhooks/pagamentos` valida assinatura HMAC antes de processar

### Infraestrutura
- **Containers:** Docker + Docker Compose (desenvolvimento)
- **Produção:** Railway.app ou Render.com (deploy simplificado para MVP)
- **CI/CD:** GitHub Actions — lint, testes e deploy automático na branch `main`

---

## 7. Arquitetura de API (REST)

### Autenticação
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/auth/login` | Login Responsável/Co-Resp (retorna JWT) |
| POST | `/api/auth/refresh` | Renova JWT via Refresh Token |
| POST | `/api/auth/filho/pin` | Login filho por PIN |
| POST | `/api/auth/filho/qrcode` | Valida token QR Code e inicia cadastro de PIN |
| POST | `/api/auth/logout` | Invalida Refresh Token |

### Família e Filhos
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/familias` | Cadastro (cria família + aceita termo LGPD) |
| GET | `/api/familias/me` | Dados da família autenticada |
| DELETE | `/api/familias/me` | Exclusão total (direito ao esquecimento) |
| POST | `/api/familias/me/filhos` | Cria filho |
| GET | `/api/familias/me/filhos` | Lista filhos |
| GET | `/api/filhos/{id}/extrato` | Extrato pontos + XP do filho |
| POST | `/api/filhos/{id}/qrcode` | Gera QR Code de acesso |

### Tarefas
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/tarefas` | Cria tarefa |
| GET | `/api/tarefas?filho_id=X` | Lista tarefas de um filho |
| PATCH | `/api/tarefas/{id}/enviar-foto` | Filho envia foto |
| PATCH | `/api/tarefas/{id}/aprovar` | Responsável aprova |
| PATCH | `/api/tarefas/{id}/rejeitar` | Responsável rejeita (requer motivo) |
| PATCH | `/api/tarefas/{id}/prorrogar` | Responsável prorroga prazo |
| PATCH | `/api/tarefas/{id}/multar` | Responsável aplica multa |
| PATCH | `/api/tarefas/{id}/cancelar` | Responsável cancela tarefa |

### Loja e Resgates
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/loja/produtos` | Cria produto |
| GET | `/api/loja/vitrine?filho_id=X` | Vitrine filtrada por nível do filho |
| PATCH | `/api/loja/produtos/{id}` | Edita produto |
| DELETE | `/api/loja/produtos/{id}` | Remove produto |
| POST | `/api/resgates` | Filho compra produto |
| PATCH | `/api/resgates/{id}/entregar` | Responsável confirma entrega |

---

## 8. Fluxo de Valor (UX End-to-End)

```
1. Responsável cadastra família → aceita termo LGPD → trial de 14 dias inicia

2. Responsável cria perfil do filho → gera QR Code

3. Filho lê QR Code → define seu PIN de 4 dígitos → acessa o app

4. Responsável cria tarefa "Lavar Louça"
   └── 100 pts | 10 XP | prazo: hoje 20h | foto obrigatória: sim

5. Filho visualiza a tarefa no app → completa → tira foto → envia

6. Responsável recebe push "Nova tarefa em análise"
   └── Aprova → filho recebe: +100 pts, +10 XP
   └── Rejeita → filho recebe push com motivo → pode reenviar foto

7. Filho acumula 200 XP total → sobe para Nível 2
   └── Modo Autonomia: "Sorvete" (bloqueado até Nível 2) aparece na vitrine automaticamente
   └── Modo Manual: pai recebe push e decide liberar o "Sorvete" manualmente

8. Filho resgata "Sorvete" (item físico, 80 pts)
   └── Saldo verificado → compra processada → pai recebe push "Pendente de entrega"
   └── Pai entrega e confirma no app → status: Entregue
```

---

## 9. Roadmap de Monetização (SaaS)

| Feature | Free | Premium |
|---|---|---|
| Filhos | 1 | Ilimitados |
| Tarefas ativas | 5 | Ilimitadas |
| Foto de comprovação | ❌ | ✅ |
| Co-Responsável | ❌ | ✅ |
| Relatórios de performance | ❌ | ✅ |
| Trial | 14 dias Premium | — |
| Preço | R$ 0 | R$ 19,90/mês ou R$ 179/ano |

**Gateway:** Mercado Pago (recorrência via assinatura)

**Webhook de pagamento** (`/api/webhooks/pagamentos`):
- Pagamento aprovado → `familias.id_plano` atualizado para Premium
- Pagamento recusado/cancelado → e-mail de aviso + grace period de 3 dias
- Downgrade após grace period → política de filhos excedentes aplicada (ver RF06)

---

## 10. Master Admin — Painel Operacional

Painel web separado do app mobile (Next.js), acessível apenas por admins.

**Funcionalidades:**
- Listar e buscar famílias cadastradas
- Visualizar métricas globais (DAU, MRR, Churn)
- Alterar manualmente o plano de uma família (suporte)
- Desativar contas abusivas
- Gerenciar versões dos Termos de Uso (cria novo registro em `consentimentos` exigindo re-aceite)
- Exportar relatório de consentimentos LGPD (para auditoria)

---

## 11. Diagrama de Estados da Tarefa

```
                    ┌─────────────┐
                    │   Pendente  │◄──── Prorrogação pelo pai
                    └──────┬──────┘
                           │ Filho envia foto
                           ▼
                    ┌─────────────┐
                    │ Em_Analise  │ ← IMUNE à expiração automática
                    └──────┬──────┘
               ┌───────────┴───────────┐
          Aprovado                  Rejeitado
               │                       │
               ▼                       ▼
        ┌──────────┐           ┌─────────────┐
        │ Concluída│           │  Rejeitada  │──► Filho pode reenviar
        └──────────┘           └─────────────┘
                                       
    [Pendente ou Rejeitada] + deadline vencido
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
Prorrogar   Multar    Cancelar
    │          │          │
    ▼          ▼          ▼
 Pendente  Concluída  Cancelada
 (nova       (com        (-20 XP)
  data)      multa)
```

---

*Documento gerado em: 2026-04-06 | Versão: 3.0*

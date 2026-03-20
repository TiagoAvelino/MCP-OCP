# 🚀 MCP OpenShift — Servidor MCP para Red Hat OpenShift

> **Integre assistentes de IA com seu cluster OpenShift** através do Model Context Protocol (MCP). Consulte status, liste recursos, inicie upgrades e gerencie deployments usando linguagem natural.

---

## 🎯 O que é este projeto?

Este projeto implementa um **servidor MCP** que expõe operações do OpenShift/Kubernetes como ferramentas que modelos de linguagem (LLMs) podem invocar. Em vez de digitar comandos `oc` ou `kubectl`, você pode pedir ao assistente de IA para:

- Verificar o status do cluster
- Listar nodes e pods
- Iniciar upgrades do OpenShift
- Consultar logs de pods
- Definir variáveis de ambiente em deployments

O fluxo é simples: **Cliente (IA) → Servidor MCP → API do OpenShift**.

---

## 🏗️ Arquitetura

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Cliente (IA)   │────▶│  Servidor MCP    │────▶│  OpenShift API  │
│  Claude/GPT/    │      │  (server-gpt.py) │      │  (Kubernetes)   │
│  Llama, etc.    │◀────│                  │◀────│                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
```

1. **Cliente** — Envia solicitações em linguagem natural (ex.: Claude Desktop ou `client-gpt.py`)
2. **Servidor MCP** — Recebe a solicitação, executa a função Python correspondente e retorna o resultado
3. **Modelo** — Usa o resultado para formular uma resposta ao usuário

---

## 🔧 Ferramentas disponíveis

| Ferramenta                  | Descrição                                                           |
| --------------------------- | ------------------------------------------------------------------- |
| `verificar_status_sistema`  | Verifica status de cluster, API ou nodes (`cluster`, `api`, `nos`)  |
| `listar_nodes`              | Lista nodes do cluster com nome, status Ready e versão do kubelet   |
| `listar_pods`               | Lista pods em um namespace com fase, restarts e indicação de erros  |
| `iniciar_upgrade_openshift` | Inicia upgrade do cluster para uma versão específica (ex.: 4.14.25) |
| `ver_logs_pod`              | Obtém logs de um pod (com suporte a tail e timestamps)              |
| `definir_env_deployment`    | Define variáveis de ambiente em um Deployment                       |

---

## 📦 Pré-requisitos

- **Python** ≥ 3.14
- **uv** — gerenciador de pacotes Python (recomendado)
- Acesso a um cluster **OpenShift** ou **Kubernetes** (via `~/.kube/config` ou ServiceAccount in-cluster)

---

## ⚡ Instalação

### 1. Instale o uv (se ainda não tiver)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone o repositório e entre no diretório

```bash
cd MCP-OCP
```

### 3. Crie o ambiente virtual e instale as dependências

```bash
uv sync
source .venv/bin/activate   # No Windows: .venv\Scripts\activate
```

### 4. Configure o acesso ao cluster

Certifique-se de que `KUBECONFIG` está configurado ou que `~/.kube/config` aponta para seu cluster OpenShift.

---

## 🚀 Como usar

Para usar este servidor no **Cursor**, adicione-o ao arquivo de configuração MCP:

1. Abra o arquivo `~/.cursor/mcp.json` (ou crie-o se não existir)
2. Inclua a entrada do servidor na seção `mcpServers`:

```json
{
  "mcpServers": {
    "server-gpt": {
      "command": "/caminho/para/MCP-OCP/.venv/bin/python",
      "args": ["/caminho/para/MCP-OCP/server-gpt.py"],
      "env": {
        "KUBECONFIG": "~/.kube/config"
      }
    }
  }
}
```

Substitua `/caminho/para/MCP-OCP` pelo caminho absoluto do projeto no seu sistema. Após salvar, reinicie o Cursor para que o servidor seja carregado.

---

## 🔍 Testando com o MCP Inspector

Antes de conectar a uma IA real, use o **MCP Inspector** para testar se o servidor está funcionando e se as ferramentas estão visíveis.

No terminal:

```bash
mcp dev server-gpt.py
```

Isso abrirá uma interface no navegador onde você pode:

- Ver todas as ferramentas disponíveis
- Inserir argumentos e ver a resposta JSON
- Validar o comportamento antes de integrar com IA

---

## 📚 Documentação adicional

- `CLIENT_USAGE.md` — Guia detalhado de uso do cliente
- `CLIENT_WALKTHROUGH.md` — Passo a passo para configurar e testar o fluxo completo
- **[`deploy/openshift/README.md`](deploy/openshift/README.md)** — Implantação no OpenShift (imagens, Services, Route, RBAC, nginx + SSE)
- **[`deploy/ansible/README.md`](deploy/ansible/README.md)** — Ansible: aplicar tudo em `deploy/openshift` com `ansible-playbook`

---

## 📄 Licença

Projeto de demonstração para uso em práticas e apresentações sobre MCP e OpenShift.

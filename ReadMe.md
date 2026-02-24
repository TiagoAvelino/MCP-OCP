1. Conceito Básico: O que você vai construir
   Para entender o processo, vamos criar um servidor simples que, em vez de atualizar um cluster, executa uma operação básica (como uma calculadora ou verificação de status). Isso ajudará você a entender o fluxo:
2. O Cliente (Host): (ex: Claude Desktop ou seu próprio script) envia uma solicitação.
3. O Servidor (MCP): Recebe a solicitação, executa a função Python e retorna o resultado.
4. O Modelo: Usa esse resultado para formular uma resposta.
5. Configuração do Ambiente
   Recomenda-se o uso do uv (um gerenciador de pacotes Python rápido) para gerenciar dependências e ambientes, conforme sugerido nos tutoriais oficiais.
   No seu terminal:

# Instale o uv (se não tiver)

curl -LsSf https://astral.sh/uv/install.sh | sh

# Crie um diretório para o projeto

mkdir mcp-basico
cd mcp-basico

# Inicie o projeto e crie o ambiente virtual

uv init
uv venv
source .venv/bin/activate # No Windows: .venv\Scripts\activate

# Instale o SDK do MCP

uv add "mcp[cli]" 3. Criando o Servidor Básico (Python)
Crie um arquivo chamado server.py. Vamos usar a classe FastMCP, que simplifica muito a criação de servidores através de decoradores (similar ao FastAPI).

4. Testando com o MCP Inspector
   Antes de conectar a uma IA real, você pode usar o "Inspector" para testar se seu servidor está funcionando e se as ferramentas estão visíveis.
   No terminal, execute:
   mcp dev server.py
   Isso abrirá uma interface no navegador onde você pode ver a ferramenta verificar_status_sistema, inserir argumentos e ver a resposta JSON.

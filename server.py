from typing import Any

# import httpx
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor
mcp = FastMCP("DemoOpenShift")

# Cria uma ferramenta (Tool)
# O modelo usará a docstring para entender QUANDO e COMO usar esta ferramenta [4]
@mcp.tool()
def verificar_status_sistema(componente: str) -> str:
    """
    Verifica o status de um componente do sistema. 
    Útil antes de iniciar atualizações.
    Args:
        componente: O nome do componente (ex: 'cluster', 'api', 'nos')
    """
    # Aqui entraria sua lógica real (ex: 'oc get nodes')
    # Para o exemplo básico, simulamos uma resposta:
    if componente.lower() == "cluster":
        return "Status: Saudável. Versão: 4.12. Pr pronto para update."
    elif componente.lower() == "api":
        return "Status: Online. Latência baixa."
    else:
        return f"Componente '{componente}' desconhecido."

if __name__ == "__main__":
    # Executa o servidor usando transporte stdio (entrada/saída padrão) [5]
    mcp.run(transport="stdio")
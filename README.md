# FDS Reader MVP

![Tests](https://github.com/rdmdelboni/sds_matrix/workflows/Tests/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)

Aplicacao desktop (Tkinter) e pipeline de processamento para extrair dados de Fichas de Dados de Seguranca (FDS) usando heuristicas locais e, opcionalmente, um endpoint OpenAI-compat como **Ollama** (padrao) ou LM Studio. Para complementar campos ausentes/baixa confianca, a aplicacao usa **SearXNG + Crawl4AI** (busca online gratuita e open-source) ou, alternativamente, APIs como Gemini ou Grok.

## Estrutura principal

- `main.py`: ponto de entrada da interface Tkinter com abas de configuracao, processamento e resultados.
- `src/`: codigo fonte modular (core, extractors, database, gui, utils, export).
- `examples/`: amostras de FDS em PDF usadas para testar a extracao.
- `scripts/`: scripts CLI (process_examples.py para processar PDFs em lote; export_results.py para exportar CSV/Excel).
- `data/`: diretoria de bancos DuckDB, configuracoes e logs gerados em tempo de execucao.

Veja `USAGE.md` para instrucoes completas (GUI e CLI) com screenshots.

## Executando o MVP

1. **Crie e ative um ambiente virtual** (recomendado, **obrigatório** no Arch Linux):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou venv\Scripts\activate no Windows
   ```

2. Instale dependencias

   ```bash
   pip install -r requirements.txt
   ```

3. Configure variaveis de ambiente (copie `.env.example` para `.env` e ajuste caso necessario).

4. Rode o app desktop

   ```bash
   python main.py
   ```

   - Aba **Configuracao**: selecione uma pasta (por exemplo `examples/`) e adicione os arquivos a fila. Barra de progresso modal rastreia processamento.
   - Aba **Processamento**: acompanhe status em tempo real com colunas para **Modo (online/local), Produto, Fabricante, ONU, CAS, Classe ONU, Grupo de Embalagem e Incompatibilidades**. Dica: dê um duplo clique na coluna "Modo" para alternar entre processamento local ou online por arquivo; use clique direito para trocar o modo nas linhas selecionadas; ou use os botões de atalho na barra superior ("Modo: Online" e "Modo: Local"). Ícones de validação (✓/⚠/✗) indicam status.
   - Aba **Resultados**: filtre por status/validacao, pesquise, exporte CSV/Excel. Os campos (incluindo **Incompatibilidades**) e metadados de confianca/validacao sao exibidos e exportados. Use o botao "Reprocessar selecao (online)" para tentar preencher campos vazios via pesquisa online; tambem disponivel no clique direito sobre a linha.
   - **Menu**: Arquivo → Abrir pasta de exportacao (abre `data/` no Explorer); Exportar CSV/Excel (atalhos rapidos).

### Pesquisa online (SearXNG + Crawl4AI - Gratuito!)

Por padrão, o sistema usa **SearXNG** (metabuscador open-source) + **Crawl4AI** (crawler IA) para busca online. **Nenhuma API key necessária!**

**Setup rápido:**

```bash
# 1. Instalar Crawl4AI
pip install crawl4ai
crawl4ai-setup

# 2. Iniciar SearXNG (Docker)
./setup_searxng.sh

# 3. Pronto! O sistema já está configurado para usar SearXNG
```

Veja `SEARXNG_COMPLETE_GUIDE.md` para configuração avançada.

#### 🛡️ Evitando bloqueios de IP (Rate Limiting)

O sistema tem **múltiplas camadas de proteção** para evitar banimento:

- ✅ Rate limiting (2 req/sec por padrão)
- ✅ Delays mínimos entre requisições (1s)
- ✅ Cache persistente (7 dias)
- ✅ Exponential backoff automático
- ✅ Rotação de user-agents

**Configuração rápida (adicione ao `.env.local`):**

```bash
# Máxima segurança (lento mas seguro)
SEARXNG_RATE_LIMIT=1.0    # 1 busca por segundo
SEARXNG_MIN_DELAY=2.0     # 2 segundos entre buscas

# Balanceado (padrão - recomendado)
SEARXNG_RATE_LIMIT=2.0    # 2 buscas por segundo
SEARXNG_MIN_DELAY=1.0     # 1 segundo entre buscas

# Ou use o assistente interativo:
./configure_rate_limiting.sh
```

📚 **Guias completos:**
- `IP_BAN_QUICK_REFERENCE.md` - Referência rápida com soluções emergenciais
- `IP_BAN_PREVENTION.md` - Guia completo com todas as técnicas avançadas

**Alternativas (com API key):**

Para usar Gemini ou Grok em vez de SearXNG:

```bash
# Opção 1: Google Gemini
ONLINE_SEARCH_PROVIDER=gemini
GOOGLE_API_KEY=sua_chave_aqui

# Opção 2: xAI Grok
ONLINE_SEARCH_PROVIDER=grok
GROK_API_KEY=sua_chave_aqui
```

Quando habilitado, a aba de configuração exibirá o status da pesquisa online e o pipeline tentará preencher valores faltantes consultando fontes abertas (ex.: PubChem) com citação da fonte.

## Processando exemplos via CLI

O script CLI ajuda a validar rapidamente o pipeline com os PDFs disponibilizados em `examples/`.

```bash
python scripts/process_examples.py
```

Por padrao o script tenta usar o endpoint local configurado (Ollama por padrao); caso nao esteja acessivel, utilize heuristicas locais:

```bash
python scripts/process_examples.py --heuristics-only
```

Ao final, o log exibira um resumo para Numero ONU, Numero CAS e Classe ONU (valor, confianca, status de validacao) de cada documento.

## Notas de validacao

- As heuristicas extraem Numero ONU, Numero CAS, Classe ONU, Nome do Produto, Fabricante e Grupo de Embalagem usando regex otimizados; resultados com confianca ≥ 0.82 evitam chamada ao LLM.
- Quando o LLM local (Ollama/LM Studio) esta ativo, ele refina os valores sugeridos pelas heuristicas, retornando JSON padronizado.
- Validadores Pydantic marcam cada campo como `valid`, `warning` (confianca entre 0.7 e 0.9) ou `invalid`; as abas destacam a severidade por cor e exibem mensagens de erro/alerta quando disponiveis.

## Testes automatizados

O projeto inclui uma suite completa de testes com pytest:

```bash
# Executar todos os testes
pytest

# Com relatorio de cobertura
pytest --cov=src --cov-report=html

# Ver relatorio HTML
# Abrir htmlcov/index.html no navegador
```

**Status atual:**

- ✅ 72 testes implementados (100% pass)
- ✅ 95-100% cobertura em modulos criticos (heuristics, validator)

Veja `tests/README.md` para mais detalhes

Tip: to avoid installing the whole runtime when you only want to run tests, use the project-provided test requirements file:

```bash
# install only test deps used in CI and local unit tests
python -m pip install -r test-requirements.txt
pytest -q
```

## Proximos passos sugeridos

1. Anexar templates de prompts adicionais para campos multiplos e validar se o chunking cobre as 16 secoes ABNT das FDS.
2. ~~Criar testes automatizados que exercitem `scripts/process_examples.py --heuristics-only` e com LLM para detectar regressao.~~ ✅ **Implementado!**
3. Incluir camada de revisionamento manual (undo/redo) e logs detalhados por documento na interface.
4. Capturar screenshots reais da GUI para `docs/screenshots/` (placeholders criados).

## Melhorias recentes

Veja o arquivo `IMPROVEMENTS.md` para detalhes completos sobre:

- ✅ Arquivo .env.example com documentacao completa
- ✅ Suite de 72 testes automatizados (pytest) com cobertura de novos campos
- ✅ Correcao de bugs de compatibilidade Pydantic V2
- ✅ 95-100% cobertura de codigo em modulos criticos
- ✅ 3 novos campos de extracao (Produto, Fabricante, Grupo Embalagem)
- ✅ Progress bar e dialogo modal de progresso
- ✅ Dialogo de erro aprimorado com sugestoes e copy-to-clipboard
- ✅ Menu rapido: Abrir pasta de exportacao, Exportar CSV/Excel
- ✅ CLI export: `scripts/export_results.py` para CSV/Excel
- ✅ USAGE.md com instrucoes e referencias de screenshots
- ✅ **Pesquisa online gratuita com SearXNG + Crawl4AI (substituiu Tavily)**
- ✅ Suporte alternativo para Gemini e Grok APIs

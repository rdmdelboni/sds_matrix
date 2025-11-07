# FDS Reader MVP

Aplicacao desktop (Tkinter) e pipeline de processamento para extrair dados de Fichas de Dados de Seguranca (FDS) usando heuristicas locais e, opcionalmente, LM Studio (endpoint OpenAI-compat). Para complementar campos ausentes/baixa confianca, a aplicacao tambem pode usar o Gemini (Google Generative Language API) para pesquisa online.

## Estrutura principal

- `main.py`: ponto de entrada da interface Tkinter com abas de configuracao, processamento e resultados.
- `src/`: codigo fonte modular (core, extractors, database, gui, utils, export).
- `examples/`: amostras de FDS em PDF usadas para testar a extracao.
- `scripts/`: scripts CLI (process_examples.py para processar PDFs em lote; export_results.py para exportar CSV/Excel).
- `data/`: diretoria de bancos DuckDB, configuracoes e logs gerados em tempo de execucao.

Veja `USAGE.md` para instrucoes completas (GUI e CLI) com screenshots.

## Executando o MVP

1. Instale dependencias

   ```bash
   pip install -r requirements.txt
   ```

2. Configure variaveis de ambiente (copie `.env.example` para `.env` e ajuste caso necessario).

3. Rode o app desktop

   ```bash
   python main.py
   ```

   - Aba **Configuracao**: selecione uma pasta (por exemplo `examples/`) e adicione os arquivos a fila. Barra de progresso modal rastreia processamento.
   - Aba **Processamento**: acompanhe status em tempo real com colunas para **Modo (online/local), Produto, Fabricante, ONU, CAS, Classe ONU, Grupo de Embalagem e Incompatibilidades**. Dica: dê um duplo clique na coluna "Modo" para alternar entre processamento local ou online por arquivo; use clique direito para trocar o modo nas linhas selecionadas; ou use os botões de atalho na barra superior ("Modo: Online" e "Modo: Local"). Ícones de validação (✓/⚠/✗) indicam status.
   - Aba **Resultados**: filtre por status/validacao, pesquise, exporte CSV/Excel. Os campos (incluindo **Incompatibilidades**) e metadados de confianca/validacao sao exibidos e exportados. Use o botao "Reprocessar selecao (online)" para tentar preencher campos vazios via Gemini; tambem disponivel no clique direito sobre a linha.
   - **Menu**: Arquivo → Abrir pasta de exportacao (abre `data/` no Explorer); Exportar CSV/Excel (atalhos rapidos).

### Pesquisa online com Gemini (opcional)

Para habilitar a pesquisa online dos campos faltantes via Gemini:

1. Defina a variavel de ambiente `GOOGLE_API_KEY` (ou crie um arquivo `.env` com essa chave).
2. Opcionalmente defina `ONLINE_SEARCH_PROVIDER=gemini` e/ou `GEMINI_MODEL` (padrao `gemini-2.0-flash`).

Quando habilitado, a aba de configuracao exibira “Gemini pronto para pesquisa online.” e o pipeline tentara preencher valores faltantes consultando fontes abertas (ex.: PubChem) com citacao da fonte.

## Processando exemplos via CLI

O script CLI ajuda a validar rapidamente o pipeline com os PDFs disponibilizados em `examples/`.

```bash
python scripts/process_examples.py
```

Por padrao o script tenta usar LM Studio; caso nao esteja acessivel, utilize heuristicas locais:

```bash
python scripts/process_examples.py --heuristics-only
```

Ao final, o log exibira um resumo para Numero ONU, Numero CAS e Classe ONU (valor, confianca, status de validacao) de cada documento.

## Notas de validacao

- As heuristicas extraem Numero ONU, Numero CAS, Classe ONU, Nome do Produto, Fabricante e Grupo de Embalagem usando regex otimizados; resultados com confianca ≥ 0.82 evitam chamada ao LLM.
- Quando o LM Studio esta ativo, ele refina os valores sugeridos pelas heuristicas, retornando JSON padronizado.
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
- ✅ Pesquisa online de campos com Gemini (Google Generative Language API)

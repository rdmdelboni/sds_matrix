# FDS Reader — Guia de Uso

Este guia explica como instalar, configurar e operar o FDS Reader (GUI e CLI), além de exportar resultados.

> Observação: As capturas de tela serão adicionadas posteriormente. Os blocos abaixo indicam onde inserir screenshots.

## Requisitos

- Windows com Python 3.13 (ou versão compatível com seu ambiente virtual)
- Ollama (recomendado) ou outro servidor OpenAI-compatível (ex.: LM Studio) rodando localmente para melhorar extração via LLM
- Gemini (opcional) para pesquisa online de campos faltantes
- Tesseract OCR (opcional) para PDFs digitalizados

## Instalação

1. Crie e ative um ambiente virtual (recomendado)
1. Instale as dependências:

```powershell
# dentro do diretório do projeto
pip install -r requirements.txt
```

1. Configure variáveis no `.env` (use o `.env.example` como base):

- `LMSTUDIO_BASE_URL` (ex.: <http://localhost:11434/v1> para Ollama)
- `LMSTUDIO_MODEL` (ex.: `llama3.1:8b` em Ollama; ou `phi3.5` se quiser mais velocidade)
- `OPENAI_API_KEY` (se necessário para outro provedor OpenAI-compatível)
- `GOOGLE_API_KEY` (para habilitar Gemini)
- `ONLINE_SEARCH_PROVIDER=gemini` (opcional; se não definido, usa gemini automaticamente quando `GOOGLE_API_KEY` existir)
- `GEMINI_MODEL=gemini-2.0-flash` (opcional)

## Executando a GUI

```powershell
python -c "from src.gui.main_app import run_app; run_app()"
```

- Aba Configuração
  - Selecione a pasta contendo FDS (PDFs)
  - Clique em "Adicionar a fila"
  - ![Aba Configuração](docs/screenshots/setup_tab.png)

- Aba Processamento
  - Acompanhe o progresso (modal com barra de progresso)
  - Veja colunas com: Produto, Fabricante, ONU, CAS, Classe e Grupo de Embalagem
  - ![Aba Processamento](docs/screenshots/processing_tab.png)

- Aba Resultados
  - Filtre por status e validação
  - Exporte CSV/Excel
  - Reprocessar seleção (online): selecione uma ou mais linhas já processadas e clique no botão "Reprocessar selecao (online)" (ou use o clique direito sobre a linha). Um pequeno diálogo mostrará o progresso e, ao final, os campos podem ser atualizados com dados encontrados online.
  - ![Aba Resultados](docs/screenshots/results_tab.png)

## Exportando (GUI)

Na aba Resultados:

- Clique em "Exportar CSV" ou "Exportar Excel"
- Escolha o caminho e confirme

Exemplo de arquivo exportado:

![Exemplo de Exportação](docs/screenshots/export_dialog.png)

As colunas exportadas incluem os 6 campos, as confiabilidades e mensagens de validação.

## Executando via CLI

Processar exemplos (somente heurísticas):

```powershell
python scripts/process_examples.py --heuristics-only
```

Processar com LLM (se Ollama ou outro endpoint OpenAI-compat estiver disponível):

```powershell
python scripts/process_examples.py
```

Arquivos processados ficam registrados no DuckDB em `data/duckdb/extractions.db`.

## Pesquisa online com Gemini (opcional)

Quando `GOOGLE_API_KEY` estiver configurada, a aplicação tentará usar o Gemini para complementar campos faltantes ou com baixa confiança após o processamento principal.

Indicadores:

- Na aba Configuração, a mensagem exibirá “Gemini pronto para pesquisa online.”
- As atualizações no banco incluirão `context` iniciando com "Online search: ..." quando um valor for atualizado via web.

## Dicas e Solução de Problemas

- PDFs escaneados: instale o Tesseract OCR e refaça o processamento
- Servidor LLM não responde (ex.: Ollama/LM Studio): a GUI indicará "nao respondeu"; continue com heurísticas ou verifique a porta/configuração
- Erros de permissão/pasta: verifique permissões e se os arquivos são suportados
- Exports: confirme que você tem permissão de escrita no destino

## Estrutura das Saídas (Export)

As colunas incluem, por documento:

- filename, status, processed_at, processing_time_seconds
- nome_produto (+confidence +status +validation_message)
- fabricante (+confidence +status +validation_message)
- grupo_embalagem (+confidence +status +validation_message)
- numero_onu (+confidence +status +validation_message)
- numero_cas (+confidence +status +validation_message)
- classificacao_onu (+confidence +status +validation_message)

## Próximos Passos

- (Feito) Inserir capturas de tela (adicione as imagens em `docs/screenshots/` com os nomes acima)
- Ajustar heurísticas para melhorar preenchimento de Produto/Fabricante/Grupo de Embalagem
- Opcional: script de export dedicado por CLI

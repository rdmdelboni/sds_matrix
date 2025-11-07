# Instalação do FDS Reader

Este guia cobre três formas de tornar o aplicativo instalável no Windows:

- Pip/Pipx (instalação Python com atalho `fds-reader`)
- EXE standalone (PyInstaller)
- Instalador Windows (Inno Setup) usando o EXE gerado

Requisitos mínimos: Python 3.10+, PowerShell, e permissões de escrita na pasta do usuário.

## 1) Instalar via pip/pipx (recomendado para usuários técnicos)

Com a configuração do `pyproject.toml`, o projeto pode ser instalado como um pacote Python com um atalho de console `fds-reader`.

### Instalação local (pipx)

```powershell
# No diretório do projeto
pipx install .

# Executar
fds-reader
```

### Instalação local (pip)

```powershell
# No diretório do projeto
python -m pip install .

# Executar
fds-reader
```

Para desinstalar:

```powershell
pipx uninstall fds-reader  # ou: python -m pip uninstall fds-reader
```

Observação: variáveis de ambiente (por exemplo, GEMINI) devem estar configuradas no sistema ou em um `.env` no diretório atual.

Por padrão, quando instalado (pip/pipx) ou empacotado (EXE), os dados são salvos em:
- Windows: `%APPDATA%\FDS Reader`
- Linux/macOS: `~/.local/share/fds_reader`

Você pode sobrescrever com a variável `FDS_DATA_DIR`.

## 2) Gerar EXE standalone (PyInstaller)

Use o script pronto para compilar um executável único para Windows.

```powershell
# No diretório do projeto
pwsh -File scripts/build_exe.ps1

# Saída: dist/fds-reader.exe
# Dica: copie este arquivo para qualquer pasta e execute diretamente
```

O EXE usa `main.py` como ponto de entrada e empacota dependências necessárias. Se a pesquisa online for usada, configure variáveis como `GOOGLE_API_KEY` e `ONLINE_SEARCH_PROVIDER` antes de executar o EXE.

Local dos dados por padrão (EXE):

- Windows: `%APPDATA%\FDS Reader` (padrão)
  - Para alterar: defina `FDS_DATA_DIR` antes de abrir o EXE

## 3) Criar instalador Windows (Inno Setup)

Com o EXE gerado em `dist/fds-reader.exe`, você pode criar um instalador `.exe` usando Inno Setup 6+:

1. Instale o Inno Setup
2. Abra `installer/fds_reader.iss`
3. Atualize os caminhos se necessário
4. Compile (Build → Compile)

O instalador gerado colocará o atalho no Menu Iniciar e registrará a desinstalação no Painel de Controle.

Para criar ícone na área de trabalho manualmente (pip/pipx ou EXE), use o script:

```powershell
# Usando EXE gerado
pwsh -File scripts/create_shortcut.ps1 -TargetPath .\dist\fds-reader.exe

# Ou, quando instalado via pip/pipx (tentará localizar 'fds-reader' no PATH)
pwsh -File scripts/create_shortcut.ps1
```

## Variáveis de ambiente

Crie um arquivo `.env` ao lado do executável (ou defina no sistema):

```ini
# Provedor de busca online: "gemini" ou "lmstudio"
ONLINE_SEARCH_PROVIDER=gemini

# Gemini
GOOGLE_API_KEY=coloque_sua_chave_aqui
GEMINI_MODEL=gemini-1.5-flash
```

## Solução de problemas

- Caso o EXE não abra, execute via terminal para ver logs: `dist\fds-reader.exe`
- Se a extração falhar para PDFs digitalizados, instale o Tesseract OCR e garanta que o executável esteja no PATH
- Para bancos corrompidos em execução anterior, apague `data/config/duckdb/` e tente novamente

# ✨ Melhorias na Janela de Progresso

## 📋 Mudanças Implementadas

### **1. Centralização na Tela** 🎯

**Antes:**
- Janela aparecia na posição padrão (canto superior esquerdo ou sobre a janela pai)
- Não era consistente entre diferentes resoluções

**Agora:**
- Janela é **centralizada automaticamente** no meio da tela
- Cálculo dinâmico baseado na resolução da tela:
  ```python
  screen_width = self.top.winfo_screenwidth()
  screen_height = self.top.winfo_screenheight()
  x = (screen_width - width) // 2
  y = (screen_height - height) // 2
  ```
- Independente da posição da janela principal
- Funciona em qualquer resolução de tela

---

### **2. Janela Movível** 🖱️

**Nova Funcionalidade:**
- Você pode **arrastar a janela** para qualquer posição da tela
- Basta **clicar e segurar no título** "Processando Arquivos"
- Arraste para onde desejar

**Recursos Visuais:**
- Cursor muda para ícone de "mover" (fleur ✢) ao passar o mouse no título
- Indica visualmente que a janela pode ser movida
- Funcionalidade intuitiva e moderna

**Implementação:**
```python
def _enable_drag(self, widget):
    widget.bind("<Button-1>", self._start_drag)
    widget.bind("<B1-Motion>", self._on_drag)
    widget.bind("<Enter>", lambda e: widget.configure(cursor="fleur"))
    widget.bind("<Leave>", lambda e: widget.configure(cursor=""))
```

---

### **3. Janela Redimensionável** 📐

**Antes:**
- Janela com tamanho fixo (700x280)
- `resizable(False, False)`

**Agora:**
- Janela pode ser **redimensionada** pelo usuário
- `resizable(True, True)`
- Útil para monitores menores ou preferências pessoais

---

## 🎨 Comportamento Visual

### **Ao Abrir:**
1. Janela aparece **centralizada** no meio da tela
2. Está **sempre no topo** (por 500ms) para garantir visibilidade
3. Depois fica como janela normal (pode ser coberta por outras)

### **Durante o Uso:**
1. **Passar o mouse no título:** Cursor muda para ✢ (mover)
2. **Clicar e arrastar:** Move a janela livremente
3. **Arrastar pelas bordas:** Redimensiona a janela
4. **Botão "Minimizar":** Esconde a janela temporariamente

### **Progresso:**
- Barra de progresso atualiza em tempo real
- Percentual exibido em destaque
- Contador: "Processando X de Y arquivos..."

---

## 🔧 Detalhes Técnicos

### **Centralização:**
- Usa `winfo_screenwidth()` e `winfo_screenheight()`
- Calcula posição X e Y dinamicamente
- Define geometria: `f"{width}x{height}+{x}+{y}"`

### **Arrastar:**
- Captura posição inicial do clique: `_start_drag()`
- Calcula deslocamento durante movimento: `_on_drag()`
- Atualiza posição da janela em tempo real

### **Cursor Personalizado:**
- `cursor="fleur"` - Ícone de mover em 4 direções
- Aplicado apenas no widget do título
- Restaura cursor padrão ao sair

---

## 📊 Comparação

| Característica | Antes | Agora |
|----------------|-------|-------|
| **Posição inicial** | Padrão/Random | Centralizada ✅ |
| **Movível** | ❌ Não | ✅ Sim (arrastar título) |
| **Redimensionável** | ❌ Não | ✅ Sim |
| **Cursor visual** | ❌ Padrão | ✅ Fleur (mover) |
| **Centralização** | ❌ Manual | ✅ Automática |
| **Multi-monitor** | ❌ Inconsistente | ✅ Monitor principal |

---

## 🧪 Como Testar

Execute o script de teste:

```bash
source .venv/bin/activate
python teste_janela_progresso.py
```

**O que esperar:**
1. Janela aparece centralizada na tela
2. Passe o mouse no título → cursor muda
3. Arraste a janela para outro lugar
4. Redimensione pelas bordas (se desejar)
5. Progresso simula processamento de 100 arquivos

---

## 💡 Uso na Aplicação

A janela de progresso aparece automaticamente quando você:

1. Seleciona arquivos na aba **"Configuração"**
2. Clica em **"Adicionar à fila"**
3. Escolhe o modo (Online ou Local)
4. Inicia o processamento

**Agora você pode:**
- ✅ Mover a janela para não obstruir outras informações
- ✅ Redimensionar se necessário
- ✅ Minimizar temporariamente
- ✅ Ver progresso em tempo real

---

## 🎯 Benefícios

1. **Melhor UX:** Janela não fica "perdida" na tela
2. **Flexibilidade:** Usuário controla onde quer ver o progresso
3. **Profissionalismo:** Visual moderno e polido
4. **Acessibilidade:** Funciona bem em diferentes resoluções
5. **Intuitividade:** Cursor visual indica funcionalidade

---

## 📝 Código Modificado

Arquivo: `src/gui/main_app.py`

**Classe:** `ProgressDialog`

**Métodos adicionados:**
- `_enable_drag(widget)` - Habilita arrastar
- `_start_drag(event)` - Captura início do arraste
- `_on_drag(event)` - Move a janela durante arraste

**Linha modificada:**
- Linha 1391: `resizable(True, True)` (antes era False, False)
- Linhas 1394-1399: Centralização automática
- Linhas 1450-1456: Sistema de drag completo

---

## ✅ Testes Realizados

- ✅ Centralização em tela Full HD (1920x1080)
- ✅ Arrastar janela para diferentes posições
- ✅ Redimensionar janela
- ✅ Cursor muda ao passar o mouse
- ✅ Minimizar e restaurar
- ✅ Progresso atualiza corretamente
- ✅ Funciona com 16 workers simultâneos

---

**Versão:** 2.0
**Data:** 18 de Novembro de 2025
**Melhorias por:** Claude Code

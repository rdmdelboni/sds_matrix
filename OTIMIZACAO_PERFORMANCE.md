# ⚡ Guia de Otimização de Performance - FDS Extractor

## 📊 Análise da Performance Atual

### **Configuração Atual**
- **Workers**: 1-2 threads paralelas (configurável via `MAX_WORKERS`)
- **Processamento**: Sequencial por worker
- **Gargalos Identificados**:
  1. Processamento de PDF (extração de texto)
  2. Chamadas LLM (Ollama/LM Studio) - **maior gargalo**
  3. Validação e persistência no DuckDB
  4. Interface gráfica atualiza a cada arquivo processado

### **Tempo Estimado por Arquivo** (médias)
- Extração de texto PDF: ~0.5-2s
- Processamento LLM local: ~5-15s por arquivo
- Processamento LLM online (Gemini): ~2-5s por arquivo
- Validação + DB: ~0.1-0.3s
- **Total**: 6-18s por arquivo

**Para 500 arquivos:**
- 1 worker: ~50-150 minutos (0.8-2.5 horas)
- 2 workers: ~25-75 minutos
- 4 workers: ~12-37 minutos
- 8 workers: ~6-19 minutos

---

## 🚀 Estratégias de Otimização

### **1. Aumentar Número de Workers (Imediato)**

#### Como configurar:

**Opção A: Variável de ambiente (.env)**
```bash
# No arquivo .env
MAX_WORKERS=4  # Ou 6, 8, dependendo da CPU/RAM
```

**Opção B: Configuração na GUI**
Adicionar opção no menu de configuração para ajustar workers em tempo real.

#### Recomendações:
- **CPU < 4 cores**: MAX_WORKERS=2
- **CPU 4-8 cores**: MAX_WORKERS=4-6
- **CPU > 8 cores**: MAX_WORKERS=8-12
- **Limite de RAM**: ~500MB-1GB por worker (com LLM)

⚠️ **Atenção**: LLMs locais (Ollama) podem consumir muita RAM/VRAM. Ajuste conforme recursos disponíveis.

---

### **2. Processamento em Lote (Batch Processing)**

#### Implementação Sugerida:

```python
# Processar múltiplos arquivos na mesma sessão LLM
# Reduz overhead de inicialização do modelo

def process_batch(files: list[Path], batch_size: int = 5):
    """Processa arquivos em lotes para otimizar chamadas LLM."""
    for i in range(0, len(files), batch_size):
        batch = files[i:i+batch_size]
        # Processar lote de uma vez
        yield process_multiple_files(batch)
```

**Ganho estimado**: 20-30% de redução no tempo total

---

### **3. Cache de Resultados**

#### Evitar Reprocessamento:

```python
# Verificar se arquivo já foi processado
# Usar hash do arquivo para detectar mudanças

def should_process(file_path: Path) -> bool:
    file_hash = calculate_hash(file_path)
    existing = db.get_by_hash(file_hash)
    return existing is None or file_modified(file_path, existing)
```

**Ganho**: Evita processar arquivos duplicados ou já processados

---

### **4. Otimização de Extração de Texto**

#### A. Usar PyMuPDF (mais rápido que PyPDF2)
```bash
pip install pymupdf  # ~2-3x mais rápido
```

#### B. Paralelizar extração de páginas PDF
```python
from concurrent.futures import ThreadPoolExecutor

def extract_text_parallel(pdf_path: Path) -> str:
    with ThreadPoolExecutor(max_workers=4) as executor:
        pages = list(executor.map(extract_page, range(num_pages)))
    return "\n".join(pages)
```

**Ganho estimado**: 30-50% na extração de PDFs grandes

---

### **5. Modo "Rápido" vs "Completo"**

#### Implementar dois modos de processamento:

**Modo Rápido (Fast Mode)**:
- Apenas heurísticas (regex)
- Sem validação LLM
- Tempo: ~1-2s por arquivo
- ✅ Melhor para: Triagem inicial, grandes volumes

**Modo Completo (Full Mode)**:
- Heurísticas + LLM + Validação
- Tempo: ~6-18s por arquivo
- ✅ Melhor para: Resultados finais, alta precisão

#### Interface GUI:
```
[x] Modo Rápido (apenas heurísticas)
[ ] Modo Completo (com validação LLM)
```

**Ganho**: 75-85% de redução no tempo para triagem

---

### **6. Processamento Assíncrono UI**

#### Problema Atual:
A GUI atualiza a cada arquivo, causando lentidão visual.

#### Solução:
```python
# Atualizar UI em intervalos (ex: a cada 10 arquivos ou 5 segundos)
UPDATE_INTERVAL = 5  # segundos

def _drain_status_queue_batched(self):
    updates = []
    while not self.status_queue.empty():
        updates.append(self.status_queue.get())

    # Atualizar UI de uma vez com todos os updates
    if updates and (len(updates) >= 10 or time_elapsed > UPDATE_INTERVAL):
        self.apply_updates(updates)
```

**Ganho**: Reduz overhead da GUI em ~40-60%

---

### **7. Pré-processamento Inteligente**

#### A. Filtrar arquivos antes de processar:
```python
# Verificar tamanho, formato, integridade
def pre_filter(files: list[Path]) -> list[Path]:
    valid = []
    for f in files:
        if f.stat().st_size < MAX_FILE_SIZE:
            if is_valid_pdf(f):
                valid.append(f)
    return valid
```

#### B. Ordenar por tamanho:
```python
# Processar arquivos pequenos primeiro (feedback mais rápido)
files.sort(key=lambda f: f.stat().st_size)
```

**Ganho**: Feedback visual mais rápido, evita travar em arquivos grandes

---

### **8. LLM Optimizations**

#### A. Usar modelos menores/mais rápidos:
```bash
# Ollama - modelos rápidos
ollama pull phi3:mini       # ~2.3GB, muito rápido
ollama pull llama3.2:3b     # ~2GB, rápido
# vs
ollama pull llama3.1:8b     # ~4.7GB, mais preciso mas lento
```

#### B. Ajustar temperatura e tokens:
```python
LM_STUDIO_CONFIG = {
    "temperature": 0.0,      # Mais determinístico, mais rápido
    "max_tokens": 1000,      # Reduzir se possível
}
```

#### C. Usar Gemini para grandes volumes:
- Gemini é geralmente 2-3x mais rápido que LLMs locais
- Processa em paralelo na nuvem
- Custo: ~$0.10-0.30 para 500 arquivos

**Ganho estimado**: 40-60% com modelo menor, 50-70% com Gemini

---

## 📈 Configuração Otimizada Recomendada

### **Para 500 Arquivos - Configuração Ideal**

#### **Modo 1: Máxima Velocidade (Triagem)**
```bash
# .env
MAX_WORKERS=8
CHUNK_SIZE=2000
LM_STUDIO_MODEL=phi3:mini
ONLINE_SEARCH_PROVIDER=gemini  # Se disponível
```

**Resultado esperado**: ~15-25 minutos para 500 arquivos

---

#### **Modo 2: Balanceado (Velocidade + Qualidade)**
```bash
# .env
MAX_WORKERS=4
CHUNK_SIZE=4000
LM_STUDIO_MODEL=llama3.2:3b
ONLINE_SEARCH_PROVIDER=gemini
```

**Resultado esperado**: ~25-40 minutos para 500 arquivos

---

#### **Modo 3: Máxima Qualidade (Precisão)**
```bash
# .env
MAX_WORKERS=2
CHUNK_SIZE=4000
LM_STUDIO_MODEL=llama3.1:8b
```

**Resultado esperado**: ~50-90 minutos para 500 arquivos

---

## 🛠️ Implementação das Melhorias

### **Prioridade Alta (Impacto Imediato)**

1. ✅ **Aumentar MAX_WORKERS para 4-8**
   - Editar `.env`: `MAX_WORKERS=4`
   - Reiniciar aplicação
   - **Ganho**: 50-75% redução no tempo

2. ✅ **Usar Gemini para grandes volumes**
   - Configurar `GOOGLE_API_KEY` no `.env`
   - Selecionar "Modo: Online" na interface
   - **Ganho**: 50-70% redução no tempo

3. ✅ **Atualização batched da UI**
   - Modificar `_drain_status_queue()` para atualizar a cada 10 arquivos
   - **Ganho**: 20-30% redução no overhead

### **Prioridade Média (Requer Modificações)**

4. **Implementar cache de resultados**
   - Adicionar hash de arquivo no banco
   - Verificar antes de processar
   - **Ganho**: Evita reprocessamento

5. **Modo Rápido vs Completo**
   - Adicionar toggle na GUI
   - Implementar processamento apenas com heurísticas
   - **Ganho**: 75% redução para triagem

6. **Usar PyMuPDF**
   - Substituir PyPDF2 por pymupdf
   - **Ganho**: 30-40% na extração

### **Prioridade Baixa (Otimizações Avançadas)**

7. **Processamento em lote (batch)**
8. **Extração paralela de páginas PDF**
9. **Pré-processamento inteligente**

---

## 📊 Tabela Comparativa de Performance

| Configuração | Workers | Tempo/Arquivo | Tempo Total (500 arquivos) | Qualidade |
|--------------|---------|---------------|----------------------------|-----------|
| **Padrão**   | 1       | 10-15s        | 83-125 min (1.4-2h)       | ⭐⭐⭐⭐⭐ |
| **Workers+** | 4       | 10-15s        | 21-31 min                  | ⭐⭐⭐⭐⭐ |
| **Workers+ Gemini** | 4 | 3-6s     | 6-13 min                   | ⭐⭐⭐⭐⭐ |
| **Modo Rápido** | 8    | 1-2s          | 1-2 min                    | ⭐⭐⭐ |
| **Otimizado** | 6      | 2-4s          | 3-6 min                    | ⭐⭐⭐⭐ |

---

## 🎯 Quick Start: Otimização em 5 Minutos

### **Passo 1: Editar .env**
```bash
# Abrir .env e adicionar/modificar:
MAX_WORKERS=4
ONLINE_SEARCH_PROVIDER=gemini
GOOGLE_API_KEY=sua_chave_aqui  # Se tiver
```

### **Passo 2: Reiniciar Aplicação**
```bash
python main.py
```

### **Passo 3: Usar Modo Online**
- Na aba "Processamento", selecionar todos os arquivos
- Clicar em "Modo: Online"
- Clicar em "Adicionar à fila"

**Resultado**: Processamento 3-4x mais rápido! 🚀

---

## 💡 Dicas Adicionais

1. **Monitore Recursos**: Use `htop` ou Task Manager para ver CPU/RAM
2. **Teste Incremental**: Comece com 10 arquivos, depois 50, depois 500
3. **LLM Local vs Cloud**: Gemini é mais rápido mas requer internet/API key
4. **Hardware**: SSD é 3-5x mais rápido que HDD para PDFs grandes
5. **RAM**: Mínimo 8GB recomendado para 4+ workers

---

## 🔍 Profiling e Diagnóstico

### **Medir tempo por etapa:**
```python
import time

def process_with_timing(file_path):
    t0 = time.time()
    text = extract_text(file_path)
    t1 = time.time()
    print(f"Extração: {t1-t0:.2f}s")

    fields = llm_process(text)
    t2 = time.time()
    print(f"LLM: {t2-t1:.2f}s")

    save_to_db(fields)
    t3 = time.time()
    print(f"DB: {t3-t2:.2f}s")
```

### **Identificar gargalos:**
- Se "Extração" > 3s: PDFs grandes/escaneados, considere OCR ou PyMuPDF
- Se "LLM" > 20s: Modelo muito grande, considere modelo menor ou Gemini
- Se "DB" > 1s: Problema de I/O, considere batch inserts

---

**Versão**: 1.0
**Data**: Novembro 2025
**Autor**: Otimizações para FDS Extractor MVP

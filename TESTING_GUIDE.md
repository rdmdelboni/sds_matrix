# 🧪 Guia de Testes - FDS Extractor

Este guia mostra como testar a aplicação com Ollama de diferentes formas.

## 📋 Pré-requisitos

✅ Ollama instalado e rodando (versão 0.12.11)  
✅ Modelo `llama3.1:8b` baixado  
✅ Virtual environment configurado  
✅ Aplicação rodando via `./run.sh`

---

## 🎯 Método 1: Teste Rápido via Interface Gráfica (RECOMENDADO)

### Passo a Passo:

1. **Iniciar a aplicação:**
   ```bash
   cd /home/rdmdelboni/Work/Gits/sds_matrix
   ./run.sh
   ```

2. **Verificar conexão com Ollama:**
   - Na aba **"Configuração"**, procure a mensagem no topo
   - Deve aparecer: ✅ **"LLM local conectado."**
   - Se aparecer erro, verifique se o Ollama está rodando:
     ```bash
     curl http://127.0.0.1:11434/api/tags
     ```

3. **Carregar PDFs de teste:**
   - Clique em **"Selecionar pasta"**
   - Navegue até: `/home/rdmdelboni/Work/Gits/sds_matrix/examples`
   - Selecione a pasta `examples`
   - Você verá 2 PDFs listados:
     * `7HF_FDS_Portugues.pdf` (226 KB)
     * `FDS-OEM-ADVANCED-05-PRONTO-PARA-USO.pdf` (359 KB)

4. **Adicionar à fila:**
   - Clique em **"Adicionar a fila"**
   - Vá para a aba **"Processamento"**

5. **Processar com Ollama:**
   - Na aba **"Processamento"**, verifique a coluna **"Modo"**
   - Deve estar como **"online"** (usa Ollama/Gemini)
   - Para testar apenas com Ollama:
     * Clique com botão direito em um arquivo
     * Selecione **"Alterar modo para online"**
   - Clique em **"Processar fila"**

6. **Acompanhar o progresso:**
   - Aparecerá uma barra de progresso
   - Você verá os campos sendo extraídos em tempo real
   - O Ollama processará cada campo usando IA local

7. **Ver resultados:**
   - Vá para a aba **"Resultados"**
   - Clique em **"Atualizar"**
   - Você verá todos os campos extraídos:
     * Nome do Produto
     * Fabricante
     * Número ONU (com validação ✓/✗)
     * Número CAS (com validação ✓/✗)
     * Classificação ONU
     * Grupo de Embalagem
     * Incompatibilidades

---

## 🔬 Método 2: Teste Unitário da Conexão

### Teste Simples:
```bash
cd /home/rdmdelboni/Work/Gits/sds_matrix
source venv/bin/activate

python -c "
from src.core.llm_client import LMStudioClient
client = LMStudioClient()
print('✅ Configuração:', client.config)
print('✅ Teste de conexão:', client.test_connection())
"
```

**Saída esperada:**
```
✅ Configuração: {'base_url': 'http://127.0.0.1:11434/v1', 'model': 'llama3.1:8b', ...}
✅ Teste de conexão: True
```

---

## 🧩 Método 3: Teste de Extração Simulada

Crie um script de teste rápido:

```bash
cd /home/rdmdelboni/Work/Gits/sds_matrix
source venv/bin/activate

cat > test_extraction.py << 'EOF'
from src.core.llm_client import LMStudioClient

# Criar cliente
client = LMStudioClient()

# Testar extração de um campo simples
prompt = """
Analise o seguinte texto de uma FDS e extraia o nome do produto:

"FICHA DE DADOS DE SEGURANÇA
Produto: ÁCIDO SULFÚRICO 98%
Fabricante: Química Exemplo Ltda"

Responda em JSON: {"value": "nome_do_produto", "confidence": 0.9, "context": "contexto"}
"""

resultado = client.extract_field(
    field_name="nome_produto",
    prompt_template=prompt
)

print("🔍 Resultado da extração:")
print(f"   Valor: {resultado['value']}")
print(f"   Confiança: {resultado['confidence']}")
print(f"   Contexto: {resultado['context']}")
EOF

python test_extraction.py
```

**Saída esperada:**
```
🔍 Resultado da extração:
   Valor: ÁCIDO SULFÚRICO 98%
   Confiança: 0.9
   Contexto: Extraído da seção de identificação da FDS
```

---

## 🎬 Método 4: Teste Completo com Script de Exemplos

Execute o script que processa todos os exemplos:

```bash
cd /home/rdmdelboni/Work/Gits/sds_matrix
source venv/bin/activate

python scripts/process_examples.py
```

Este script:
- ✅ Processa todos os PDFs da pasta `examples/`
- ✅ Usa Ollama para extração
- ✅ Salva resultados no banco DuckDB
- ✅ Mostra estatísticas ao final

---

## 🔍 Método 5: Teste Manual com Curl (Ollama Direto)

Teste o Ollama diretamente sem a aplicação:

```bash
# 1. Verificar modelos disponíveis
curl http://127.0.0.1:11434/api/tags | jq

# 2. Testar geração simples
curl http://127.0.0.1:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Extraia o nome do produto desta FDS: ÁCIDO SULFÚRICO 98%",
  "stream": false
}' | jq

# 3. Testar via API OpenAI-compatible (como a aplicação usa)
curl http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {
        "role": "system",
        "content": "Você é um assistente especialista em FDS."
      },
      {
        "role": "user",
        "content": "Qual o número CAS do ácido sulfúrico?"
      }
    ],
    "temperature": 0.1,
    "max_tokens": 100
  }' | jq
```

---

## 🐛 Método 6: Teste com Modo Debug

Execute com logs detalhados:

```bash
cd /home/rdmdelboni/Work/Gits/sds_matrix
source venv/bin/activate

# Definir nível de log como DEBUG
export LOG_LEVEL=DEBUG

# Executar aplicação
python main.py
```

Agora você verá logs detalhados de cada chamada ao Ollama:
```
DEBUG - Consulting LLM for nome_produto
DEBUG - LLM response for nome_produto: {"value": "...", "confidence": 0.9}
```

---

## ✅ Checklist de Validação

Após testar, verifique se:

- [ ] ✅ Ollama está respondendo em `http://127.0.0.1:11434`
- [ ] ✅ Modelo `llama3.1:8b` está disponível
- [ ] ✅ Aplicação conecta com sucesso (mensagem "LLM local conectado")
- [ ] ✅ PDFs podem ser carregados da pasta `examples/`
- [ ] ✅ Processamento extrai campos corretamente
- [ ] ✅ Validações ONU/CAS funcionam (✓/✗)
- [ ] ✅ Resultados aparecem na aba "Resultados"
- [ ] ✅ Exportação CSV/Excel funciona

---

## 📊 Comparando Resultados: Local vs Online

Para testar a diferença entre Ollama (local) e Gemini (online):

1. **Processar com Ollama (modo online + sem API Gemini):**
   - Processe um PDF normalmente
   - Anote os resultados

2. **Processar com heurísticas (modo local):**
   - Clique com botão direito no arquivo
   - Selecione **"Alterar modo para local"**
   - Reprocesse
   - Compare os resultados

3. **Processar com Gemini (se tiver API key):**
   - Configure `GOOGLE_API_KEY` no `.env`
   - Processe novamente
   - Compare qualidade e velocidade

---

## 🎯 Casos de Teste Sugeridos

### Teste 1: Extração Básica
- **Arquivo:** `7HF_FDS_Portugues.pdf`
- **Objetivo:** Verificar extração de campos principais
- **Campos esperados:** Nome, Fabricante, Números ONU/CAS

### Teste 2: Validação de Números
- **Arquivo:** Ambos PDFs
- **Objetivo:** Verificar validações ✓/✗
- **Verificar:** Formato correto de ONU (4 dígitos) e CAS (XXX-XX-X)

### Teste 3: Performance
- **Ação:** Processar os 2 PDFs simultaneamente
- **Objetivo:** Medir tempo de processamento
- **Métrica:** Tempo total e por arquivo

### Teste 4: Robustez
- **Ação:** Processar PDF corrompido ou texto incompleto
- **Objetivo:** Verificar tratamento de erros
- **Esperado:** Mensagens de erro claras, aplicação não trava

---

## 🚀 Próximos Passos

Após validar o funcionamento básico:

1. **Ajustar parâmetros** (temperatura, max_tokens) para melhor qualidade
2. **Testar outros modelos** Ollama (llama3.2, mistral, etc.)
3. **Comparar performance** entre diferentes modelos
4. **Criar testes automatizados** para CI/CD
5. **Documentar casos de uso** específicos da sua empresa

---

## 💡 Dicas

- 🔥 **Ollama é mais rápido** para testes iterativos
- 🌐 **Gemini tem melhor qualidade** para campos complexos
- 🎯 **Modo local (heurísticas)** é instantâneo mas menos preciso
- 📊 **Compare sempre os 3 modos** para encontrar o melhor para seu caso

---

## ❓ Troubleshooting

### Problema: "LLM local não respondeu"
```bash
# Iniciar Ollama se não estiver rodando
ollama serve

# Ou verificar se já está rodando
pgrep -fl ollama
```

### Problema: "Model not found"
```bash
# Baixar o modelo
ollama pull llama3.1:8b

# Verificar modelos instalados
ollama list
```

### Problema: Extração retorna "NAO ENCONTRADO"
- Verifique se o PDF tem texto extraível (não é imagem pura)
- Tente aumentar `max_tokens` para respostas mais longas
- Ajuste a `temperature` (0.1 = mais focado, 0.7 = mais criativo)

---

**Boa sorte com os testes! 🎉**

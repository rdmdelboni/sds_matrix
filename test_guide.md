# Guia de Teste - FDS Extractor com Ollama

## Teste Completo via Interface Gráfica

### 1. Inicie a aplicação:
```bash
cd /home/rdmdelboni/Work/Gits/sds_matrix
./run.sh
```

### 2. Verifique a conexão:
- Na aba "Setup", procure a mensagem: **"LLM local conectado."**
- Se aparecer "LLM local não respondeu", o Ollama não está rodando

### 3. Selecione os PDFs de exemplo:
- Clique em **"Selecionar pasta"**
- Navegue até: `/home/rdmdelboni/Work/Gits/sds_matrix/examples`
- Você verá 3 PDFs listados:
  - 7HF_FDS_Portugues.pdf (226 KB)
  - 841578_SDS_BR_Z9.PDF (306 KB)
  - FDS-OEM-ADVANCED-05-PRONTO-PARA-USO.pdf (359 KB)

### 4. Adicione à fila:
- Clique em **"Adicionar à fila"**
- Vá para a aba **"Processamento"**

### 5. Processe com modo LOCAL (Ollama):
- Na aba "Processamento", os arquivos terão modo "online" por padrão
- **Clique com botão direito** em um arquivo
- Selecione: **"Alterar modo para local"**
- Clique em **"Processar fila"**

### 6. Observe o processamento:
- Uma barra de progresso aparecerá
- O status mudará de "pending" → "processing" → "success"
- Você verá os campos sendo extraídos em tempo real

### 7. Veja os resultados:
- Vá para a aba **"Resultados"**
- Clique em **"Atualizar"**
- Verifique os dados extraídos:
  - Nome do Produto
  - Fabricante
  - Número ONU (com validação)
  - Número CAS (com validação)
  - Classificação ONU
  - Grupo de Embalagem
  - Incompatibilidades


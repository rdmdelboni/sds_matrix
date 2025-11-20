#!/usr/bin/env python3
"""Script rápido para testar extração com Ollama."""

from pathlib import Path
from src.core.llm_client import LMStudioClient
from src.extractors.pdf_extractor import PDFExtractor

def test_ollama_connection():
    """Testa conexão com Ollama."""
    print("🔌 Testando conexão com Ollama...")
    client = LMStudioClient()
    
    print(f"   Endpoint: {client.config['base_url']}")
    print(f"   Modelo: {client.config['model']}")
    
    if client.test_connection():
        print("   ✅ Ollama conectado com sucesso!")
        return True
    else:
        print("   ❌ Ollama não respondeu")
        return False

def test_pdf_extraction():
    """Testa extração de um PDF de exemplo."""
    print("\n📄 Testando extração de PDF...")
    
    # Usar o PDF menor para teste rápido
    pdf_path = Path("examples/7HF_FDS_Portugues.pdf")
    
    if not pdf_path.exists():
        print(f"   ❌ PDF não encontrado: {pdf_path}")
        return
    
    print(f"   Arquivo: {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")
    
    # Extrair texto do PDF
    extractor = PDFExtractor()
    payload = extractor.extract(pdf_path)
    text = payload.get("text")
    
    if text:
        print(f"   ✅ Texto extraído: {len(text)} caracteres")
        print(f"   Preview: {text[:200]}...")
    else:
        print("   ❌ Falha ao extrair texto")

def test_llm_extraction():
    """Testa extração de campo com LLM."""
    print("\n🤖 Testando extração com Ollama...")
    
    client = LMStudioClient()
    
    # Prompt simples para teste
    prompt = """
Analise o seguinte texto e extraia o nome do produto químico:

"FICHA DE INFORMAÇÕES DE SEGURANÇA DE PRODUTO QUÍMICO
Nome do Produto: ÁCIDO SULFÚRICO CONCENTRADO 98%
Fabricante: Química Industrial Ltda"

Responda APENAS em formato JSON:
{"value": "nome_do_produto", "confidence": 0.9, "context": "onde_encontrou"}
"""
    
    print("   Enviando prompt para o modelo...")
    result = client.extract_field(
        field_name="nome_produto_teste",
        prompt_template=prompt
    )
    
    print(f"\n   📊 Resultado:")
    print(f"      Valor: {result.get('value', 'N/A')}")
    print(f"      Confiança: {result.get('confidence', 0)}")
    print(f"      Contexto: {result.get('context', 'N/A')}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTE RÁPIDO - FDS Extractor + Ollama")
    print("=" * 60)
    
    # Teste 1: Conexão
    if not test_ollama_connection():
        print("\n⚠️  Certifique-se que o Ollama está rodando:")
        print("   ollama serve")
        exit(1)
    
    # Teste 2: Extração de PDF
    test_pdf_extraction()
    
    # Teste 3: Extração com LLM
    test_llm_extraction()
    
    print("\n" + "=" * 60)
    print("✅ Testes concluídos!")
    print("=" * 60)
    print("\n💡 Para testar na interface gráfica:")
    print("   ./run.sh")

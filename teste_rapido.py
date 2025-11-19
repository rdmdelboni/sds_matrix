#!/usr/bin/env python3
"""
Script de teste rápido para verificar a configuração agressiva.
Execute antes de processar grandes volumes.
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_env_config():
    """Testa se as variáveis de ambiente estão corretas."""
    print("\n" + "="*60)
    print("🔍 VERIFICANDO CONFIGURAÇÃO DO .ENV")
    print("="*60)

    from src.utils.config import (
        MAX_WORKERS,
        CHUNK_SIZE,
        LM_STUDIO_CONFIG,
        ONLINE_SEARCH_PROVIDER,
    )

    lm_model = LM_STUDIO_CONFIG["model"]

    print(f"✅ MAX_WORKERS: {MAX_WORKERS}")
    print(f"✅ CHUNK_SIZE: {CHUNK_SIZE}")
    print(f"✅ LM_STUDIO_MODEL: {lm_model}")
    print(f"✅ ONLINE_SEARCH_PROVIDER: {ONLINE_SEARCH_PROVIDER}")

    # Validações
    if MAX_WORKERS < 16:
        print(f"⚠️  MAX_WORKERS é {MAX_WORKERS}, recomendado: 16")

    if CHUNK_SIZE != 2000:
        print(f"⚠️  CHUNK_SIZE é {CHUNK_SIZE}, recomendado: 2000")

    if lm_model != "phi3:mini":
        print(f"⚠️  Modelo é {lm_model}, recomendado: phi3:mini")

    print("\n✅ Configuração do .env carregada!")
    return True


def test_ollama_connection():
    """Testa conexão com Ollama e modelo phi3:mini."""
    print("\n" + "="*60)
    print("🔌 TESTANDO CONEXÃO COM OLLAMA")
    print("="*60)

    import subprocess

    try:
        # Verificar se Ollama está rodando
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            print("❌ Ollama não está respondendo")
            print("   Execute: ollama serve")
            return False

        # Verificar se phi3:mini está instalado
        if "phi3:mini" not in result.stdout:
            print("❌ Modelo phi3:mini não encontrado")
            print("   Execute: ollama pull phi3:mini")
            return False

        print("✅ Ollama está rodando")
        print("✅ Modelo phi3:mini está disponível")

        # Testar uma inferência rápida
        print("\n⚡ Testando inferência com phi3:mini...")
        from src.core.llm_client import LMStudioClient

        client = LMStudioClient()
        if client.test_connection():
            print("✅ Inferência funcionando corretamente!")
            return True
        else:
            print("⚠️  Conexão OK mas inferência falhou")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Timeout ao conectar com Ollama")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_cpu_cores():
    """Verifica número de cores disponíveis."""
    print("\n" + "="*60)
    print("💻 VERIFICANDO RECURSOS DO SISTEMA")
    print("="*60)

    import multiprocessing

    cores = multiprocessing.cpu_count()
    print(f"✅ CPUs disponíveis: {cores}")

    if cores < 16:
        print(f"⚠️  Você tem menos de 16 cores ({cores})")
        print(f"   Recomendado ajustar MAX_WORKERS para {cores}")
    else:
        print("✅ Hardware adequado para configuração agressiva!")

    return True


def test_database():
    """Testa conexão com banco de dados DuckDB."""
    print("\n" + "="*60)
    print("🗄️  TESTANDO BANCO DE DADOS")
    print("="*60)

    try:
        from src.database.duckdb_manager import DuckDBManager

        db = DuckDBManager()
        print("✅ Banco de dados conectado com sucesso")

        # Tentar buscar registros existentes
        try:
            results = db.get_all()
            print(f"📊 Registros já processados: {len(results)}")
        except:
            print("📊 Banco de dados vazio ou sem registros")

        return True
    except Exception as e:
        print(f"❌ Erro ao conectar com banco: {e}")
        return False


def main():
    """Executa todos os testes."""
    print("\n" + "🚀 "+"="*58 + "🚀")
    print("   TESTE RÁPIDO - CONFIGURAÇÃO AGRESSIVA FDS EXTRACTOR")
    print("🚀 "+"="*58 + "🚀")

    results = []

    # Executar testes
    results.append(("Configuração .env", test_env_config()))
    results.append(("CPU/Cores", test_cpu_cores()))
    results.append(("Banco de Dados", test_database()))
    results.append(("Ollama + phi3:mini", test_ollama_connection()))

    # Resumo
    print("\n" + "="*60)
    print("📋 RESUMO DOS TESTES")
    print("="*60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Seu sistema está pronto para processar em alta velocidade!")
        print("\n💡 Próximo passo: Execute 'python main.py' e processe seus arquivos")
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
        print("📝 Revise as mensagens de erro acima e corrija os problemas")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

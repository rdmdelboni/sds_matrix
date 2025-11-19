#!/usr/bin/env python3
"""
Script de benchmark para testar performance de processamento em lote.
Use este script para encontrar a configuração ótima para seu hardware.
"""

import os
import sys
import time
from pathlib import Path
from typing import List

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def benchmark_configuration(folder: Path, max_files: int = 10, workers: int = 2) -> dict:
    """
    Executa benchmark com uma configuração específica.

    Args:
        folder: Pasta com arquivos FDS
        max_files: Número máximo de arquivos para testar
        workers: Número de workers paralelos

    Returns:
        Dicionário com estatísticas de performance
    """
    from src.utils.file_utils import list_supported_files
    from src.core.document_processor import DocumentProcessor, DEFAULT_FIELDS, ADDITIONAL_FIELDS
    from src.core.llm_client import LMStudioClient, GeminiClient
    from src.database.duckdb_manager import DuckDBManager
    from src.core.chunk_strategy import ChunkStrategy
    from src.core.queue_manager import ProcessingQueue
    from src.utils.config import ONLINE_SEARCH_PROVIDER

    print(f"\n{'='*60}")
    print(f"🔬 BENCHMARK: {workers} worker(s)")
    print(f"{'='*60}\n")

    # Configurar componentes
    db_manager = DuckDBManager()
    llm_client = LMStudioClient()
    gemini_client = GeminiClient() if ONLINE_SEARCH_PROVIDER.lower() == "gemini" else None

    processor = DocumentProcessor(
        db_manager=db_manager,
        llm_client=llm_client,
        online_search_client=gemini_client,
        chunk_strategy=ChunkStrategy(),
        fields=[*DEFAULT_FIELDS, *ADDITIONAL_FIELDS],
    )

    # Listar arquivos
    print(f"📂 Procurando arquivos em: {folder}")
    files = list_supported_files(folder, recursive=True)

    if not files:
        print("❌ Nenhum arquivo encontrado!")
        return {}

    # Limitar número de arquivos
    test_files = files[:max_files]
    print(f"📊 Testando com {len(test_files)} arquivo(s)\n")

    # Estatísticas
    processed = 0
    failed = 0
    times: List[float] = []

    def on_started(_, file_path: Path):
        print(f"⚡ Processando: {file_path.name}")

    def on_finished(_, file_path: Path):
        nonlocal processed
        processed += 1
        elapsed = time.time() - start_time
        avg_time = elapsed / processed
        remaining = len(test_files) - processed
        eta = avg_time * remaining

        print(f"✅ Concluído: {file_path.name} ({processed}/{len(test_files)})")
        print(f"   ⏱️  Tempo médio: {avg_time:.2f}s/arquivo | ETA: {eta:.1f}s")

    def on_failed(file_path: Path, exc: Exception):
        nonlocal failed
        failed += 1
        print(f"❌ Erro: {file_path.name} - {exc}")

    # Criar fila de processamento
    queue = ProcessingQueue(
        processor=processor,
        workers=workers,
        on_started=on_started,
        on_finished=on_finished,
        on_failed=on_failed,
    )
    queue.start()

    # Iniciar processamento
    start_time = time.time()
    for file_path in test_files:
        queue.enqueue(file_path, mode="online")

    # Aguardar conclusão
    queue._queue.join()
    end_time = time.time()

    # Calcular estatísticas
    total_time = end_time - start_time
    avg_time = total_time / len(test_files) if test_files else 0
    throughput = len(test_files) / total_time if total_time > 0 else 0

    # Parar fila
    queue.stop()

    # Resultados
    results = {
        "workers": workers,
        "total_files": len(test_files),
        "processed": processed,
        "failed": failed,
        "total_time": total_time,
        "avg_time_per_file": avg_time,
        "throughput": throughput,  # arquivos/segundo
    }

    print(f"\n{'='*60}")
    print(f"📊 RESULTADOS: {workers} worker(s)")
    print(f"{'='*60}")
    print(f"✅ Processados: {processed}/{len(test_files)}")
    print(f"❌ Falhas: {failed}")
    print(f"⏱️  Tempo total: {total_time:.2f}s ({total_time/60:.2f} min)")
    print(f"⚡ Tempo médio: {avg_time:.2f}s por arquivo")
    print(f"🚀 Throughput: {throughput:.2f} arquivos/segundo")
    print(f"📈 Projeção para 500 arquivos: {(500 * avg_time)/60:.1f} minutos")
    print(f"{'='*60}\n")

    return results


def compare_configurations(folder: Path, max_files: int = 10):
    """
    Compara diferentes configurações de workers.

    Args:
        folder: Pasta com arquivos FDS
        max_files: Número máximo de arquivos para testar
    """
    configurations = [1, 2, 4, 6, 8]
    results = []

    print("\n" + "="*60)
    print("🎯 COMPARAÇÃO DE CONFIGURAÇÕES")
    print("="*60)
    print(f"📂 Pasta: {folder}")
    print(f"📊 Arquivos de teste: {max_files}")
    print(f"🔧 Configurações: {configurations} workers")
    print("="*60)

    for workers in configurations:
        try:
            result = benchmark_configuration(folder, max_files, workers)
            results.append(result)
            time.sleep(2)  # Pausa entre testes
        except KeyboardInterrupt:
            print("\n⚠️  Benchmark interrompido pelo usuário")
            break
        except Exception as e:
            print(f"\n❌ Erro ao testar {workers} workers: {e}")
            continue

    if not results:
        print("\n❌ Nenhum resultado para comparar")
        return

    # Tabela comparativa
    print("\n" + "="*80)
    print("📊 TABELA COMPARATIVA")
    print("="*80)
    print(f"{'Workers':<10} {'Tempo Total':<15} {'Tempo/Arq':<15} {'Throughput':<15} {'500 arquivos':<15}")
    print("-"*80)

    for r in results:
        print(
            f"{r['workers']:<10} "
            f"{r['total_time']:.2f}s{'':<10} "
            f"{r['avg_time_per_file']:.2f}s{'':<10} "
            f"{r['throughput']:.2f} arq/s{'':<7} "
            f"{(500 * r['avg_time_per_file'])/60:.1f} min"
        )

    print("="*80)

    # Melhor configuração
    best = min(results, key=lambda x: x['avg_time_per_file'])
    print(f"\n🏆 MELHOR CONFIGURAÇÃO: {best['workers']} workers")
    print(f"   ⏱️  Tempo médio: {best['avg_time_per_file']:.2f}s por arquivo")
    print(f"   📈 Projeção 500 arquivos: {(500 * best['avg_time_per_file'])/60:.1f} minutos")
    print()


def main():
    """Função principal do benchmark."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark de performance do FDS Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Teste rápido com 5 arquivos, 4 workers
  python benchmark_performance.py /caminho/pasta --files 5 --workers 4

  # Comparar diferentes configurações
  python benchmark_performance.py /caminho/pasta --compare --files 10

  # Teste completo com 50 arquivos
  python benchmark_performance.py /caminho/pasta --files 50 --workers 8
        """
    )

    parser.add_argument(
        "folder",
        type=str,
        help="Pasta contendo arquivos FDS para teste"
    )
    parser.add_argument(
        "--files",
        type=int,
        default=10,
        help="Número de arquivos para teste (padrão: 10)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Número de workers paralelos (padrão: 2)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Comparar múltiplas configurações de workers"
    )

    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"❌ Pasta não encontrada: {folder}")
        sys.exit(1)

    print("\n" + "="*60)
    print("🚀 FDS EXTRACTOR - BENCHMARK DE PERFORMANCE")
    print("="*60)

    if args.compare:
        compare_configurations(folder, args.files)
    else:
        benchmark_configuration(folder, args.files, args.workers)

    print("\n✅ Benchmark concluído!")
    print("\n💡 Dica: Use a configuração com melhor throughput no seu .env:")
    print("   MAX_WORKERS=<número_ideal>")
    print()


if __name__ == "__main__":
    main()

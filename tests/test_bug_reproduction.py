
from src.core.heuristics import HeuristicExtractor

class TestBugReproduction:
    def test_year_false_positive(self):
        """Test that years (e.g., 2024) are not extracted as ONU numbers when a valid ONU exists later."""
        extractor = HeuristicExtractor()
        text = """
        FDS (FICHA DE DADOS DE SEGURANÇA)
        Data de preparação: 03/04/2024
        Versão: 5.0
        
        SEÇÃO 14: INFORMAÇÕES SOBRE TRANSPORTE
        Número ONU: 1075
        """
        result = extractor._extract_numero_onu(text, None)
        
        assert result is not None
        # The bug is that it picks 2024 instead of 1075
        assert result["value"] == "1075", f"Expected 1075, got {result['value']}"

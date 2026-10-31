"""
Módulo de Integração Econômica CEPEA / Mercado Brasileiro - Fazenda Campo Dourado (GO)
Centro de Estudos Avançados em Economia Aplicada (CEPEA - ESALQ/USP) & CNA/Senar

Fornece cotações de mercado e conversões de unidades comerciais (R$/saca, R$/tonelada, R$/kg MN)
para a base oficial do simulador RuFaS (R$/kg de Matéria Seca - MS).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class CepeaFeedQuote:
    feed_id: int
    name: str
    category: str
    raw_unit: str             # ex: "R$/saca_60kg", "R$/t_MN", "R$/kg_MN"
    raw_price: float          # Preço nominal de mercado em moeda corrente (R$)
    dry_matter_pct: float     # Teor de Matéria Seca (% MS)
    price_per_kg_dm: float    # Preço convertido para R$/kg de Matéria Seca
    source: str               # Fonte da cotação (CEPEA, CNA/Senar, MF Rural)
    historical_std_pct: float = 0.15  # Volatilidade histórica para análise estocástica


class CepeaCampoDouradoProvider:
    """
    Provedor de dados econômicos para o cenário da Fazenda Campo Dourado (Goiás).
    """

    # Cotações Oficiais consolidadas da planilha 'ingredientes_racoes_GO_campo_dourado.xlsx' (28/10/2026)
    OFFICIAL_MARKET_QUOTES: Dict[int, Dict[str, Any]] = {
        18: {
            "name": "Feno de Bermudagrass (Tifton e Jiggs)",
            "category": "Forragem",
            "raw_unit": "R$/kg_MN",
            "raw_price": 1.70,
            "dry_matter_pct": 93.37,
            "source": "MF Rural - Anúncio Feno Tifton e Jiggs",
            "historical_std_pct": 0.12,
        },
        23: {
            "name": "Farinha de Sangue (Blood meal, low dRUP)",
            "category": "Concentrado Proteico",
            "raw_unit": "R$/kg_MS",
            "raw_price": 999.00,
            "dry_matter_pct": 90.86,
            "source": "Proibida para Ruminantes no Brasil (IN MAPA nº 8/2004) - Custo penalizado",
            "historical_std_pct": 0.00,
        },
        44: {
            "name": "Milho Grão Moído Seco",
            "category": "Concentrado Energético",
            "raw_unit": "R$/saca_60kg",
            "raw_price": 64.73,
            "dry_matter_pct": 86.91,
            "source": "CEPEA/ESALQ - Indicador do Milho BM&FBOVESPA (28/10/2026)",
            "historical_std_pct": 0.18,
        },
        51: {
            "name": "Silagem de Milho (Meia Maturação)",
            "category": "Forragem",
            "raw_unit": "R$/t_MN",
            "raw_price": 247.08,
            "dry_matter_pct": 35.36,
            "source": "CNA/Senar + Cepea-Esalq - Projeto Campo Futuro Leite GO (Safra 25/26)",
            "historical_std_pct": 0.10,
        },
        94: {
            "name": "Mistura Capim-Leguminosa (Feno)",
            "category": "Forragem",
            "raw_unit": "R$/t_MN",
            "raw_price": 2250.00,
            "dry_matter_pct": 89.24,
            "source": "MF Rural - Cotação Feno Tifton e Alfafa Premium",
            "historical_std_pct": 0.14,
        },
        100: {
            "name": "Mistura Capim-Leguminosa (Silagem)",
            "category": "Forragem",
            "raw_unit": "R$/t_MN",
            "raw_price": 1100.00,
            "dry_matter_pct": 40.02,
            "source": "MF Rural - Feno Tifton 85 Pré-Secado Luziânia/GO",
            "historical_std_pct": 0.15,
        },
        110: {
            "name": "Leguminosa Forrageira (Silagem)",
            "category": "Forragem",
            "raw_unit": "R$/t_MN",
            "raw_price": 1100.00,
            "dry_matter_pct": 42.88,
            "source": "MF Rural - Silagem Pré-Secada Luziânia/GO",
            "historical_std_pct": 0.15,
        },
        176: {
            "name": "Sudan Grass (Silagem Madura)",
            "category": "Forragem",
            "raw_unit": "R$/t_MN",
            "raw_price": 247.08,
            "dry_matter_pct": 31.47,
            "source": "CNA/Senar + Cepea-Esalq - Custo de Silagem Centro-Oeste",
            "historical_std_pct": 0.12,
        },
        202: {
            "name": "Leite Integral (Lote Bezerros)",
            "category": "Leite Líquido",
            "raw_unit": "R$/litro",
            "raw_price": 2.9692,
            "dry_matter_pct": 12.50,
            "source": "CEPEA/ESALQ - Preço do Leite ao Produtor Goiás (ago-out/2026)",
            "historical_std_pct": 0.11,
        },
        216: {
            "name": "Starter 18CP High Starch (Bezerros)",
            "category": "Concentrado Inicial",
            "raw_unit": "R$/saco_40kg",
            "raw_price": 100.53,
            "dry_matter_pct": 88.00,
            "source": "Cooperativa Cocamar - Ração Comercial Bezerro 20% PB",
            "historical_std_pct": 0.10,
        },
        301: {
            "name": "Premix Mineral/Vitamínico Lactação",
            "category": "Suplemento Mineral",
            "raw_unit": "R$/saco_25kg",
            "raw_price": 305.60,
            "dry_matter_pct": 99.46,
            "source": "Compras Públicas / UFMA Pregão nº 90032 - Mineral Lactação",
            "historical_std_pct": 0.08,
        },
        303: {
            "name": "Blend de Subprodutos (DDGS de Milho)",
            "category": "Concentrado Proteico",
            "raw_unit": "R$/t_MN",
            "raw_price": 901.11,
            "dry_matter_pct": 74.11,
            "source": "MF Rural - DDGS de Milho Granel Centro-Oeste (Mediana de Anúncios)",
            "historical_std_pct": 0.16,
        },
    }

    # Preço oficial do Leite ao Produtor no Estado de Goiás (CEPEA)
    LEITE_GOIAS_CEPEA = 2.9692  # R$/litro

    @classmethod
    def converter_para_kg_ms(cls, raw_price: float, raw_unit: str, dm_pct: float) -> float:
        """Converte a cotação comercial nominal para R$/kg de Matéria Seca."""
        dm_frac = dm_pct / 100.0
        if raw_unit == "R$/saca_60kg":
            preco_kg_mn = raw_price / 60.0
        elif raw_unit == "R$/saco_40kg":
            preco_kg_mn = raw_price / 40.0
        elif raw_unit == "R$/saco_25kg":
            preco_kg_mn = raw_price / 25.0
        elif raw_unit in ("R$/t_MN", "R$/tonelada"):
            preco_kg_mn = raw_price / 1000.0
        elif raw_unit in ("R$/kg_MN", "R$/kg"):
            preco_kg_mn = raw_price
        elif raw_unit == "R$/litro":
            # Densidade aproximada do leite: 1.032 kg/L -> R$/kg MN = R$/L / 1.032
            # Na planilha oficial: R$ 2,9692 / kg MN diretamente
            preco_kg_mn = raw_price
        elif raw_unit == "R$/kg_MS":
            return round(raw_price, 4)
        else:
            raise ValueError(f"Unidade não suportada: {raw_unit}")

        return round(preco_kg_mn / dm_frac, 4)

    @classmethod
    def get_cotacoes_campo_dourado(cls, overrides: Optional[Dict[int, float]] = None) -> Dict[int, CepeaFeedQuote]:
        """Retorna cotações completas indexadas por feed_id."""
        quotes = {}
        for fid, item in cls.OFFICIAL_MARKET_QUOTES.items():
            raw_p = item["raw_price"]
            if overrides and fid in overrides:
                raw_p = overrides[fid]

            p_ms = cls.converter_para_kg_ms(raw_p, item["raw_unit"], item["dry_matter_pct"])

            quotes[fid] = CepeaFeedQuote(
                feed_id=fid,
                name=item["name"],
                category=item["category"],
                raw_unit=item["raw_unit"],
                raw_price=raw_p,
                dry_matter_pct=item["dry_matter_pct"],
                price_per_kg_dm=p_ms,
                source=item["source"],
                historical_std_pct=item.get("historical_std_pct", 0.15),
            )
        return quotes

    @classmethod
    def calcular_iofc_vaca(cls, custo_diario_dieta: float, producao_leite_litros: float = 30.0) -> Dict[str, float]:
        """
        Calcula o IOFC (Income Over Feed Cost / Receita Menos Custo com Alimentação)
        usando o preço oficial de leite do CEPEA para Goiás.
        """
        receita_leite = producao_leite_litros * cls.LEITE_GOIAS_CEPEA
        iofc = receita_leite - custo_diario_dieta
        margem_pct = (iofc / receita_leite) * 100.0 if receita_leite > 0 else 0.0

        return {
            "producao_leite_litros": producao_leite_litros,
            "preco_leite_cepea_go": cls.LEITE_GOIAS_CEPEA,
            "receita_leite_diaria_rs": round(receita_leite, 2),
            "custo_dieta_diaria_rs": round(custo_diario_dieta, 2),
            "iofc_diario_rs": round(iofc, 2),
            "margem_alimentar_pct": round(margem_pct, 1),
        }


if __name__ == "__main__":
    quotes = CepeaCampoDouradoProvider.get_cotacoes_campo_dourado()
    print("=" * 85)
    print(" COTAÇÕES CEPEA / MERCADO BRASIL — FAZENDA CAMPO DOURADO (GO_campo_dourado)")
    print("=" * 85)
    print(f"{'ID':<4} {'Alimento':<35} {'Unidade':<12} {'Cotação':>10} {'% MS':>6} {'R$/kg MS':>10}")
    print("-" * 85)
    for fid, q in quotes.items():
        print(f"{q.feed_id:<4} {q.name[:34]:<35} {q.raw_unit:<12} R$ {q.raw_price:>7.2f} {q.dry_matter_pct:>5.1f}% R$ {q.price_per_kg_dm:>7.4f}")
    print("=" * 85)

    iofc = CepeaCampoDouradoProvider.calcular_iofc_vaca(custo_diario_dieta=25.0107, producao_leite_litros=30.0)
    print(f"\nIndicador de Leite CEPEA Goiás: R$ {iofc['preco_leite_cepea_go']:.4f}/litro")
    print(f"Receita Diária (30 L/vaca): R$ {iofc['receita_leite_diaria_rs']:.2f}")
    print(f"Custo Alimentar Diário: R$ {iofc['custo_dieta_diaria_rs']:.2f}")
    print(f"IOFC (Margem Diária sobre a Alimentação): R$ {iofc['iofc_diario_rs']:.2f}/vaca/dia ({iofc['margem_alimentar_pct']}%)")

"""
Gerador de Gráficos e Figuras Científicas - Otimização Simplex Fazenda Campo Dourado
Gera figuras em alta resolução (300 DPI) para inserção nos relatórios (MD, DOCX e PDF).
"""

from __future__ import annotations

import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

WORKSPACE_DIR = Path(__file__).resolve().parents[1]
FIG_DIR = WORKSPACE_DIR / "campo_dourado" / "figuras"
FIG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = WORKSPACE_DIR / "campo_dourado" / "resultados"

# Configuração de estilo visual acadêmico limpo
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "figure.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
})


def gerar_grafico_composicao_dieta():
    """Figura 1: Composição e Custo da Dieta Ótima."""
    labels = ["Silagem de Milho (x51)", "DDGS / Blend (x303)", "Premix Mineral (x301)"]
    kg_ms = [19.7374, 6.6039, 0.2594]
    custo_rs = [13.7925, 8.0296, 3.1885]
    colors = ["#2E7D32", "#E65100", "#1565C0"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))

    # Gráfico de Pizza: Matéria Seca
    wedges, texts, autotexts = ax1.pie(
        kg_ms,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        colors=colors,
        explode=(0.04, 0.04, 0.1),
        textprops=dict(color="black"),
    )
    for at in autotexts:
        at.set_weight("bold")
    ax1.set_title("A) Participação na Matéria Seca (% MS)\nTotal: 26,60 kg MS/dia", pad=10)

    # Gráfico de Barras: Custo Econômico Diário
    bars = ax2.bar(labels, custo_rs, color=colors, width=0.55, edgecolor="black", alpha=0.85)
    for bar in bars:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.3, f"R$ {yval:.2f}", ha="center", va="bottom", weight="bold")

    ax2.set_ylabel("Custo Diário (R$ / vaca / dia)")
    ax2.set_title("B) Decomposição do Custo Diário\nCusto Mínimo Total Z* = R$ 25,01/dia", pad=10)
    ax2.set_ylim(0, 16)
    ax2.set_xticklabels(["Silagem de Milho", "DDGS (Proteico)", "Premix Mineral"], rotation=15)

    plt.tight_layout()
    output_path = FIG_DIR / "fig1_composicao_dieta.png"
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Salvo: {output_path}")


def gerar_grafico_sensibilidade_milho():
    """Figura 2: Sensibilidade ao Preço do Milho e Ponto de Virada."""
    csv_file = RESULTS_DIR / "cenario_1_sensibilidade_milho.csv"
    if not csv_file.exists():
        from campo_dourado.sensibilidade_campo_dourado import cenario_1_preco_milho
        cenario_1_preco_milho()

    df = pd.read_csv(csv_file)

    fig, ax1 = plt.subplots(figsize=(9, 5.5))

    color_custo = "#C62828"
    color_milho = "#1565C0"

    x_vals = df["preco_milho_rs_kg"].to_numpy()
    y_custo = df["custo_diario_rs"].to_numpy()
    y_milho = df["milho_kg"].to_numpy()

    # Eixo 1: Custo Diário Total
    ax1.set_xlabel("Preço do Milho Moído (R$ / kg MS)")
    ax1.set_ylabel("Custo Diário da Dieta (R$ / vaca / dia)", color=color_custo)
    line1 = ax1.plot(x_vals, y_custo, color=color_custo, marker="o", linewidth=2.2, label="Custo Diário (Z*)")
    ax1.tick_params(axis="y", labelcolor=color_custo)

    # Destaque do limiar analítico do Simplex
    ax1.axvline(x=0.7367, color="black", linestyle=":", linewidth=1.8, label="Limiar Simplex (R$ 0,7367)")
    ax1.axvline(x=1.2413, color="#2E7D32", linestyle="--", linewidth=1.5, label="Preço Atual CEPEA (R$ 1,2413)")

    # Eixo 2: Inclusão do Milho
    ax2 = ax1.twinx()
    ax2.set_ylabel("Inclusão de Milho na Ração (kg MS/dia)", color=color_milho)
    line2 = ax2.plot(x_vals, y_milho, color=color_milho, marker="s", linestyle="--", linewidth=2.0, label="Consumo de Milho")
    ax2.tick_params(axis="y", labelcolor=color_milho)
    ax2.set_ylim(-0.5, 16)

    # Anotação pedagógica
    ax1.annotate(
        "Ponto de Troca de Base\n(Milho entra na dieta abaixo de R$ 0,7367)",
        xy=(0.7367, 25.0107),
        xytext=(0.95, 23.2),
        arrowprops=dict(facecolor="black", shrink=0.05, width=1.2, headwidth=6),
        bbox=dict(boxstyle="round,pad=0.4", fc="#FFF9C4", ec="#FBC02D"),
        fontsize=9.5,
    )

    lines = line1 + line2 + [ax1.get_lines()[1], ax1.get_lines()[2]]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right", framealpha=0.9)

    plt.title("Sensibilidade Econômica ao Preço do Milho Moído (x44)\nIdentificação Analítica do Ponto de Bifurcação da Base Ótima", pad=12)
    plt.tight_layout()
    output_path = FIG_DIR / "fig2_sensibilidade_milho.png"
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Salvo: {output_path}")


def gerar_grafico_competicao_silagens():
    """Figura 3: Competição entre Silagens."""
    csv_file = RESULTS_DIR / "cenario_2_sensibilidade_silagens.csv"
    if not csv_file.exists():
        from campo_dourado.sensibilidade_campo_dourado import cenario_2_competicao_silagens
        cenario_2_competicao_silagens()

    df = pd.read_csv(csv_file)

    fig, ax = plt.subplots(figsize=(8.5, 5))
    x_sil = df["fator_custo_silagem_milho"].to_numpy()
    y_sil = df["custo_diario_rs"].to_numpy()
    ax.plot(x_sil, y_sil, color="#2E7D32", marker="o", linewidth=2.2, label="Custo da Dieta (R$/dia)")
    ax.axvline(x=1.0, color="gray", linestyle="--", label="Caso Base (Fator 1.00 = R$ 0,6988)")

    for _, row in df.iterrows():
        ax.annotate(
            f"R$ {row['custo_diario_rs']:.2f}",
            (row["fator_custo_silagem_milho"], row["custo_diario_rs"]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=9,
        )

    ax.set_xlabel("Variação do Custo da Silagem de Milho (Fator Multiplicativo)")
    ax.set_ylabel("Custo Diário Total (R$ / vaca / dia)")
    ax.set_title("Impacto da Flutuação de Custo da Silagem de Milho (x51)\nCenário Conservador da Bacia Leiteira de Goiás", pad=12)
    ax.legend(loc="upper left")

    plt.tight_layout()
    output_path = FIG_DIR / "fig3_competicao_silagens.png"
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Salvo: {output_path}")


def gerar_grafico_buffer_fosforo():
    """Figura 4: Buffer de Fósforo e Preço-Sombra."""
    csv_file = RESULTS_DIR / "cenario_3_buffer_fosforo.csv"
    if not csv_file.exists():
        from campo_dourado.sensibilidade_campo_dourado import cenario_3_buffer_fosforo
        cenario_3_buffer_fosforo()

    df = pd.read_csv(csv_file)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8))

    x_buf = df["buffer_fosforo_pct"].to_numpy()
    y_buf = df["custo_diario_rs"].to_numpy()
    y_shadow = df["preco_sombra_p"].to_numpy()

    # Custo Diário vs Buffer
    ax1.plot(x_buf, y_buf, color="#1565C0", marker="s", linewidth=2.2)
    ax1.set_xlabel("Buffer de Segurança de Fósforo (%)")
    ax1.set_ylabel("Custo da Dieta (R$ / vaca / dia)")
    ax1.set_title("A) Custo da Dieta vs Buffer de Fósforo")
    for _, row in df.iterrows():
        ax1.annotate(f"R$ {row['custo_diario_rs']:.2f}", (row["buffer_fosforo_pct"], row["custo_diario_rs"]), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9)

    # Preço-Sombra do Fósforo
    bars = ax2.bar([f"{b}%" for b in x_buf], y_shadow, color="#E65100", width=0.5, edgecolor="black", alpha=0.85)
    for bar in bars:
        yval = bar.get_height()
        if yval > 0.001:
            ax2.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.02, f"R$ {yval:.4f}", ha="center", va="bottom", weight="bold", fontsize=9)
        else:
            ax2.text(bar.get_x() + bar.get_width() / 2.0, 0.02, "Folga (R$ 0,00)", ha="center", va="bottom", fontsize=8.5)

    ax2.set_xlabel("Buffer de Fósforo (%)")
    ax2.set_ylabel("Preço-Sombra / Dual (R$ por grama de P)")
    ax2.set_title("B) Preço-Sombra do Fósforo (Restrição Ativa)")
    ax2.set_ylim(0, 0.8)

    plt.tight_layout()
    output_path = FIG_DIR / "fig4_buffer_fosforo.png"
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Salvo: {output_path}")


def gerar_diagrama_arquitetura():
    """Figura 5: Diagrama de Arquitetura do Simplex no RuFaS."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.axis("off")

    # Caixas do diagrama
    boxes = [
        {"text": "Fazenda Campo Dourado\n(GO_campo_dourado)\n100 Vacas | Clima Goiás\nNASEM_Comp.csv (176 itens)", "x": 0.08, "y": 0.55, "w": 0.22, "h": 0.32, "color": "#E8F5E9", "ec": "#2E7D32"},
        {"text": "Cotações de Mercado\nCEPEA / ESALQ / CNA\nMilho: R$ 64,73/sc\nLeite: R$ 2,97/L\nConversão p/ R$/kg MS", "x": 0.08, "y": 0.12, "w": 0.22, "h": 0.32, "color": "#FFF3E0", "ec": "#EF6C00"},
        {"text": "Modelo Canônico de PL\nMinimizar Custo Z = c^T x\n12 Restrições NASEM\n(DMI, Energia, PM, FDN, Ca, P)", "x": 0.39, "y": 0.33, "w": 0.24, "h": 0.35, "color": "#E3F2FD", "ec": "#1565C0"},
        {"text": "TwoPhaseSimplexSolver\n(Nativo em NumPy)\n• Fase 1: Viabilidade (min W)\n• Fase 2: Custo Mínimo (min Z)\n• 20 Tableaus Didáticos\n• Preços-Sombra & Sensibilidade", "x": 0.71, "y": 0.48, "w": 0.25, "h": 0.42, "color": "#F3E5F5", "ec": "#7B1FA2"},
        {"text": "Benchmark HiGHS & RuFaS\nValidação Cruzada (1e-15)\nSimulação Biofísica 5 Anos\nIOFC = R$ 64,07/vaca/dia", "x": 0.71, "y": 0.08, "w": 0.25, "h": 0.32, "color": "#EDE7F6", "ec": "#4527A0"},
    ]

    for b in boxes:
        rect = plt.Rectangle((b["x"], b["y"]), b["w"], b["h"], facecolor=b["color"], edgecolor=b["ec"], linewidth=2, linestyle="-", transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(b["x"] + b["w"] / 2.0, b["y"] + b["h"] / 2.0, b["text"], ha="center", va="center", fontsize=9.5, transform=ax.transAxes, weight="medium")

    # Setas
    arrow_props = dict(facecolor="#37474F", edgecolor="#37474F", width=1.5, headwidth=6, shrink=0.05)
    ax.annotate("", xy=(0.39, 0.55), xytext=(0.30, 0.65), arrowprops=arrow_props)
    ax.annotate("", xy=(0.39, 0.45), xytext=(0.30, 0.30), arrowprops=arrow_props)
    ax.annotate("", xy=(0.71, 0.60), xytext=(0.63, 0.55), arrowprops=arrow_props)
    ax.annotate("", xy=(0.71, 0.30), xytext=(0.63, 0.45), arrowprops=arrow_props)

    plt.title("Arquitetura da Solução: Integração RuFaS, CEPEA e Simplex de Duas Fases", fontsize=13, weight="bold", pad=15)
    plt.tight_layout()
    output_path = FIG_DIR / "fig5_arquitetura_simplex_rufas.png"
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Salvo: {output_path}")


def gerar_todas_figuras():
    print("=== GERANDO FIGURAS CIENTÍFICAS E GRÁFICOS ===")
    gerar_grafico_composicao_dieta()
    gerar_grafico_sensibilidade_milho()
    gerar_grafico_competicao_silagens()
    gerar_grafico_buffer_fosforo()
    gerar_diagrama_arquitetura()
    print(f"Todas as figuras salvas com sucesso em: {FIG_DIR}")


if __name__ == "__main__":
    gerar_todas_figuras()

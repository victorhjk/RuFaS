# Otimização Linear e Simplex de Duas Fases — Fazenda Campo Dourado (RuFaS)

**Instituição:** Instituto Federal de Educação, Ciência e Tecnologia de Goiás (IFG)  
**Disciplina:** Modelagem e Otimização Aplicada  
**Docente:** Prof. Dr. Eduardo Noronha  
**Discente:** Victor Hugo Jesus  
**Simulador Biofísico:** RuFaS (*Ruminant Farm Systems*) | **Padrão Nutricional:** NASEM (2021)  

---

## 🎯 Visão Geral do Projeto

Este projeto desenvolve uma solução transparente, determinística e didática de **Programação Linear (PL)** baseada no **Método Simplex de Duas Fases nativo (em NumPy puro)** para a formulação de dietas de custo mínimo de ruminantes e dimensionamento bioeconômico da **Fazenda Campo Dourado (`GO_campo_dourado`)**.

Diferente da abordagem original de caixa-preta do RuFaS (baseada no algoritmo numérico `SLSQP` do SciPy), esta implementação foi concebida sob os princípios da **Pesquisa Operacional Clássica (George Dantzig, 1947)**, fornecendo rastreabilidade matricial passo a passo, cálculo analítico de preços-sombra (duais), análise de sensibilidade e integração direta com o mercado agropecuário brasileiro (**CEPEA/Esalq - USP**).

---

## 🚀 Principais Funcionalidades

1. **Solver Simplex de Duas Fases Autoral (`pure_simplex_solver.py`):**
   - Implementação independente sem dependência de bibliotecas externas de otimização (apenas NumPy).
   - Resolução da Fase 1 (viabilidade via variáveis artificiais) e Fase 2 (minimização de custo econômico).
   - Rastreamento completo dos **20 tableaus matriciais** com identificação explícita de pivôs pela regra de Dantzig e teste da razão mínima.
   - Cálculo rigoroso de preços-sombra ($y_i = \partial Z / \partial b_i$) e faixas analíticas de sensibilidade $[c_{\min}, c_{\max}]$ e $[b_{\min}, b_{\max}]$.
2. **Integração Econômica CEPEA/CNA (`cepea_data.py`):**
   - Cotações oficiais para o estado de Goiás: Milho Esalq/BM&F (R$ 64,73/sc 60kg), Silagem de Milho (R$ 247,08/t MN), DDGS (R$ 901,11/t MN), Feno Tifton (R$ 1,70/kg MN) e Leite CEPEA (R$ 2,9692/L).
   - Cálculo automático da margem bruta sobre alimentação (*Income Over Feed Cost* - IOFC).
3. **Dashboard Web Interativo em Tempo Real (`campo_dourado/dashboard/app.py`):**
   - **Módulo 1 (Rebanho):** Simula a expansão do rebanho (ex: **200 vacas adultas**, **79% em lactação**), calculando demanda física no cocho (11,74 t de comida fresca/dia), área de lavoura de silagem (71,5 ha), faturamento (R$ 464,4 mil/mês) e mitigação de metano entérico com 3-NOP Bovaer (169,5 t $CO_2e$/ano).
   - **Módulo 2 (Dieta & Sensibilidade):** Sliders de preços dos insumos e botões rápidos de cenários de mercado com reotimização instantânea (< 5 ms).
   - **Módulo 3 (Tableaus):** Inspetor didático da evolução matricial do Simplex.
4. **Acoplamento no Motor de Simulação do RuFaS:**
   - Injeção dinâmica no `ration_optimizer.py`, executando a simulação completa de 5 anos (2015 a 2019) com **zero erros**.
5. **Relatórios Acadêmicos Oficiais:**
   - Disponíveis em Markdown ([`RELATORIO_MODELAGEM_OTIMIZACAO_RUFAS.md`](file:///testes/RuFaS/campo_dourado/RELATORIO_MODELAGEM_OTIMIZACAO_RUFAS.md)), Word formatado ([`.docx`](file:///testes/RuFaS/campo_dourado/RELATORIO_MODELAGEM_OTIMIZACAO_RUFAS.docx), 1,4 MB) e PDF compilado ([`.pdf`](file:///testes/RuFaS/campo_dourado/RELATORIO_MODELAGEM_OTIMIZACAO_RUFAS.pdf), 950 KB).

---

## 📁 Estrutura de Arquivos

```
campo_dourado/
├── modelo_pl_campo_dourado.py       # Modelo canônico linear (12 restrições NASEM / 9 alimentos)
├── cepea_data.py                    # Cotações oficiais CEPEA/CNA/Esalq e cálculo de IOFC
├── otimizar_campo_dourado.py        # Otimização Simplex nativa e benchmark contra HiGHS
├── sensibilidade_campo_dourado.py   # Análise de sensibilidade paramétrica (4 cenários)
├── visualizar_tableaus.py           # Exportador didático dos 20 tableaus matriciais
├── executar_tudo.py                 # Pipeline mestre de execução ponta a ponta
│
├── dashboard/                       # Aplicação Web Interativa (Flask + Tailwind + Chart.js)
│   ├── app.py                       # Backend e API de otimização em tempo real (Porta 5050)
│   └── templates/index.html         # Interface com 3 módulos (Rebanho, Dieta e Tableaus)
│
├── figuras/                         # Gráficos científicos de alta resolução (300 DPI)
│   ├── fig1_composicao_dieta.png    # Composição ótima da ração e custo Z*
│   ├── fig2_sensibilidade_milho.png # Sensibilidade do milho e limiar de troca de base
│   ├── fig3_competicao_silagens.png # Competição e estabilidade da silagem de milho
│   ├── fig4_buffer_fosforo.png      # Curva de buffer e preço-sombra do fósforo
│   └── fig5_arquitetura_simplex_rufas.png # Diagrama de arquitetura do sistema
│
├── gerar_graficos.py                # Script automatizado para renderizar as figuras
├── gerar_relatorio_documentos.py    # Compilador dos relatórios acadêmicos (.docx e .pdf)
│
├── RELATORIO_MODELAGEM_OTIMIZACAO_RUFAS.md   # Relatório técnico completo (Markdown)
├── RELATORIO_MODELAGEM_OTIMIZACAO_RUFAS.docx # Relatório acadêmico oficial ABNT (Word)
├── RELATORIO_MODELAGEM_OTIMIZACAO_RUFAS.pdf  # Relatório acadêmico oficial ABNT (PDF)
├── TABLEAUS_SIMPLEX_DETALHADOS.md            # Documentação passo a passo dos 20 tableaus
├── RELATORIO_TECNICO_CAMPO_DOURADO.md        # Síntese técnica do cenário Campo Dourado
│
└── resultados/                      # CSVs consolidados dos experimentos paramétricos
    ├── cenario_1_sensibilidade_milho.csv
    ├── cenario_2_sensibilidade_silagens.csv
    ├── cenario_3_buffer_fosforo.csv
    └── cenario_4_elasticidade_producao.csv
```

---

## ⚡ Como Executar

### 1. Iniciar o Dashboard Interativo Web (Recomendado)
```bash
python3 campo_dourado/dashboard/app.py
```
Acesse no navegador: **[http://localhost:5050](http://localhost:5050)**

### 2. Executar o Pipeline Completo de Otimização e Validação
```bash
python3 campo_dourado/executar_tudo.py
```

### 3. Recompilar os Relatórios Acadêmicos (.docx e .pdf)
```bash
python3 campo_dourado/gerar_relatorio_documentos.py
```

### 4. Rodar a Simulação da Fazenda Campo Dourado no RuFaS com o Simplex Ativo
```bash
RUFAS_OPTIMIZATION_MODE=simplex python3 main.py -p GO_campo_dourado/_pipeline_task_manager_metadata.json
```

---

## 📊 Principais Resultados Encontrados

1. **Solução Básica Ótima da Dieta:**
   - **Custo Diário Mínimo ($Z^*$):** **R$ 25,0107 / vaca / dia** (26,60 kg MS/dia a **R$ 0,9402 / kg MS**).
   - **Composição da Ração:**
     - `x51` (Silagem de Milho): **19,7374 kg MS** (74,2% da ração; 55,8 kg de comida fresca no cocho).
     - `x303` (Blend DDGS / Subprodutos de Etanol): **6,6039 kg MS** (24,8% da ração; concentrado proteico).
     - `x301` (Premix Mineral/Vitamínico): **0,2594 kg MS** (1,0% da ração; fornecimento de cálcio).
     - `x44` (Milho Grão Moído): **0,0 kg (0,0%)** — fora da base pelo custo atual de R$ 1,2413/kg MS.
2. **Restrições Ativas e Preços-Sombra (Custo Dual $\lambda_i$):**
   - **Energia Líquida Mínima ($NE_L \ge 53,85\text{ Mcal}$):** Preço-sombra = **R$ 0,2648 / Mcal**.
   - **Proteína Metabolizável Mínima ($PDR \ge 2.742,9\text{ g}$):** Preço-sombra = **R$ 0,0018 / g**.
   - **Cálcio Digestível Mínimo ($Ca \ge 68,78\text{ g}$):** Preço-sombra = **R$ 0,0841 / g**.
   - **Fósforo ($P \ge 65,52\text{ g}$):** Restrição **folgada** (+2,35 g de sobra natural trazida pelo DDGS).
3. **Ponto de Troca do Milho Moído (Análise de Sensibilidade):**
   - O custo reduzido do milho grão moído é de **R$ 0,5046 / kg MS**.
   - O milho só entra na dieta se seu preço cair abaixo de **R$ 0,7367 / kg MS** (equivalente a **R$ 38,42 por saca de 60 kg**).
4. **Dimensionamento de Escala da Fazenda (Cenário 200 Vacas / 79% Lactação):**
   - **Rebanho:** 158 vacas em lactação e 42 vacas secas (período pré-parto).
   - **Produção Diária:** 5.214 litros de leite/dia (156,4 mil litros/mês).
   - **Faturamento Mensal:** **R$ 464.442,26 / mês** (a R$ 2,97/L CEPEA Goiás).
   - **Logística do Cocho:** Demanda diária de **11,74 toneladas de comida fresca/dia** (352 t/mês).
   - **Área de Lavoura:** **71,5 hectares de milho** necessários para colheita da silagem anual (3.218 t/ano a 45 t MN/ha).
   - **Margem Bruta IOFC da Fazenda:** Lucro operacional sobre alimentação de **R$ 331.401,56 / mês**.

---

## 📚 Referências Bibliográficas (ABNT NBR 6023)

1. **CENTRO DE ESTUDOS AVANÇADOS EM ECONOMIA APLICADA (CEPEA).** *Indicador do Milho ESALQ/BM&FBOVESPA e Cotações do Leite ao Produtor no Estado de Goiás*. Piracicaba: Departamento de Economia, Administração e Sociologia da ESALQ/USP, 2026. Disponível em: https://www.cepea.esalq.usp.br. Acesso em: 28 out. 2026.
2. **CONFEDERAÇÃO DA AGRICULTURA E PECUÁRIA DO BRASIL (CNA); SERVIÇO NACIONAL DE APRENDIZAGEM RURAL (SENAR).** *Painel de Custos de Produção da Pecuária de Leite: Projeto Campo Futuro*. Brasília: CNA/SENAR, 2026. Disponível em: https://www.cnabrasil.org.br. Acesso em: 28 out. 2026.
3. **DANTZIG, George B.** *Linear Programming and Extensions*. Princeton, NJ: Princeton University Press, 1963. 625 p.
4. **DANTZIG, George B.** *Maximization of a linear function of variables subject to linear inequalities*. In: KOOPMANS, T. C. (Ed.). Activity Analysis of Production and Allocation. Cowles Commission Monograph No. 13. New York: John Wiley & Sons, 1951. p. 339–347.
5. **DIJKSTRA, Jan et al.** *Feeding Strategies to Reduce Enteric Methane Emissions from Ruminants*. In: KEBREAB, E. (Ed.). Animal Nutrition and Emissions. Wageningen: Wageningen Academic Publishers, 2018. p. 115–138.
6. **HILLIER, Frederick S.; LIEBERMAN, Gerald J.** *Introdução à Pesquisa Operacional*. 9. ed. Porto Alegre: McGraw-Hill / AMGH Editora, 2013. 1048 p.
7. **INTERGOVERNMENTAL PANEL ON CLIMATE CHANGE (IPCC).** *Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report*. Cambridge: Cambridge University Press, 2021. 2391 p.
8. **MINISTÉRIO DA AGRICULTURA, PECUÁRIA E ABASTECIMENTO (MAPA).** *Instrução Normativa nº 8, de 25 de março de 2004*. Proíbe em todo o território nacional a produção e comercialização de produtos destinados à alimentação de ruminantes que contenham proteínas e gorduras de origem animal. Diário Oficial da União: seção 1, Brasília, DF, n. 59, p. 8, 26 mar. 2004.
9. **NATIONAL ACADEMIES OF SCIENCES, ENGINEERING, AND MEDICINE (NASEM).** *Nutrient Requirements of Dairy Cattle*. 8th rev. ed. Washington, DC: The National Academies Press, 2021. 502 p. DOI: https://doi.org/10.17226/25806.
10. **NATIONAL RESEARCH COUNCIL (NRC).** *Nutrient Requirements of Dairy Cattle*. 7th rev. ed. Washington, DC: National Academy Press, 2001. 408 p.
11. **ROTEZAHN, Kathryn et al.** *The Ruminant Farm Systems (RuFaS) Model: Design and Evaluation of a Whole-Farm Simulation Model for Dairy Systems*. Journal of Dairy Science, Champaign, v. 106, n. 12, p. 8920–8938, 2023. DOI: 10.3168/jds.2023-23456.
12. **TAHA, Hamdy A.** *Pesquisa Operacional: Uma Visão Geral*. 8. ed. São Paulo: Pearson Prentice Hall, 2008. 384 p.
13. **VALADARES FILHO, Sebastião de Campos et al.** *Tabelas Brasileiras de Composição de Alimentos para Bovinos (CQBAL 4.0)*. 4. ed. Viçosa: Universidade Federal de Viçosa (UFV), 2016. 142 p.

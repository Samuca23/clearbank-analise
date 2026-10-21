"""Versão alternativa da análise usando pandas.

Lê transacoes.csv com pd.read_csv, aplica as mesmas regras de validação da
solução nativa, agrupa por mês com groupby e compara o resultado com o
resumo_mensal salvo em relatorio.json pelo notebook.
"""

import json

import pandas as pd

CAMINHO_CSV = "transacoes.csv"
CAMINHO_JSON = "relatorio.json"
TIPOS_VALIDOS = ("credito", "debito")
TOLERANCIA = 0.005  # metade do centavo: diferenças menores são arredondamento
COLUNAS_METRICAS = [
    "quantidade", "total_credito", "total_debito", "saldo",
    "media", "maior_valor", "menor_valor",
]


def carregar_dados(caminho):
    """Lê o CSV como texto puro para validar cada campo explicitamente."""
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    return df.apply(lambda coluna: coluna.str.strip())


def validar(df):
    """Aplica as regras de validação e descarta inválidos e ids duplicados."""
    df = df.copy()
    df["valor_num"] = pd.to_numeric(df["valor"], errors="coerce")
    df["data_dt"] = pd.to_datetime(df["data"], format="%Y-%m-%d", errors="coerce")

    valida = (
        df["id"].str.isdigit()
        & (df["cliente_id"] != "")
        & df["data"].str.fullmatch(r"\d{4}-\d{2}-\d{2}")
        & df["data_dt"].notna()
        & df["tipo"].isin(TIPOS_VALIDOS)
        & (df["valor_num"] > 0)
    )
    validas = df[valida].drop_duplicates(subset="id", keep="first")
    return validas, len(df) - len(validas)


def gerar_resumo_mensal(validas):
    """Agrupa por mês com groupby e calcula as mesmas métricas da versão nativa."""
    df = validas.assign(
        mes=validas["data_dt"].dt.strftime("%Y-%m"),
        credito=validas["valor_num"].where(validas["tipo"] == "credito", 0.0),
        debito=validas["valor_num"].where(validas["tipo"] == "debito", 0.0),
    )
    resumo = df.groupby("mes").agg(
        quantidade=("valor_num", "count"),
        total_credito=("credito", "sum"),
        total_debito=("debito", "sum"),
        media=("valor_num", "mean"),
        maior_valor=("valor_num", "max"),
        menor_valor=("valor_num", "min"),
    )
    resumo["saldo"] = resumo["total_credito"] - resumo["total_debito"]
    # round() do Python, igual ao da solução nativa: o .round() do pandas
    # arredonda meio centavo de forma diferente (ex.: média de 2026-03, 3559.975)
    return resumo[COLUNAS_METRICAS].map(lambda valor: round(valor, 2))


def carregar_resumo_nativo(caminho):
    """Lê o resumo_mensal gerado pela solução nativa (relatorio.json)."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            relatorio = json.load(arquivo)
    except FileNotFoundError:
        print(f"Arquivo '{caminho}' não encontrado. Execute o notebook antes.")
        return None
    nativo = pd.DataFrame.from_dict(relatorio["resumo_mensal"], orient="index")
    return nativo[COLUNAS_METRICAS]


def comparar(resumo_pandas, resumo_nativo):
    """Compara os dois resumos célula a célula. Retorna True se forem iguais."""
    if list(resumo_pandas.index) != list(resumo_nativo.index):
        print("Os meses encontrados são diferentes entre as versões.")
        return False
    diferenca = (resumo_pandas - resumo_nativo.astype(float)).abs()
    divergentes = diferenca.stack()
    divergentes = divergentes[divergentes > TOLERANCIA]
    for (mes, metrica), valor in divergentes.items():
        print(f"Divergência em {mes} / {metrica}: {valor}")
    return divergentes.empty


def main():
    """Executa a análise com pandas e compara com a solução nativa."""
    df = carregar_dados(CAMINHO_CSV)
    validas, total_invalidas = validar(df)
    print(f"Total de linhas lidas: {len(df)}")
    print(f"Linhas válidas: {len(validas)}")
    print(f"Linhas inválidas: {total_invalidas}")

    resumo = gerar_resumo_mensal(validas)
    print("\n===== RESUMO MENSAL (pandas) =====")
    print(resumo.to_string())

    nativo = carregar_resumo_nativo(CAMINHO_JSON)
    if nativo is None:
        return
    print("\n===== COMPARAÇÃO COM A SOLUÇÃO NATIVA =====")
    if comparar(resumo, nativo):
        print("Resultados idênticos: pandas e solução nativa produzem os mesmos valores.")
    else:
        print("Atenção: os resultados divergem.")


if __name__ == "__main__":
    main()

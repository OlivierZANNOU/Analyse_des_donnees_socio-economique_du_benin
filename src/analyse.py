"""Analyse exploratoire des indicateurs socio-économiques du Bénin.

Usage : python src/analyse.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
START, END = 2000, 2024


def load_raw():
    raw = pd.read_csv(ROOT / "data/raw/wdi_afrique_ouest.csv")
    meta = pd.read_csv(ROOT / "data/raw/indicateurs.csv")
    return raw, meta


def clean(raw, meta):
    """Contrôle les données et les met au format large sur une grille complète.

    Les valeurs absentes restent vides : aucune imputation.
    """
    key = ["code_pays", "code_indicateur", "annee"]
    if raw.duplicated(key).any():
        raise ValueError("Observations en double")
    if not set(raw.code_indicateur) <= set(meta.code_indicateur):
        raise ValueError("Code indicateur inconnu")
    df = raw[raw.annee.between(START, END)].merge(meta[["code_indicateur", "nom"]], on="code_indicateur")
    wide = df.pivot(index=["pays", "annee"], columns="nom", values="valeur")
    grid = pd.MultiIndex.from_product([sorted(raw.pays.unique()), range(START, END + 1)],
                                      names=["pays", "annee"])
    wide = wide.reindex(index=grid, columns=meta.nom)
    percent = ["urbanisation", "alphabetisation", "electricite", "internet", "eau_base"]
    bad = (wide[percent] < 0) | (wide[percent] > 100)
    if bad.any().any():
        raise ValueError("Pourcentage hors de l'intervalle [0, 100]")
    return wide


def quality_report(benin):
    return pd.DataFrame({
        "annees_disponibles": benin.notna().sum(),
        "manquantes": benin.isna().sum(),
        "taux_manquant_pct": 100 * benin.isna().mean(),
        "premiere_annee": benin.apply(lambda s: s.first_valid_index()),
        "derniere_annee": benin.apply(lambda s: s.last_valid_index()),
    }).sort_values("taux_manquant_pct", ascending=False)


def trends(benin, min_points=5):
    """Évolution entre les valeurs extrêmes disponibles et pente linéaire par an."""
    rows = []
    for name, series in benin.items():
        s = series.dropna()
        if s.empty:
            continue
        enough = len(s) >= min_points
        rows.append({"nom": name, "annee_debut": s.index[0], "valeur_debut": s.iloc[0],
                     "annee_fin": s.index[-1], "valeur_fin": s.iloc[-1],
                     "variation_absolue": s.iloc[-1] - s.iloc[0],
                     "pente_par_an": np.polyfit(s.index, s.values, 1)[0] if enough else np.nan,
                     "n": len(s)})
    return pd.DataFrame(rows).set_index("nom")


def latest_comparison(wide, names):
    """Compare les pays à la dernière année disponible pour tous, par indicateur."""
    rows = []
    for name in names:
        table = wide[name].unstack("pays")
        complete = table.dropna()
        if complete.empty:
            continue
        year = complete.index[-1]
        rows.append({"indicateur": name, "annee": year, **complete.loc[year].to_dict()})
    return pd.DataFrame(rows)


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def panels(benin, labels, names, path, title):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, name in zip(axes.flat, names):
        s = benin[name].dropna()
        ax.plot(s.index, s.values, marker="o", ms=4)
        ax.set_title(labels[name], fontsize=11)
        ax.set_xlim(START - 1, END + 1)
    fig.suptitle(title, fontsize=15)
    save(fig, path)


def main():
    raw, meta = load_raw()
    wide = clean(raw, meta)
    benin = wide.loc["Bénin"]
    labels = dict(zip(meta.nom, meta.libelle))
    tables, figures = ROOT / "outputs/tableaux", ROOT / "outputs/figures"
    for folder in (tables, figures, ROOT / "data/processed"):
        folder.mkdir(parents=True, exist_ok=True)

    wide.to_csv(ROOT / "data/processed/panel_afrique_ouest.csv")
    benin.to_csv(ROOT / "data/processed/benin.csv")
    quality = quality_report(benin)
    quality.round(1).to_csv(tables / "qualite_donnees.csv", index_label="nom")
    benin.describe().T.round(3).to_csv(tables / "statistiques_descriptives.csv", index_label="nom")
    trend = trends(benin)
    trend.round(3).to_csv(tables / "tendances.csv")
    names = ["pib_hab", "esperance_vie", "mortalite_5ans", "fecondite", "electricite",
             "internet", "eau_base", "incidence_palu"]
    comparison = latest_comparison(wide, names)
    comparison.round(2).to_csv(tables / "comparaison_regionale.csv", index=False)

    sns.set_theme(style="whitegrid")

    # 1. Disponibilité des données
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(benin.notna().T.astype(int), cmap=["#e8e8e8", "#2b6c8f"], cbar=False,
                vmin=0, vmax=1, linewidths=.5, ax=ax)
    ax.set(title="Bénin : disponibilité des données (bleu = disponible)", xlabel="", ylabel="")
    save(fig, figures / "1_disponibilite.png")

    panels(benin, labels, ["population", "pib_hab", "croissance_pib", "inflation"],
           figures / "2_economie_demographie.png", "Bénin : population et économie")
    panels(benin, labels, ["esperance_vie", "mortalite_5ans", "fecondite", "incidence_palu"],
           figures / "3_sante.png", "Bénin : santé")
    panels(benin, labels, ["electricite", "eau_base", "internet", "urbanisation"],
           figures / "4_infrastructures.png", "Bénin : accès aux services et urbanisation")

    # 5. Corrélations : niveaux contre variations annuelles
    cols = ["pib_hab", "esperance_vie", "mortalite_5ans", "fecondite", "electricite",
            "internet", "eau_base", "incidence_palu"]
    levels = benin[cols].corr()
    changes = benin[cols].diff().corr(min_periods=10)
    levels.round(3).to_csv(tables / "correlations_niveaux.csv")
    changes.round(3).to_csv(tables / "correlations_variations.csv")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, matrix, title in zip(axes, (levels, changes), ("Niveaux", "Variations d'une année à l'autre")):
        sns.heatmap(matrix, vmin=-1, vmax=1, cmap="RdBu_r", annot=True, fmt=".2f", square=True,
                    cbar_kws={"shrink": .7}, ax=ax)
        ax.set(title=title, xlabel="", ylabel="")
    save(fig, figures / "5_correlations.png")

    # 6. Comparaison régionale
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    for ax in axes.flat:
        ax.set_visible(False)
    for ax, row in zip(axes.flat, comparison.to_dict("records")):
        name, year = row.pop("indicateur"), row.pop("annee")
        values = pd.Series(row, dtype=float).sort_values()
        ax.set_visible(True)
        ax.barh(values.index, values.values,
                color=["#d9822b" if c == "Bénin" else "#9aa9b5" for c in values.index])
        ax.set_title(f"{labels[name].split(' (')[0]} ({year})", fontsize=10)
    fig.suptitle("Le Bénin parmi ses voisins (unités : voir data/raw/indicateurs.csv)", fontsize=14)
    save(fig, figures / "6_comparaison_regionale.png")

    print(quality.round(1).to_string(), "\n")
    print(trend.round(2).to_string(), "\n")
    print(comparison.round(2).to_string(index=False), "\n")
    print(levels.round(2).to_string(), "\n")
    print(changes.round(2).to_string())


if __name__ == "__main__":
    main()

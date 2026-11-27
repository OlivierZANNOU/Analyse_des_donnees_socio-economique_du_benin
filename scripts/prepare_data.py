"""Reconstruit data/raw/ à partir du miroir public des World Development Indicators.

Usage :
    git clone --depth 1 https://github.com/open-numbers/ddf--world_bank--world_development_indicators wdi
    python scripts/prepare_data.py wdi
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = {"ben": "Bénin", "tgo": "Togo", "nga": "Nigeria", "ner": "Niger",
             "bfa": "Burkina Faso", "gha": "Ghana", "civ": "Côte d'Ivoire"}
# code Banque mondiale -> (nom court, libellé, thème)
INDICATORS = {
    "SP.POP.TOTL": ("population", "Population totale (habitants)", "Démographie"),
    "SP.POP.GROW": ("croissance_pop", "Croissance démographique (% par an)", "Démographie"),
    "SP.URB.TOTL.IN.ZS": ("urbanisation", "Population urbaine (% du total)", "Démographie"),
    "SP.DYN.TFRT.IN": ("fecondite", "Fécondité (enfants par femme)", "Démographie"),
    "NY.GDP.PCAP.KD": ("pib_hab", "PIB par habitant (US$ constants)", "Économie"),
    "NY.GDP.MKTP.KD.ZG": ("croissance_pib", "Croissance du PIB (% par an)", "Économie"),
    "FP.CPI.TOTL.ZG": ("inflation", "Inflation, prix à la consommation (% par an)", "Économie"),
    "SP.DYN.LE00.IN": ("esperance_vie", "Espérance de vie à la naissance (années)", "Santé"),
    "SH.DYN.MORT": ("mortalite_5ans", "Mortalité des moins de 5 ans (pour 1 000 naissances)", "Santé"),
    "SH.MLR.INCD.P3": ("incidence_palu", "Incidence du paludisme (pour 1 000 à risque)", "Santé"),
    "SE.PRM.CMPT.ZS": ("achevement_primaire", "Taux d'achèvement du primaire (%)", "Éducation"),
    "SE.ADT.LITR.ZS": ("alphabetisation", "Alphabétisation des adultes (%)", "Éducation"),
    "EG.ELC.ACCS.ZS": ("electricite", "Accès à l'électricité (% de la population)", "Infrastructures"),
    "IT.NET.USER.ZS": ("internet", "Utilisateurs d'Internet (% de la population)", "Infrastructures"),
    "SH.H2O.BASW.ZS": ("eau_base", "Accès à l'eau potable de base (% de la population)", "Infrastructures"),
}


def main(wdi_dir):
    frames = []
    for code in INDICATORS:
        key = code.lower().replace(".", "_")
        path = Path(wdi_dir) / "datapoints" / f"ddf--datapoints--{key}--by--economy--year.csv"
        df = pd.read_csv(path, dtype={key: str}).rename(columns={key: "valeur", "year": "annee"})
        df = df[df.economy.isin(COUNTRIES)].copy()
        df["code_indicateur"] = code
        frames.append(df)
    raw = pd.concat(frames)
    raw["code_pays"] = raw.economy.str.upper()
    raw["pays"] = raw.economy.map(COUNTRIES)
    cols = ["code_pays", "pays", "code_indicateur", "annee", "valeur"]
    raw[cols].sort_values(["code_pays", "code_indicateur", "annee"]).to_csv(
        ROOT / "data/raw/wdi_afrique_ouest.csv", index=False)
    pd.DataFrame([(c, *v) for c, v in INDICATORS.items()],
                 columns=["code_indicateur", "nom", "libelle", "theme"]).to_csv(
        ROOT / "data/raw/indicateurs.csv", index=False)
    print(f"{len(raw)} observations extraites")


if __name__ == "__main__":
    main(sys.argv[1])

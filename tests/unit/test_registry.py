from pathlib import Path

from feature_store.registry import DTYPES, FEATURE_NAMES, FEATURES, features_for

CATALOG = Path(__file__).parents[2] / "docs" / "feature_catalog.md"


def test_noms_uniques():
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))


def test_entre_15_et_25_variables():
    assert 15 <= len(FEATURES) <= 25


def test_types_et_consommateurs_valides():
    for feature in FEATURES:
        assert feature.dtype in DTYPES, feature.name
        assert feature.consumers, feature.name
        assert set(feature.consumers) <= {"scoring", "marketing"}, feature.name


def test_variables_partagees_entre_les_deux_modeles():
    scoring, marketing = set(features_for("scoring")), set(features_for("marketing"))
    assert scoring & marketing
    assert scoring | marketing == set(FEATURE_NAMES)


def test_catalogue_documente_chaque_variable():
    catalogue = CATALOG.read_text(encoding="utf-8")
    absentes = [nom for nom in FEATURE_NAMES if f"`{nom}`" not in catalogue]
    assert absentes == []

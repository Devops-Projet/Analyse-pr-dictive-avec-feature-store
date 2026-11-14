import pytest

from feature_store.config import REQUIRED, ConfigError, get_settings

VALID = {
    "POSTGRES_HOST": "postgres",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "feature_store",
    "POSTGRES_USER": "feature_store",
    "POSTGRES_PASSWORD": "secret",
}


@pytest.fixture
def env(monkeypatch):
    for name, value in VALID.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def test_configuration_valide(env):
    settings = get_settings()
    assert settings.postgres_port == 5432
    assert settings.database_url.database == "feature_store"


@pytest.mark.parametrize("name", REQUIRED)
def test_variable_obligatoire_absente(env, name):
    env.delenv(name)
    with pytest.raises(ConfigError, match=name):
        get_settings()


def test_variable_obligatoire_vide(env):
    env.setenv("POSTGRES_PASSWORD", "")
    with pytest.raises(ConfigError, match="POSTGRES_PASSWORD"):
        get_settings()


def test_port_par_defaut(env):
    env.delenv("POSTGRES_PORT")
    assert get_settings().postgres_port == 5432


def test_port_invalide(env):
    env.setenv("POSTGRES_PORT", "abc")
    with pytest.raises(ConfigError, match="POSTGRES_PORT"):
        get_settings()


def test_mot_de_passe_absent_de_la_representation(env):
    assert "secret" not in str(get_settings().database_url)

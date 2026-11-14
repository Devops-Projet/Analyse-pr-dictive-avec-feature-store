from scripts.sync_env import main, missing_lines

EXAMPLE = "# commentaire\nA=1\nB=2\nC=x=y\n"


def test_variables_absentes_detectees():
    assert missing_lines(EXAMPLE, "A=10\n") == ["B=2", "C=x=y"]


def test_aucune_variable_absente():
    assert missing_lines(EXAMPLE, "A=1\nB=2\nC=3\n") == []


def test_ajout_sans_modifier_les_valeurs_existantes(tmp_path):
    example, env = tmp_path / ".env.example", tmp_path / ".env"
    example.write_text(EXAMPLE)
    env.write_text("A=valeur-locale")
    main(str(example), str(env))
    main(str(example), str(env))  # idempotent
    assert env.read_text() == "A=valeur-locale\nB=2\nC=x=y\n"

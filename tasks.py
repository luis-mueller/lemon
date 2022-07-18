from invoke import task


@task
def build(c, install=False, freeze=False):
    if install:
        c.run("python -m pip install -r requirements.txt", pty=True)
        c.run("python -m pip install .", pty=True)
    if freeze:
        c.run(
            "python -m pip list --format=freeze --exclude-editable"
            + "> requirements.txt", pty=True)
    c.run("autopep8 --in-place --recursive .", pty=True)

    # More permissive: --select=E9,F63,F7,F82
    c.run("flake8 . --show-source --statistics", pty=True)

    print("\n GENERATE DOCS")
    c.run("cd sphinx && make html", pty=True)
    c.run("cp -r sphinx/build/html/* docs && cd docs && touch .nojekyll",
          pty=True)

    print("\n INTEGRATION TESTS")
    c.run("python -m pytest test/integration", pty=True)

    print("\n UNIT TESTS & COVERAGE")
    c.run(
        "coverage run --source lemon"
        + " --omit lemon/__init__.py"
        + " -m pytest test/unit ", pty=True)
    c.run("coverage report", pty=True)

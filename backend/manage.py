import typer
from alembic.config import Config
from alembic import command

app = typer.Typer()
CFG = Config("alembic.ini")

@app.command()
def makemigrations(message: str):
    """Generate a new migration (autogenerate)."""
    command.revision(CFG, message=message, autogenerate=True)

@app.command()
def migrate(rev: str = "head"):
    """Apply migrations up to <rev> (default: head)."""
    command.upgrade(CFG, rev)

@app.command()
def revert(rev: str = "-1"):
    """Revert migrations down to <rev> (default: one step)."""
    command.downgrade(CFG, rev)

@app.command()
def history():
    """Show migration history."""
    command.history(CFG, verbose=True)

@app.command()
def stamp(rev: str = "head"):
    """Mark database at a given revision without running migrations."""
    command.stamp(CFG, rev)

if __name__ == "__main__":
    app()


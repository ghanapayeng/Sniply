import os
import sys
import click
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.services.auth_service import AuthService
from backend.app.services.security_service import SecurityService

app = create_app(os.getenv("FLASK_ENV", "development"))


def run_bootstrap_admin(username=None, email=None, password=None):
    admin_user = username or os.getenv("ADMIN_BOOTSTRAP_USERNAME", "admin")
    admin_email = email or os.getenv("ADMIN_BOOTSTRAP_EMAIL", "admin@sniply.io")
    admin_pass = password or os.getenv("ADMIN_BOOTSTRAP_PASSWORD")

    if not admin_pass:
        click.echo("Error: Administrator password must be provided via --password or ADMIN_BOOTSTRAP_PASSWORD environment variable.", err=True)
        sys.exit(1)

    with app.app_context():
        existing = User.query.filter(
            (User.username == admin_user.lower()) | (User.email == admin_email.lower())
        ).first()

        if existing:
            if existing.role != "admin":
                existing.role = "admin"
                db.session.commit()
                click.echo(f"Existing user '{existing.username}' upgraded to administrator role.")
            else:
                click.echo(f"Administrator account '{existing.username}' already exists.")
            return

        user, err = AuthService.register_user(
            username=admin_user,
            email=admin_email,
            password=admin_pass,
            role="admin",
        )
        if err:
            click.echo(f"Failed to create admin: {err}", err=True)
            sys.exit(1)

        user.email_verified = True
        db.session.commit()
        click.echo(f"Successfully bootstrapped administrator account: {admin_user} ({admin_email})")


@app.cli.command("bootstrap-admin")
@click.option("--username", default=None, help="Administrator username")
@click.option("--email", default=None, help="Administrator email")
@click.option("--password", default=None, help="Administrator password")
def bootstrap_admin_cli(username, email, password):
    """Securely bootstrap the initial administrator account."""
    run_bootstrap_admin(username, email, password)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap-admin":
        run_bootstrap_admin()
    else:
        port = int(os.getenv("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))

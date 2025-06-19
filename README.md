# Avtopark

## Running tests

Install the project dependencies and run `pytest` from the repository root:

```bash
pip install -r requirements.txt
pytest
```

## Configuration

The application relies on a few secrets that should be provided through
environment variables. **Do not commit a `.env` file containing these values.**

Set the following variables before running the app or the tests:

* `SECRET_KEY` – secret key used by Flask.
* `CLOUDINARY_URL` – connection string for your Cloudinary account.
* `DATABASE_URL` – optional SQLAlchemy URI to use instead of the default
  SQLite database.

Example on Linux or macOS:

```bash
export SECRET_KEY=your-secret
export CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>
export DATABASE_URL=postgresql://user:pass@localhost:5432/fleet
```

You may place these lines in a local `.env` file for convenience, but keep in
mind that `.env` is ignored by Git and should never be added to the
repository.

After configuring the database, apply migrations with:

```bash
flask db upgrade
```

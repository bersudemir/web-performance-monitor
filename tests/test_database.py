"""Configuration and PostgreSQL migration checks without a running database."""

import io
import os
import unittest
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import configure_mappers

from app.infrastructure.config import PROJECT_ROOT, get_database_url
from app.infrastructure.models import CheckResult, Site


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "POSTGRES_DB": "test_database",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "p@ss:/%$word",
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        dotenv = patch("app.infrastructure.config.load_dotenv")
        self.load_dotenv = dotenv.start()
        self.addCleanup(dotenv.stop)

    def test_credentials_with_special_characters_round_trip(self):
        from sqlalchemy import make_url

        url = get_database_url()
        parsed = make_url(url.render_as_string(hide_password=False))
        self.assertEqual(parsed.password, os.environ["POSTGRES_PASSWORD"])
        self.assertEqual(parsed.drivername, "postgresql+psycopg")
        self.load_dotenv.assert_called_once_with(PROJECT_ROOT / ".env", override=False)

    def test_missing_settings_fail_without_exposing_credentials(self):
        del os.environ["POSTGRES_DB"]
        with self.assertRaisesRegex(ValueError, "Missing database settings: POSTGRES_DB") as error:
            get_database_url()
        self.assertNotIn(os.environ["POSTGRES_PASSWORD"], str(error.exception))

    def test_invalid_ports_are_rejected(self):
        for port in ("0", "65536", "invalid"):
            with self.subTest(port=port), patch.dict(os.environ, {"POSTGRES_PORT": port}):
                with self.assertRaises(ValueError):
                    get_database_url()

    def test_relationship_mappers_configure(self):
        configure_mappers()
        self.assertIs(Site.check_results.property.mapper.class_, CheckResult)
        self.assertIs(CheckResult.site.property.mapper.class_, Site)
        self.assertTrue(Site.check_results.property.uselist)
        self.assertFalse(CheckResult.site.property.uselist)

    def test_migration_renders_postgresql_upgrade_and_downgrade(self):
        output = io.StringIO()
        config = Config(str(PROJECT_ROOT / "alembic.ini"), output_buffer=output)
        command.upgrade(config, "head", sql=True)
        sql = output.getvalue()
        self.assertIn("CREATE TABLE sites", sql)
        self.assertIn("CREATE TABLE check_results", sql)
        self.assertIn("FOREIGN KEY(site_id) REFERENCES sites (id) ON DELETE CASCADE", sql)
        self.assertIn("TIMESTAMP WITH TIME ZONE", sql)
        self.assertIn("check_interval_seconds > 0", sql)
        self.assertNotIn("INSERT INTO sites", sql)
        self.assertNotIn("INSERT INTO check_results", sql)

        output.seek(0)
        output.truncate()
        command.downgrade(config, "0001:base", sql=True)
        sql = output.getvalue()
        self.assertLess(sql.index("DROP TABLE check_results"), sql.index("DROP TABLE sites"))

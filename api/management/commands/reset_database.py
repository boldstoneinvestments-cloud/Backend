import os

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Reset the PostgreSQL public schema once for a new DATABASE_RESET_KEY.'

    def handle(self, *args, **options):
        reset_key = os.getenv('DATABASE_RESET_KEY', '').strip()
        if not reset_key:
            self.stdout.write('DATABASE_RESET_KEY is not set; keeping the existing database.')
            return

        if connection.vendor != 'postgresql':
            raise RuntimeError('Database reset is only supported for PostgreSQL.')

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = '_database_reset_marker')"
            )
            marker_exists = cursor.fetchone()[0]
            if marker_exists:
                cursor.execute('SELECT reset_key FROM public._database_reset_marker LIMIT 1')
                current_key = cursor.fetchone()
                if current_key and current_key[0] == reset_key:
                    self.stdout.write('Database reset already completed for this key.')
                    return

            cursor.execute('DROP SCHEMA public CASCADE')
            cursor.execute('CREATE SCHEMA public')
            cursor.execute('GRANT ALL ON SCHEMA public TO public')
            cursor.execute('CREATE TABLE public._database_reset_marker (reset_key VARCHAR(255) PRIMARY KEY)')
            cursor.execute('INSERT INTO public._database_reset_marker (reset_key) VALUES (%s)', [reset_key])

        self.stdout.write(self.style.SUCCESS('PostgreSQL public schema reset. Django migrations will run next.'))

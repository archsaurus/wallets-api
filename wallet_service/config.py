"""Прокси-конфиг."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PgSQLConfig(BaseSettings):
    """Параметры подключения к базе"""

    dialect: str = 'postgresql'

    ALCHEMY_POOL_SIZE: int
    ALCHEMY_MAX_OVERFLOW: int

    RUN_MIGRATIONS: bool

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    @property
    def database_url_asyncpg(self):
        """Формирует и возвращает строку подключения к базе данных PostgreSQL,
            используя драйвер 'asyncpg'.

            Returns:
                str: строка подключения в формате:
                    '{dialect}+{driver}://{user}:{password}@{host}:{port}/{db}'
    """
        driver = 'asyncpg'

        return \
            f'{self.dialect}+{driver}://'\
            f'{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@'\
            f'{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/'\
            f'{self.POSTGRES_DB}'

    @property
    def database_url_psycopg(self):
        """Формирует и возвращает строку подключения к базе данных PostgreSQL,
            используя драйвер 'psycopg2'.

            Returns:
                str: строка подключения в формате:
                    '{dialect}+{driver}://{user}:{password}@{host}:{port}/{db}'
        """
        driver = 'psycopg2'

        return \
            f'{self.dialect}+{driver}://'\
            f'{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@'\
            f'{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/'\
            f'{self.POSTGRES_DB}'

    @property
    def pool_size(self):
        return self.ALCHEMY_POOL_SIZE

    @property
    def max_overflow(self):
        return self.ALCHEMY_MAX_OVERFLOW

    @property
    def run_migration(self):
        return self.RUN_MIGRATIONS

    model_config = SettingsConfigDict(env_file='.env')


settings = PgSQLConfig()

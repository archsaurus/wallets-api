# ITK Test – Wallets API

[![Pylint](https://github.com/archsaurus/ITK_Test-wallets-api/actions/workflows/pylint.yml/badge.svg)](https://github.com/archsaurus/ITK_Test-wallets-api/actions/workflows/pylint.yml)
[![Pytest](https://github.com/archsaurus/ITK_Test-wallets-api/actions/workflows/pytest.yml/badge.svg)](https://github.com/archsaurus/ITK_Test-wallets-api/actions/workflows/pytest.yml)
![Python Version](https://img.shields.io/badge/python-3.14%2B-blue)
![PostgreSQL Version](https://img.shields.io/badge/postgresql-18.0%2B-blue)
[![License](https://img.shields.io/github/license/archsaurus/ngs-analyzer)](LICENSE)


Данный проект является FastAPI‑реализацией **REST‑API** для управления сервисом электронных кошельков в рамках выполнения тестового задания компании ITK-Academy.

Проект покрыт тестами (кроме error-handler'ов), проверяется линтерами и упакован в Docker‑контейнеры.

---

## Содержание

| № |                                         Раздел |
|---|------------------------------------------------|
| 1 | [Анализ исходного ТЗ](#-анализ-исходного-тз)   |
| 2 | [Архитектура](#-архитектура)                   |
| 3 | [Стек технологий](#-стек-технологий)           |
| 4 | [Как запустить проект](#-как-запустить-проект) |

---

## Анализ исходного ТЗ

> **Требуется** реализовать сервис, позволяющий:
> 1. Изменение баланса кошелька
> 2. Получение баланса кошелька
> 3. Cоответствовать стандарту `PEP-8`
> 4.  Делать миграции для базы данных
> 5. Работать корректно в конкурентной среде (корректно использовать асинхронный веб-фреймворк)
> 6. Быть покрытым тестами и запускаться в Docker‑контейнерах.

Исходный вариант задания предлагал два эндпоинта:

1. `POST /api/v1/wallets/<WALLET_UUID>/operation` с полем `operation_type`.
   Это **не RESTful** (один ресурс не должен решать две разные задачи).
2. `GET /api/v1/wallets/<WALLET_UUID>`.

Опять же, для RESTful архитектуры приведён не полный список CRUD операций.

Из комментария к списку выше, было решено сохранить требуемый в задании эндпоинт, но к тому реализовать разделённые эндпоинты под здачи списания и зачисления средств, а также дополнить исходных спиоск до CRUD-полного.

Ниже приведена таблица итогового списка эндпоинтов текущей реализации:

|            Операция | HTTP‑метод |                                                            Путь |
|---------------------|------------|-----------------------------------------------------------------|
| Пополнение кошелька |     `POST` | `/api/v1/wallets/{wallet_id}/deposit`                           |
| Пополнение кошелька |     `POST` |  `/api/v1/wallets/{wallet_id}/operation?operation_type=DEPOSIT` |
|    Списание средств |     `POST` | `/api/v1/wallets/{wallet_id}/withdraw`                          |
|    Списание средств |     `POST` | `/api/v1/wallets/{wallet_id}/operation?operation_type=WITHDRAW` |
|       Узнать баланс |      `GET` | `/api/v1/wallets/{wallet_id}`                                   |
|     Создать кошелёк |     `POST` | `/api/v1/wallets`                                               |
|     Удалить кошелёк |   `DELETE` | `/api/v1/wallets/{wallet_uuid}`                                 |

На операции изменения баланса кошелька наложены ограничения снизу (`0.00`) и сверху `1'000'000.00` для корректной обработки запросов.

---

## Архитектура

|                   Требование |                                                                                                   Реализация |
|------------------------------|--------------------------------------------------------------------------------------------------------------|
|            **Асинхронность** | `FastAPI` + SQLAlchemy + `asyncpg`-драйвер для PostgreSQL                                                    |
|           **Конкурентность** | Транзакции с уровнем изоляции `SERIALIZABLE` + `SELECT … FOR UPDATE` (row‑level pessimistic lock), `asyncio` |
|                 **Миграции** | `alembic` (автоматически генерируемые скрипты для миграций)                                                  |
|                   **Docker** | 2‑контейнерный `docker‑compose`‑стек: `app` (FastAPI) + `db` (PostgreSQL)                                    |
|                    **Тесты** | `pytest` + `pytest‑asyncio`                                                                                  |
|               **Стиль кода** | PEP‑8, `ruff`, `pylint`, `flake8`, `mypy`, `black`                                                           |
| **Управление зависимостями** | `pip-tools` (`pip‑compile` + `pip‑sync`).                                                                    |

---

## Стек технологий

|                Назначение |                                            Инструмент |
|-------------------------- |-------------------------------------------------------|
|         **Web‑framework** | FastAPI v0.135                                        |
|              **ORM / DB** | SQLAlchemy v2.0 (async) + PostgreSQL v18              |
|              **Миграции** | Alembic v1.18                                         |
|                 **Тесты** | pytest, pytest‑asyncio                                |
|                **Docker** | Docker 20+, docker‑compose 2.20                       |
|  **Linters / formatters** | ruff v0.15, pylint v4, flake8 v7.3.0, black, isort v8 |
|         **Type checking** | mypy v1.19                                            |
| **Dependency management** | pip‑tools (`requirements*.txt`)                       |

---

## Как развернуть проект

### Вариант 1. Docker (минимальная сборка, ничего лишнего  для непосредственной работы)

```sh
$ git clone https://github.com/archsaurus/ITK_Test-wallets-api.git
$ cd ITK_Test-wallets-api
$ docker compose up --build -d
```

### Вариант 2. Локальная разработка (проект целиком, включая тесты и *requirements-dev* зависимости)

Требуются предустановленные `Python 3.14+` и `PostgreSQL`.

```sh
$ git clone https://github.com/archsaurus/ITK_Test-wallets-api.git
$ cd ITK_Test-wallets-api

$ pip-sync requirements.txt # runtime-зависимости
$ pip-sync requirements-dev.txt # включает линтеры, mypy, pytest и т.д.

$ cp .env.example .env # копируем шаблон для задания переменных окружения .env (см. ниже)

$ alembic revision --autogenerate # создаём миграции (если изменяли структуру моделей)
$ alembic upgrade head # применяем миграции

uvicorn application.main:app --host 0.0.0.0 --port 8000 --reload # запускаем ASGI-сервер приложения
```

#### Переменные окружения

|          Переменная |                                                   Описание |                                               Пример |
|---------------------|------------------------------------------------------------|------------------------------------------------------|
|     `POSTGRES_USER` |                                  Администратор базы данных |                                          wallet_user |
| `POSTGRES_PASSWORD` |                                                     Пароль |                                               qwerty |
|       `POSTGRES_DB` |                                            Имя базы данных |                                           wallets_db |
|     `POSTGRES_HOST` |                                      Хост (Docker‑service) |                                                   db |
|     `POSTGRES_PORT` |                                                       Порт |                                                 5432 |
|      `DATABASE_URL` |                                         DSN для SQLAlchemy | postgresql+asyncpg://user:password@host:port/db_name |
|        `MIGRATIONS` | Флаг аавтоматического совершения миграций (для контейнера) |                                                 true |

**Файл example.env содержит подготовленный шаблон.**

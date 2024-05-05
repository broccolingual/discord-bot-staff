# DSN

.envに以下の通り記述

`DSN="mysql+pymysql://{db_user}:{db_user_pass}@{db_host}/{db_name}?charset=utf8mb4"`

# alembic

データベース作成

`pipenv run alembic revision --autogenerate -m "commit message"`

マイグレーション実行

`pipenv run alembic upgrade head`

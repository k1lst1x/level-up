# level-up
level-up — веб-платформа для организации мероприятий и расчёта коммерческих предложений. Проект включает каталог услуг, конструктор КП, CRM-модуль и клиентскую часть с современным адаптивным интерфейсом. Stack: Django · PostgreSQL · HTML/CSS · JavaScript

## Запуск проекта (локально)

1. Перейди в корень проекта:
```bash
cd /home/royalka/Загрузки/level-up-main
```

2. Создай и активируй виртуальное окружение:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Установи зависимости:
```bash
pip install -r source/requirements.txt
```

4. Применяй миграции:
```bash
python source/manage.py migrate
```

5. Запусти сервер:
```bash
python source/manage.py runserver 0.0.0.0:8000
```

Открывай в браузере: `http://127.0.0.1:8000/`

### Частые проблемы

- Если получаешь `DisallowedHost (400)`, добавь в `source/config/settings.py`:
```python
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0"]
```

### Опционально (PDF в КП)

Если хочешь генерацию PDF через Playwright:
```bash
python -m playwright install chromium
```

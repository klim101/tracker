# Timeline Tracker (Streamlit)

Лёгкий таймлайн-трекер с кружочками по дням (проекты/группы, заметки на ховере, размер кружка 0–100%).
Нижняя серая линия — календарные дни (всегда 100%).

## Demo (локально)

```bash
pip install -r requirements.txt
streamlit run streamlit_timeline_tracker.py
```

## Функции
- Группы и проекты; фильтр по группам.
- Отметки по датам с заметкой и размером кружка (0–100%).
- Нижняя «День»-линия: каждый день = 100% (серые кружки).
- Зум: пресеты 30/60/90 дней, 6/12 мес, «всё время» + range slider.
- Табличный редактор для правок/удаления отметок.
- Экспорт/импорт JSON.

## Деплой (Streamlit Community Cloud)
1. Создайте новый публичный репозиторий на GitHub (например, `timeline-tracker`).
2. Перейдите на https://share.streamlit.io, нажмите **New app**, подключите GitHub-репозиторий.
3. Укажите **Main file**: `streamlit_timeline_tracker.py` и разверните.

## Деплой (Docker)
```bash
docker build -t timeline-tracker .
docker run -p 8501:8501 timeline-tracker
```
Откройте http://localhost:8501

## Структура
```
.
├─ streamlit_timeline_tracker.py   # приложение
├─ requirements.txt
├─ Dockerfile
├─ .gitignore
└─ LICENSE (MIT)
```

## Лицензия
MIT © 2025 Klim Nelyubov

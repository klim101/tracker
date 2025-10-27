# Timeline Tracker — минималистичная «нотная тетрадь»
# Запуск: pip install streamlit plotly pandas python-dateutil streamlit-plotly-events
#         streamlit run streamlit_timeline_tracker.py

from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dateutil.relativedelta import relativedelta
from streamlit_plotly_events import plotly_events

st.set_page_config(page_title="Timeline Tracker", layout="wide")

# =====================
# Вспомогательные
# =====================

def today() -> date:
    return date.today()


def to_date(x) -> date:
    if isinstance(x, date):
        return x
    return pd.to_datetime(x).date()


def start_of_month(d: date) -> date:
    return d.replace(day=1)


def days_in_month(d: date) -> int:
    first = start_of_month(d)
    nxt = first + relativedelta(months=1)
    return (nxt - first).days


def compute_size(note: str) -> int:
    """Размер точки/ноты растёт с длиной заметки (reward-механика)."""
    if not note:
        return 4  # микро-точка напоминалка
    # 6 .. 28 px в зависимости от длины
    n = len(note.strip())
    return max(6, min(28, 6 + n // 6))


# =====================
# Session State (данные)
# =====================
if "groups" not in st.session_state:
    # Порядок важен; стартуем с двух пустых групп
    st.session_state.groups: List[str] = ["Работа", "Личное"]

if "tracks" not in st.session_state:
    # список дорожек: {id, group, name}
    st.session_state.tracks: List[Dict] = []

if "entries" not in st.session_state:
    # отметки: {date: ISO, track_id: str, note: str}
    st.session_state.entries: List[Dict] = []

if "birthday" not in st.session_state:
    # по умолчанию 28 сентября
    st.session_state.birthday = {"m": 9, "d": 28}

# окно по умолчанию (без видимых контролов)
END = today()
START = END - timedelta(days=120)
all_days = pd.date_range(START, END, freq="D")

# =====================
# Шапка (минимализм, без контролов)
# =====================
now = datetime.now()
hour = now.hour
if 5 <= hour < 11:
    day_emoji = "🌅"
elif 11 <= hour < 17:
    day_emoji = "☀️"
elif 17 <= hour < 22:
    day_emoji = "🌇"
else:
    day_emoji = "🌙"

# метрики мотивации
m_first = start_of_month(END)
month_pct = int(round((END - m_first).days / max(1, days_in_month(END)) * 100))

b = st.session_state.birthday
next_bd_year = END.year if (END.month, END.day) <= (b["m"], b["d"]) else END.year + 1
next_bd = date(next_bd_year, b["m"], b["d"])
days_to_bd = (next_bd - END).days

colA, colB = st.columns([1, 2])
with colA:
    st.markdown(f"### {day_emoji} \- {END.strftime('%d %b %Y')}")
with colB:
    st.markdown(
        f"**Месяц пройден на ~{month_pct}%** · **до ДР {days_to_bd} дн.**",
    )

# =====================
# Подготовка данных для отрисовки
# =====================
# Категории (ось Y): группы как заголовки, под ними дорожки, внизу \"ДНИ\"
cat_labels: List[str] = []
CAT_GROUP_PREFIX = "▧ "  # визуальный заголовок группы (клик по нему добавляет дорожку)
CAT_TRACK_PREFIX = "• "  # дорожка

for g in st.session_state.groups:
    cat_labels.append(f"{CAT_GROUP_PREFIX}{g}")
    for t in st.session_state.tracks:
        if t["group"] == g:
            cat_labels.append(f"{CAT_TRACK_PREFIX}{t['name']}")

cat_labels.append("ДНИ")  # базовая шкала внизу

# маппинги для быстрого поиска
track_label_to_id: Dict[str, str] = {}
for t in st.session_state.tracks:
    track_label_to_id[f"{CAT_TRACK_PREFIX}{t['name']}"] = t["id"]

# entries -> DataFrame
if st.session_state.entries:
    df_e = pd.DataFrame(st.session_state.entries)
    df_e["date"] = pd.to_datetime(df_e["date"]).dt.date
else:
    df_e = pd.DataFrame(columns=["date", "track_id", "note"])  # пусто

# =====================
# Фигура (нотная тетрадь)
# =====================
fig = go.Figure()

# 0) текущая дата — вертикальная тонкая линия
fig.add_vline(x=pd.Timestamp(END), line_width=1, line_dash="dot", line_color="rgba(0,0,0,0.4)")

# 1) базовая нижняя шкала ДНИ: тонкая серая линия + тики по дням
fig.add_trace(
    go.Scatter(
        x=all_days,
        y=["ДНИ"] * len(all_days),
        mode="lines",
        line=dict(color="rgba(0,0,0,0.25)", width=1),
        hoverinfo="skip",
        showlegend=False,
    )
)
# тики (вертикальные риски) — ежедн., но очень лёгкие
fig.add_trace(
    go.Scatter(
        x=all_days,
        y=["ДНИ"] * len(all_days),
        mode="markers",
        marker=dict(symbol="line-ns-open", size=12, color="rgba(0,0,0,0.25)"),
        hoverinfo="skip",
        showlegend=False,
    )
)

# 2) группы: пунктирные линии (клик по строке добавляет дорожку)
for g in st.session_state.groups:
    ylab = f"{CAT_GROUP_PREFIX}{g}"
    # тонкая линия по всей ширине окна
    fig.add_trace(
        go.Scatter(
            x=[all_days.min(), all_days.max()],
            y=[ylab, ylab],
            mode="lines",
            line=dict(color="rgba(0,0,0,0.15)", width=1, dash="dot"),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    # невидимые точки-кликкачеры по каждому дню
    fig.add_trace(
        go.Scatter(
            x=all_days,
            y=[ylab] * len(all_days),
            mode="markers",
            marker=dict(size=8, color="rgba(0,0,0,0.001)"),
            hoverinfo="skip",
            name=f"add-track-{g}",
            showlegend=False,
        )
    )

# 3) дорожки: тонкие линии + точки/ноты
for g in st.session_state.groups:
    for t in [t for t in st.session_state.tracks if t["group"] == g]:
        ylab = f"{CAT_TRACK_PREFIX}{t['name']}"
        # тонкая линия
        fig.add_trace(
            go.Scatter(
                x=[all_days.min(), all_days.max()],
                y=[ylab, ylab],
                mode="lines",
                line=dict(color="rgba(0,0,0,0.25)", width=1),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        # точки/ноты из entries
        if not df_e.empty:
            dsub = df_e.loc[df_e["track_id"] == t["id"]].copy()
        else:
            dsub = pd.DataFrame(columns=df_e.columns)
        if not dsub.empty:
            dsub = dsub[(dsub["date"] >= START) & (dsub["date"] <= END)]
            if not dsub.empty:
                sizes = [compute_size(n) for n in dsub["note"].tolist()]
                # reward: если есть заметка — символ меняется на «звезду» (в будущем можно заменить на ноту)
                symbols = ["star" if (n and n.strip()) else "circle-open" for n in dsub["note"].tolist()]
                fig.add_trace(
                    go.Scatter(
                        x=pd.to_datetime(dsub["date"]),
                        y=[ylab] * len(dsub),
                        mode="markers",
                        marker=dict(size=sizes, symbol=symbols, line=dict(width=1, color="rgba(0,0,0,0.55)"), color="rgba(0,0,0,0.55)"),
                        hovertemplate=(
                            "<b>" + t['name'] + "</b><br>Дата: %{x|%Y-%m-%d}<br>Заметка: %{text}<extra></extra>"
                        ),
                        text=[(s if s else "—") for s in dsub["note"].tolist()],
                        showlegend=False,
                    )
                )
        # кликабельный слой по дням (чтобы добавлять заметки одним кликом)
        fig.add_trace(
            go.Scatter(
                x=all_days,
                y=[ylab] * len(all_days),
                mode="markers",
                marker=dict(size=10, color="rgba(0,0,0,0.001)"),
                hoverinfo="skip",
                name=f"add-note-{t['id']}",
                showlegend=False,
            )
        )

# Оформление — полностью минималистично
fig.update_layout(
    height=max(380, 52 * max(2, len(cat_labels))),
    margin=dict(l=20, r=20, t=10, b=10),
    xaxis=dict(
        range=[pd.Timestamp(START), pd.Timestamp(END)],
        showgrid=False,
        showline=False,
        zeroline=False,
        tickformat="%d %b",
        ticks="outside",
        ticklen=4,
        tickcolor="rgba(0,0,0,0.3)",
    ),
    yaxis=dict(
        categoryorder="array",
        categoryarray=cat_labels[::-1],  # ДНИ внизу
        showgrid=False,
        showline=False,
        zeroline=False,
        title="",
    ),
    hovermode="closest",
)

# Без лишних кнопок
config = {"displaylogo": False, "displayModeBar": False}

# Рендер с обработкой кликов
clicked = plotly_events(
    fig,
    click_event=True,
    select_event=False,
    hover_event=False,
    override_height=fig.layout.height,
    override_width="100%",
    key="timeline-minimal",
    config=config,
)

# =====================
# Обработка кликов (добавление дорожек/заметок)
# =====================
if clicked:
    pt = clicked[0]
    ylab = pt.get("y")
    xval = to_date(pt.get("x"))

    if isinstance(ylab, str) and ylab.startswith(CAT_GROUP_PREFIX):
        # клик по заголовку группы => добавить дорожку
        gname = ylab.replace(CAT_GROUP_PREFIX, "", 1)
        with st.modal(f"Новая дорожка в группе ‘{gname}’"):
            name = st.text_input("Название дорожки", max_chars=48)
            if st.button("Добавить", use_container_width=True):
                if name:
                    new_id = f"{gname}:{name}:{int(datetime.now().timestamp())}"
                    st.session_state.tracks.append({"id": new_id, "group": gname, "name": name})
                    st.rerun()
                else:
                    st.warning("Введите название")

    elif isinstance(ylab, str) and ylab.startswith(CAT_TRACK_PREFIX):
        # клик по дорожке => добавить/редактировать заметку на выбранную дату
        tid = track_label_to_id.get(ylab)
        if tid:
            # найти существующую запись для этой даты
            idx = None
            for i, e in enumerate(st.session_state.entries):
                if e["track_id"] == tid and to_date(e["date"]) == xval:
                    idx = i
                    break
            existing = st.session_state.entries[idx]["note"] if idx is not None else ""

            with st.modal(f"Заметка — {ylab.replace(CAT_TRACK_PREFIX,'',1)} · {xval.isoformat()}"):
                note = st.text_area("Текст заметки", value=existing, height=160, label_visibility="collapsed")
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("Сохранить", use_container_width=True):
                        if idx is None:
                            st.session_state.entries.append({"date": xval.isoformat(), "track_id": tid, "note": note.strip()})
                        else:
                            st.session_state.entries[idx]["note"] = note.strip()
                        st.rerun()
                with c2:
                    if st.button("Удалить точку", use_container_width=True):
                        if idx is not None:
                            st.session_state.entries.pop(idx)
                        st.rerun()

# Низ — лёгкая подсказка (без контролов)
st.caption("Клик по названию группы — добавить дорожку. Клик по строке дорожки — создать/изменить заметку на выбранную дату. Точки без заметок — микро-напоминалки; с текстом превращаются в ‘звёзды’ и растут.")

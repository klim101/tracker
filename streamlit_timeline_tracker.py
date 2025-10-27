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

# Опциональный компонент кликов; без него приложение работает в статичном режиме
try:
    from streamlit_plotly_events import plotly_events as _plotly_events
    _HAS_EVENTS = True
except Exception:
    _HAS_EVENTS = False
    def _plotly_events(fig, **kwargs):
        st.plotly_chart(fig, use_container_width=True, config=kwargs.get("config"))
        return []

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


def dot_size_empty() -> int:
    return 2  # почти точка


def note_size(note: str) -> int:
    """Размер ‘ноты’ растёт с длиной заметки (reward‑механика)."""
    n = len((note or "").strip())
    if n <= 0:
        return dot_size_empty()
    # 10..28
    return max(10, min(28, 8 + n // 4))


# =====================
# Session State (данные)
# =====================
if "groups" not in st.session_state:
    st.session_state.groups: List[str] = ["Работа", "Личное"]

if "tracks" not in st.session_state:
    # список дорожек: {id, group, name}
    st.session_state.tracks: List[Dict] = []

if "entries" not in st.session_state:
    # отметки: {date: ISO, track_id: str, note: str}
    st.session_state.entries: List[Dict] = []

if "birthday" not in st.session_state:
    st.session_state.birthday = {"m": 9, "d": 28}  # по умолчанию 28 сентября

# Временное окно (120 дней, без контролов)
END = today()
START = END - timedelta(days=120)
all_days = pd.date_range(START, END, freq="D")

# =====================
# Шапка (минимализм)
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

m_first = start_of_month(END)
month_pct = int(round(((END - m_first).days) / max(1, days_in_month(END)) * 100))

b = st.session_state.birthday
next_bd_year = END.year if (END.month, END.day) <= (b["m"], b["d"]) else END.year + 1
next_bd = date(next_bd_year, b["m"], b["d"])
days_to_bd = (next_bd - END).days

colA, colB = st.columns([1, 2])
with colA:
    st.markdown(f"### {day_emoji} \- {END.strftime('%d %b %Y')}")
with colB:
    st.markdown(f"**Месяц ~{month_pct}%** · **до ДР {days_to_bd} дн.**")

# =====================
# Категории (ось Y)
# =====================
NEW_GROUP_LABEL = "▧ + Новая подгруппа"
CAT_GROUP_PREFIX = "▧ "     # заголовок группы
CAT_TRACK_PREFIX = "• "     # дорожка

cat_labels: List[str] = [NEW_GROUP_LABEL]
for g in st.session_state.groups:
    cat_labels.append(f"{CAT_GROUP_PREFIX}{g}")
    for t in st.session_state.tracks:
        if t["group"] == g:
            cat_labels.append(f"{CAT_TRACK_PREFIX}{t['name']}")
cat_labels.append("ДНИ")  # базовая шкала

# маппинги
track_label_to_id: Dict[str, str] = {}
for t in st.session_state.tracks:
    track_label_to_id[f"{CAT_TRACK_PREFIX}{t['name']}"] = t["id"]

# entries -> df
if st.session_state.entries:
    df_e = pd.DataFrame(st.session_state.entries)
    df_e["date"] = pd.to_datetime(df_e["date"]).dt.date
else:
    df_e = pd.DataFrame(columns=["date", "track_id", "note"])  # пусто

# =====================
# Фигура (нотная тетрадь)
# =====================
fig = go.Figure()

# Вертикальная линия «сейчас»
fig.add_vline(x=pd.Timestamp(END), line_width=1, line_dash="dot", line_color="rgba(0,0,0,0.45)")
# Маленький символ времени суток на базовой линии
fig.add_annotation(x=pd.Timestamp(END), y="ДНИ", text=day_emoji, showarrow=False, yshift=10, opacity=0.85)

# Базовая нижняя шкала «ДНИ»
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
# Ежедневные риски
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

# Строка «Новая подгруппа» — лёгкая пунктирная + кликабельный слой
fig.add_trace(
    go.Scatter(
        x=[all_days.min(), all_days.max()],
        y=[NEW_GROUP_LABEL, NEW_GROUP_LABEL],
        mode="lines",
        line=dict(color="rgba(0,0,0,0.12)", width=1, dash="dot"),
        hoverinfo="skip",
        showlegend=False,
    )
)
fig.add_trace(
    go.Scatter(
        x=all_days,
        y=[NEW_GROUP_LABEL] * len(all_days),
        mode="markers",
        marker=dict(size=10, color="rgba(0,0,0,0.001)"),
        hoverinfo="skip",
        name="add-group",
        showlegend=False,
    )
)

# Строки групп + кликабельные слои для добавления дорожек
for g in st.session_state.groups:
    ylab = f"{CAT_GROUP_PREFIX}{g}"
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
    fig.add_trace(
        go.Scatter(
            x=all_days,
            y=[ylab] * len(all_days),
            mode="markers",
            marker=dict(size=10, color="rgba(0,0,0,0.001)"),
            hoverinfo="skip",
            name=f"add-track-{g}",
            showlegend=False,
        )
    )

# Дорожки: тонкая линия + точки (пустые) и ноты (с заметкой)
for g in st.session_state.groups:
    for t in [t for t in st.session_state.tracks if t["group"] == g]:
        ylab = f"{CAT_TRACK_PREFIX}{t['name']}"
        # линия дорожки
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
        # данные по точкам
        if not df_e.empty:
            dsub = df_e.loc[df_e["track_id"] == t["id"]].copy()
            dsub = dsub[(dsub["date"] >= START) & (dsub["date"] <= END)]
        else:
            dsub = pd.DataFrame(columns=df_e.columns)

        if not dsub.empty:
            # Пустые заметки -> маленькие кружки
            empty_mask = dsub["note"].fillna("").str.strip() == ""
            if empty_mask.any():
                d0 = dsub[empty_mask]
                fig.add_trace(
                    go.Scatter(
                        x=pd.to_datetime(d0["date"]),
                        y=[ylab] * len(d0),
                        mode="markers",
                        marker=dict(size=[dot_size_empty()] * len(d0), symbol="circle", color="rgba(0,0,0,0.55)"),
                        hovertemplate=(
                            "<b>" + t['name'] + "</b><br>Дата: %{x|%Y-%m-%d}<br>Заметка: —<extra></extra>"
                        ),
                        showlegend=False,
                    )
                )
            # Есть заметка -> рисуем символы нот ♪/♫ как текст
            filled = dsub[~empty_mask]
            if not filled.empty:
                # размер текста по содержимому
                sizes = [note_size(n) for n in filled["note"].tolist()]
                glyphs = ["♫" if len((n or '').strip()) > 24 else "♪" for n in filled["note"].tolist()]
                fig.add_trace(
                    go.Scatter(
                        x=pd.to_datetime(filled["date"]),
                        y=[ylab] * len(filled),
                        mode="text",
                        text=glyphs,
                        textposition="middle center",
                        textfont=dict(size=sizes, color="rgba(0,0,0,0.8)"),
                        hovertemplate=(
                            "<b>" + t['name'] + "</b><br>Дата: %{x|%Y-%m-%d}<br>Заметка: %{text_custom}<extra></extra>"
                        ),
                        text_custom=filled["note"].fillna("—"),
                        showlegend=False,
                    )
                )
        # невидимый слой для клика по датам данной дорожки
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

# Оформление (минимализм)
fig.update_layout(
    height=max(400, 56 * max(2, len(cat_labels))),
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

config = {"displaylogo": False, "displayModeBar": False}

# Рендер
clicked = _plotly_events(
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
# Обработка кликов (без кнопок/сайдбаров)
# =====================
if clicked:
    pt = clicked[0]
    ylab = pt.get("y")
    xval = to_date(pt.get("x"))

    # Добавить группу
    if isinstance(ylab, str) and ylab == NEW_GROUP_LABEL:
        with st.modal("Новая подгруппа"):
            gname = st.text_input("Название подгруппы", max_chars=48)
            if st.button("Добавить", use_container_width=True):
                if gname and gname not in st.session_state.groups:
                    st.session_state.groups.append(gname)
                    st.rerun()
                else:
                    st.warning("Введите уникальное название")

    # Добавить дорожку в группу
    elif isinstance(ylab, str) and ylab.startswith(CAT_GROUP_PREFIX):
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

    # Добавить/редактировать заметку на дорожке
    elif isinstance(ylab, str) and ylab.startswith(CAT_TRACK_PREFIX):
        tid = track_label_to_id.get(ylab)
        if tid:
            # поиск существующей записи
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

# Лёгкая подсказка
st.caption("Клик по ‘Новая подгруппа’ — создать группу. Клик по названию группы — добавить дорожку. Клик по дорожке — заметка на выбранную дату. Пустые точки — микро‑напоминалки; заметка превращает их в ноты ♪/♫ и увеличивает размер.")

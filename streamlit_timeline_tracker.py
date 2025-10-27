# Streamlit Timeline Tracker — single file app
# Author: ChatGPT (GPT-5 Thinking)
# Run: 1) pip install streamlit plotly pandas python-dateutil
#      2) streamlit run streamlit_timeline_tracker.py

from __future__ import annotations
import json
from datetime import date, timedelta, datetime
from typing import List, Dict

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Timeline Tracker", layout="wide")

# -----------------------------
# Helpers
# -----------------------------

def _today() -> date:
    return date.today()


def daterange(d0: date, d1: date) -> List[date]:
    """Inclusive [d0, d1] daily range."""
    days = (d1 - d0).days
    return [d0 + timedelta(days=i) for i in range(days + 1)]


def px_size(percent: int, min_px: int = 6, max_px: int = 28) -> int:
    if percent <= 0:
        return 0
    percent = max(0, min(100, int(percent)))
    return int(min_px + (max_px - min_px) * (percent / 100))


def to_iso(d: date | datetime | str) -> str:
    if isinstance(d, str):
        return d
    if isinstance(d, datetime):
        return d.date().isoformat()
    return d.isoformat()


# -----------------------------
# Session State init
# -----------------------------
if "groups" not in st.session_state:
    st.session_state.groups: List[str] = ["Личное", "Работа"]

if "projects" not in st.session_state:
    # project -> group
    st.session_state.projects: Dict[str, str] = {
        "ЗОЖ": "Личное",
        "Диссертация": "Работа",
    }

if "entries" not in st.session_state:
    # entries: list of {date:str, project:str, group:str, percent:int, note:str}
    st.session_state.entries: List[Dict] = []

if "palette" not in st.session_state:
    st.session_state.palette = px.colors.qualitative.Plotly + px.colors.qualitative.D3

# -----------------------------
# Sidebar — Controls
# -----------------------------
with st.sidebar:
    st.header("⚙️ Настройки")

    # Time window presets
    preset = st.selectbox(
        "Окно по времени",
        (
            "30 дней",
            "60 дней",
            "90 дней",
            "6 месяцев",
            "12 месяцев",
            "Всё время",
        ),
        index=2,
    )
    end_date = st.date_input("Конец периода", _today())

    if preset == "30 дней":
        start_date = end_date - timedelta(days=29)
    elif preset == "60 дней":
        start_date = end_date - timedelta(days=59)
    elif preset == "90 дней":
        start_date = end_date - timedelta(days=89)
    elif preset == "6 месяцев":
        start_date = end_date - relativedelta(months=6) + timedelta(days=1)
    elif preset == "12 месяцев":
        start_date = end_date - relativedelta(months=12) + timedelta(days=1)
    else:
        # Всё время — если есть отметки, от первой; иначе 180 дней назад
        if st.session_state.entries:
            start_date = min(datetime.fromisoformat(e["date"]).date() for e in st.session_state.entries)
        else:
            start_date = end_date - timedelta(days=179)

    # Group filter
    groups = list(dict.fromkeys(st.session_state.groups))
    groups_to_show = st.multiselect("Показывать группы", options=groups, default=groups)

    st.divider()

    with st.expander("➕ Добавить группу"):
        new_group = st.text_input("Название группы", key="add_group_name")
        if st.button("Добавить группу", use_container_width=True, key="btn_add_group"):
            if new_group and new_group not in st.session_state.groups:
                st.session_state.groups.append(new_group)
                st.success(f"Группа ‘{new_group}’ добавлена")
            else:
                st.warning("Введите уникальное название группы")

    with st.expander("➕ Добавить проект/дело"):
        proj_name = st.text_input("Название проекта", key="add_proj_name")
        proj_group = st.selectbox("Группа", options=list(st.session_state.groups), key="add_proj_group")
        if st.button("Добавить проект", use_container_width=True, key="btn_add_project"):
            if proj_name:
                st.session_state.projects[proj_name] = proj_group
                st.success(f"Проект ‘{proj_name}’ добавлен в группу ‘{proj_group}’")
            else:
                st.warning("Укажите название проекта")

    with st.expander("📝 Добавить отметку на шкале"):
        if not st.session_state.projects:
            st.info("Сначала добавьте проект")
        else:
            sel_proj = st.selectbox("Проект", options=sorted(st.session_state.projects.keys()), key="mark_proj")
            mark_date = st.date_input("Дата", _today(), key="mark_date")
            mark_percent = st.slider("Размер кружка (0–100%)", 0, 100, 50, step=5, key="mark_percent")
            mark_note = st.text_area("Заметка (опционально)", key="mark_note", placeholder="Что произошло/что сделано")
            if st.button("Сохранить отметку", use_container_width=True, key="btn_add_mark"):
                entry = {
                    "date": to_iso(mark_date),
                    "project": sel_proj,
                    "group": st.session_state.projects.get(sel_proj, ""),
                    "percent": int(mark_percent),
                    "note": mark_note.strip(),
                }
                st.session_state.entries.append(entry)
                st.success("Отметка добавлена")

    st.divider()
    with st.expander("⬇️ Экспорт / ⬆️ Импорт"):
        if st.button("Скачать JSON", use_container_width=True):
            payload = {
                "groups": st.session_state.groups,
                "projects": st.session_state.projects,
                "entries": st.session_state.entries,
            }
            st.download_button(
                "Скачать файл",
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"timeline_{_today().isoformat()}.json",
                mime="application/json",
            )
        uploaded = st.file_uploader("Загрузить JSON", type=["json"])
        if uploaded is not None:
            try:
                payload = json.load(uploaded)
                st.session_state.groups = list(payload.get("groups", []))
                st.session_state.projects = dict(payload.get("projects", {}))
                st.session_state.entries = list(payload.get("entries", []))
                st.success("Данные импортированы")
            except Exception as e:
                st.error(f"Не удалось импортировать: {e}")

# -----------------------------
# Main — Title
# -----------------------------
col_l, col_r = st.columns([1, 1])
with col_l:
    st.title("🗓️ Timeline Tracker — кружочки по дням")
with col_r:
    st.caption("Наведите на кружок, чтобы увидеть заметку. Масштабируйте колесом мыши или ползунком под графиком.")

# -----------------------------
# Build plot data
# -----------------------------

start_date = min(start_date, end_date)
all_days = pd.date_range(start=start_date, end=end_date, freq="D")

# Determine visible projects by group filter
visible_projects = [p for p, g in st.session_state.projects.items() if g in groups_to_show]

# Prepare entries df
if st.session_state.entries:
    df_e = pd.DataFrame(st.session_state.entries)
    # coerce types
    df_e["date"] = pd.to_datetime(df_e["date"]).dt.date
    df_e["percent"] = pd.to_numeric(df_e["percent"], errors="coerce").fillna(0).astype(int)
    df_e["group"] = df_e["group"].astype(str)
    df_e["project"] = df_e["project"].astype(str)
else:
    df_e = pd.DataFrame(columns=["date", "project", "group", "percent", "note"])  # empty

# Filter entries by window & group filter
mask = (df_e["date"].between(start_date, end_date)) if not df_e.empty else []
if not df_e.empty:
    df_e_win = df_e.loc[mask & (df_e["project"].isin(visible_projects))].copy()
else:
    df_e_win = df_e.copy()

# Category labels (y-axis): baseline first, then projects grouped
category_labels: List[str] = ["⏱ День"]
for g in groups_to_show:
    for p in sorted([p for p, gg in st.session_state.projects.items() if gg == g]):
        category_labels.append(f"{g} • {p}")

# Map project->category label and color
proj_to_cat = {p: f"{st.session_state.projects[p]} • {p}" for p in st.session_state.projects}
proj_colors = {}
for idx, p in enumerate(sorted(st.session_state.projects.keys())):
    proj_colors[p] = st.session_state.palette[idx % len(st.session_state.palette)]

# -----------------------------
# Figure
# -----------------------------
fig = go.Figure()

# 1) Baseline "Day" — gray line + daily markers 100%
fig.add_trace(
    go.Scatter(
        x=all_days,
        y=["⏱ День"] * len(all_days),
        mode="lines+markers",
        line=dict(color="#C2C7CF", width=1),
        marker=dict(color="#C2C7CF", size=[px_size(100)] * len(all_days)),
        hovertemplate="%{x|%Y-%m-%d}<extra>День</extra>",
        name="День",
        showlegend=False,
    )
)

# 2) Project swimlanes — dotted line across window + markers for entries
for g in groups_to_show:
    group_projects = [p for p, gg in st.session_state.projects.items() if gg == g]
    for p in sorted(group_projects):
        cat = proj_to_cat[p]
        # dotted guide line across the window
        fig.add_trace(
            go.Scatter(
                x=[all_days.min(), all_days.max()],
                y=[cat, cat],
                mode="lines",
                line=dict(color="rgba(0,0,0,0.15)", width=1, dash="dot"),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        # markers for actual entries (if any)
        if not df_e_win.empty:
            dsub = df_e_win.loc[df_e_win["project"] == p]
        else:
            dsub = pd.DataFrame(columns=df_e_win.columns)
        if not dsub.empty:
            sizes = [px_size(int(v)) for v in dsub["percent"].tolist()]
            custom = list(
                zip(
                    [g] * len(dsub),
                    [p] * len(dsub),
                    dsub["percent"].tolist(),
                    [s if s else "—" for s in dsub["note"].fillna("").tolist()],
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=pd.to_datetime(dsub["date"]),
                    y=[cat] * len(dsub),
                    mode="markers",
                    marker=dict(size=sizes, color=proj_colors.get(p)),
                    customdata=custom,
                    hovertemplate=(
                        "<b>%{customdata[1]}</b><br>Группа: %{customdata[0]}<br>Дата: %{x|%Y-%m-%d}"
                        "<br>Размер: %{customdata[2]}%<br>Заметка: %{customdata[3]}<extra></extra>"
                    ),
                    name=cat,
                    showlegend=False,
                )
            )

# Layout
row_height = 56
fig_height = max(400, row_height * max(2, len(category_labels)))
fig.update_layout(
    height=fig_height,
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis=dict(
        categoryorder="array",
        categoryarray=category_labels[::-1],  # put baseline at the bottom
        title="",
    ),
    xaxis=dict(
        title="Дата",
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=7, label="7d", step="day", stepmode="backward"),
                    dict(count=30, label="30d", step="day", stepmode="backward"),
                    dict(count=90, label="90d", step="day", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(step="all"),
                ]
            )
        ),
        rangeslider=dict(visible=True),
    ),
    hovermode="closest",
)

# Limit visible window to [start_date, end_date]
fig.update_xaxes(range=[pd.Timestamp(start_date), pd.Timestamp(end_date)])

st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

# -----------------------------
# Editor (optional)
# -----------------------------
with st.expander("📋 Таблица отметок (редактирование/удаление)"):
    if st.session_state.entries:
        df_show = pd.DataFrame(st.session_state.entries)
        df_show = df_show[["date", "group", "project", "percent", "note"]]
        edited = st.data_editor(
            df_show,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "percent": st.column_config.NumberColumn("percent", min_value=0, max_value=100, step=1),
            },
        )
        # Persist changes back to session_state
        try:
            # Coerce types
            edited["date"] = pd.to_datetime(edited["date"]).dt.date
            edited["percent"] = pd.to_numeric(edited["percent"], errors="coerce").fillna(0).astype(int)
            # Overwrite entries
            st.session_state.entries = [
                {
                    "date": to_iso(r["date"]),
                    "group": str(r["group"]).strip(),
                    "project": str(r["project"]).strip(),
                    "percent": int(r["percent"]),
                    "note": str(r["note"]).strip(),
                }
                for _, r in edited.iterrows()
            ]
        except Exception as e:
            st.warning(f"Не удалось применить изменения: {e}")
    else:
        st.info("Пока нет данных")

# -----------------------------
# Footer
# -----------------------------
st.caption(
    """
    ▶️ Подсказки:
    • Добавляйте группы и проекты в сайдбаре; затем создавайте отметки по дням с процентом (0–100%).  
    • Серая нижняя линия — базовая шкала времени: каждый день = 100%.  
    • Масштабируйте график колесом мыши или с помощью ползунка снизу; используйте пресеты окна слева.  
    • Экспортируйте/импортируйте JSON, если хотите переносить данные между сессиями.
    """
)

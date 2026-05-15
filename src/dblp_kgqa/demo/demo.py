import contextlib
import json
import logging
from typing import get_args

import pandas as pd
import streamlit as st
from rich.logging import RichHandler
from streamlit_ace import st_ace

# LOGGING ---------------------------------------------------------------------

stream_handler = RichHandler(
    rich_tracebacks=True, show_time=False, show_path=False
)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(logging.Formatter("%(name)s >> %(message)s"))

logging.basicConfig(
    level=logging.WARNING,
    force=True,
    handlers=[stream_handler],
)
logging.getLogger("dblp_kgqa").setLevel(logging.DEBUG)


class _QueryErrorCapture(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        marker = "Error: "
        error = msg.split(marker, 1)[1] if marker in msg else msg
        with contextlib.suppress(Exception):
            st.session_state.last_query_error = error


_endpoint_logger = logging.getLogger(
    "dblp_kgqa.modules.query_executor.endpoint"
)
if not any(
    isinstance(h, _QueryErrorCapture) for h in _endpoint_logger.handlers
):
    _endpoint_logger.addHandler(_QueryErrorCapture())


from dblp_kgqa import PROJECT_ROOT  # noqa: E402
from dblp_kgqa.demo.schemas import DemoConfig  # noqa: E402
from dblp_kgqa.modules.relation_linker.full_schema import (  # noqa: E402
    PROPERTIES_URI_AND_DESCRIPTION,
)
from dblp_kgqa.modules.schemas import (  # noqa: E402
    AskResult,
    LinkedEntity,
    NamedEntity,
    PipelineOutput,
    SelectResult,
    SparqlResult,
)
from dblp_kgqa.pipeline.factory import PipelineFactory  # noqa: E402
from dblp_kgqa.pipeline.pipeline import KGQAPipeline  # noqa: E402
from dblp_kgqa.services.dblp_quad import QUERY_TYPE  # noqa: E402
from dblp_kgqa.services.registry import (  # noqa: E402
    ServiceRegistry,
    ServiceRegistryConfig,
)
from dblp_kgqa.utils.yaml import yaml_load  # noqa: E402

# CONSTANTS -------------------------------------------------------------------

CONFIG_DIR = PROJECT_ROOT / "config"

QUERY_TYPES = list(get_args(QUERY_TYPE))
ENTITY_TYPES = ["person", "venue", "publication"]

STEP_TITLES = {
    "info_extractor": "Info Extractor",
    "entity_linker": "Entity Linker",
    "relation_linker": "Relation Linker",
    "query_generator": "Query Generator",
    "query_executor": "Query Executor",
}
STEP_ORDER = tuple(STEP_TITLES)
CONTAINER_STEPS = STEP_ORDER[:3]

QUERY_TYPE_INFO: dict[str, dict[str, str]] = {
    "SINGLE_FACT": {
        "description": "A question that can be answered using a single fact.",
        "example": (
            "What are the papers written by the person Sabrina Senatore?"
        ),
    },
    "MULTI_FACT": {
        "description": (
            "A question that requires connecting two or more facts to answer."
        ),
        "example": "In which venues has Wazir Muhammad published?",
    },
    "DOUBLE_INTENT": {
        "description": (
            "A question that poses two user intentions, usually about the "
            "same subject."
        ),
        "example": (
            "Mention the papers published by Wazir Muhammad and in which year."
        ),
    },
    "BOOLEAN": {
        "description": "A question on whether a given fact is true or false.",
        "example": (
            "Did Ming-Wang Cheng publish the paper 'Individual Cell "
            "Equalization for Series Connected Lithium-Ion Batteries'?"
        ),
    },
    "NEGATION": {
        "description": (
            "A question that negates the answer to a Boolean question."
        ),
        "example": (
            "Was the paper 'A Priority Queue Transform' not published by the "
            "person Michael L. Fredman?"
        ),
    },
    "DOUBLE_NEGATION": {
        "description": (
            "A question that negates the answer to a Boolean question twice."
        ),
        "example": (
            "Wasn't the paper 'Modeling Syntactic Complexity with P Systems: "
            "A Preview' not not published by the person named Benedek Nagy?"
        ),
    },
    "UNION": {
        "description": (
            "A question that covers a single intent for multiple subjects "
            "at the same time."
        ),
        "example": (
            "In VL/HCC and Comput. Music. J., what papers did S. Conversy "
            "publish?"
        ),
    },
    "COUNT": {
        "description": "A question about the count of occurrences of facts.",
        "example": (
            "Report the count of papers that Fanggang Wang has published in "
            "IEEE Wirel. Commun.."
        ),
    },
    "SUPERLATIVE+COMPARATIVE": {
        "description": (
            "A question that asks for the maximum or minimum for a subject "
            "(superlative) or compares values between two subjects "
            "(comparative)."
        ),
        "example": ("When was the first paper by Tom Tollenaere published?"),
    },
    "DISAMBIGUATION": {
        "description": (
            "A question that requires identifying the correct subject in "
            "the question, often by relying on a partial description such "
            "as a keyword extracted from the title of a publication, "
            "instead of the full title."
        ),
        "example": (
            "Mention the publication on neural networks that Sabrina "
            "Senatore published in ECAI."
        ),
    },
}

# PIPELINE LOADING ------------------------------------------------------------


@st.cache_resource(show_spinner="Loading services and pipeline...")
def load_pipeline() -> KGQAPipeline:
    services_config = yaml_load(
        ServiceRegistryConfig, CONFIG_DIR / "services.yml"
    )
    demo_config = yaml_load(DemoConfig, CONFIG_DIR / "demo.yml")
    registry = ServiceRegistry()
    registry.load_services(services_config)
    return PipelineFactory.create(demo_config.pipeline_config, registry)


# STATE -----------------------------------------------------------------------

_TRANSIENT_KEYS = (
    "relation_linker_rows",
    "relation_linker_initial_schema",
    "last_query_error",
    "info_extractor_initial_rows",
    "edit_named_entities",
    "edit_query_type",
)


def _default_state() -> dict[str, object]:
    return {
        "pipeline_iter": None,
        "state": None,
        "submitted_question": None,
        "steps_locked": [],
        "pending_step": None,
        "step_error": None,
        "failing_step": None,
        "advance_pending": False,
    }


def init_state() -> None:
    for key, value in _default_state().items():
        st.session_state.setdefault(key, value)


def reset_pipeline() -> None:
    for key, value in _default_state().items():
        st.session_state[key] = value
    for key in _TRANSIENT_KEYS:
        st.session_state.pop(key, None)


def advance(target: str) -> None:
    try:
        step_name, state = next(st.session_state.pipeline_iter)
        st.session_state.state = state
        st.session_state.pending_step = step_name
    except Exception as exc:
        st.session_state.step_error = f"{type(exc).__name__}: {exc}"
        st.session_state.failing_step = target


def start_pipeline(pipeline: KGQAPipeline, question: str) -> None:
    reset_pipeline()
    st.session_state.submitted_question = question
    st.session_state.pipeline_iter = pipeline.run_iter(question)
    first_step = STEP_ORDER[0]
    with st.spinner(f"Running {STEP_TITLES[first_step]}..."):
        advance(first_step)


def handle_advance() -> None:
    st.session_state.advance_pending = False
    next_step = STEP_ORDER[STEP_ORDER.index(st.session_state.pending_step) + 1]
    if next_step == "query_generator":
        with st.spinner("Generating SPARQL query..."):
            advance("query_generator")
        if st.session_state.step_error is None:
            with st.spinner("Running query..."):
                advance("query_executor")
    else:
        with st.spinner(f"Running {STEP_TITLES[next_step]}..."):
            advance(next_step)


# UTILS -----------------------------------------------------------------------


def _strip_uri_brackets(uri: str) -> str:
    return uri[1:-1] if uri.startswith("<") and uri.endswith(">") else uri


def _wrap_uri_brackets(uri: str) -> str:
    if not uri or (uri.startswith("<") and uri.endswith(">")):
        return uri
    return f"<{uri}>"


def _parse_schema_context(
    schema_context: list[str],
) -> dict[str, dict[str, str]]:
    if not schema_context:
        return {}
    try:
        parsed = json.loads(schema_context[0])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


# RENDERING: LOCKED (read-only) STEPS -----------------------------------------


def render_locked_step(step: str, state: PipelineOutput) -> None:
    with st.expander(f"✅ {STEP_TITLES[step]}", expanded=False):
        VIEW_RENDERERS[step](state)


def _render_info_extractor_view(state: PipelineOutput) -> None:
    extracted = state.extracted_info
    st.markdown(f"**Query type:** `{extracted.query_type}`")
    if extracted.named_entities:
        st.dataframe(
            pd.DataFrame([e.model_dump() for e in extracted.named_entities]),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("(no named entities)")


def _render_entity_linker_view(state: PipelineOutput) -> None:
    linked = state.linked_entities.linked_entities
    if linked:
        rows = [
            {
                "name": e.name,
                "uri": _strip_uri_brackets(e.uri),
                "type": e.type,
            }
            for e in linked
        ]
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("(no linked entities)")


def _render_relation_linker_view(state: PipelineOutput) -> None:
    schema = _parse_schema_context(state.linked_relation.schema_context)
    if not schema:
        st.caption("(no relations selected)")
        return
    rows = [{"name": name, **props} for name, props in schema.items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _render_query_executor_view(state: PipelineOutput) -> None:
    if state.sparql_result is None:
        err = st.session_state.get("last_query_error")
        suffix = f": `{err}`" if err else "."
        st.error(f"Query execution failed{suffix}")
        return
    _render_sparql_result(state.sparql_result)


# RENDERING: PENDING (editable) STEP ------------------------------------------


def render_pending_step(step: str, state: PipelineOutput) -> None:
    with st.container(border=True):
        st.subheader(f"⏳ {STEP_TITLES[step]}")
        EDIT_RENDERERS[step](state)
        if st.button("Continue ▶", type="primary", key=f"continue_{step}"):
            st.session_state.steps_locked.append(step)
            st.session_state.advance_pending = True
            st.rerun()


def _render_info_extractor_edit(state: PipelineOutput) -> None:
    extracted = state.extracted_info
    current_qt = (
        extracted.query_type
        if extracted.query_type in QUERY_TYPES
        else QUERY_TYPES[0]
    )

    new_qt = (
        st.selectbox(
            "Query type",
            options=QUERY_TYPES,
            index=QUERY_TYPES.index(current_qt),
            key="edit_query_type",
        )
        or current_qt
    )
    info = QUERY_TYPE_INFO.get(new_qt)
    if info:
        st.info(
            f"**{new_qt}** — {info['description']}\n\n"
            f"*Example:* {info['example']}",
            icon=":material/info:",
        )

    st.markdown("**Named entities** — edit, add or remove rows:")
    if "info_extractor_initial_rows" not in st.session_state:
        initial_rows = [
            {"name": e.name, "type": e.type} for e in extracted.named_entities
        ]
        if not initial_rows:
            initial_rows = [{"name": "", "type": "person"}]
        st.session_state.info_extractor_initial_rows = pd.DataFrame(
            initial_rows
        )
    edited_df = st.data_editor(
        st.session_state.info_extractor_initial_rows,
        column_config={
            "name": st.column_config.TextColumn("Name", width="large"),
            "type": st.column_config.SelectboxColumn(
                "Type", options=ENTITY_TYPES, required=True
            ),
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="edit_named_entities",
    )

    extracted.query_type = new_qt
    extracted.named_entities = [
        NamedEntity(name=row["name"].strip(), type=row["type"])
        for _, row in edited_df.iterrows()
        if isinstance(row["name"], str) and row["name"].strip()
    ]


def _render_entity_linker_edit(state: PipelineOutput) -> None:
    linked = state.linked_entities.linked_entities
    st.markdown(
        "**Linked entities** — edit, add or remove rows. "
        "URIs are shown without angle brackets; they are added automatically "
        "before the query is built."
    )
    initial_rows = [
        {
            "name": e.name,
            "uri": _strip_uri_brackets(e.uri),
            "type": e.type,
        }
        for e in linked
    ]
    if not initial_rows:
        initial_rows = [{"name": "", "uri": "", "type": "person"}]
    edited_df = st.data_editor(
        pd.DataFrame(initial_rows),
        column_config={
            "name": st.column_config.TextColumn("Name", width="medium"),
            "uri": st.column_config.TextColumn("URI", width="large"),
            "type": st.column_config.TextColumn("Type", width="small"),
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="edit_linked_entities",
    )

    state.linked_entities.linked_entities = [
        LinkedEntity(
            name=row["name"].strip(),
            uri=_wrap_uri_brackets(
                row["uri"].strip() if isinstance(row["uri"], str) else ""
            ),
            type=row["type"].strip() if isinstance(row["type"], str) else "",
        )
        for _, row in edited_df.iterrows()
        if isinstance(row["name"], str) and row["name"].strip()
    ]


def _render_relation_linker_edit(state: PipelineOutput) -> None:
    st.markdown(
        "**Linked relations** — tick the relations to include. "
        "All DBLP schema predicates are listed below; descriptions are "
        "visible to help you pick the right one."
    )

    if "relation_linker_rows" not in st.session_state:
        initial_schema = _parse_schema_context(
            state.linked_relation.schema_context
        )
        selected_names = set(initial_schema.keys())
        rows = sorted(
            (
                {
                    "selected": name in selected_names,
                    "name": name,
                    "description": props["description"],
                    "IRI": props["IRI"],
                }
                for name, props in PROPERTIES_URI_AND_DESCRIPTION.items()
            ),
            key=lambda r: (not r["selected"], r["name"]),
        )
        st.session_state.relation_linker_rows = rows
        st.session_state.relation_linker_initial_schema = initial_schema

    df = pd.DataFrame(st.session_state.relation_linker_rows)
    initial_schema = st.session_state.relation_linker_initial_schema

    edited_df = st.data_editor(
        df,
        column_config={
            "selected": st.column_config.CheckboxColumn(
                "Selected", width="small"
            ),
            "name": st.column_config.TextColumn(
                "Name", disabled=True, width="medium"
            ),
            "description": st.column_config.TextColumn(
                "Description", disabled=True, width="large"
            ),
            "IRI": st.column_config.TextColumn(
                "IRI", disabled=True, width="medium"
            ),
        },
        hide_index=True,
        width="stretch",
        height=400,
        key="edit_relations",
    )

    new_schema: dict[str, dict[str, str]] = {}
    for _, row in edited_df.iterrows():
        if not row["selected"]:
            continue
        name = row["name"]
        if name in initial_schema:
            new_schema[name] = initial_schema[name]
        else:
            full = PROPERTIES_URI_AND_DESCRIPTION[name]
            new_schema[name] = {
                "IRI": full["IRI"],
                "description": full["description"],
                "domain": "Entity",
                "range": "literal",
            }
    state.linked_relation.schema_context = [json.dumps(new_schema, indent=4)]


def _render_query_panel(state: PipelineOutput) -> None:
    with st.container(border=True):
        st.subheader("Query")
        st.markdown("**Generated SPARQL query** — edit and run again:")
        new_query = st_ace(
            value=state.generated_query.query or "",
            language="sparql",
            theme="tomorrow_night",
            keybinding="vscode",
            font_size=16,
            tab_size=2,
            wrap=True,
            show_gutter=False,
            show_print_margin=False,
            auto_update=True,
            key="query_panel_editor",
        )
        if new_query and new_query.strip():
            state.generated_query.query = new_query

        if st.button(
            "Run query",
            type="primary",
            icon=":material/play_arrow:",
            key="run_query",
        ):
            with st.spinner("Running query..."):
                state.sparql_result = load_pipeline().query_executor(state)
            st.rerun()

        st.divider()
        _render_query_executor_view(state)


def _render_sparql_result(sparql_result: SparqlResult) -> None:
    root = sparql_result.root
    if isinstance(root, AskResult):
        verdict = "TRUE ✅" if root.boolean else "FALSE ❌"
        st.markdown(f"### Answer: {verdict}")
        return

    assert isinstance(root, SelectResult)
    bindings = root.results.bindings
    variables = root.head.vars
    if not bindings:
        st.info("No results.")
        return

    uri_columns = {
        var
        for binding in bindings
        for var, val in binding.items()
        if val.type == "uri"
    }
    rows = [
        {
            var: binding[var].value if var in binding else None
            for var in variables
        }
        for binding in bindings
    ]
    column_config = {
        var: st.column_config.LinkColumn(var) for var in uri_columns
    }
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config=column_config,
    )
    st.caption(f"{len(rows)} row(s)")


# DISPATCH --------------------------------------------------------------------

VIEW_RENDERERS = {
    "info_extractor": _render_info_extractor_view,
    "entity_linker": _render_entity_linker_view,
    "relation_linker": _render_relation_linker_view,
}

EDIT_RENDERERS = {
    "info_extractor": _render_info_extractor_edit,
    "entity_linker": _render_entity_linker_edit,
    "relation_linker": _render_relation_linker_edit,
}


# APP -------------------------------------------------------------------------

st.set_page_config(page_title="DBLP-KGQA Demo", layout="wide")
init_state()

st.title("DBLP-KGQA Demo")

pipeline = load_pipeline()

with st.container(border=True):
    question = st.text_area(
        "Question",
        value=st.session_state.submitted_question or "",
        placeholder="What are the papers written by Sabrina Senatore?",
        height=80,
        key="question_input",
    )
    run_clicked = st.button(
        "Run pipeline",
        type="primary",
        icon=":material/play_arrow:",
        disabled=not question.strip(),
    )

if run_clicked:
    start_pipeline(pipeline, question.strip())
    st.rerun()

if st.session_state.submitted_question is not None:
    with st.container(border=True):
        st.markdown(
            f"**Question:** _{st.session_state.submitted_question}_"
        )

    state: PipelineOutput | None = st.session_state.state
    if state is not None:
        for step in st.session_state.steps_locked:
            render_locked_step(step, state)

        if st.session_state.advance_pending:
            handle_advance()
            st.rerun()

        pending = st.session_state.pending_step
        if st.session_state.step_error:
            failing = st.session_state.failing_step or "unknown"
            st.error(
                f"Pipeline error during step `{failing}`: "
                f"{st.session_state.step_error}"
            )
        elif pending in CONTAINER_STEPS:
            render_pending_step(pending, state)
        elif pending in {"query_generator", "query_executor"}:
            st.divider()
            _render_query_panel(state)

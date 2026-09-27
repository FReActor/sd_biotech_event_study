"""Beat the AI: label real SEC filings, then compare with Claude Haiku."""

import numpy as np
import streamlit as st

from data import LABEL_COLORS
from product import LABEL_NAMES, load_quiz
from ui import page_intro, passage, reveal, scoreboard, tag

CHOICES = ["CLINICAL", "REGULATORY", "PRESENTATION", "OTHER"]

quiz = load_quiz()

page_intro(
    "Beat the AI",
    "Read the start of a real SEC filing and decide what it is. Then see what "
    "Claude Haiku said, and the right answer.",
)

# --- state --------------------------------------------------------------------------------
# A fresh random order per visitor; answers and scores live in session_state.
if "quiz_order" not in st.session_state:
    st.session_state["quiz_order"] = np.random.default_rng().permutation(len(quiz)).tolist()
    st.session_state["quiz_pos"] = 0
    st.session_state["quiz_guess"] = None
    st.session_state["quiz_you"] = 0
    st.session_state["quiz_ai"] = 0
    st.session_state["quiz_done"] = 0


def answer(choice: str) -> None:
    q = quiz.iloc[st.session_state["quiz_order"][st.session_state["quiz_pos"]]]
    st.session_state["quiz_guess"] = choice
    st.session_state["quiz_done"] += 1
    st.session_state["quiz_you"] += int(choice == q["answer"])
    st.session_state["quiz_ai"] += int(q["ai"] == q["answer"])


def next_question() -> None:
    st.session_state["quiz_pos"] = (st.session_state["quiz_pos"] + 1) % len(quiz)
    st.session_state["quiz_guess"] = None


def restart() -> None:
    for k in [k for k in st.session_state if k.startswith("quiz_")]:
        del st.session_state[k]


done = st.session_state["quiz_done"]
scoreboard(
    you=st.session_state["quiz_you"], ai=st.session_state["quiz_ai"], done=done,
    question=done + (0 if st.session_state["quiz_guess"] else 1),
)

q = quiz.iloc[st.session_state["quiz_order"][st.session_state["quiz_pos"]]]
passage(f"{q['company']} · filed {q['filing_date']}", q["passage"])

guess = st.session_state["quiz_guess"]
if guess is None:
    st.markdown("**What is this filing?**")
    cols = st.columns(len(CHOICES))
    for col, choice in zip(cols, CHOICES):
        col.button(LABEL_NAMES[choice], on_click=answer, args=(choice,),
                   width="stretch", key=f"quiz_btn_{choice}")
else:
    def chip(label: str) -> str:
        return tag(LABEL_NAMES[label], LABEL_COLORS[label])

    reveal([
        ("You", chip(guess), guess == q["answer"]),
        ("Claude Haiku", chip(q["ai"]), q["ai"] == q["answer"]),
        ("Answer", chip(q["answer"]), None),
    ])
    if q["move"] == q["move"]:  # not NaN
        st.markdown(f"That day, the stock moved **{q['move']:+.1f}%** beyond the market.")
    b1, b2 = st.columns([1, 4])
    b1.button("Next →", on_click=next_question, type="primary")
    b2.button("Start over", on_click=restart)

with st.expander("What the labels mean"):
    st.markdown(
        "- **Clinical data**: results from a study in people, including interim or "
        "conference data. Not animal or lab results.\n"
        "- **Regulatory**: an FDA (or other regulator) decision, designation or "
        "submission that the filing is about.\n"
        "- **Presentation**: investor decks and corporate overviews that restate "
        "known information.\n"
        "- **Other**: everything else: financing, hiring, deals, earnings, lab results."
    )
st.caption(
    "These are the 100 filings hand-labelled for the study, blind to the model. "
    "Claude Haiku's answers are the ones it gave when the study ran; across all "
    "100 it matched the hand label 90% of the time."
)

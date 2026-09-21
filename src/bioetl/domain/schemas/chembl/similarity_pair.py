"""Shared complete-pair invariant for public and legacy similarity records."""

from __future__ import annotations

import pandas as pd


def valid_similarity_pairs(frame: pd.DataFrame) -> pd.Series:
    """Require two distinct endpoints in one namespace, never mix namespaces."""
    valid = pd.Series(False, index=frame.index)
    legacy = ("doc_1", "doc_2")
    public = ("publication_id1", "publication_id2")
    if all(name in frame for name in legacy):
        valid |= (
            frame[list(legacy)].notna().all(axis=1)
            & frame[list(legacy)].gt(0).all(axis=1)
            & frame[legacy[0]].ne(frame[legacy[1]])
        ).fillna(False)
    if any(name in frame for name in public):
        public_frame = frame.reindex(columns=list(public))
        present = public_frame.notna().any(axis=1)
        complete = public_frame.notna().all(axis=1) & public_frame[public[0]].ne(
            public_frame[public[1]]
        )
        valid = valid.where(~present, complete)
    return valid.fillna(False)

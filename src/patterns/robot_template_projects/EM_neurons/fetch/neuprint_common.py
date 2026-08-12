"""Shared helpers for the opt-in neuPrint fetch scripts.

These scripts are **not** part of the normal ontology build. They are run
occasionally by a curator (who has a neuPrint token) to (re)generate the
committed evidence caches under ``EM_neurons/data/`` that the offline build
scripts consume.

Design principle: fetch scripts do the *minimum* transformation — connect, run
the query, expand ``roiInfo`` to a long table — and write a committed cache.
All ROI→FBbt mapping, side/laterality logic and aggregation lives in the build
scripts (from committed data), so a change to a mapping file is picked up by a
plain rebuild without re-fetching.

Token: pass ``--token`` or set the ``NEUPRINT_TOKEN`` environment variable.
Requires ``neuprint-python`` (``pip install neuprint-python``).
"""

import csv
import datetime
import os

import pandas as pd


def get_token(cli_token=None):
    """Resolve the neuPrint token from the CLI arg or NEUPRINT_TOKEN."""
    token = cli_token or os.environ.get("NEUPRINT_TOKEN", "")
    if not token:
        raise SystemExit(
            "No neuPrint token. Pass --token or set NEUPRINT_TOKEN "
            "(get one from https://neuprint.janelia.org, Account page)."
        )
    return token


def connect(dataset, token):
    """Return a neuprint.Client for the given dataset (e.g. 'hemibrain:v1.2.1')."""
    import neuprint

    return neuprint.Client("https://neuprint.janelia.org", dataset=dataset, token=token)


def fetch_roiinfo_long(client, types, include_instance=True, drop_column_rois=True):
    """Fetch per-body roiInfo for the given neuron types and return a long table.

    Reproduces the query used by the hemibrain/male_cns/optic_lobe notebooks::

        MATCH (n:Neuron) WHERE n.type IN [...]
        RETURN n.type, n.bodyId, [n.instance,]
               apoc.convert.fromJsonMap(n.roiInfo) AS ROIs

    Returns columns: type, bodyId, [instance,] roi, pre, post — one row per
    (body, roi) pair present in that body's roiInfo. Missing pre/post keys are
    stored as 0 (matching the notebooks' ``fillna(0)``). No ROI→FBbt mapping is
    done here; the build step does that.

    ``drop_column_rois`` (default True) drops optic-lobe column ROIs (name
    contains '_col_'). These are ~2,600 unmappable per-column identifiers that
    both the male_cns and optic_lobe builds discard before any mapping, so
    dropping them here is downstream-identical and keeps the cache lean.
    """
    type_list = sorted({t for t in types if isinstance(t, str) and t})
    instance_sel = "n.instance AS instance, " if include_instance else ""
    query = (
        "MATCH (n:Neuron) WHERE n.type IN %s "
        "RETURN n.type AS type, n.bodyId AS bodyId, %s"
        "apoc.convert.fromJsonMap(n.roiInfo) AS ROIs" % (type_list, instance_sel)
    )
    raw = client.fetch_custom(query)

    rows = []
    for rec in raw.itertuples(index=False):
        roi_info = rec.ROIs or {}
        for roi_np, vals in roi_info.items():
            if drop_column_rois and "_col_" in roi_np:
                continue
            vals = vals or {}
            row = {
                "type": rec.type,
                "bodyId": rec.bodyId,
                "roi": roi_np,
                "pre": vals.get("pre", 0),
                "post": vals.get("post", 0),
            }
            if include_instance:
                row["instance"] = getattr(rec, "instance", "")
            rows.append(row)

    cols = ["type", "bodyId"] + (["instance"] if include_instance else []) + ["roi", "pre", "post"]
    return pd.DataFrame(rows, columns=cols)


def fetch_hemilineage(client, types, out_type_col,
                      hl_expr="coalesce(n.itoleeHl, n.trumanHl)",
                      exists_expr="(EXISTS(n.itoleeHl) OR EXISTS(n.trumanHl))"):
    """Fetch hemilineage per type. ``out_type_col`` is the type column name.

    The hemilineage property differs by generator:
      * male_cns uses coalesce(n.itoleeHl, n.trumanHl)  (the defaults)
      * optic_lobe uses n.hemilineage  (pass hl_expr='n.hemilineage',
        exists_expr='EXISTS(n.hemilineage)')
    Returns columns: <out_type_col>, hemilineage.
    """
    type_list = sorted({t for t in types if isinstance(t, str) and t})
    query = (
        "MATCH (n:Neuron) WHERE n.type IN %s AND %s "
        "RETURN DISTINCT n.type AS %s, %s AS hemilineage"
        % (type_list, exists_expr, out_type_col, hl_expr)
    )
    return client.fetch_custom(query)


def data_path(*parts):
    """Absolute path inside EM_neurons/data/ (created if needed)."""
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(here, "..", "data"))
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, *parts)


PROVENANCE_COLS = ["cache_file", "dataset", "version", "source", "fetched", "n_rows"]


def record_provenance(cache_file, dataset_full, source, n_rows):
    """Upsert a provenance row into EM_neurons/data/PROVENANCE.tsv.

    The cache TSVs themselves are gitignored (they are only needed to
    regenerate the committed component); PROVENANCE.tsv is the committed record
    of which connectome dataset/version each cache was fetched from, and when.
    ``dataset_full`` is a 'name:version' string (e.g. 'hemibrain:v1.2.1'); for
    non-neuprint sources pass e.g. 'flywire-fafb:v783'.
    """
    name, _, version = dataset_full.partition(":")
    path = data_path("PROVENANCE.tsv")
    rows = {}
    if os.path.exists(path):
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                rows[row["cache_file"]] = row
    rows[cache_file] = {
        "cache_file": cache_file, "dataset": name, "version": version,
        "source": source, "fetched": datetime.date.today().isoformat(),
        "n_rows": str(n_rows),
    }
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PROVENANCE_COLS, delimiter="\t")
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])


def project_path(*parts):
    """Absolute path inside the robot_template_projects/ tree (for reading the
    existing curated source TSVs until they are relocated in Phase 2)."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, "..", ".."))
    return os.path.join(root, *parts)

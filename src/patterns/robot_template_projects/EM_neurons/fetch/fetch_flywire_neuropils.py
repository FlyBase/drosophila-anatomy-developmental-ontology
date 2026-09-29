#!/usr/bin/env python3
"""Cache FlyWire neuropil-volume centres for the offline FlyWire soma step.

Opt-in: needs the ``fafbseg`` package (``pip install fafbseg``) and network
access to fetch neuropil meshes. This is the ONLY live call in the FlyWire
generator; all its other inputs (the annotations TSV and the per-neuron synapse
``.feather`` files) are local files. The build step builds the KDTree of
soma-to-neuropil distances from this cache.

Usage:
    python3 fetch_flywire_neuropils.py

Writes: EM_neurons/data/flywire_neuropil_volumes.tsv  (columns: name, x, y, z)
"""

import pandas as pd

import neuprint_common as nc


def main():
    from fafbseg import flywire

    all_neuropils = flywire.get_neuropil_volumes(None)
    neuropils = flywire.get_neuropil_volumes(all_neuropils)

    rows = []
    for vol in neuropils:
        cx, cy, cz = vol.center
        rows.append({"name": vol.name, "x": cx, "y": cy, "z": cz})
    df = pd.DataFrame(rows, columns=["name", "x", "y", "z"])

    out = nc.data_path("flywire_neuropil_volumes.tsv")
    df.to_csv(out, sep="\t", index=False)
    nc.record_provenance("flywire_neuropil_volumes.tsv", "flywire-fafb:v783",
                         "fafbseg flywire.get_neuropil_volumes", len(df))
    print(f"Wrote {len(df)} neuropil-volume centres -> {out}")


if __name__ == "__main__":
    main()

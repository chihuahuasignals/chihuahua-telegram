#!/usr/bin/env python3
"""Validate the workflow files the way GitHub does, before pushing.

PyYAML happily accepts a duplicate key (last one wins); GitHub Actions rejects the whole file
and the run never starts, which looks exactly like "the build is taking a while". That cost one
build cycle on 2026-09-08 — a second `name:` on the job — so check for it here.

Usage: python3 .github/check-workflows.py
"""
import pathlib
import sys

import yaml


class Strict(yaml.SafeLoader):
    pass


def no_duplicate_keys(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicate_keys)

bad = 0
for path in sorted(pathlib.Path(__file__).parent.joinpath("workflows").glob("*.yml")):
    try:
        data = yaml.load(path.read_text(), Loader=Strict)
        jobs = list(data.get("jobs", {}))
        print(f"  ok  {path.name}  jobs: {', '.join(jobs)}")
    except Exception as e:
        bad += 1
        print(f"  !!  {path.name}: {e}")
sys.exit(1 if bad else 0)

#!/usr/bin/env python3
from dataclasses import asdict
import json
from searchleads.acceptance import run_dental_commercial_acceptance
print(json.dumps(asdict(run_dental_commercial_acceptance()),sort_keys=True))

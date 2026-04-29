import json
import os
import re

_PATTERNS = None


def _load_patterns():
    global _PATTERNS
    if _PATTERNS is not None:
        return _PATTERNS

    base = os.path.dirname(__file__)
    yaml_path = os.path.join(base, 'extraction_patterns.yaml')
    json_path = os.path.join(base, 'extraction_patterns.json')

    data = {}
    try:
        # prefer PyYAML if available
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception:
        # fallback to json if yaml not available
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # last-resort: try rudimentary parser for simple YAML (key: 'value') lines
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if ':' in line:
                            k, v = line.split(':', 1)
                            data[k.strip()] = v.strip().strip("'\"")
            except Exception:
                data = {}

    # compile common regexes
    compiled = {}
    for k, v in (data or {}).items():
        if k.endswith('_pattern'):
            try:
                compiled[k] = re.compile(v, re.IGNORECASE)
            except Exception:
                compiled[k] = re.compile(re.escape(v), re.IGNORECASE)
        else:
            compiled[k] = v

    _PATTERNS = compiled
    return _PATTERNS


def get_pattern(key: str):
    pats = _load_patterns()
    return pats.get(key)


def get_compiled(key: str):
    pats = _load_patterns()
    # return compiled regex or None
    return pats.get(key)

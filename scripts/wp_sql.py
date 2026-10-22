"""Read selected tables from a BackWPup MySQL dump without executing SQL."""
import re
from pathlib import Path


def read_tables(path, names):
    sql = Path(path).read_text(encoding='utf-8')
    tables = {name: [] for name in names}
    insert = re.compile(r'INSERT INTO `([^`]+)`\s*\(([^)]+)\) VALUES\s*')
    token = re.compile(r"'((?:[^'\\]|\\.|'')*)'|(-?\d+(?:\.\d+)?)|(NULL)", re.S)
    escapes = {'0': '\0', 'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'Z': '\x1a'}
    for match in insert.finditer(sql):
        name = next((n for n in names if match[1] == 'hal9k_dk_wp_' + n), None)
        if name is None:
            continue
        columns = re.findall(r'`([^`]+)`', match[2])
        pos = match.end()
        while True:
            while sql[pos].isspace() or sql[pos] == ',':
                pos += 1
            if sql[pos] == ';':
                break
            if sql[pos] != '(':
                raise ValueError(f'Expected tuple at {pos}')
            pos += 1
            values = []
            while True:
                while sql[pos].isspace() or sql[pos] == ',':
                    pos += 1
                if sql[pos] == ')':
                    pos += 1
                    break
                value = token.match(sql, pos)
                if not value:
                    raise ValueError(f'Invalid value at {pos}')
                if value[1] is not None:
                    text = value[1].replace("''", "'")
                    values.append(re.sub(r'\\(.)', lambda m: escapes.get(m[1], m[1]), text, flags=re.S))
                elif value[2] is not None:
                    values.append(int(value[2]) if '.' not in value[2] else float(value[2]))
                else:
                    values.append(None)
                pos = value.end()
            if len(values) != len(columns):
                raise ValueError(f'Column mismatch in {name}')
            tables[name].append(dict(zip(columns, values)))
    return tables

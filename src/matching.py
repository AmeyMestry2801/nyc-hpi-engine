import re
import pandas as pd
from rapidfuzz import fuzz


def normalize_address(addr):
    if pd.isna(addr):
        return None
    addr = addr.upper().strip()
    addr = re.sub(r'\s+', ' ', addr)

    replacements = {
        r'\bSTREET\b': 'ST', r'\bAVENUE\b': 'AVE', r'\bBOULEVARD\b': 'BLVD',
        r'\bPLACE\b': 'PL', r'\bROAD\b': 'RD', r'\bDRIVE\b': 'DR',
        r'\bLANE\b': 'LN', r'\bCOURT\b': 'CT', r'\bPARKWAY\b': 'PKWY',
        r'\bSQUARE\b': 'SQ',
    }
    for pattern, repl in replacements.items():
        addr = re.sub(pattern, repl, addr)

    # Strip ordinal suffix ONLY when followed by a street-type word
    street_types = r'(?:ST|AVE|BLVD|PL|RD|DR|LN|CT|PKWY|SQ)'
    addr = re.sub(rf'\b(\d+)(ST|ND|RD|TH)\b(?=\s+{street_types}\b)', r'\1', addr)
    return addr


def split_address(addr):
    if pd.isna(addr):
        return None, None
    if ',' in addr:
        base, unit = addr.split(',', 1)
        return base.strip(), unit.strip()
    match = re.search(r'(?:\b(?:APT|APARTMENT|UNIT)(?![A-Z])\.?|(?<!\w)#)\s*#?\s*\S+', addr)
    if match:
        return addr[:match.start()].strip(), match.group(0).strip()
    return addr.strip(), None


def normalize_unit(unit):
    if pd.isna(unit):
        return None
    unit = str(unit).upper().strip()
    unit = re.sub(r'^(?:(?:APTS?|APARTMENT|UNIT(?!ED\b))\.?\s*)?#?\s*', '', unit)
    return unit.strip() if unit else None


def split_house_number(base_addr):
    if pd.isna(base_addr):
        return None, None
    match = re.match(r'^(\d+[A-Z]?(?:-\d+)?)\s+(.*)$', base_addr)
    if match:
        return match.group(1), match.group(2)
    return None, base_addr


def split_street_number(street):
    if pd.isna(street):
        return None, None
    match = re.search(r'\b(\d+)\b', street)
    if match:
        return match.group(1), street
    return None, street


def street_similarity_match(street_a, street_b, word_threshold=90):
    """Numeric token in street name must match exactly; the rest is fuzzy."""
    num_a, _ = split_street_number(street_a)
    num_b, _ = split_street_number(street_b)
    if num_a is not None or num_b is not None:
        if num_a != num_b:
            return False
    return fuzz.token_sort_ratio(street_a, street_b) >= word_threshold


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry

ORDINAL_WORDS = {'FIRST': '1', 'SECOND': '2', 'THIRD': '3', 'FOURTH': '4', 'FIFTH': '5',
                 'SIXTH': '6', 'SEVENTH': '7', 'EIGHTH': '8', 'NINTH': '9', 'TENTH': '10',
                 'ELEVENTH': '11', 'TWELFTH': '12'}
DIRECTIONS = {'E': 'EAST', 'W': 'WEST', 'N': 'NORTH', 'S': 'SOUTH'}


def normalize_street(street):
    """Canonical form of a street name, for comparison only."""
    if pd.isna(street):
        return None
    tokens = [t.rstrip('.') for t in str(street).upper().split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    if len(tokens) > 1 and tokens[0] in DIRECTIONS:
        tokens[0] = DIRECTIONS[tokens[0]]
    if len(tokens) > 1 and tokens[-1] in DIRECTIONS:
        tokens[-1] = DIRECTIONS[tokens[-1]]
    tokens = [ORDINAL_WORDS.get(t, t) for t in tokens]
    out = ' '.join(tokens)
    return re.sub(r'\b(\d+)(?:ST|ND|RD|TH)\b', r'\1', out)




from itertools import combinations

NO_UNIT = "<NONE>"
_MISSING_UNIT = {'N/A', 'NA', 'NONE', 'NULL', ''}


def clean_unit(addr_unit, apt_number):
    """Unit from the address if present, else from the APARTMENT NUMBER column."""
    for raw in (addr_unit, apt_number):
        u = normalize_unit(raw)
        if u is not None and u not in _MISSING_UNIT:
            return u
    return None


def build_match_groups(df, unit_col, street_col='STREET_NORM'):
    def nid(boro, z, house, unit, street):
        return f"{boro}|{z}|{house}|{unit}|{street}"

    cand = df[df['HOUSE_NUMBER'].notna() & df[street_col].notna()].copy()
    cand['UNIT_KEY'] = cand[unit_col].fillna(NO_UNIT)
    cand['ZIP_KEY'] = cand['ZIP CODE'].where(cand['ZIP CODE'] > 0).fillna(-1).astype(int)

    uf = UnionFind()
    for (boro, z, house, unit), g in cand.groupby(['BOROUGH', 'ZIP_KEY', 'HOUSE_NUMBER', 'UNIT_KEY']):
        streets = g[street_col].unique()
        if len(streets) < 2:
            continue
        for a, b in combinations(streets, 2):
            if street_similarity_match(a, b):
                uf.union(nid(boro, z, house, unit, a), nid(boro, z, house, unit, b))

    keys3 = ['BOROUGH', 'HOUSE_NUMBER', 'UNIT_KEY']
    miss_keys = cand.loc[cand['ZIP_KEY'] == -1, keys3].drop_duplicates()
    sub = cand.merge(miss_keys, on=keys3)
    rescued = ambiguous = 0
    for (boro, house, unit), g in sub.groupby(keys3):
        nodes = g[['ZIP_KEY', street_col]].drop_duplicates()
        miss_nodes = nodes[nodes['ZIP_KEY'] == -1][street_col].tolist()
        real_nodes = [(r[0], r[1]) for r in nodes[nodes['ZIP_KEY'] != -1].itertuples(index=False)]
        for ms in miss_nodes:
            hits = [(z, s) for z, s in real_nodes if street_similarity_match(ms, s)]
            if len(hits) == 1:
                uf.union(nid(boro, -1, house, unit, ms), nid(boro, hits[0][0], house, unit, hits[0][1]))
                rescued += 1
            elif len(hits) > 1:
                ambiguous += 1

    mapping = {n: uf.find(n) for n in list(uf.parent)}
    node = (cand['BOROUGH'].astype(str) + '|' + cand['ZIP_KEY'].astype(str) + '|'
            + cand['HOUSE_NUMBER'] + '|' + cand['UNIT_KEY'] + '|' + cand[street_col])
    groups = pd.Series('ROW|' + df.index.astype(str), index=df.index)
    groups.loc[cand.index] = node.map(mapping).fillna(node)
    return groups, {'candidates': len(cand), 'rescued': rescued, 'ambiguous': ambiguous}


def evaluate_matching(df, unit_col, group_col='MATCH_GROUP'):
    h = df[df['BBL'].notna() & (df['BBL'] != 0)].copy()
    h['UNIT_KEY'] = h[unit_col].fillna(NO_UNIT)

    def n_pairs(sizes):
        s = sizes.astype('int64')
        return int((s * (s - 1) // 2).sum())

    P = n_pairs(h.groupby(group_col).size())
    TP = n_pairs(h.groupby([group_col, 'BBL']).size())
    hb = h[h['HOUSE_NUMBER'].notna()]
    T = n_pairs(hb.groupby(['BBL', 'HOUSE_NUMBER', 'UNIT_KEY']).size())
    return {'rows': len(h), 'P': P, 'TP': TP, 'T': T,
            'precision': round(TP / P, 4), 'recall_fair': round(TP / T, 4)}
"""24 additional coding tasks (code-v2 = 8 original + these). Tuple: (name, description,
hidden tests, reference solution, plausible broken solution). Each is self-tested:
reference must pass and broken must fail (tests/test_code_verifier.py)."""

EXTRA = [
("balanced_brackets",
 "Write balanced_brackets(s) returning True if the brackets ()[]{} in s are balanced and properly nested; other characters are ignored.",
 '''assert balanced_brackets('([]{})')
assert not balanced_brackets('([)]')
assert not balanced_brackets('((')
assert not balanced_brackets(')(')
assert balanced_brackets('a(b)c')''',
 '''def balanced_brackets(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    st = []
    for c in s:
        if c in '([{':
            st.append(c)
        elif c in pairs:
            if not st or st.pop() != pairs[c]:
                return False
    return not st''',
 '''def balanced_brackets(s):
    return s.count('(') == s.count(')') and s.count('[') == s.count(']') and s.count('{') == s.count('}')'''),

("valid_ipv4",
 "Write valid_ipv4(s) returning True only for four dot-separated decimal octets, each 0-255, with no leading zeros (except '0' itself) and no other characters.",
 '''assert valid_ipv4('192.168.1.1')
assert valid_ipv4('0.0.0.0')
assert not valid_ipv4('256.1.1.1')
assert not valid_ipv4('01.2.3.4')
assert not valid_ipv4('1.2.3')
assert not valid_ipv4('1.2.3.4.5')
assert not valid_ipv4('a.b.c.d')
assert not valid_ipv4('1.2.3.-4')''',
 '''def valid_ipv4(s):
    p = s.split('.')
    if len(p) != 4:
        return False
    for x in p:
        if not (x.isascii() and x.isdigit()):
            return False
        if len(x) > 1 and x[0] == '0':
            return False
        if int(x) > 255:
            return False
    return True''',
 '''def valid_ipv4(s):
    p = s.split('.')
    return len(p) == 4 and all(x.isdigit() and int(x) <= 255 for x in p)'''),

("rle_encode",
 "Write rle_encode(s) run-length encoding consecutive repeats as count followed by character, e.g. 'aaabcc' gives '3a1b2c'. The empty string gives ''.",
 '''assert rle_encode('aaabcc') == '3a1b2c'
assert rle_encode('') == ''
assert rle_encode('aabaa') == '2a1b2a'
assert rle_encode('x' * 12) == '12x\'''',
 '''def rle_encode(s):
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(str(j - i) + s[i])
        i = j
    return ''.join(out)''',
 '''from collections import Counter
def rle_encode(s):
    return ''.join(str(n) + c for c, n in Counter(s).items())'''),

("rle_decode",
 "Write rle_decode(s) inverting rle_encode; counts may have several digits, e.g. '10a2b' gives 'aaaaaaaaaabb'.",
 '''assert rle_decode('3a1b2c') == 'aaabcc'
assert rle_decode('12x') == 'x' * 12
assert rle_decode('') == ''
assert rle_decode('10a2b') == 'a' * 10 + 'bb\'''',
 '''import re
def rle_decode(s):
    return ''.join(c * int(n) for n, c in re.findall(r'(\\d+)(\\D)', s))''',
 '''def rle_decode(s):
    return ''.join(s[i + 1] * int(s[i]) for i in range(0, len(s), 2))'''),

("binary_search_left",
 "Write binary_search_left(a, x) returning the index of the leftmost occurrence of x in sorted list a, or -1 if x is absent.",
 '''assert binary_search_left([1, 2, 2, 2, 3], 2) == 1
assert binary_search_left([1, 3, 5], 4) == -1
assert binary_search_left([], 1) == -1
assert binary_search_left([2, 2, 2, 2], 2) == 0
assert binary_search_left([1, 2, 3], 3) == 2''',
 '''def binary_search_left(a, x):
    lo, hi = 0, len(a)
    while lo < hi:
        m = (lo + hi) // 2
        if a[m] < x:
            lo = m + 1
        else:
            hi = m
    return lo if lo < len(a) and a[lo] == x else -1''',
 '''def binary_search_left(a, x):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        m = (lo + hi) // 2
        if a[m] == x:
            return m
        if a[m] < x:
            lo = m + 1
        else:
            hi = m - 1
    return -1'''),

("rotate_matrix",
 "Write rotate_matrix(m) returning a new matrix rotated 90 degrees clockwise (m is a non-empty list of equal-length lists, not necessarily square). Do not modify m.",
 '''assert rotate_matrix([[1, 2], [3, 4]]) == [[3, 1], [4, 2]]
assert rotate_matrix([[1, 2, 3]]) == [[1], [2], [3]]
m = [[1, 2], [3, 4]]
rotate_matrix(m)
assert m == [[1, 2], [3, 4]]''',
 '''def rotate_matrix(m):
    return [list(r) for r in zip(*m[::-1])]''',
 '''def rotate_matrix(m):
    return [list(r) for r in zip(*m)][::-1]'''),

("longest_common_prefix",
 "Write longest_common_prefix(strs) returning the longest common prefix of a list of strings, or '' for an empty list.",
 '''assert longest_common_prefix(['flower', 'flow', 'flight']) == 'fl'
assert longest_common_prefix(['dog', 'car']) == ''
assert longest_common_prefix([]) == ''
assert longest_common_prefix(['abc']) == 'abc'
assert longest_common_prefix(['ab', 'abc', 'a']) == 'a\'''',
 '''def longest_common_prefix(strs):
    if not strs:
        return ''
    p = strs[0]
    for s in strs[1:]:
        while not s.startswith(p):
            p = p[:-1]
    return p''',
 '''def longest_common_prefix(strs):
    return min(strs, key=len) if strs else \'\''''),

("group_anagrams",
 "Write group_anagrams(words) returning a list of groups of anagrams; each group is sorted alphabetically and the groups are ordered by their first word.",
 '''assert group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat']) == [['ate', 'eat', 'tea'], ['bat'], ['nat', 'tan']]
assert group_anagrams([]) == []''',
 '''def group_anagrams(words):
    d = {}
    for w in words:
        d.setdefault(''.join(sorted(w)), []).append(w)
    return sorted(sorted(g) for g in d.values())''',
 '''def group_anagrams(words):
    d = {}
    for w in words:
        d.setdefault(''.join(sorted(w)), []).append(w)
    return list(d.values())'''),

("lru_cache",
 "Write class LRUCache(capacity) with get(key) returning the value or -1, and put(key, value) inserting or updating; when over capacity evict the least recently used key. Both get and put count as a use.",
 '''c = LRUCache(2)
c.put(1, 1)
c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)
assert c.get(2) == -1
c.put(4, 4)
assert c.get(1) == -1
assert c.get(3) == 3
assert c.get(4) == 4
c = LRUCache(1)
c.put(1, 1)
c.put(1, 5)
assert c.get(1) == 5
c.put(2, 2)
assert c.get(1) == -1''',
 '''from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        self.c = capacity
        self.d = OrderedDict()
    def get(self, key):
        if key not in self.d:
            return -1
        self.d.move_to_end(key)
        return self.d[key]
    def put(self, key, value):
        if key in self.d:
            self.d.move_to_end(key)
        self.d[key] = value
        if len(self.d) > self.c:
            self.d.popitem(last=False)''',
 '''from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        self.c = capacity
        self.d = OrderedDict()
    def get(self, key):
        return self.d.get(key, -1)
    def put(self, key, value):
        if key in self.d:
            self.d.move_to_end(key)
        self.d[key] = value
        if len(self.d) > self.c:
            self.d.popitem(last=False)'''),

("word_wrap",
 "Write word_wrap(text, width) splitting text on whitespace and greedily packing words into lines of at most width characters joined by single spaces; a word longer than width gets its own line. Return a list of lines.",
 '''assert word_wrap('the quick brown fox', 10) == ['the quick', 'brown fox']
assert word_wrap('a b c', 1) == ['a', 'b', 'c']
assert word_wrap('supercalifragilistic hi', 5) == ['supercalifragilistic', 'hi']
assert word_wrap('', 5) == []
assert word_wrap('abc def', 7) == ['abc def']''',
 '''def word_wrap(text, width):
    lines, cur = [], ''
    for w in text.split():
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines''',
 '''def word_wrap(text, width):
    lines, cur = [], ''
    for w in text.split():
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) < width:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines'''),

("is_valid_date",
 "Write is_valid_date(s) returning True if s is a real calendar date in 'YYYY-MM-DD' format (4-digit year, 2-digit month and day), handling leap years (divisible by 4, except centuries unless divisible by 400).",
 '''assert is_valid_date('2024-02-29')
assert not is_valid_date('2023-02-29')
assert not is_valid_date('1900-02-29')
assert is_valid_date('2000-02-29')
assert not is_valid_date('2024-13-01')
assert not is_valid_date('2024-04-31')
assert not is_valid_date('2024-1-01')
assert not is_valid_date('abcd-ef-gh')''',
 '''import re
def is_valid_date(s):
    m = re.fullmatch(r'([0-9]{4})-([0-9]{2})-([0-9]{2})', s)
    if not m:
        return False
    y, mo, d = map(int, m.groups())
    if not 1 <= mo <= 12 or d < 1:
        return False
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= days[mo - 1]''',
 '''import re
def is_valid_date(s):
    m = re.fullmatch(r'([0-9]{4})-([0-9]{2})-([0-9]{2})', s)
    if not m:
        return False
    y, mo, d = map(int, m.groups())
    if not 1 <= mo <= 12 or d < 1:
        return False
    leap = y % 4 == 0
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= days[mo - 1]'''),

("collatz_steps",
 "Write collatz_steps(n) returning the number of steps to reach 1 using n/2 if n is even else 3n+1 (0 steps for n=1). Raise ValueError if n < 1.",
 '''assert collatz_steps(1) == 0
assert collatz_steps(6) == 8
assert collatz_steps(27) == 111
try:
    collatz_steps(0)
    assert False
except ValueError:
    pass''',
 '''def collatz_steps(n):
    if n < 1:
        raise ValueError('n must be >= 1')
    c = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        c += 1
    return c''',
 '''def collatz_steps(n):
    c = 0
    while n > 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        c += 1
    return c + 1'''),

("spiral_order",
 "Write spiral_order(m) returning the elements of a (possibly non-square, possibly empty) matrix in clockwise spiral order starting at the top-left.",
 '''assert spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]
assert spiral_order([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]
assert spiral_order([[1], [2], [3]]) == [1, 2, 3]
assert spiral_order([]) == []''',
 '''def spiral_order(m):
    out = []
    m = [list(r) for r in m]
    while m:
        out += m.pop(0)
        m = [list(r) for r in zip(*m)][::-1]
    return out''',
 '''def spiral_order(m):
    return [x for r in m for x in r]'''),

("count_inversions",
 "Write count_inversions(a) returning the number of index pairs i<j with a[i] > a[j] (strictly greater). It must handle 20000 elements quickly.",
 '''assert count_inversions([2, 4, 1, 3, 5]) == 3
assert count_inversions([]) == 0
assert count_inversions([1, 1, 1]) == 0
assert count_inversions([5, 4, 3, 2, 1]) == 10
assert count_inversions(list(range(20000, 0, -1))) == 20000 * 19999 // 2''',
 '''def count_inversions(a):
    def sort(x):
        if len(x) <= 1:
            return x, 0
        m = len(x) // 2
        l, a1 = sort(x[:m])
        r, a2 = sort(x[m:])
        i = j = c = 0
        out = []
        while i < len(l) and j < len(r):
            if l[i] <= r[j]:
                out.append(l[i])
                i += 1
            else:
                out.append(r[j])
                j += 1
                c += len(l) - i
        out += l[i:] + r[j:]
        return out, a1 + a2 + c
    return sort(list(a))[1]''',
 '''def count_inversions(a):
    def sort(x):
        if len(x) <= 1:
            return x, 0
        m = len(x) // 2
        l, a1 = sort(x[:m])
        r, a2 = sort(x[m:])
        i = j = c = 0
        out = []
        while i < len(l) and j < len(r):
            if l[i] < r[j]:
                out.append(l[i])
                i += 1
            else:
                out.append(r[j])
                j += 1
                c += len(l) - i
        out += l[i:] + r[j:]
        return out, a1 + a2 + c
    return sort(list(a))[1]'''),

("median_of_two_sorted",
 "Write median_of_two_sorted(a, b) returning the median (always a float) of the union of two sorted lists; raise ValueError if both are empty.",
 '''assert median_of_two_sorted([1, 3], [2]) == 2.0
assert median_of_two_sorted([1, 2], [3, 4]) == 2.5
assert median_of_two_sorted([], [5]) == 5.0
assert isinstance(median_of_two_sorted([2], [2]), float)
try:
    median_of_two_sorted([], [])
    assert False
except ValueError:
    pass''',
 '''def median_of_two_sorted(a, b):
    m = sorted(a + b)
    if not m:
        raise ValueError('empty')
    n = len(m)
    return float(m[n // 2]) if n % 2 else (m[n // 2 - 1] + m[n // 2]) / 2''',
 '''def median_of_two_sorted(a, b):
    m = sorted(a + b)
    n = len(m)
    return m[n // 2] if n % 2 else (m[n // 2 - 1] + m[n // 2]) // 2'''),

("dedupe_keep_order",
 "Write dedupe_keep_order(xs) removing duplicates while keeping first occurrences in order; elements may be unhashable (for example lists).",
 '''assert dedupe_keep_order([3, 1, 3, 2, 1]) == [3, 1, 2]
assert dedupe_keep_order([[1], [2], [1]]) == [[1], [2]]
assert dedupe_keep_order([]) == []
assert dedupe_keep_order([1, '1', 1.0]) == [1, '1']''',
 '''def dedupe_keep_order(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out''',
 '''def dedupe_keep_order(xs):
    return list(dict.fromkeys(xs))'''),

("chunk",
 "Write chunk(xs, n) splitting list xs into consecutive lists of length n (the last may be shorter). Raise ValueError if n <= 0.",
 '''assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
assert chunk([], 3) == []
assert chunk([1, 2], 5) == [[1, 2]]
for v in (0, -1):
    try:
        chunk([1], v)
        assert False
    except ValueError:
        pass''',
 '''def chunk(xs, n):
    if n <= 0:
        raise ValueError('n must be positive')
    return [xs[i:i + n] for i in range(0, len(xs), n)]''',
 '''def chunk(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]'''),

("topo_sort",
 "Write topo_sort(deps) where deps maps node to a list of prerequisite nodes (every node appears as a key). Return an order with prerequisites first, choosing the alphabetically smallest available node at each step. Raise ValueError on a cycle.",
 '''assert topo_sort({'a': [], 'b': ['a'], 'c': ['a'], 'd': ['b', 'c']}) == ['a', 'b', 'c', 'd']
assert topo_sort({'x': [], 'a': []}) == ['a', 'x']
assert topo_sort({}) == []
try:
    topo_sort({'a': ['b'], 'b': ['a']})
    assert False
except ValueError:
    pass
assert topo_sort({'c': [], 'b': ['c'], 'a': ['c']}) == ['c', 'a', 'b']''',
 '''import heapq
def topo_sort(deps):
    indeg = {n: len(set(p)) for n, p in deps.items()}
    rev = {n: [] for n in deps}
    for n, ps in deps.items():
        for p in set(ps):
            rev[p].append(n)
    h = [n for n, d in indeg.items() if d == 0]
    heapq.heapify(h)
    out = []
    while h:
        n = heapq.heappop(h)
        out.append(n)
        for m in rev[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(h, m)
    if len(out) != len(deps):
        raise ValueError('cycle')
    return out''',
 '''def topo_sort(deps):
    seen, out = set(), []
    def v(n):
        if n in seen:
            return
        seen.add(n)
        for p in deps[n]:
            v(p)
        out.append(n)
    for n in deps:
        v(n)
    return out'''),

("evaluate_rpn",
 "Write evaluate_rpn(tokens) evaluating a reverse Polish expression given as a list of strings containing integers and the operators + - * /; division truncates toward zero. Return an int.",
 '''assert evaluate_rpn(['2', '1', '+', '3', '*']) == 9
assert evaluate_rpn(['4', '13', '5', '/', '+']) == 6
assert evaluate_rpn(['-7', '2', '/']) == -3
assert evaluate_rpn(['7', '-2', '/']) == -3
assert evaluate_rpn(['3']) == 3''',
 '''def evaluate_rpn(tokens):
    st = []
    for t in tokens:
        if len(t) == 1 and t in '+-*/':
            b = st.pop()
            a = st.pop()
            if t == '+':
                st.append(a + b)
            elif t == '-':
                st.append(a - b)
            elif t == '*':
                st.append(a * b)
            else:
                st.append(int(a / b))
        else:
            st.append(int(t))
    return st[0]''',
 '''def evaluate_rpn(tokens):
    st = []
    for t in tokens:
        if len(t) == 1 and t in '+-*/':
            b = st.pop()
            a = st.pop()
            if t == '+':
                st.append(a + b)
            elif t == '-':
                st.append(a - b)
            elif t == '*':
                st.append(a * b)
            else:
                st.append(a // b)
        else:
            st.append(int(t))
    return st[0]'''),

("camel_to_snake",
 "Write camel_to_snake(s) converting CamelCase or camelCase to snake_case while keeping acronyms together: 'HTTPServerError' gives 'http_server_error', 'getHTTPResponse' gives 'get_http_response', 'userID2' gives 'user_id2'.",
 '''assert camel_to_snake('HTTPServerError') == 'http_server_error'
assert camel_to_snake('getHTTPResponse') == 'get_http_response'
assert camel_to_snake('userID2') == 'user_id2'
assert camel_to_snake('simple') == 'simple'
assert camel_to_snake('') == \'\'''',
 '''import re
def camel_to_snake(s):
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\\1_\\2', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\\1_\\2', s)
    return s.lower()''',
 '''def camel_to_snake(s):
    return ''.join('_' + c.lower() if c.isupper() else c for c in s).lstrip('_')'''),

("next_permutation",
 "Write next_permutation(a) returning a new list holding the next lexicographically greater permutation of list a; if a is already the last permutation return the sorted ascending list. Do not modify a.",
 '''assert next_permutation([1, 2, 3]) == [1, 3, 2]
assert next_permutation([3, 2, 1]) == [1, 2, 3]
assert next_permutation([1, 1, 5]) == [1, 5, 1]
assert next_permutation([1, 3, 2]) == [2, 1, 3]
assert next_permutation([]) == []
a = [1, 2, 3]
next_permutation(a)
assert a == [1, 2, 3]''',
 '''def next_permutation(a):
    a = list(a)
    i = len(a) - 2
    while i >= 0 and a[i] >= a[i + 1]:
        i -= 1
    if i < 0:
        return sorted(a)
    j = len(a) - 1
    while a[j] <= a[i]:
        j -= 1
    a[i], a[j] = a[j], a[i]
    a[i + 1:] = reversed(a[i + 1:])
    return a''',
 '''def next_permutation(a):
    a = list(a)
    if len(a) > 1:
        a[-1], a[-2] = a[-2], a[-1]
    return a'''),

("number_to_words",
 "Write number_to_words(n) for integers 0-999 in lowercase English, with a hyphen between tens and ones for 21-99 and no 'and': 0 gives 'zero', 21 gives 'twenty-one', 105 gives 'one hundred five', 342 gives 'three hundred forty-two'. Raise ValueError outside 0-999.",
 '''assert number_to_words(0) == 'zero'
assert number_to_words(13) == 'thirteen'
assert number_to_words(21) == 'twenty-one'
assert number_to_words(40) == 'forty'
assert number_to_words(100) == 'one hundred'
assert number_to_words(105) == 'one hundred five'
assert number_to_words(342) == 'three hundred forty-two'
assert number_to_words(999) == 'nine hundred ninety-nine'
try:
    number_to_words(1000)
    assert False
except ValueError:
    pass''',
 '''ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
def number_to_words(n):
    if not 0 <= n <= 999:
        raise ValueError('out of range')
    if n < 20:
        return ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return TENS[t] + ('-' + ONES[o] if o else '')
    h, r = divmod(n, 100)
    return ONES[h] + ' hundred' + (' ' + number_to_words(r) if r else '')''',
 '''ONES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
def number_to_words(n):
    if not 0 <= n <= 999:
        raise ValueError('out of range')
    if n < 20:
        return ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return TENS[t] + (' ' + ONES[o] if o else '')
    h, r = divmod(n, 100)
    return ONES[h] + ' hundred' + (' ' + number_to_words(r) if r else '')'''),

("parse_csv_line",
 "Write parse_csv_line(line) splitting one CSV line into a list of fields: fields are comma-separated; a field may be wrapped in double quotes to contain commas, and a doubled quote inside a quoted field means a literal quote. An empty line gives [''].",
 '''assert parse_csv_line('a,b,c') == ['a', 'b', 'c']
assert parse_csv_line('a,"b,c",d') == ['a', 'b,c', 'd']
assert parse_csv_line('"say ""hi""",x') == ['say "hi"', 'x']
assert parse_csv_line('') == ['']
assert parse_csv_line('a,,c') == ['a', '', 'c']
assert parse_csv_line(',') == ['', '']''',
 '''def parse_csv_line(line):
    out, cur, q, i = [], [], False, 0
    while i < len(line):
        c = line[i]
        if q:
            if c == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    cur.append('"')
                    i += 1
                else:
                    q = False
            else:
                cur.append(c)
        elif c == '"':
            q = True
        elif c == ',':
            out.append(''.join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append(''.join(cur))
    return out''',
 '''def parse_csv_line(line):
    return line.split(',')'''),

("min_coins",
 "Write min_coins(coins, amount) returning the fewest coins (unlimited supply of each denomination) that sum to amount, or -1 if impossible; amount 0 gives 0.",
 '''assert min_coins([1, 5, 10, 25], 63) == 6
assert min_coins([1, 3, 4], 6) == 2
assert min_coins([2], 3) == -1
assert min_coins([5], 0) == 0
assert min_coins([186, 419, 83, 408], 6249) == 20''',
 '''def min_coins(coins, amount):
    INF = float('inf')
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return -1 if dp[amount] == INF else dp[amount]''',
 '''def min_coins(coins, amount):
    n = 0
    for c in sorted(coins, reverse=True):
        n += amount // c
        amount %= c
    return n if amount == 0 else -1'''),
]

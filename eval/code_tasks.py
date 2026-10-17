"""Coding proving ground: each task has hidden asserts, a reference solution (verifier
self-test) and a plausible broken solution. TASKSET: code-v1. Extend to 30+ before
drawing conclusions; 8 tasks is a smoke test."""
from caa.core.schemas import Task

SUFFIX = " Reply with only one ```python code block."

_SPECS = [
 ("fizzbuzz", "Write fizzbuzz(n) returning a list of strings for 1..n: 'Fizz' for multiples of 3, 'Buzz' for 5, 'FizzBuzz' for both, else the number as a string.",
  "assert fizzbuzz(5)==['1','2','Fizz','4','Buzz']\nassert fizzbuzz(15)[-1]=='FizzBuzz'\nassert fizzbuzz(0)==[]",
  "def fizzbuzz(n):\n    o=[]\n    for i in range(1,n+1):\n        s=('Fizz' if i%3==0 else '')+('Buzz' if i%5==0 else '')\n        o.append(s or str(i))\n    return o",
  "def fizzbuzz(n):\n    return [str(i) for i in range(1,n+1)]"),
 ("is_palindrome", "Write is_palindrome(s) that ignores case and non-alphanumeric characters.",
  "assert is_palindrome('A man, a plan, a canal: Panama')\nassert not is_palindrome('hello')\nassert is_palindrome('')",
  "def is_palindrome(s):\n    t=[c.lower() for c in s if c.isalnum()]\n    return t==t[::-1]",
  "def is_palindrome(s):\n    return s==s[::-1]"),
 ("merge_intervals", "Write merge_intervals(iv) taking a list of [start,end] lists (unsorted) and returning merged overlapping or touching intervals sorted by start.",
  "assert merge_intervals([[8,10],[1,3],[2,6]])==[[1,6],[8,10]]\nassert merge_intervals([[1,4],[4,5]])==[[1,5]]\nassert merge_intervals([])==[]",
  "def merge_intervals(iv):\n    out=[]\n    for s,e in sorted(iv):\n        if out and s<=out[-1][1]:\n            out[-1][1]=max(out[-1][1],e)\n        else:\n            out.append([s,e])\n    return out",
  "def merge_intervals(iv):\n    out=[]\n    for s,e in iv:\n        if out and s<out[-1][1]:\n            out[-1][1]=max(out[-1][1],e)\n        else:\n            out.append([s,e])\n    return out"),
 ("roman_to_int", "Write roman_to_int(s) converting a valid Roman numeral to an integer.",
  "assert roman_to_int('III')==3\nassert roman_to_int('IV')==4\nassert roman_to_int('MCMXCIV')==1994",
  "def roman_to_int(s):\n    v={'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}\n    t=0\n    for i,c in enumerate(s):\n        if i+1<len(s) and v[c]<v[s[i+1]]:\n            t-=v[c]\n        else:\n            t+=v[c]\n    return t",
  "def roman_to_int(s):\n    v={'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}\n    return sum(v[c] for c in s)"),
 ("two_sum", "Write two_sum(nums, target) returning a tuple (i, j) with i<j and nums[i]+nums[j]==target, or None if no pair exists.",
  "assert two_sum([2,7,11,15],9)==(0,1)\nassert two_sum([3,3],6)==(0,1)\nassert two_sum([1,2],10) is None",
  "def two_sum(nums,target):\n    seen={}\n    for j,x in enumerate(nums):\n        if target-x in seen:\n            return (seen[target-x],j)\n        seen[x]=j\n    return None",
  "def two_sum(nums,target):\n    for i in range(len(nums)):\n        for j in range(len(nums)):\n            if nums[i]+nums[j]==target:\n                return (i,j)\n    return None"),
 ("flatten", "Write flatten(x) that flattens arbitrarily nested lists into one flat list, preserving order.",
  "assert flatten([1,[2,[3,[4]]],5])==[1,2,3,4,5]\nassert flatten([])==[]\nassert flatten([[],[[]]])==[]",
  "def flatten(x):\n    o=[]\n    for i in x:\n        o.extend(flatten(i) if isinstance(i,list) else [i])\n    return o",
  "def flatten(x):\n    o=[]\n    for i in x:\n        o.extend(i if isinstance(i,list) else [i])\n    return o"),
 ("parse_duration", "Write parse_duration(s) converting strings like '1h30m15s', '45s', '2h' to total seconds (int). Units are h, m, s in any subset, in that order.",
  "assert parse_duration('1h30m15s')==5415\nassert parse_duration('45s')==45\nassert parse_duration('2h')==7200",
  "import re\ndef parse_duration(s):\n    m=re.fullmatch(r'(?:(\\d+)h)?(?:(\\d+)m)?(?:(\\d+)s)?',s)\n    h,mi,se=(int(g or 0) for g in m.groups())\n    return h*3600+mi*60+se",
  "def parse_duration(s):\n    return int(s[:-1])"),
 ("top_k_frequent", "Write top_k_frequent(words, k) returning the k most frequent words; ties broken alphabetically.",
  "assert top_k_frequent(['b','a','b','c','a','b'],2)==['b','a']\nassert top_k_frequent(['x','y'],2)==['x','y']\nassert top_k_frequent([],3)==[]\nassert top_k_frequent(['b','a'],1)==['a']",
  "from collections import Counter\ndef top_k_frequent(words,k):\n    c=Counter(words)\n    return sorted(c,key=lambda w:(-c[w],w))[:k]",
  "from collections import Counter\ndef top_k_frequent(words,k):\n    return [w for w,_ in Counter(words).most_common(k)]"),
]

from .code_specs_extra import EXTRA
_SPECS = _SPECS + EXTRA
TASKSET_VERSION = "code-v2"

REFERENCE = {n: "```python\n" + ref + "\n```" for n, _, _, ref, _ in _SPECS}
BROKEN = {n: "```python\n" + bad + "\n```" for n, _, _, _, bad in _SPECS}


def build_code_tasks() -> list[Task]:
    return [Task(intent=desc + SUFFIX, task_type="code", meta={"tests": tests, "name": n, "lang": "python"})
            for n, desc, tests, _, _ in _SPECS]

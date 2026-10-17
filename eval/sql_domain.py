"""SQL domain: model writes one SELECT; the checker EXECUTES it on a fixed in-memory SQLite DB
and compares rows with a reference query. Objective, deterministic, offline.
Read-only: single SELECT/WITH statements only, row cap, op-count timeout."""
from __future__ import annotations
import re
import sqlite3
from caa.core.schemas import Task

SETUP = """
CREATE TABLE departments(id INTEGER, name TEXT);
CREATE TABLE employees(id INTEGER, name TEXT, dept_id INTEGER, salary INTEGER, hire_year INTEGER);
CREATE TABLE orders(id INTEGER, customer TEXT, amount INTEGER, year INTEGER);
INSERT INTO departments VALUES (1,'Eng'),(2,'Sales'),(3,'HR'),(4,'Legal');
INSERT INTO employees VALUES (1,'Ana',1,120,2019),(2,'Ben',1,100,2020),(3,'Cai',1,120,2021),
 (4,'Dee',2,80,2019),(5,'Eli',2,90,2022),(6,'Fay',3,70,2020),(7,'Gus',2,85,2020),(8,'Hal',3,70,2021);
INSERT INTO orders VALUES (1,'acme',300,2023),(2,'acme',400,2024),(3,'bolt',200,2023),
 (4,'bolt',150,2023),(5,'cyan',900,2024),(6,'acme',100,2024);
"""
SCHEMA = ("Schema: departments(id,name), employees(id,name,dept_id,salary,hire_year), "
          "orders(id,customer,amount,year).")

# (name, question, ordered, reference SQL, plausible broken SQL)
SPECS = [
 ("avg_salary_by_dept", "average salary per department name rounded to 2 decimals, ordered by department name; columns name, avg_salary.", True,
  "SELECT d.name, ROUND(AVG(e.salary),2) AS avg_salary FROM employees e JOIN departments d ON d.id=e.dept_id GROUP BY d.name ORDER BY d.name",
  "SELECT e.dept_id, ROUND(AVG(e.salary),2) FROM employees e GROUP BY e.dept_id ORDER BY e.dept_id"),
 ("above_dept_avg", "names of employees earning more than their own department's average salary, ordered by name.", True,
  "SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id=e.dept_id) ORDER BY name",
  "SELECT name FROM employees WHERE salary > (SELECT AVG(salary) FROM employees) ORDER BY name"),
 ("empty_departments", "names of departments that have no employees.", False,
  "SELECT d.name FROM departments d LEFT JOIN employees e ON e.dept_id=d.id WHERE e.id IS NULL",
  "SELECT d.name FROM departments d JOIN employees e ON e.dept_id=d.id WHERE e.id IS NULL"),
 ("second_highest_salary", "the second highest DISTINCT salary as a single value.", False,
  "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees)",
  "SELECT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1"),
 ("busy_hire_years", "hire years in which more than one employee was hired, with the count; columns hire_year, n; ordered by hire_year.", True,
  "SELECT hire_year, COUNT(*) AS n FROM employees GROUP BY hire_year HAVING COUNT(*) > 1 ORDER BY hire_year",
  "SELECT hire_year, COUNT(*) AS n FROM employees WHERE COUNT(*) > 1 GROUP BY hire_year ORDER BY hire_year"),
 ("top_earner_per_dept", "for each department the names of the employees with the highest salary in that department (ties included); columns dept_id, name; ordered by dept_id, name.", True,
  "SELECT dept_id, name FROM employees e WHERE salary = (SELECT MAX(salary) FROM employees WHERE dept_id=e.dept_id) ORDER BY dept_id, name",
  "SELECT dept_id, name FROM employees WHERE salary = (SELECT MAX(salary) FROM employees) ORDER BY dept_id, name"),
 ("big_customers", "customers whose total order amount exceeds 500; columns customer, total; ordered by total descending.", True,
  "SELECT customer, SUM(amount) AS total FROM orders GROUP BY customer HAVING SUM(amount) > 500 ORDER BY total DESC",
  "SELECT customer, amount AS total FROM orders WHERE amount > 500 ORDER BY total DESC"),
 ("running_total", "each order id with the running total of amount ordered by id; columns id, running; ordered by id.", True,
  "SELECT id, SUM(amount) OVER (ORDER BY id) AS running FROM orders ORDER BY id",
  "SELECT id, SUM(amount) AS running FROM orders GROUP BY id ORDER BY id"),
 ("customers_both_years", "customers that placed orders in BOTH 2023 and 2024.", False,
  "SELECT customer FROM orders GROUP BY customer HAVING COUNT(DISTINCT year)=2",
  "SELECT DISTINCT customer FROM orders WHERE year IN (2023, 2024)"),
 ("earliest_hires", "names of all employees hired in the earliest hire year, ordered by name.", True,
  "SELECT name FROM employees WHERE hire_year=(SELECT MIN(hire_year) FROM employees) ORDER BY name",
  "SELECT name FROM employees ORDER BY hire_year LIMIT 1"),
]

_FENCE = re.compile(r"```(?:sql)?\s*\n(.*?)```", re.S)


def extract_sql(output: str) -> str:
    m = _FENCE.search(output)
    return (m.group(1) if m else output).strip().rstrip(";")


def run_sql(sql: str, max_rows: int = 1000, max_ops: int = 2_000_000):
    """Execute one read-only statement on a fresh DB. Returns (rows, error)."""
    if ";" in sql or not re.match(r"(?is)^\s*(select|with)\b", sql):
        return None, "only a single SELECT/WITH statement is allowed"
    db = sqlite3.connect(":memory:")
    db.executescript(SETUP)
    db.execute("PRAGMA query_only=ON")
    ops = [0]

    def guard():
        ops[0] += 1
        return 1 if ops[0] > max_ops // 1000 else 0
    db.set_progress_handler(guard, 1000)
    try:
        return db.execute(sql).fetchmany(max_rows), None
    except Exception as e:  # sqlite3.Error and interrupts
        return None, f"{type(e).__name__}: {e}"
    finally:
        db.close()


def _norm(rows):
    return [tuple(round(x, 4) if isinstance(x, float) else x for x in r) for r in rows]


def build_sql_tasks() -> list[Task]:
    tasks = []
    for name, question, ordered, ref, bad in SPECS:
        expected, err = run_sql(ref)
        assert err is None, (name, err)
        expected = _norm(expected)

        def check(output, expected=expected, ordered=ordered):
            rows, err = run_sql(extract_sql(output))
            if err:
                return "fail", f"SQL error: {err}"
            got = _norm(rows)
            ok = got == expected if ordered else sorted(map(repr, got)) == sorted(map(repr, expected))
            if ok:
                return "pass", "rows match"
            return "fail", f"result mismatch: expected {expected[:3]}... ({len(expected)} rows), got {got[:3]}... ({len(got)} rows)"

        tasks.append(Task(intent=f"{SCHEMA} Write one SQLite SELECT query returning the {question} Reply with only one ```sql block.",
                          task_type="sql", meta={"check": check, "name": name}))
    return tasks


REFERENCE = {n: f"```sql\n{r}\n```" for n, _, _, r, _ in SPECS}
BROKEN = {n: f"```sql\n{b}\n```" for n, _, _, _, b in SPECS}

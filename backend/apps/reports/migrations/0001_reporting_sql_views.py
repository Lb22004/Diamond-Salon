# Generated for Diamond Salón — P3 Reporting SQL Views (schema.sql lines 569-602)
from django.db import migrations


CREATE_VIEWS_SQL = """
DROP VIEW IF EXISTS accounting_v_journal_book;
CREATE VIEW accounting_v_journal_book AS
SELECT e.id AS entry_id,
       e.entry_number,
       e.entry_date,
       e.period_id,
       e.entry_type,
       e.status,
       e.description AS entry_description,
       l.line_no,
       a.code AS account_code,
       a.name AS account_name,
       l.description AS line_description,
       l.debit,
       l.credit
FROM accounting_journal_entry e
JOIN accounting_journal_entry_line l ON l.entry_id = e.id
JOIN accounting_account a ON a.id = l.account_id
WHERE e.status IN ('POSTED','REVERSED');

DROP VIEW IF EXISTS accounting_v_general_ledger;
CREATE VIEW accounting_v_general_ledger AS
SELECT l.account_id,
       a.code AS account_code,
       a.name AS account_name,
       a.nature,
       e.id AS entry_id,
       e.entry_number,
       e.entry_date,
       e.period_id,
       e.entry_type,
       COALESCE(NULLIF(l.description, ''), e.description) AS concept,
       l.debit,
       l.credit,
       SUM(CASE WHEN a.nature = 'DEBIT' THEN l.debit - l.credit ELSE l.credit - l.debit END)
           OVER (PARTITION BY l.account_id
                 ORDER BY e.entry_date, e.entry_number, e.id, l.line_no
                 ROWS UNBOUNDED PRECEDING) AS running_balance
FROM accounting_journal_entry_line l
JOIN accounting_journal_entry e ON e.id = l.entry_id
JOIN accounting_account a ON a.id = l.account_id
WHERE e.status IN ('POSTED','REVERSED');

DROP VIEW IF EXISTS accounting_v_trial_balance;
CREATE VIEW accounting_v_trial_balance AS
SELECT e.period_id,
       a.id AS account_id,
       a.code,
       a.name,
       a.nature,
       SUM(l.debit) AS debit_total,
       SUM(l.credit) AS credit_total,
       SUM(CASE WHEN a.nature = 'DEBIT' THEN l.debit - l.credit ELSE l.credit - l.debit END) AS net_movement
FROM accounting_journal_entry_line l
JOIN accounting_journal_entry e ON e.id = l.entry_id
JOIN accounting_account a ON a.id = l.account_id
WHERE e.status IN ('POSTED','REVERSED')
GROUP BY e.period_id, a.id, a.code, a.name, a.nature;
"""

DROP_VIEWS_SQL = """
DROP VIEW IF EXISTS accounting_v_trial_balance;
DROP VIEW IF EXISTS accounting_v_general_ledger;
DROP VIEW IF EXISTS accounting_v_journal_book;
"""


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounting", "0001_initial_and_seed"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_VIEWS_SQL, reverse_sql=DROP_VIEWS_SQL),
    ]

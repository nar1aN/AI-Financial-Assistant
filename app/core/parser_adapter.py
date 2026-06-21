from parsers import auto_parse

transactions = auto_parse("../../w.pdf", bank_id="tbank")

for t in transactions:
    print(t.date_op, t.amount, t.currency, t.description)
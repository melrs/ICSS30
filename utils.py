from datetime import datetime

def is_valid_date(date_var):
    try:
        datetime.strptime(date_var, "%d/%m/%Y")
        return True
    except ValueError:
        return False
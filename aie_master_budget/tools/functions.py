def safe_getattr(obj, attr, default=''):
    item = getattr(obj, attr, default)
    return item if item else default

def build_master_data_table_name(master_data_item):
    return f"{safe_getattr(master_data_item, 'name')} - {safe_getattr(master_data_item, 'description')}"
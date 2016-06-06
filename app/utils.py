def validate(data, required_fields):
    """Validate if all required_fields are in the given data dictionary"""
    if all(field in data for field in required_fields):
        return True
    return False
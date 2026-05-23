class Fintech:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Fintech Company: {self.name}"

    def __repr__(self):
        return f"Fintech(name={self.name!r})"

    def __eq__(self, other):
        if isinstance(other, Fintech):
            return self.name == other.name
        return False


"""
The __str__ dunder method allows you to intercept that behavior and define a clean, 
human-readable string representation of the object instead.
"""
    


class upay(Fintech):
    def __init__(self, name, parent_company, market_share):
        super().__init__(name)
        self.parent_company = parent_company
        self.market_share = market_share

    def __str__(self):
        return f"upay: {self.name}, Parent: {self.parent_company}, Market Share: {self.market_share}"

    def __repr__(self):
        return (f"upay(name={self.name!r}, parent_company={self.parent_company!r}, "
                f"market_share={self.market_share!r})")

    def __eq__(self, other):
        if isinstance(other, upay):
            return (self.name == other.name and
                    self.parent_company == other.parent_company and
                    self.market_share == other.market_share)
        return False

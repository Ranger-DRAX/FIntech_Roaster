
from abc import ABC, abstractmethod

class Fintech:
    def __init__(self,name):
        self.name=name

    def industry(self):
        return f"{self.name} is the growing tech industry!!" 


class upay(Fintech):
    def __init__(self, name,parent_company,market_share):
        super().__init__(name) #call the parent constructor
        self.parent_company=parent_company
        self.market_share=market_share


    #overriding the industry method
    def industry(self):
        return f"{self.name} is a leading fintech company under {self.parent_company}!!"


    def marketshare(self):
        return f"{self.name} holds the {self.market_share} in this country"
    



# 1. ABSTRACTION: Creating a blueprint for all Fintech institutions.
class FinancialRegulations(ABC):
    @abstractmethod
    def process_compliance_check(self):
        pass


class Fintech(FinancialRegulations):
    def __init__(self, name):
        self.name = name

    def industry(self):
        return f"{self.name} is in the growing tech industry!!"
    
    # Implementing the abstract method
    def process_compliance_check(self):
        return f"[{self.name}] Compliance check passed against central bank regulations."


class upay(Fintech):
    def __init__(self, name, parent_company, market_share, initial_reserve):
        super().__init__(name)
        self.parent_company = parent_company
        self.market_share = market_share
        
        # 2. ENCAPSULATION: Hiding sensitive financial data.
        self.__vault_reserve = initial_reserve 

    # Overriding the industry method (Polymorphism)
    def industry(self):
        return f"{self.name} is a leading fintech company under {self.parent_company}!!"

    def marketshare(self):
        return f"{self.name} holds {self.market_share} market share in this country."

    # ENCAPSULATION (Getter/Setter): Controlled access to private data
    def get_vault_reserve(self):
        # Imagine adding an authorization check here
        return f"Access Granted: Vault Balance is ${self.__vault_reserve:,}"

    def inject_liquidity(self, amount):
        if amount > 0:
            self.__vault_reserve += amount
            return f"Successfully added ${amount:,} to reserve."
        return "Invalid amount."


# 3. POLYMORPHISM (Duck Typing / Interface Flexibility)
class TraditionalBank:
    def __init__(self, name):
        self.name = name
        
    def industry(self):
        return f"{self.name} is a traditional brick-and-mortar legacy bank."


# Polymorphic function that accepts any object with an 'industry' method
def display_market_status(financial_entity):
    print(financial_entity.industry())


# --- Execution ---

# Initialize Upay with name, parent, share, and private vault reserve
mfsCompany = upay("Upay", "UCB", "8%", 5000000)
legacyBank = TraditionalBank("UCB")

print("--- 1. Testing Inherited & Overridden Methods ---")
print(mfsCompany.industry())
print(mfsCompany.marketshare())

print("\n--- 2. Testing Abstraction ---")
print(mfsCompany.process_compliance_check())

print("\n--- 3. Testing Encapsulation ---")
# print(mfsCompany.__vault_reserve) # This line would throw an AttributeError (Hidden!)
print(mfsCompany.get_vault_reserve()) 
print(mfsCompany.inject_liquidity(1500000))
print(mfsCompany.get_vault_reserve())

print("\n--- 4. Testing Polymorphism (Interface Flexibility) ---")
display_market_status(mfsCompany)
display_market_status(legacyBank)
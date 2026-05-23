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
    

mfsCompany = upay("Upay","UCB","8%")
print(mfsCompany.industry())

